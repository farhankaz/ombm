"""Tests for the scraper module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from playwright.async_api import Error as PlaywrightError

from ombm.scraper import (
    WebScraper,
    PlaywrightScraper,
    HTTPXScraper,
    ScraperError,
    scrape_url,
)
from ombm.models import ScrapeResult


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page Title</title>
        <meta name="description" content="Test page description">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is some test content that should be extracted.</p>
        <p>This is additional content for testing readability extraction.</p>
        <div class="sidebar">This is sidebar content that might be filtered out.</div>
    </body>
    </html>
    """


@pytest.fixture
def expected_scrape_result():
    """Expected scrape result for sample HTML."""
    return ScrapeResult(
        url="https://example.com",
        text="Main Heading This is some test content that should be extracted. This is additional content for testing readability extraction.",
        html_title="Test Page Title"
    )


class TestHTTPXScraper:
    """Test HTTPX scraper functionality."""

    @pytest.fixture
    def httpx_scraper(self):
        """Create HTTPX scraper instance."""
        return HTTPXScraper(timeout=10)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, httpx_scraper, sample_html):
        """Test successful content fetching with HTTPX."""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.text = sample_html
            mock_response.raise_for_status = MagicMock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            # Test fetch
            result = await httpx_scraper.fetch("https://example.com")
            
            # Verify result
            assert isinstance(result, ScrapeResult)
            assert result.url == "https://example.com"
            assert result.html_title == "Test Page Title"
            assert "Main Heading" in result.text
            assert "test content" in result.text
            assert len(result.text) <= 10000  # Should be truncated if too long

    @pytest.mark.asyncio
    async def test_http_error_handling(self, httpx_scraper):
        """Test HTTP error handling."""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock to raise HTTP error
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404)
            ))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            # Test error handling
            with pytest.raises(ScraperError, match="HTTP 404"):
                await httpx_scraper.fetch("https://example.com/not-found")

    @pytest.mark.asyncio
    async def test_request_error_handling(self, httpx_scraper):
        """Test request error handling."""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock to raise request error
            mock_get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            # Test error handling
            with pytest.raises(ScraperError, match="Request failed"):
                await httpx_scraper.fetch("https://invalid-url.com")

    @pytest.mark.asyncio
    async def test_text_truncation(self, httpx_scraper):
        """Test that long text content is properly truncated."""
        long_html = f"""
        <html>
        <head><title>Long Content</title></head>
        <body>
        <p>{'A' * 12000}</p>
        </body>
        </html>
        """
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = long_html
            mock_response.raise_for_status = MagicMock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            result = await httpx_scraper.fetch("https://example.com")
            
            # Should be truncated to 10k chars + "..."
            assert len(result.text) <= 10003  # 10000 + "..."
            assert result.text.endswith("...")


class TestPlaywrightScraper:
    """Test Playwright scraper functionality."""

    @pytest.fixture
    def playwright_scraper(self):
        """Create Playwright scraper instance."""
        return PlaywrightScraper(timeout=10000, headless=True)

    @pytest.mark.asyncio
    async def test_context_manager(self, playwright_scraper):
        """Test Playwright scraper context manager."""
        with patch('ombm.scraper.async_playwright') as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            
            # Test context manager
            async with playwright_scraper as scraper:
                assert scraper._browser is mock_browser
                assert scraper._context is mock_context
            
            # Verify cleanup
            mock_context.close.assert_called_once()
            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_fetch(self, playwright_scraper, sample_html):
        """Test successful content fetching with Playwright."""
        with patch('ombm.scraper.async_playwright') as mock_playwright:
            # Setup mocks
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_response = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock(return_value=mock_response)
            mock_page.content = AsyncMock(return_value=sample_html)
            mock_page.title = AsyncMock(return_value="Test Page Title")
            mock_response.status = 200
            
            # Start scraper
            await playwright_scraper.start()
            
            # Test fetch
            result = await playwright_scraper.fetch("https://example.com")
            
            # Verify result
            assert isinstance(result, ScrapeResult)
            assert result.url == "https://example.com"
            assert result.html_title == "Test Page Title"
            assert "Main Heading" in result.text
            
            await playwright_scraper.close()

    @pytest.mark.asyncio
    async def test_http_error_handling(self, playwright_scraper):
        """Test HTTP error handling in Playwright."""
        with patch('ombm.scraper.async_playwright') as mock_playwright:
            # Setup mocks
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_response = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock(return_value=mock_response)
            mock_response.status = 404  # HTTP error
            
            await playwright_scraper.start()
            
            # Test error handling
            with pytest.raises(ScraperError, match="HTTP 404"):
                await playwright_scraper.fetch("https://example.com/not-found")
            
            await playwright_scraper.close()

    @pytest.mark.asyncio
    async def test_playwright_timeout_error(self, playwright_scraper):
        """Test Playwright timeout error handling."""
        with patch('ombm.scraper.async_playwright') as mock_playwright:
            # Setup mocks
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock(side_effect=PlaywrightError("Timeout"))
            
            await playwright_scraper.start()
            
            # Test error handling
            with pytest.raises(ScraperError, match="Playwright fetch failed"):
                await playwright_scraper.fetch("https://slow-website.com")
            
            await playwright_scraper.close()

    @pytest.mark.asyncio
    async def test_browser_not_started_error(self, playwright_scraper):
        """Test error when browser is not started."""
        with pytest.raises(ScraperError, match="Browser not started"):
            await playwright_scraper.fetch("https://example.com")


