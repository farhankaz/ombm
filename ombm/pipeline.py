"""
Pipeline service that integrates scraping, LLM processing, and caching.

This module provides a unified interface for processing URLs through
the complete pipeline: scraping -> LLM metadata generation -> caching.
"""

import asyncio
import logging
from collections.abc import Callable

from .cache import CacheManager
from .llm import LLMError, LLMService
from .models import BookmarkRecord, LLMMetadata, ScrapeResult
from .scraper import ScraperError, WebScraper

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Base exception for pipeline-related errors."""

    pass


class ProcessingResult:
    """Result of processing a URL through the pipeline."""

    def __init__(
        self,
        bookmark: BookmarkRecord,
        scrape_result: ScrapeResult | None = None,
        llm_metadata: LLMMetadata | None = None,
        error: str | None = None,
        used_cache: bool = False,
    ):
        self.bookmark = bookmark
        self.scrape_result = scrape_result
        self.llm_metadata = llm_metadata
        self.error = error
        self.used_cache = used_cache
        self.success = error is None and llm_metadata is not None


class BookmarkProcessor:
    """
    Service that processes bookmarks through the complete pipeline
    with caching and error handling.
    """

    def __init__(
        self,
        cache_manager: CacheManager | None = None,
        scraper: WebScraper | None = None,
        llm_service: LLMService | None = None,
        use_cache: bool = True,
    ):
        """
        Initialize the bookmark processor.

        Args:
            cache_manager: Cache manager instance (created if None)
            scraper: Web scraper instance (created if None)
            llm_service: LLM service instance (created if None)
            use_cache: Whether to use caching
        """
        self.cache_manager = cache_manager or CacheManager()
        self.use_cache = use_cache
        self._scraper: WebScraper | None = scraper
        self._llm_service: LLMService | None = llm_service
        self._scraper_context = None

    async def __aenter__(self) -> "BookmarkProcessor":
        """Async context manager entry."""
        # Initialize cache
        if self.use_cache:
            await self.cache_manager.initialize()

        # Initialize scraper if needed
        if self._scraper is None:
            self._scraper = WebScraper()
            await self._scraper.__aenter__()

        # Initialize LLM service if needed
        if self._llm_service is None:
            self._llm_service = LLMService()

        return self

    async def __aexit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        if self._scraper is not None:
            await self._scraper.__aexit__(exc_type, exc_val, exc_tb)

    async def process_bookmark(
        self, bookmark: BookmarkRecord, force_refresh: bool = False
    ) -> ProcessingResult:
        """
        Process a single bookmark through the complete pipeline.

        Args:
            bookmark: The bookmark to process
            force_refresh: If True, skip cache and force fresh processing

        Returns:
            ProcessingResult with the outcome of processing
        """
        logger.debug(f"Processing bookmark: {bookmark.url}")

        try:
            # Step 1: Get or generate scrape result
            scrape_result = None
            used_cache = False

            if self.use_cache and not force_refresh:
                scrape_result = await self.cache_manager.get_scrape_result(bookmark.url)
                if scrape_result:
                    logger.debug(f"Found cached scrape result for {bookmark.url}")
                    used_cache = True

            if scrape_result is None:
                # Scrape the URL
                try:
                    if self._scraper is None:
                        raise PipelineError("Scraper not initialized")
                    scrape_result = await self._scraper.fetch(bookmark.url)
                    logger.debug(
                        f"Scraped content from {bookmark.url}: {len(scrape_result.text)} chars"
                    )

                    # Cache the scrape result
                    if self.use_cache:
                        await self.cache_manager.store_scrape_result(scrape_result)

                except ScraperError as e:
                    logger.error(f"Failed to scrape {bookmark.url}: {e}")
                    return ProcessingResult(
                        bookmark=bookmark, error=f"Scraping failed: {e}"
                    )

            # Step 2: Get or generate LLM metadata
            llm_metadata = None

            if self.use_cache and not force_refresh:
                llm_metadata = await self.cache_manager.get_llm_metadata(bookmark.url)
                if llm_metadata:
                    logger.debug(f"Found cached LLM metadata for {bookmark.url}")
                    used_cache = True

            if llm_metadata is None:
                # Generate LLM metadata
                try:
                    if self._llm_service is None:
                        raise PipelineError("LLM service not initialized")
                    llm_metadata = (
                        await self._llm_service.title_desc_from_scrape_result(
                            scrape_result
                        )
                    )
                    logger.debug(
                        f"Generated LLM metadata for {bookmark.url}: {llm_metadata.name}"
                    )

                    # Cache the LLM metadata
                    if self.use_cache:
                        await self.cache_manager.store_llm_metadata(llm_metadata)

                except LLMError as e:
                    logger.error(
                        f"Failed to generate LLM metadata for {bookmark.url}: {e}"
                    )
                    return ProcessingResult(
                        bookmark=bookmark,
                        scrape_result=scrape_result,
                        error=f"LLM processing failed: {e}",
                    )

            return ProcessingResult(
                bookmark=bookmark,
                scrape_result=scrape_result,
                llm_metadata=llm_metadata,
                used_cache=used_cache,
            )

        except Exception as e:
            logger.error(f"Unexpected error processing {bookmark.url}: {e}")
            return ProcessingResult(bookmark=bookmark, error=f"Unexpected error: {e}")

    async def process_bookmarks(
        self,
        bookmarks: list[BookmarkRecord],
        concurrency: int = 4,
        force_refresh: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ProcessingResult]:
        """
        Process multiple bookmarks concurrently.

        Args:
            bookmarks: List of bookmarks to process
            concurrency: Maximum number of concurrent operations
            force_refresh: If True, skip cache and force fresh processing
            progress_callback: Optional callback for progress updates (completed, total)

        Returns:
            List of ProcessingResult objects
        """
        logger.info(
            f"Processing {len(bookmarks)} bookmarks with concurrency {concurrency}"
        )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        completed = 0

        async def process_with_semaphore(bookmark: BookmarkRecord) -> ProcessingResult:
            nonlocal completed
            async with semaphore:
                result = await self.process_bookmark(
                    bookmark, force_refresh=force_refresh
                )
                completed += 1
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(completed, len(bookmarks))
                return result

        # Process all bookmarks concurrently
        tasks = [process_with_semaphore(bookmark) for bookmark in bookmarks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions from gather
        processed_results: list[ProcessingResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task failed for bookmark {bookmarks[i].url}: {result}")
                processed_results.append(
                    ProcessingResult(
                        bookmark=bookmarks[i], error=f"Task failed: {result}"
                    )
                )
            else:
                # We know result is ProcessingResult here due to isinstance check above
                from typing import cast

                processed_results.append(cast("ProcessingResult", result))

        # Log summary
        successful = sum(1 for r in processed_results if r.success)
        cached = sum(1 for r in processed_results if r.used_cache)

        logger.info(
            f"Processing complete: {successful}/{len(bookmarks)} successful, {cached} from cache"
        )

        return processed_results

    async def get_processing_stats(self) -> dict:
        """
        Get statistics about processing and cache usage.

        Returns:
            Dictionary with processing statistics
        """
        if not self.use_cache:
            return {"cache_enabled": False}

        cache_stats = await self.cache_manager.get_cache_stats()
        cache_stats["cache_enabled"] = True
        return cache_stats


# Convenience function for processing a single URL
async def process_url(
    url: str,
    original_title: str = "",
    use_cache: bool = True,
    api_key: str | None = None,
) -> ProcessingResult:
    """
    Convenience function to process a single URL through the pipeline.

    Args:
        url: URL to process
        original_title: Original title from bookmark
        use_cache: Whether to use caching
        api_key: OpenAI API key (optional)

    Returns:
        ProcessingResult with the outcome
    """
    from datetime import datetime

    # Create a mock bookmark record
    bookmark = BookmarkRecord(
        uuid="temp", title=original_title, url=url, created_at=datetime.now()
    )

    llm_service = LLMService(api_key=api_key) if api_key else None

    async with BookmarkProcessor(
        use_cache=use_cache, llm_service=llm_service
    ) as processor:
        return await processor.process_bookmark(bookmark)
