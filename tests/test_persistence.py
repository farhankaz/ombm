from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ombm.persistence import PersistenceManager


@pytest.fixture
def mock_logger():
    with patch("ombm.persistence.log") as mock_log:
        yield mock_log


@pytest.mark.asyncio
async def test_backup_bookmarks_dry_run(mock_logger: MagicMock):
    """Test that backup is skipped in dry-run mode."""
    manager = PersistenceManager(dry_run=True)
    result = await manager.backup_bookmarks()

    assert result == Path("/tmp/dry_run_backup.plist")
    mock_logger.info.assert_called_with("DRY RUN: Skipping bookmark backup.")


@pytest.mark.asyncio
@patch("ombm.persistence.Path.exists", return_value=False)
async def test_backup_bookmarks_file_not_found(
    mock_exists: MagicMock, mock_logger: MagicMock
):
    """Test that backup is skipped if Bookmarks.plist doesn't exist."""
    manager = PersistenceManager(dry_run=False)
    result = await manager.backup_bookmarks()

    assert result == Path("/tmp/no_backup_made.plist")
    mock_logger.warning.assert_called_with(
        "Could not find Bookmarks.plist, skipping backup.",
        path=str(Path.home() / "Library/Safari/Bookmarks.plist"),
    )


@pytest.mark.asyncio
@patch("ombm.persistence.Path.exists", return_value=True)
@patch("shutil.copy")
async def test_backup_bookmarks_success(
    mock_copy: MagicMock, mock_exists: MagicMock, mock_logger: MagicMock
):
    """Test successful bookmark backup."""
    manager = PersistenceManager(dry_run=False)
    with patch("ombm.persistence.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        backup_path = await manager.backup_bookmarks()

    expected_path = Path.home() / ".ombm/backups/bookmarks_20240101_120000.plist"
    assert backup_path == expected_path
    mock_copy.assert_called_once_with(
        Path.home() / "Library/Safari/Bookmarks.plist", expected_path
    )
    mock_logger.info.assert_any_call(
        "Backing up Safari bookmarks",
        source=Path.home() / "Library/Safari/Bookmarks.plist",
        destination=expected_path,
    )
    mock_logger.info.assert_any_call(
        "Bookmark backup created successfully", path=expected_path
    )


@pytest.mark.asyncio
async def test_run_applescript_dry_run(mock_logger: MagicMock):
    """Test that AppleScript execution is skipped in dry-run mode."""
    manager = PersistenceManager(dry_run=True)
    result = await manager._run_applescript("create_folder", folder_name="Test")

    assert result == "dry-run"
    mock_logger.info.assert_called_with(
        "DRY RUN: AppleScript execution skipped.",
        script_name="create_folder",
    )


@pytest.mark.asyncio
async def test_apply_taxonomy_dry_run(mock_logger: MagicMock):
    """Test that taxonomy application is skipped in dry-run mode."""
    manager = PersistenceManager(dry_run=True)
    manager._traverse_and_apply = AsyncMock()  # Mock the recursive method
    await manager.apply_taxonomy(MagicMock())

    mock_logger.info.assert_any_call("Applying taxonomy to Safari", dry_run=True)
    mock_logger.info.assert_any_call("DRY RUN: Skipping taxonomy application.")
    manager._traverse_and_apply.assert_not_called()