class TestWebScraper:
    """Test main WebScraper class with fallback logic."""

    @pytest.mark.asyncio
    async def test_playwright_success(self, sample_html):
        """Test successful scraping with Playwright."""
        with patch('ombm.scraper.async_playwright') as mock_playwright:
            # Setup Playwright mocks
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_response = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.goto = AsyncMock(return_value=mock_response)
            mock_page.content = AsyncMock(return_value=sample_html)
            mock_page.title = AsyncMock(return_value="Test Page Title")
            mock_response.status = 200
            
            async with WebScraper(use_playwright=True) as scraper:
                result = await scraper.fetch("https://example.com")
                
                assert isinstance(result, ScrapeResult)
                assert result.url == "https://example.com"
                assert result.html_title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_fallback_to_httpx(self, sample_html):
        """Test fallback from Playwright to HTTPX."""
        with patch('ombm.scraper.async_playwright') as mock_playwright, \
             patch('httpx.AsyncClient') as mock_httpx_client:
            
            # Setup Playwright to start successfully but fail during fetch
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            # Make the page.goto fail to trigger fallback
            mock_page.goto = AsyncMock(side_effect=Exception("Playwright fetch failed"))
            
            # Setup HTTPX to succeed
            mock_response = MagicMock()
            mock_response.text = sample_html
            mock_response.raise_for_status = MagicMock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_httpx_client.return_value.__aenter__.return_value.get = mock_get
            
            async with WebScraper(use_playwright=True) as scraper:
                result = await scraper.fetch("https://example.com")
                
                assert isinstance(result, ScrapeResult)
                assert result.url == "https://example.com"
                assert result.html_title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_httpx_only_mode(self, sample_html):
        """Test HTTPX-only mode (no Playwright)."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = sample_html
            mock_response.raise_for_status = MagicMock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            async with WebScraper(use_playwright=False) as scraper:
                result = await scraper.fetch("https://example.com")
                
                assert isinstance(result, ScrapeResult)
                assert result.url == "https://example.com"
                assert result.html_title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_all_methods_fail(self):
        """Test when both Playwright and HTTPX fail."""
        with patch('ombm.scraper.async_playwright') as mock_playwright, \
             patch('httpx.AsyncClient') as mock_httpx_client:
            
            # Setup Playwright to start successfully but fail during fetch
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_playwright_instance = AsyncMock()
            
            # Setup the async playwright call chain
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.webkit.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            # Make the page.goto fail
            mock_page.goto = AsyncMock(side_effect=Exception("Playwright fetch failed"))
            
            # Setup HTTPX to also fail
            mock_httpx_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.RequestError("HTTPX failed"))
            
            async with WebScraper(use_playwright=True) as scraper:
                with pytest.raises(ScraperError, match="Request failed"):
                    await scraper.fetch("https://example.com")


class TestScrapingIntegration:
    """Integration tests for scraping functionality."""

    @pytest.mark.asyncio
    async def test_scrape_url_convenience_function(self, sample_html):
        """Test the convenience scrape_url function."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = sample_html
            mock_response.raise_for_status = MagicMock()
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            result = await scrape_url("https://example.com", use_playwright=False)
            
            assert isinstance(result, ScrapeResult)
            assert result.url == "https://example.com"
            assert result.html_title == "Test Page Title"

    @pytest.mark.asyncio
    async def test_real_website_scraping(self):
        """Test scraping a real website (example.com)."""
        # This test requires internet connection and should be marked as integration
        pytest.skip("Integration test - requires internet connection")
        
        try:
            result = await scrape_url("https://example.com", use_playwright=False)
            assert result.url == "https://example.com"
            assert len(result.text) > 0
            assert len(result.html_title) > 0
        except Exception as e:
            pytest.skip(f"Network error: {e}")


class TestReadabilityExtraction:
    """Test readability text extraction."""

    def test_readability_extraction_with_complex_html(self):
        """Test readability extraction with complex HTML."""
        complex_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Complex Page</title>
        </head>
        <body>
            <nav>Navigation content</nav>
            <aside>Sidebar content</aside>
            <main>
                <article>
                    <h1>Main Article Title</h1>
                    <p>This is the main content that should be extracted.</p>
                    <p>This is another important paragraph.</p>
                </article>
            </main>
            <footer>Footer content</footer>
            <script>console.log('script content');</script>
        </body>
        </html>
        """
        
        from ombm.scraper import HTTPXScraper
        scraper = HTTPXScraper()
        
        # Test the internal method
        text = scraper._extract_readable_text(complex_html)
        
        # Should extract main content
        assert "Main Article Title" in text
        assert "main content that should be extracted" in text
        assert "another important paragraph" in text
        
        # Should filter out navigation/sidebar/footer
        assert "Navigation content" not in text or len(text.split("Navigation content")) == 1
        assert "script content" not in text
