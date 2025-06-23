"""Tests for the bookmark adapter."""

from datetime import datetime

import pytest

from ombm.bookmark_adapter import BookmarkAdapter
from ombm.models import BookmarkRecord


class TestBookmarkAdapter:
    """Test cases for BookmarkAdapter."""

    @pytest.mark.asyncio
    async def test_get_bookmarks_returns_records(self):
        """Test that get_bookmarks returns at least one BookmarkRecord."""
        adapter = BookmarkAdapter()
        bookmarks = await adapter.get_bookmarks()

        # Acceptance criteria: Unit test asserts ≥1 BookmarkRecord
        assert len(bookmarks) >= 1

        # Verify all returned items are BookmarkRecord instances
        for bookmark in bookmarks:
            assert isinstance(bookmark, BookmarkRecord)
            assert isinstance(bookmark.uuid, str)
            assert isinstance(bookmark.title, str)
            assert isinstance(bookmark.url, str)
            assert isinstance(bookmark.created_at, datetime)
            assert len(bookmark.uuid) > 0
            assert len(bookmark.title) > 0
            assert bookmark.url.startswith("http")

    @pytest.mark.asyncio
    async def test_get_bookmarks_with_max_count(self):
        """Test that max_count parameter limits the number of returned bookmarks."""
        adapter = BookmarkAdapter()

        # Test with max_count = 3
        bookmarks = await adapter.get_bookmarks(max_count=3)
        assert len(bookmarks) == 3

        # Test with max_count = 1
        bookmarks = await adapter.get_bookmarks(max_count=1)
        assert len(bookmarks) == 1

        # Test with max_count larger than available bookmarks
        bookmarks_all = await adapter.get_bookmarks()
        total_count = len(bookmarks_all)
        bookmarks_large = await adapter.get_bookmarks(max_count=total_count + 10)
        assert len(bookmarks_large) == total_count

    @pytest.mark.asyncio
    async def test_get_bookmarks_without_max_count(self):
        """Test that get_bookmarks without max_count returns all mock bookmarks."""
        adapter = BookmarkAdapter()
        bookmarks = await adapter.get_bookmarks()

        # Should return all mock bookmarks (currently 8 in the implementation)
        assert len(bookmarks) >= 8

        # Verify unique UUIDs
        uuids = [bookmark.uuid for bookmark in bookmarks]
        assert len(uuids) == len(set(uuids)), "All bookmark UUIDs should be unique"

    @pytest.mark.asyncio
    async def test_bookmark_record_fields(self):
        """Test that BookmarkRecord fields are properly populated."""
        adapter = BookmarkAdapter()
        bookmarks = await adapter.get_bookmarks(max_count=1)

        bookmark = bookmarks[0]

        # Test UUID format (should be valid UUID string)
        import uuid

        try:
            uuid.UUID(bookmark.uuid)
        except ValueError:
            pytest.fail("UUID should be a valid UUID string")

        # Test URL format
        assert bookmark.url.startswith(("http://", "https://"))

        # Test datetime
        assert bookmark.created_at <= datetime.now()
