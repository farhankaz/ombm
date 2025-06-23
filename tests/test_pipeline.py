"""Tests for the pipeline integration module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ombm.cache import CacheManager
from ombm.llm import LLMError, LLMService
from ombm.models import BookmarkRecord, LLMMetadata, ScrapeResult
from ombm.pipeline import (
    BookmarkProcessor,
    ProcessingResult,
    process_url,
)
from ombm.scraper import ScraperError, WebScraper


@pytest.fixture
def sample_bookmark():
    """Sample bookmark for testing."""
    return BookmarkRecord(
        uuid="test-123",
        title="Original Title",
        url="https://example.com/article",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_scrape_result():
    """Sample scrape result."""
    return ScrapeResult(
        url="https://example.com/article",
        text="This is sample article content about Python programming.",
        html_title="Python Tutorial",
    )


@pytest.fixture
def sample_llm_metadata():
    """Sample LLM metadata."""
    return LLMMetadata(
        url="https://example.com/article",
        name="Python Programming Tutorial",
        description="Comprehensive guide to Python programming basics",
        tokens_used=150,
    )


class TestProcessingResult:
    """Test ProcessingResult class."""

    def test_successful_result(
        self, sample_bookmark, sample_scrape_result, sample_llm_metadata
    ):
        """Test successful processing result."""
        result = ProcessingResult(
            bookmark=sample_bookmark,
            scrape_result=sample_scrape_result,
            llm_metadata=sample_llm_metadata,
            used_cache=False,
        )

        assert result.success is True
        assert result.error is None
        assert result.bookmark == sample_bookmark
        assert result.scrape_result == sample_scrape_result
        assert result.llm_metadata == sample_llm_metadata
        assert result.used_cache is False

    def test_failed_result(self, sample_bookmark):
        """Test failed processing result."""
        result = ProcessingResult(bookmark=sample_bookmark, error="Test error")

        assert result.success is False
        assert result.error == "Test error"
        assert result.scrape_result is None
        assert result.llm_metadata is None


class TestBookmarkProcessor:
    """Test BookmarkProcessor functionality."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager."""
        cache = AsyncMock(spec=CacheManager)
        cache.initialize = AsyncMock()
        cache.get_scrape_result = AsyncMock(return_value=None)
        cache.get_llm_metadata = AsyncMock(return_value=None)
        cache.store_scrape_result = AsyncMock()
        cache.store_llm_metadata = AsyncMock()
        cache.get_cache_stats = AsyncMock(
            return_value={
                "scrape_results_count": 10,
                "llm_metadata_count": 10,
                "total_tokens_used": 1500,
            }
        )
        return cache

    @pytest.fixture
    def mock_scraper(self):
        """Mock web scraper."""
        scraper = AsyncMock(spec=WebScraper)
        scraper.__aenter__ = AsyncMock(return_value=scraper)
        scraper.__aexit__ = AsyncMock()
        return scraper

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        service = AsyncMock(spec=LLMService)
        return service

    @pytest.mark.asyncio
    async def test_successful_processing_no_cache(
        self,
        sample_bookmark,
        sample_scrape_result,
        sample_llm_metadata,
        mock_cache_manager,
        mock_scraper,
        mock_llm_service,
    ):
        """Test successful processing without cached data."""
        # Setup mocks
        mock_scraper.fetch = AsyncMock(return_value=sample_scrape_result)
        mock_llm_service.title_desc_from_scrape_result = AsyncMock(
            return_value=sample_llm_metadata
        )

        # Create processor
        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            result = await processor.process_bookmark(sample_bookmark)

        # Verify result
        assert result.success is True
        assert result.bookmark == sample_bookmark
        assert result.scrape_result == sample_scrape_result
        assert result.llm_metadata == sample_llm_metadata
        assert result.used_cache is False

        # Verify calls
        mock_cache_manager.get_scrape_result.assert_called_once_with(
            sample_bookmark.url
        )
        mock_cache_manager.get_llm_metadata.assert_called_once_with(sample_bookmark.url)
        mock_scraper.fetch.assert_called_once_with(sample_bookmark.url)
        mock_llm_service.title_desc_from_scrape_result.assert_called_once_with(
            sample_scrape_result
        )
        mock_cache_manager.store_scrape_result.assert_called_once_with(
            sample_scrape_result
        )
        mock_cache_manager.store_llm_metadata.assert_called_once_with(
            sample_llm_metadata
        )

    @pytest.mark.asyncio
    async def test_processing_with_cached_data(
        self,
        sample_bookmark,
        sample_scrape_result,
        sample_llm_metadata,
        mock_cache_manager,
        mock_scraper,
        mock_llm_service,
    ):
        """Test processing with cached scrape and LLM data."""
        # Setup cache to return data
        mock_cache_manager.get_scrape_result = AsyncMock(
            return_value=sample_scrape_result
        )
        mock_cache_manager.get_llm_metadata = AsyncMock(
            return_value=sample_llm_metadata
        )

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            result = await processor.process_bookmark(sample_bookmark)

        # Verify result
        assert result.success is True
        assert result.used_cache is True

        # Verify no scraping or LLM calls were made
        mock_scraper.fetch.assert_not_called()
        mock_llm_service.title_desc_from_scrape_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_scraping_error_handling(
        self, sample_bookmark, mock_cache_manager, mock_scraper, mock_llm_service
    ):
        """Test handling of scraping errors."""
        # Setup scraper to fail
        mock_scraper.fetch = AsyncMock(side_effect=ScraperError("Scraping failed"))

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            result = await processor.process_bookmark(sample_bookmark)

        # Verify error result
        assert result.success is False
        assert "Scraping failed" in result.error
        assert result.scrape_result is None
        assert result.llm_metadata is None

    @pytest.mark.asyncio
    async def test_llm_error_handling(
        self,
        sample_bookmark,
        sample_scrape_result,
        mock_cache_manager,
        mock_scraper,
        mock_llm_service,
    ):
        """Test handling of LLM errors."""
        # Setup mocks
        mock_scraper.fetch = AsyncMock(return_value=sample_scrape_result)
        mock_llm_service.title_desc_from_scrape_result = AsyncMock(
            side_effect=LLMError("LLM processing failed")
        )

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            result = await processor.process_bookmark(sample_bookmark)

        # Verify error result
        assert result.success is False
        assert "LLM processing failed" in result.error
        assert result.scrape_result == sample_scrape_result  # Should have scrape result
        assert result.llm_metadata is None

    @pytest.mark.asyncio
    async def test_force_refresh(
        self,
        sample_bookmark,
        sample_scrape_result,
        sample_llm_metadata,
        mock_cache_manager,
        mock_scraper,
        mock_llm_service,
    ):
        """Test force refresh skips cache."""
        # Setup cache to return data (which should be ignored)
        mock_cache_manager.get_scrape_result = AsyncMock(
            return_value=sample_scrape_result
        )
        mock_cache_manager.get_llm_metadata = AsyncMock(
            return_value=sample_llm_metadata
        )

        # Setup fresh processing
        mock_scraper.fetch = AsyncMock(return_value=sample_scrape_result)
        mock_llm_service.title_desc_from_scrape_result = AsyncMock(
            return_value=sample_llm_metadata
        )

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            result = await processor.process_bookmark(
                sample_bookmark, force_refresh=True
            )

        # Verify fresh processing occurred
        assert result.success is True
        assert result.used_cache is False
        mock_scraper.fetch.assert_called_once()
        mock_llm_service.title_desc_from_scrape_result.assert_called_once()

        # Verify cache wasn't checked
        mock_cache_manager.get_scrape_result.assert_not_called()
        mock_cache_manager.get_llm_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_disabled(
        self,
        sample_bookmark,
        sample_scrape_result,
        sample_llm_metadata,
        mock_cache_manager,
        mock_scraper,
        mock_llm_service,
    ):
        """Test processing with cache disabled."""
        mock_scraper.fetch = AsyncMock(return_value=sample_scrape_result)
        mock_llm_service.title_desc_from_scrape_result = AsyncMock(
            return_value=sample_llm_metadata
        )

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
            use_cache=False,
        )

        async with processor:
            result = await processor.process_bookmark(sample_bookmark)

        # Verify result
        assert result.success is True
        assert result.used_cache is False

        # Verify no cache operations
        mock_cache_manager.initialize.assert_not_called()
        mock_cache_manager.get_scrape_result.assert_not_called()
        mock_cache_manager.get_llm_metadata.assert_not_called()
        mock_cache_manager.store_scrape_result.assert_not_called()
        mock_cache_manager.store_llm_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_multiple_bookmarks(
        self, mock_cache_manager, mock_scraper, mock_llm_service
    ):
        """Test processing multiple bookmarks concurrently."""
        # Create multiple bookmarks
        bookmarks = [
            BookmarkRecord(
                uuid=f"test-{i}",
                title=f"Title {i}",
                url=f"https://example.com/{i}",
                created_at=datetime.now(),
            )
            for i in range(3)
        ]

        # Setup mocks
        mock_scraper.fetch = AsyncMock(
            side_effect=[
                ScrapeResult(
                    url=f"https://example.com/{i}",
                    text=f"Content {i}",
                    html_title=f"Title {i}",
                )
                for i in range(3)
            ]
        )
        mock_llm_service.title_desc_from_scrape_result = AsyncMock(
            side_effect=[
                LLMMetadata(
                    url=f"https://example.com/{i}",
                    name=f"Name {i}",
                    description=f"Description {i}",
                    tokens_used=100,
                )
                for i in range(3)
            ]
        )

        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            results = await processor.process_bookmarks(bookmarks, concurrency=2)

        # Verify results
        assert len(results) == 3
        assert all(result.success for result in results)
        assert mock_scraper.fetch.call_count == 3
        assert mock_llm_service.title_desc_from_scrape_result.call_count == 3

    @pytest.mark.asyncio
    async def test_get_processing_stats(
        self, mock_cache_manager, mock_scraper, mock_llm_service
    ):
        """Test getting processing statistics."""
        processor = BookmarkProcessor(
            cache_manager=mock_cache_manager,
            scraper=mock_scraper,
            llm_service=mock_llm_service,
        )

        async with processor:
            stats = await processor.get_processing_stats()

        # Verify stats
        assert stats["cache_enabled"] is True
        assert stats["scrape_results_count"] == 10
        assert stats["llm_metadata_count"] == 10
        assert stats["total_tokens_used"] == 1500

    @pytest.mark.asyncio
    async def test_get_processing_stats_cache_disabled(
        self, mock_scraper, mock_llm_service
    ):
        """Test stats with cache disabled."""
        processor = BookmarkProcessor(
            scraper=mock_scraper, llm_service=mock_llm_service, use_cache=False
        )

        async with processor:
            stats = await processor.get_processing_stats()

        assert stats["cache_enabled"] is False


