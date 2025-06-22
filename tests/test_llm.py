"""Tests for the LLM module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from ombm.llm import LLMError, LLMService, generate_title_desc
from ombm.models import LLMMetadata, ScrapeResult


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps(
        {
            "name": "Test Article - Python Tutorial",
            "description": "A comprehensive tutorial covering Python basics, data structures, and best practices for beginners",
        }
    )
    response.usage.total_tokens = 150
    return response


@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return """
    This is a comprehensive guide to Python programming.
    We'll cover variables, functions, classes, and more.
    Perfect for beginners who want to learn programming.
    """


class TestLLMService:
    """Test LLM service functionality."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance with mock API key."""
        return LLMService(api_key="test-key", model="gpt-4o", timeout=10.0)

    @pytest.mark.asyncio
    async def test_successful_title_desc_generation(
        self, llm_service, mock_openai_response, sample_content
    ):
        """Test successful title and description generation."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_openai_response

            result = await llm_service.title_desc(
                url="https://example.com/python-tutorial",
                text=sample_content,
                original_title="Learn Python",
            )

            # Verify result
            assert isinstance(result, LLMMetadata)
            assert result.url == "https://example.com/python-tutorial"
            assert result.name == "Test Article - Python Tutorial"
            assert (
                result.description
                == "A comprehensive tutorial covering Python basics, data structures, and best practices for beginners"
            )
            assert result.tokens_used == 150

            # Verify API call
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "gpt-4o"
            assert call_args[1]["max_tokens"] == 300
            assert call_args[1]["temperature"] == 0.3
            assert call_args[1]["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_content_truncation(self, llm_service, mock_openai_response):
        """Test that long content is properly truncated."""
        # Create content longer than 8000 chars
        long_content = "A" * 10000

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_openai_response

            await llm_service.title_desc(
                url="https://example.com", text=long_content, original_title="Test"
            )

            # Check that the prompt contains truncated content
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            # Should contain the truncation indicator
            assert "..." in prompt

    @pytest.mark.asyncio
    async def test_field_length_enforcement(self, llm_service, sample_content):
        """Test that title and description are truncated to max length."""
        # Create response with very long fields
        long_response = MagicMock()
        long_response.choices = [MagicMock()]
        long_response.choices[0].message.content = json.dumps(
            {
                "name": "A" * 150,  # Longer than 80 char limit
                "description": "B" * 300,  # Longer than 200 char limit
            }
        )
        long_response.usage.total_tokens = 100

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = long_response

            result = await llm_service.title_desc(
                url="https://example.com", text=sample_content
            )

            # Verify truncation
            assert len(result.name) == 80
            assert len(result.description) == 200
            assert result.name == "A" * 80
            assert result.description == "B" * 200

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, llm_service, sample_content):
        """Test handling of invalid JSON response."""
        bad_response = MagicMock()
        bad_response.choices = [MagicMock()]
        bad_response.choices[0].message.content = "Not valid JSON"
        bad_response.usage.total_tokens = 50

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = bad_response

            with pytest.raises(LLMError, match="Invalid JSON response"):
                await llm_service.title_desc(
                    url="https://example.com", text=sample_content
                )

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, llm_service, sample_content):
        """Test handling of response missing required fields."""
        incomplete_response = MagicMock()
        incomplete_response.choices = [MagicMock()]
        incomplete_response.choices[0].message.content = json.dumps(
            {
                "name": "Test Title"
                # Missing "description" field
            }
        )
        incomplete_response.usage.total_tokens = 50

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = incomplete_response

            with pytest.raises(LLMError, match="Response missing required fields"):
                await llm_service.title_desc(
                    url="https://example.com", text=sample_content
                )

    @pytest.mark.asyncio
    async def test_empty_response(self, llm_service, sample_content):
        """Test handling of empty response."""
        empty_response = MagicMock()
        empty_response.choices = [MagicMock()]
        empty_response.choices[0].message.content = None

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = empty_response

            with pytest.raises(LLMError, match="Empty response from OpenAI"):
                await llm_service.title_desc(
                    url="https://example.com", text=sample_content
                )

    @pytest.mark.asyncio
    async def test_rate_limit_retry(
        self, llm_service, mock_openai_response, sample_content
    ):
        """Test retry logic for rate limiting."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create a mock response for the error
            mock_response = MagicMock()
            mock_response.request = MagicMock()

            # First call raises rate limit, second succeeds
            mock_create.side_effect = [
                openai.RateLimitError(
                    "Rate limit exceeded", response=mock_response, body=None
                ),
                mock_openai_response,
            ]

            # Should succeed after retry
            result = await llm_service.title_desc(
                url="https://example.com", text=sample_content
            )

            assert isinstance(result, LLMMetadata)
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_max_retries_exceeded(self, llm_service, sample_content):
        """Test that rate limit retries eventually fail."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create a mock response for the error
            mock_response = MagicMock()
            mock_response.request = MagicMock()

            # Always raise rate limit error
            mock_create.side_effect = openai.RateLimitError(
                "Rate limit exceeded", response=mock_response, body=None
            )

            with pytest.raises(LLMError, match="Rate limit exceeded after 3 attempts"):
                await llm_service.title_desc(
                    url="https://example.com", text=sample_content
                )

            assert mock_create.call_count == 3  # Should try 3 times

    @pytest.mark.asyncio
    async def test_timeout_retry(
        self, llm_service, mock_openai_response, sample_content
    ):
        """Test retry logic for timeouts."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # First call times out, second succeeds
            mock_create.side_effect = [
                openai.APITimeoutError("Request timed out"),
                mock_openai_response,
            ]

            result = await llm_service.title_desc(
                url="https://example.com", text=sample_content
            )

            assert isinstance(result, LLMMetadata)
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_api_error_no_retry(self, llm_service, sample_content):
        """Test that API errors don't trigger retries."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create a mock request for the error
            mock_request = MagicMock()
            mock_create.side_effect = openai.APIError(
                "Invalid request", request=mock_request, body=None
            )

            with pytest.raises(LLMError, match="OpenAI API error"):
                await llm_service.title_desc(
                    url="https://example.com", text=sample_content
                )

            assert mock_create.call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_title_desc_from_scrape_result(
        self, llm_service, mock_openai_response
    ):
        """Test convenience method for generating metadata from ScrapeResult."""
        scrape_result = ScrapeResult(
            url="https://example.com/article",
            text="This is article content about Python programming.",
            html_title="Python Article",
        )

        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_openai_response

            result = await llm_service.title_desc_from_scrape_result(scrape_result)

            assert isinstance(result, LLMMetadata)
            assert result.url == scrape_result.url

            # Verify the prompt was rendered with scrape result data
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert scrape_result.url in prompt
            assert scrape_result.text in prompt
            assert scrape_result.html_title in prompt

    @pytest.mark.asyncio
    async def test_template_rendering(self, llm_service, sample_content):
        """Test that Jinja template is properly rendered."""
        with patch.object(
            llm_service.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock()
            mock_create.return_value.choices = [MagicMock()]
            mock_create.return_value.choices[0].message.content = json.dumps(
                {"name": "Test", "description": "Test description"}
            )
            mock_create.return_value.usage.total_tokens = 100

            await llm_service.title_desc(
                url="https://test.com",
                text=sample_content,
                original_title="Original Title",
            )

            # Check that template variables were substituted
            call_args = mock_create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert "https://test.com" in prompt
            assert "Original Title" in prompt
            assert sample_content.strip() in prompt


class TestConvenienceFunction:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_generate_title_desc_function(
        self, mock_openai_response, sample_content
    ):
        """Test the convenience generate_title_desc function."""
        with patch("ombm.llm.LLMService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.title_desc = AsyncMock(
                return_value=LLMMetadata(
                    url="https://example.com",
                    name="Generated Title",
                    description="Generated description",
                    tokens_used=100,
                )
            )
            mock_service_class.return_value = mock_service

            result = await generate_title_desc(
                url="https://example.com",
                text=sample_content,
                original_title="Original",
                api_key="test-key",
                model="gpt-4",
            )

            # Verify service was created with correct parameters
            mock_service_class.assert_called_once_with(
                api_key="test-key", model="gpt-4"
            )

            # Verify title_desc was called
            mock_service.title_desc.assert_called_once_with(
                "https://example.com", sample_content, "Original"
            )

            # Verify result
            assert isinstance(result, LLMMetadata)
            assert result.name == "Generated Title"


class TestLLMServiceInitialization:
    """Test LLM service initialization and configuration."""

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        service = LLMService(api_key="test-key", model="gpt-3.5-turbo", timeout=60.0)

        assert service.model == "gpt-3.5-turbo"
        assert service.timeout == 60.0
        assert service.max_retries == 3

    def test_initialization_without_api_key(self):
        """Test initialization without API key (uses environment variable)."""
        with patch("ombm.llm.openai.AsyncOpenAI") as mock_openai:
            service = LLMService(model="gpt-4", max_retries=5)

            assert service.model == "gpt-4"
            assert service.max_retries == 5
            mock_openai.assert_called_once()

    def test_template_loading(self):
        """Test that Jinja template is properly loaded."""
        service = LLMService(api_key="test-key")

        # Should load template on first access
        template = service._get_title_desc_template()
        assert template is not None

        # Should reuse cached template
        template2 = service._get_title_desc_template()
        assert template is template2
