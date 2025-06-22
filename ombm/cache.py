"""SQLite cache layer for OMBM."""

import hashlib
from pathlib import Path

import aiosqlite

from .models import LLMMetadata, ScrapeResult


class CacheManager:
    """Manages SQLite cache for scraping results and LLM metadata."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache database. Defaults to ~/.ombm/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".ombm"

        cache_dir.mkdir(exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database tables if they don't exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scrape_results (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    text TEXT NOT NULL,
                    html_title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS llm_metadata (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indices for better query performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_scrape_url ON scrape_results(url)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_llm_url ON llm_metadata(url)")

            await db.commit()

        self._initialized = True

    def _hash_url(self, url: str) -> str:
        """Generate hash for URL to use as cache key."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    async def get_scrape_result(self, url: str) -> ScrapeResult | None:
        """Retrieve cached scrape result for URL.

        Args:
            url: URL to lookup

        Returns:
            ScrapeResult if found in cache, None otherwise
        """
        await self.initialize()
        url_hash = self._hash_url(url)

        async with aiosqlite.connect(self.db_path) as db, db.execute(
            "SELECT url, text, html_title FROM scrape_results WHERE url_hash = ?",
            (url_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return ScrapeResult(
                    url=row[0],
                    text=row[1],
                    html_title=row[2]
                )
        return None

    async def store_scrape_result(self, result: ScrapeResult) -> None:
        """Store scrape result in cache.

        Args:
            result: ScrapeResult to cache
        """
        await self.initialize()
        url_hash = self._hash_url(result.url)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO scrape_results
                (url_hash, url, text, html_title)
                VALUES (?, ?, ?, ?)
            """, (url_hash, result.url, result.text, result.html_title))
            await db.commit()

    async def get_llm_metadata(self, url: str) -> LLMMetadata | None:
        """Retrieve cached LLM metadata for URL.

        Args:
            url: URL to lookup

        Returns:
            LLMMetadata if found in cache, None otherwise
        """
        await self.initialize()
        url_hash = self._hash_url(url)

        async with aiosqlite.connect(self.db_path) as db, db.execute(
            "SELECT url, name, description, tokens_used FROM llm_metadata WHERE url_hash = ?",
            (url_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return LLMMetadata(
                    url=row[0],
                    name=row[1],
                    description=row[2],
                    tokens_used=row[3]
                )
        return None

    async def store_llm_metadata(self, metadata: LLMMetadata) -> None:
        """Store LLM metadata in cache.

        Args:
            metadata: LLMMetadata to cache
        """
        await self.initialize()
        url_hash = self._hash_url(metadata.url)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO llm_metadata
                (url_hash, url, name, description, tokens_used)
                VALUES (?, ?, ?, ?, ?)
            """, (url_hash, metadata.url, metadata.name, metadata.description, metadata.tokens_used))
            await db.commit()

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM scrape_results")
            await db.execute("DELETE FROM llm_metadata")
            await db.commit()

    async def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            # Count scrape results
            async with db.execute("SELECT COUNT(*) FROM scrape_results") as cursor:
                scrape_count = (await cursor.fetchone())[0]

            # Count LLM metadata
            async with db.execute("SELECT COUNT(*) FROM llm_metadata") as cursor:
                llm_count = (await cursor.fetchone())[0]

            # Total tokens used
            async with db.execute("SELECT SUM(tokens_used) FROM llm_metadata") as cursor:
                total_tokens = (await cursor.fetchone())[0] or 0

        return {
            "scrape_results_count": scrape_count,
            "llm_metadata_count": llm_count,
            "total_tokens_used": total_tokens
        }