class TestConvenienceFunction:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_process_url_function(self):
        """Test the convenience process_url function."""
        with patch("ombm.pipeline.BookmarkProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_result = ProcessingResult(
                bookmark=MagicMock(),
                scrape_result=MagicMock(),
                llm_metadata=MagicMock(),
                used_cache=False,
            )
            mock_processor.process_bookmark = AsyncMock(return_value=mock_result)
            mock_processor.__aenter__ = AsyncMock(return_value=mock_processor)
            mock_processor.__aexit__ = AsyncMock()
            mock_processor_class.return_value = mock_processor

            result = await process_url(
                url="https://example.com/test",
                original_title="Test Title",
                use_cache=True,
                api_key="test-key",
            )

            # Verify processor was created and called
            mock_processor_class.assert_called_once()
            mock_processor.process_bookmark.assert_called_once()

            # Verify result
            assert result == mock_result


class TestIntegration:
    """Integration tests for the pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test end-to-end processing with mocked components."""
        with (
            patch("ombm.pipeline.CacheManager") as mock_cache_class,
            patch("ombm.pipeline.WebScraper") as mock_scraper_class,
            patch("ombm.pipeline.LLMService") as mock_llm_class,
        ):
            # Setup mocks
            mock_cache = AsyncMock()
            mock_cache.get_scrape_result = AsyncMock(return_value=None)
            mock_cache.get_llm_metadata = AsyncMock(return_value=None)
            mock_cache.store_scrape_result = AsyncMock()
            mock_cache.store_llm_metadata = AsyncMock()
            mock_cache_class.return_value = mock_cache

            mock_scraper = AsyncMock()
            mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
            mock_scraper.__aexit__ = AsyncMock()
            mock_scraper.fetch = AsyncMock(
                return_value=ScrapeResult(
                    url="https://example.com",
                    text="Test content",
                    html_title="Test Title",
                )
            )
            mock_scraper_class.return_value = mock_scraper

            mock_llm = AsyncMock()
            mock_llm.title_desc_from_scrape_result = AsyncMock(
                return_value=LLMMetadata(
                    url="https://example.com",
                    name="Generated Title",
                    description="Generated description",
                    tokens_used=100,
                )
            )
            mock_llm_class.return_value = mock_llm

            # Test processing
            bookmark = BookmarkRecord(
                uuid="test",
                title="Original",
                url="https://example.com",
                created_at=datetime.now(),
            )

            async with BookmarkProcessor() as processor:
                result = await processor.process_bookmark(bookmark)

            # Verify success
            assert result.success is True
            assert result.llm_metadata.name == "Generated Title"

            # Verify all components were called
            mock_cache.store_scrape_result.assert_called_once()
            mock_cache.store_llm_metadata.assert_called_once()
            mock_scraper.fetch.assert_called_once()
            mock_llm.title_desc_from_scrape_result.assert_called_once()
