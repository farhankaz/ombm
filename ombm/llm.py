"""
LLM integration for OMBM.

This module provides async integration with OpenAI for generating
semantic titles and descriptions for bookmarks.
"""

import asyncio
import json
import logging
from pathlib import Path

import openai
from jinja2 import Environment, FileSystemLoader, Template

from .models import LLMMetadata, ScrapeResult

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMService:
    """Service for interacting with OpenAI LLM for bookmark metadata generation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize LLM service.

        Args:
            api_key: OpenAI API key (if None, uses environment variable)
            model: OpenAI model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize OpenAI client
        if api_key:
            self.client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout)
        else:
            # Will use OPENAI_API_KEY environment variable
            self.client = openai.AsyncOpenAI(timeout=timeout)

        # Initialize Jinja environment for templates
        template_dir = Path(__file__).parent / "prompts"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

        # Load the title/description template
        self._title_desc_template: Template | None = None
        self._taxonomy_template: Template | None = None

    def _get_title_desc_template(self) -> Template:
        """Get the title/description template, loading it if necessary."""
        if self._title_desc_template is None:
            self._title_desc_template = self.jinja_env.get_template("title_desc.jinja")
        return self._title_desc_template

    def _get_taxonomy_template(self) -> Template:
        """Get the taxonomy template, loading it if necessary."""
        if self._taxonomy_template is None:
            self._taxonomy_template = self.jinja_env.get_template("taxonomy.jinja")
        return self._taxonomy_template

    async def title_desc(
        self, url: str, text: str, original_title: str = ""
    ) -> LLMMetadata:
        """
        Generate semantic title and description for a URL's content.

        Args:
            url: The URL being analyzed
            text: The extracted text content from the page
            original_title: The original HTML title of the page

        Returns:
            LLMMetadata with generated title, description, and token usage

        Raises:
            LLMError: If the LLM request fails or returns invalid data
        """
        logger.debug(f"Generating title/description for URL: {url}")

        # Truncate text if too long for the model
        max_text_length = 8000  # Leave room for prompt and response
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
            logger.debug(f"Truncated content to {max_text_length} chars for {url}")

        # Render the prompt template
        template = self._get_title_desc_template()
        prompt = template.render(url=url, original_title=original_title, content=text)

        # Make the OpenAI request with retries
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,  # Enough for title + description
                    temperature=0.3,  # Low temperature for consistent results
                    response_format={"type": "json_object"},  # Ensure JSON response
                )

                # Extract the response content
                if not response.choices or not response.choices[0].message.content:
                    raise LLMError("Empty response from OpenAI")

                content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0

                # Parse the JSON response
                try:
                    result_data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise LLMError(f"Invalid JSON response: {e}") from e

                # Validate required fields
                if "name" not in result_data or "description" not in result_data:
                    raise LLMError(
                        "Response missing required fields 'name' or 'description'"
                    )

                # Create and return LLMMetadata
                metadata = LLMMetadata(
                    url=url,
                    name=str(result_data["name"])[:80],  # Enforce max length
                    description=str(result_data["description"])[
                        :200
                    ],  # Enforce max length
                    tokens_used=tokens_used,
                )

                logger.debug(f"Generated metadata for {url}: {metadata.name}")
                return metadata

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit for {url}, attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2**attempt) + (attempt * 0.1)
                    await asyncio.sleep(delay)
                    continue
                raise LLMError(
                    f"Rate limit exceeded after {self.max_retries} attempts"
                ) from e

            except openai.APITimeoutError as e:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1.0)
                    continue
                raise LLMError(
                    f"Request timeout after {self.max_retries} attempts"
                ) from e

            except openai.APIError as e:
                logger.error(f"OpenAI API error for {url}: {e}")
                raise LLMError(f"OpenAI API error: {e}") from e

            except Exception as e:
                logger.error(f"Unexpected error generating metadata for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1.0)
                    continue
                raise LLMError(f"Failed to generate metadata: {e}") from e

        # Should not reach here due to the raise in the loop
        raise LLMError(f"Failed to generate metadata after {self.max_retries} attempts")

    async def title_desc_from_scrape_result(
        self, scrape_result: ScrapeResult
    ) -> LLMMetadata:
        """
        Convenience method to generate metadata from a ScrapeResult.

        Args:
            scrape_result: The result from scraping a URL

        Returns:
            LLMMetadata with generated title, description, and token usage
        """
        return await self.title_desc(
            url=scrape_result.url,
            text=scrape_result.text,
            original_title=scrape_result.html_title,
        )

    async def propose_taxonomy(self, metadata_list: list[LLMMetadata]) -> dict:
        """
        Generate a hierarchical folder taxonomy for a list of bookmark metadata.

        Args:
            metadata_list: List of LLMMetadata objects to organize

        Returns:
            Dictionary representing the folder hierarchy in JSON format

        Raises:
            LLMError: If the LLM request fails or returns invalid data
        """
        if not metadata_list:
            logger.warning("Empty metadata list provided for taxonomy generation")
            return {"folders": []}

        logger.info(f"Generating taxonomy for {len(metadata_list)} bookmarks")

        # Render the prompt template
        template = self._get_taxonomy_template()
        prompt = template.render(metadata_list=metadata_list)

        # Make the OpenAI request with retries
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,  # Larger response for taxonomy JSON
                    temperature=0.1,  # Very low temperature for consistent structure
                    response_format={"type": "json_object"},  # Ensure JSON response
                )

                # Extract the response content
                if not response.choices or not response.choices[0].message.content:
                    raise LLMError("Empty response from OpenAI")

                content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0

                # Parse the JSON response
                try:
                    taxonomy_data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise LLMError(f"Invalid JSON response: {e}") from e

                # Validate the response structure
                if "folders" not in taxonomy_data:
                    raise LLMError("Response missing required 'folders' field")

                if not isinstance(taxonomy_data["folders"], list):
                    raise LLMError("'folders' field must be a list")

                # Add token usage to the response
                taxonomy_data["_metadata"] = {
                    "tokens_used": tokens_used,
                    "input_count": len(metadata_list),
                    "model": self.model,
                }

                logger.info(
                    f"Generated taxonomy with {len(taxonomy_data['folders'])} top-level folders, "
                    f"tokens used: {tokens_used}"
                )
                return taxonomy_data

            except openai.RateLimitError as e:
                logger.warning(
                    f"Rate limit hit for taxonomy, attempt {attempt + 1}: {e}"
                )
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = (2**attempt) + (attempt * 0.1)
                    await asyncio.sleep(delay)
                    continue
                raise LLMError(
                    f"Rate limit exceeded after {self.max_retries} attempts"
                ) from e

            except openai.APITimeoutError as e:
                logger.warning(f"Timeout for taxonomy, attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2.0)  # Longer delay for taxonomy
                    continue
                raise LLMError(
                    f"Request timeout after {self.max_retries} attempts"
                ) from e

            except openai.APIError as e:
                logger.error(f"OpenAI API error for taxonomy: {e}")
                raise LLMError(f"OpenAI API error: {e}") from e

            except Exception as e:
                logger.error(f"Unexpected error generating taxonomy: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2.0)
                    continue
                raise LLMError(f"Failed to generate taxonomy: {e}") from e

        # Should not reach here due to the raise in the loop
        raise LLMError(f"Failed to generate taxonomy after {self.max_retries} attempts")


# Convenience function for single metadata generation
async def generate_title_desc(
    url: str,
    text: str,
    original_title: str = "",
    api_key: str | None = None,
    model: str = "gpt-4o",
) -> LLMMetadata:
    """
    Convenience function to generate title and description for a single URL.

    Args:
        url: The URL being analyzed
        text: The extracted text content from the page
        original_title: The original HTML title of the page
        api_key: OpenAI API key (optional)
        model: OpenAI model to use

    Returns:
        LLMMetadata with generated title, description, and token usage
    """
    service = LLMService(api_key=api_key, model=model)
    return await service.title_desc(url, text, original_title)
