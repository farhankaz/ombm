"""Safari bookmark adapter for macOS."""

import uuid as uuid_module
from datetime import datetime, timedelta

from .models import BookmarkRecord


class BookmarkAdapter:
    """Adapter for retrieving Safari bookmarks on macOS."""

    async def get_bookmarks(self, max_count: int = None) -> list[BookmarkRecord]:
        """
        Retrieve Safari bookmarks from macOS.

        For now, this returns mocked data. In the future, this will use
        AppleScript to extract actual Safari bookmarks.

        Args:
            max_count: Maximum number of bookmarks to return (None for all)

        Returns:
            List of BookmarkRecord objects
        """
        # Mock bookmark data for testing
        mock_bookmarks = [
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="GitHub - Python",
                url="https://github.com/python/cpython",
                created_at=datetime.now() - timedelta(days=30)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="OpenAI API Documentation",
                url="https://platform.openai.com/docs/api-reference",
                created_at=datetime.now() - timedelta(days=15)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="Playwright for Python",
                url="https://playwright.dev/python/",
                created_at=datetime.now() - timedelta(days=7)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="Typer Documentation",
                url="https://typer.tiangolo.com/",
                created_at=datetime.now() - timedelta(days=5)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="Rich Library",
                url="https://rich.readthedocs.io/en/stable/",
                created_at=datetime.now() - timedelta(days=3)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="Python asyncio Documentation",
                url="https://docs.python.org/3/library/asyncio.html",
                created_at=datetime.now() - timedelta(days=2)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="SQLite Tutorial",
                url="https://www.sqlitetutorial.net/",
                created_at=datetime.now() - timedelta(days=1)
            ),
            BookmarkRecord(
                uuid=str(uuid_module.uuid4()),
                title="Homebrew Formula Cookbook",
                url="https://docs.brew.sh/Formula-Cookbook",
                created_at=datetime.now() - timedelta(hours=12)
            ),
        ]

        # Apply max_count limit if specified
        if max_count is not None:
            mock_bookmarks = mock_bookmarks[:max_count]

        return mock_bookmarks


# TODO: Implement actual Safari bookmark extraction using AppleScript
# Example AppleScript commands that will be used in the future:
"""
tell application "Safari"
    set bookmarkList to {}
    repeat with bookmark in bookmarks
        set end of bookmarkList to {name:(name of bookmark), URL:(URL of bookmark)}
    end repeat
    return bookmarkList
end tell
"""
