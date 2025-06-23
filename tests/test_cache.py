"""Tests for the cache module."""

import tempfile
from pathlib import Path

import aiosqlite
import pytest

from ombm.cache import CacheManager
from ombm.models import LLMMetadata, ScrapeResult


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create a CacheManager instance for testing."""
    return CacheManager(cache_dir=temp_cache_dir)


@pytest.fixture
def sample_scrape_result():
    """Sample ScrapeResult for testing."""
    return ScrapeResult(
        url="https://example.com",
        text="This is sample text content from the webpage.",
        html_title="Sample Page Title",
    )


@pytest.fixture
def sample_llm_metadata():
    """Sample LLMMetadata for testing."""
    return LLMMetadata(
        url="https://example.com",
        name="Example Website",
        description="A sample website for testing purposes.",
        tokens_used=50,
    )


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, cache_manager):
        """Test that initialization creates required tables."""
        await cache_manager.initialize()

        # Verify database file exists
        assert cache_manager.db_path.exists()

        # Verify tables exist
        async with aiosqlite.connect(cache_manager.db_path) as db:
            # Check scrape_results table
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='scrape_results'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None

            # Check llm_metadata table
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_metadata'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None

            # Check indices exist
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_scrape_url'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None

            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_llm_url'"
            ) as cursor:
                result = await cursor.fetchone()
                assert result is not None

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, cache_manager):
        """Test that multiple initializations don't cause issues."""
        await cache_manager.initialize()
        await cache_manager.initialize()  # Should not raise error

        # Verify tables still exist
        async with (
            aiosqlite.connect(cache_manager.db_path) as db,
            db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ) as cursor,
        ):
            table_count = (await cursor.fetchone())[0]
            assert table_count == 2  # scrape_results and llm_metadata

    @pytest.mark.asyncio
    async def test_store_and_retrieve_scrape_result(
        self, cache_manager, sample_scrape_result
    ):
        """Test storing and retrieving scrape results."""
        # Store the result
        await cache_manager.store_scrape_result(sample_scrape_result)

        # Retrieve it
        retrieved = await cache_manager.get_scrape_result(sample_scrape_result.url)

        assert retrieved is not None
        assert retrieved.url == sample_scrape_result.url
        assert retrieved.text == sample_scrape_result.text
        assert retrieved.html_title == sample_scrape_result.html_title

    @pytest.mark.asyncio
    async def test_store_and_retrieve_llm_metadata(
        self, cache_manager, sample_llm_metadata
    ):
        """Test storing and retrieving LLM metadata."""
        # Store the metadata
        await cache_manager.store_llm_metadata(sample_llm_metadata)

        # Retrieve it
        retrieved = await cache_manager.get_llm_metadata(sample_llm_metadata.url)

        assert retrieved is not None
        assert retrieved.url == sample_llm_metadata.url
        assert retrieved.name == sample_llm_metadata.name
        assert retrieved.description == sample_llm_metadata.description
        assert retrieved.tokens_used == sample_llm_metadata.tokens_used

    @pytest.mark.asyncio
    async def test_get_nonexistent_entries_returns_none(self, cache_manager):
        """Test that querying non-existent entries returns None."""
        await cache_manager.initialize()

        scrape_result = await cache_manager.get_scrape_result("https://nonexistent.com")
        assert scrape_result is None

        llm_metadata = await cache_manager.get_llm_metadata("https://nonexistent.com")
        assert llm_metadata is None

    @pytest.mark.asyncio
    async def test_url_hashing_consistency(self, cache_manager):
        """Test that URL hashing is consistent."""
        url = "https://example.com/test"
        hash1 = cache_manager._hash_url(url)
        hash2 = cache_manager._hash_url(url)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length

    @pytest.mark.asyncio
    async def test_insert_or_replace_functionality(self, cache_manager):
        """Test that storing the same URL replaces previous data."""
        url = "https://example.com"

        # Store initial result
        result1 = ScrapeResult(
            url=url, text="Original text", html_title="Original title"
        )
        await cache_manager.store_scrape_result(result1)

        # Store updated result
        result2 = ScrapeResult(url=url, text="Updated text", html_title="Updated title")
        await cache_manager.store_scrape_result(result2)

        # Retrieve and verify it's the updated version
        retrieved = await cache_manager.get_scrape_result(url)
        assert retrieved.text == "Updated text"
        assert retrieved.html_title == "Updated title"

    @pytest.mark.asyncio
    async def test_clear_cache(
        self, cache_manager, sample_scrape_result, sample_llm_metadata
    ):
        """Test clearing all cached data."""
        # Store some data
        await cache_manager.store_scrape_result(sample_scrape_result)
        await cache_manager.store_llm_metadata(sample_llm_metadata)

        # Verify data exists
        scrape_result = await cache_manager.get_scrape_result(sample_scrape_result.url)
        llm_metadata = await cache_manager.get_llm_metadata(sample_llm_metadata.url)
        assert scrape_result is not None
        assert llm_metadata is not None

        # Clear cache
        await cache_manager.clear_cache()

        # Verify data is gone
        scrape_result = await cache_manager.get_scrape_result(sample_scrape_result.url)
        llm_metadata = await cache_manager.get_llm_metadata(sample_llm_metadata.url)
        assert scrape_result is None
        assert llm_metadata is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test cache statistics functionality."""
        # Initially empty
        stats = await cache_manager.get_cache_stats()
        assert stats["scrape_results_count"] == 0
        assert stats["llm_metadata_count"] == 0
        assert stats["total_tokens_used"] == 0

        # Add some data
        scrape_result = ScrapeResult(
            url="https://example1.com", text="Test text", html_title="Test title"
        )
        await cache_manager.store_scrape_result(scrape_result)

        llm_metadata1 = LLMMetadata(
            url="https://example1.com",
            name="Example 1",
            description="First example",
            tokens_used=100,
        )
        llm_metadata2 = LLMMetadata(
            url="https://example2.com",
            name="Example 2",
            description="Second example",
            tokens_used=150,
        )
        await cache_manager.store_llm_metadata(llm_metadata1)
        await cache_manager.store_llm_metadata(llm_metadata2)

        # Check updated stats
        stats = await cache_manager.get_cache_stats()
        assert stats["scrape_results_count"] == 1
        assert stats["llm_metadata_count"] == 2
        assert stats["total_tokens_used"] == 250

    @pytest.mark.asyncio
    async def test_default_cache_directory(self):
        """Test that default cache directory is created."""
        cache_manager = CacheManager()  # Use default directory
        await cache_manager.initialize()

        expected_dir = Path.home() / ".ombm"
        assert cache_manager.db_path.parent == expected_dir
        assert cache_manager.db_path.exists()
