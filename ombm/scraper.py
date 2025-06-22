"""
Web scraping functionality for OMBM.

This module provides async web scraping capabilities using Playwright
with fallback to HTTPX for simpler requests.
"""

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from readability import Document
import httpx
from bs4 import BeautifulSoup

from .models import ScrapeResult

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper-related errors."""
    pass


class PlaywrightScraper:
    """Playwright-based web scraper for dynamic content."""
    
    def __init__(self, timeout: int = 30000, headless: bool = True):
        self.timeout = timeout
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Start the browser instance."""
        playwright = await async_playwright().start()
        self._browser = await playwright.webkit.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent="OMBM/1.0 (macOS) Webkit/537.36"
        )
        logger.debug("Started Playwright browser")
    
    async def close(self) -> None:
        """Close the browser instance."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        logger.debug("Closed Playwright browser")
    
    async def fetch(self, url: str) -> ScrapeResult:
        """
        Fetch and extract content from a URL using Playwright.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapeResult with extracted content
            
        Raises:
            ScraperError: If scraping fails after retries
        """
        if not self._context:
            raise ScraperError("Browser not started. Use async context manager.")
        
        logger.debug(f"Scraping URL with Playwright: {url}")
        
        try:
            page = await self._context.new_page()
            
            # Navigate to the page
            response = await page.goto(url, timeout=self.timeout)
            
            if not response:
                raise ScraperError(f"Failed to load page: {url}")
            
            if response.status >= 400:
                raise ScraperError(f"HTTP {response.status} for URL: {url}")
            
            # Wait for the page to load
            await page.wait_for_load_state("networkidle", timeout=self.timeout)
            
            # Extract content
            html_content = await page.content()
            html_title = await page.title()
            
            # Clean and extract readable text
            text_content = self._extract_readable_text(html_content)
            
            await page.close()
            
            result = ScrapeResult(
                url=url,
                text=text_content,
                html_title=html_title
            )
            
            logger.debug(f"Successfully scraped {len(text_content)} chars from {url}")
            return result
            
        except Exception as e:
            logger.error(f"Playwright scraping failed for {url}: {e}")
            raise ScraperError(f"Playwright fetch failed: {e}") from e
    
    def _extract_readable_text(self, html_content: str) -> str:
        """
        Extract readable text from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content (max 10k chars)
        """
        try:
            # Use readability to extract main content
            doc = Document(html_content)
            readable_html = doc.summary()
            
            # Convert to plain text using BeautifulSoup
            soup = BeautifulSoup(readable_html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            # Truncate to 10k chars as per spec
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            return text
            
        except Exception as e:
            logger.warning(f"Failed to extract readable text: {e}")
            # Fallback to basic text extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text[:10000] + "..." if len(text) > 10000 else text


class HTTPXScraper:
    """Fallback HTTP scraper using HTTPX."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def fetch(self, url: str) -> ScrapeResult:
        """
        Fetch content from a URL using HTTPX.
        
        Args:
            url: The URL to scrape
            
        Returns:
            ScrapeResult with extracted content
            
        Raises:
            ScraperError: If scraping fails
        """
        logger.debug(f"Scraping URL with HTTPX: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "User-Agent": "OMBM/1.0 (macOS) Mozilla/5.0 (compatible)"
                }
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                html_content = response.text
                
                # Extract title and readable content
                soup = BeautifulSoup(html_content, 'html.parser')
                html_title = soup.title.string.strip() if soup.title else ""
                
                # Extract readable text
                text_content = self._extract_readable_text(html_content)
                
                result = ScrapeResult(
                    url=url,
                    text=text_content,
                    html_title=html_title
                )
                
                logger.debug(f"Successfully scraped {len(text_content)} chars from {url}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            raise ScraperError(f"HTTP {e.response.status_code}: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            raise ScraperError(f"Request failed: {e}") from e
        except Exception as e:
            logger.error(f"HTTPX scraping failed for {url}: {e}")
            raise ScraperError(f"HTTPX fetch failed: {e}") from e
    
    def _extract_readable_text(self, html_content: str) -> str:
        """
        Extract readable text from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned text content (max 10k chars)
        """
        try:
            # Use readability to extract main content
            doc = Document(html_content)
            readable_html = doc.summary()
            
            # Convert to plain text using BeautifulSoup
            soup = BeautifulSoup(readable_html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            # Truncate to 10k chars as per spec
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            return text
            
        except Exception as e:
            logger.warning(f"Failed to extract readable text: {e}")
            # Fallback to basic text extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text[:10000] + "..." if len(text) > 10000 else text


class WebScraper:
    """
    Main scraper class that combines Playwright and HTTPX with fallback logic.
    """
    
    def __init__(self, 
                 playwright_timeout: int = 30000,
                 httpx_timeout: int = 30,
                 use_playwright: bool = True):
        self.playwright_timeout = playwright_timeout
        self.httpx_timeout = httpx_timeout
        self.use_playwright = use_playwright
        self._playwright_scraper: Optional[PlaywrightScraper] = None
        self._httpx_scraper = HTTPXScraper(timeout=httpx_timeout)
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.use_playwright:
            self._playwright_scraper = PlaywrightScraper(
                timeout=self.playwright_timeout
            )
            await self._playwright_scraper.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._playwright_scraper:
            await self._playwright_scraper.close()
    
    async def fetch(self, url: str, retry_with_fallback: bool = True) -> ScrapeResult:
        """
        Fetch content from URL with automatic fallback.
        
        Args:
            url: The URL to scrape
            retry_with_fallback: Whether to fallback to HTTPX if Playwright fails
            
        Returns:
            ScrapeResult with extracted content
            
        Raises:
            ScraperError: If all scraping methods fail
        """
        # Try Playwright first if available
        if self._playwright_scraper:
            try:
                return await self._playwright_scraper.fetch(url)
            except ScraperError as e:
                logger.warning(f"Playwright failed for {url}: {e}")
                if not retry_with_fallback:
                    raise
        
        # Fallback to HTTPX
        try:
            return await self._httpx_scraper.fetch(url)
        except ScraperError as e:
            logger.error(f"All scraping methods failed for {url}: {e}")
            raise


# Convenience function for single URL scraping
async def scrape_url(url: str, use_playwright: bool = True) -> ScrapeResult:
    """
    Convenience function to scrape a single URL.
    
    Args:
        url: The URL to scrape
        use_playwright: Whether to use Playwright (True) or HTTPX only (False)
        
    Returns:
        ScrapeResult with extracted content
    """
    async with WebScraper(use_playwright=use_playwright) as scraper:
        return await scraper.fetch(url)
