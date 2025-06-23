"""
Tests for the controller module.

This module tests the BookmarkController class and its methods for orchestrating
the bookmark processing pipeline, including metadata aggregation and JSON export.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ombm.controller import (
    BookmarkController,
    ControllerError,
    aggregate_bookmark_metadata,
)
from ombm.models import BookmarkRecord, FolderNode, LLMMetadata


@pytest.fixture
def sample_bookmarks():
    """Sample bookmark records for testing."""
    return [
        BookmarkRecord(
            uuid="1",
            title="Example Site",
            url="https://example.com",
            created_at=datetime.now(),
        ),
        BookmarkRecord(
            uuid="2",
            title="Test Blog",
            url="https://test.blog",
            created_at=datetime.now(),
        ),
    ]


@pytest.fixture
def sample_metadata():
    """Sample LLM metadata for testing."""
    return [
        LLMMetadata(
            url="https://example.com",
            name="Example Website",
            description="A sample website for testing",
            tokens_used=50,
        ),
        LLMMetadata(
            url="https://test.blog",
            name="Test Blog Site",
            description="A blog for testing purposes",
            tokens_used=45,
        ),
    ]


@pytest.fixture
def sample_folder_tree():
    """Sample folder tree for testing."""
    return FolderNode(
        name="Bookmarks",
        children=[
            FolderNode(
                name="Development",
                children=[
                    LLMMetadata(
                        url="https://example.com",
                        name="Example Website",
                        description="A sample website for testing",
                        tokens_used=50,
                    )
                ],
            ),
            FolderNode(
                name="Blogs",
                children=[
                    LLMMetadata(
                        url="https://test.blog",
                        name="Test Blog Site",
                        description="A blog for testing purposes",
                        tokens_used=45,
                    )
                ],
            ),
        ],
    )


class TestBookmarkController:
    """Test cases for BookmarkController class."""

    @pytest.fixture
    def mock_bookmark_adapter(self):
        """Mock bookmark adapter."""
        adapter = AsyncMock()
        adapter.get_bookmarks = AsyncMock()
        return adapter

    @pytest.fixture
    def mock_processor(self):
        """Mock bookmark processor."""
        processor = AsyncMock()
        processor.__aenter__ = AsyncMock(return_value=processor)
        processor.__aexit__ = AsyncMock()
        processor.process_bookmarks = AsyncMock()
        processor.get_processing_stats = AsyncMock(return_value={"cache_enabled": True})
        return processor

    @pytest.fixture
    def controller(self, mock_bookmark_adapter, mock_processor):
        """Controller instance with mocked dependencies."""
        return BookmarkController(
            bookmark_adapter=mock_bookmark_adapter, processor=mock_processor
        )

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_processor):
        """Test async context manager functionality."""
        # Test with a processor that is externally created and passed
        controller = BookmarkController(processor=mock_processor)
        async with controller as ctx:
            assert ctx is controller
            assert controller.processor is mock_processor
            assert controller._processor_context is not None

        # __aexit__ should not be called on processors we don't create
        mock_processor.__aenter__.assert_called_once()
        mock_processor.__aexit__.assert_not_called()

        # Test with a processor that the controller creates
        mock_processor.reset_mock()
        controller = BookmarkController(processor=None)
        # We need to mock the created processor
        with patch("ombm.controller.BookmarkProcessor", return_value=mock_processor):
            async with controller as ctx:
                assert ctx is controller
                assert controller.processor is mock_processor
                assert controller._processor_context is not None

            mock_processor.__aenter__.assert_called_once()
            mock_processor.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_bookmarks_success(
        self, controller, mock_bookmark_adapter, sample_bookmarks
    ):
        """Test successful bookmark retrieval."""
        mock_bookmark_adapter.get_bookmarks.return_value = sample_bookmarks

        result = await controller.get_bookmarks()

        assert result == sample_bookmarks
        assert len(result) == 2
        mock_bookmark_adapter.get_bookmarks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_bookmarks_with_limit(
        self, controller, mock_bookmark_adapter, sample_bookmarks
    ):
        """Test bookmark retrieval with limit."""
        mock_bookmark_adapter.get_bookmarks.return_value = sample_bookmarks

        result = await controller.get_bookmarks(max_bookmarks=1)

        assert len(result) == 1
        assert result[0] == sample_bookmarks[0]

    @pytest.mark.asyncio
    async def test_get_bookmarks_failure(self, controller, mock_bookmark_adapter):
        """Test bookmark retrieval failure."""
        mock_bookmark_adapter.get_bookmarks.side_effect = Exception("Adapter failed")

        with pytest.raises(ControllerError, match="Bookmark retrieval failed"):
            await controller.get_bookmarks()

    @pytest.mark.asyncio
    async def test_process_bookmarks_to_metadata_success(
        self, controller, mock_processor, sample_bookmarks, sample_metadata
    ):
        """Test successful metadata processing."""
        # Mock successful processing results
        from ombm.pipeline import ProcessingResult

        results = [
            ProcessingResult(
                bookmark=sample_bookmarks[0], llm_metadata=sample_metadata[0]
            ),
            ProcessingResult(
                bookmark=sample_bookmarks[1], llm_metadata=sample_metadata[1]
            ),
        ]

        mock_processor.process_bookmarks.return_value = results

        result = await controller.process_bookmarks_to_metadata(sample_bookmarks)

        assert len(result) == 2
        assert result == sample_metadata
        mock_processor.process_bookmarks.assert_called_once_with(
            sample_bookmarks, concurrency=4, force_refresh=False
        )

    @pytest.mark.asyncio
    async def test_process_bookmarks_with_errors(
        self, controller, mock_processor, sample_bookmarks
    ):
        """Test metadata processing with some errors."""
        from ombm.pipeline import ProcessingResult

        results = [
            ProcessingResult(bookmark=sample_bookmarks[0], error="Scraping failed"),
            ProcessingResult(
                bookmark=sample_bookmarks[1],
                llm_metadata=LLMMetadata(
                    url=sample_bookmarks[1].url,
                    name="Test Blog",
                    description="Test description",
                    tokens_used=30,
                ),
            ),
        ]

        mock_processor.process_bookmarks.return_value = results

        result = await controller.process_bookmarks_to_metadata(sample_bookmarks)

        assert len(result) == 1  # Only successful ones returned
        assert result[0].url == sample_bookmarks[1].url

    @pytest.mark.asyncio
    async def test_aggregate_metadata_collection(
        self,
        controller,
        mock_bookmark_adapter,
        mock_processor,
        sample_bookmarks,
        sample_metadata,
    ):
        """Test complete metadata aggregation pipeline."""
        # Mock bookmark retrieval
        mock_bookmark_adapter.get_bookmarks.return_value = sample_bookmarks

        # Mock processing results
        from ombm.pipeline import ProcessingResult

        results = [
            ProcessingResult(bookmark=b, llm_metadata=m)
            for b, m in zip(sample_bookmarks, sample_metadata, strict=False)
        ]
        mock_processor.process_bookmarks.return_value = results

        async with controller:
            result = await controller.aggregate_metadata_collection(
                max_bookmarks=10, concurrency=2
            )

        assert len(result) == 2
        assert result == sample_metadata
        mock_bookmark_adapter.get_bookmarks.assert_called_once()
        mock_processor.process_bookmarks.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_processing_stats(self, controller, mock_processor):
        """Test processing statistics retrieval."""
        mock_stats = {"cache_enabled": True, "cached_items": 5}
        mock_processor.get_processing_stats.return_value = mock_stats

        async with controller:
            stats = await controller.get_processing_stats()

        assert stats["processor_initialized"] is True
        assert stats["cache_enabled"] is True
        assert stats["cached_items"] == 5

    def test_export_metadata_to_json(self, controller, sample_metadata):
        """Test metadata export to JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "metadata.json"

            controller.export_metadata_to_json(sample_metadata, output_path)

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "bookmarks" in data
            assert len(data["bookmarks"]) == 2
            assert data["bookmarks"][0]["url"] == "https://example.com"
            assert data["bookmarks"][0]["name"] == "Example Website"

            # Check metadata
            assert "_metadata" in data
            assert data["_metadata"]["bookmark_count"] == 2
            assert data["_metadata"]["total_tokens"] == 95

    def test_export_taxonomy_to_json(self, controller):
        """Test taxonomy export to JSON."""
        taxonomy_data = {
            "folders": [
                {
                    "name": "Development",
                    "bookmarks": [
                        {
                            "url": "https://example.com",
                            "name": "Example",
                            "description": "Test",
                        }
                    ],
                    "subfolders": [],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "taxonomy.json"

            controller.export_taxonomy_to_json(taxonomy_data, output_path)

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "folders" in data
            assert len(data["folders"]) == 1
            assert data["folders"][0]["name"] == "Development"

    def test_export_folder_tree_to_json(self, controller, sample_folder_tree):
        """Test folder tree export to JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "tree.json"

            controller.export_folder_tree_to_json(sample_folder_tree, output_path)

            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "tree" in data
            assert data["tree"]["name"] == "Bookmarks"
            assert len(data["tree"]["children"]) == 2

            # Check metadata
            assert "_metadata" in data
            assert data["_metadata"]["total_folders"] == 3  # Root + 2 children
            assert data["_metadata"]["total_bookmarks"] == 2

    def test_count_folders_in_tree(self, controller, sample_folder_tree):
        """Test folder counting in tree."""
        count = controller._count_folders_in_tree(sample_folder_tree)
        assert count == 3  # Root + Development + Blogs

    def test_count_bookmarks_in_tree(self, controller, sample_folder_tree):
        """Test bookmark counting in tree."""
        count = controller._count_bookmarks_in_tree(sample_folder_tree)
        assert count == 2  # 1 in Development + 1 in Blogs


@pytest.mark.asyncio
async def test_aggregate_bookmark_metadata_convenience_function():
    """Test the convenience function for metadata aggregation."""
    with patch("ombm.controller.BookmarkProcessor") as mock_processor_class:
        mock_processor = AsyncMock()
        mock_processor.__aenter__ = AsyncMock(return_value=mock_processor)
        mock_processor.__aexit__ = AsyncMock()
        mock_processor_class.return_value = mock_processor

        with patch("ombm.controller.BookmarkController") as mock_controller_class:
            mock_controller = AsyncMock()
            mock_controller.__aenter__ = AsyncMock(return_value=mock_controller)
            mock_controller.__aexit__ = AsyncMock()
            mock_controller.aggregate_metadata_collection = AsyncMock(return_value=[])
            mock_controller_class.return_value = mock_controller

            result = await aggregate_bookmark_metadata(
                max_bookmarks=10, concurrency=2, force_refresh=True, use_cache=False
            )

            assert result == []
            mock_processor_class.assert_called_once_with(use_cache=False)
            mock_controller.aggregate_metadata_collection.assert_called_once_with(
                max_bookmarks=10, concurrency=2, force_refresh=True
            )
