"""
Controller module for OMBM - orchestrates the bookmark processing pipeline.

This module provides high-level coordination of bookmark processing,
metadata aggregation, taxonomy generation, and tree rendering.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from .bookmark_adapter import BookmarkAdapter
from .models import BookmarkRecord, FolderNode, LLMMetadata
from .persistence import PersistenceManager
from .pipeline import BookmarkProcessor

logger = logging.getLogger(__name__)


class ControllerError(Exception):
    """Base exception for controller-related errors."""

    pass


class BookmarkController:
    """
    High-level controller that orchestrates the complete bookmark organization pipeline.

    This controller manages the flow from bookmark retrieval through metadata generation
    to taxonomy creation and tree rendering.
    """

    def __init__(
        self,
        bookmark_adapter: BookmarkAdapter | None = None,
        processor: BookmarkProcessor | None = None,
        persistence_manager: PersistenceManager | None = None,
    ):
        """
        Initialize the bookmark controller.

        Args:
            bookmark_adapter: Adapter for retrieving bookmarks (created if None)
            processor: Bookmark processor for the pipeline (created if None)
            persistence_manager: Manager for applying changes to Safari
        """
        self.bookmark_adapter = bookmark_adapter or BookmarkAdapter()
        self.processor = processor
        self.persistence_manager = persistence_manager
        self._processor_context: BookmarkProcessor | None = None
        self._manages_processor_lifecycle = False

    async def __aenter__(self) -> "BookmarkController":
        """Async context manager entry."""
        if self.processor is None:
            self.processor = BookmarkProcessor()
            self._manages_processor_lifecycle = True

        self._processor_context = await self.processor.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_val: Exception | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if self.processor and self._manages_processor_lifecycle:
            await self.processor.__aexit__(exc_type, exc_val, exc_tb)
        self.processor = None
        self._processor_context = None
        self._manages_processor_lifecycle = False

    async def get_bookmarks(
        self, max_bookmarks: int | None = None
    ) -> list[BookmarkRecord]:
        """
        Retrieve bookmarks from Safari.

        Args:
            max_bookmarks: Maximum number of bookmarks to retrieve (None for all)

        Returns:
            List of BookmarkRecord objects

        Raises:
            ControllerError: If bookmark retrieval fails
        """
        try:
            logger.info(f"Retrieving bookmarks (max: {max_bookmarks or 'unlimited'})")
            bookmarks = await self.bookmark_adapter.get_bookmarks()

            if max_bookmarks is not None and len(bookmarks) > max_bookmarks:
                bookmarks = bookmarks[:max_bookmarks]
                logger.info(f"Limited to {max_bookmarks} bookmarks")

            logger.info(f"Retrieved {len(bookmarks)} bookmarks")
            return bookmarks

        except Exception as e:
            logger.error(f"Failed to retrieve bookmarks: {e}")
            raise ControllerError(f"Bookmark retrieval failed: {e}") from e

    async def process_bookmarks_to_metadata(
        self,
        bookmarks: list[BookmarkRecord],
        concurrency: int = 4,
        force_refresh: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[LLMMetadata]:
        """
        Process bookmarks through the pipeline to generate metadata.

        Args:
            bookmarks: List of bookmarks to process
            concurrency: Maximum concurrent operations
            force_refresh: Whether to skip cache and force fresh processing
            progress_callback: Optional callback for progress updates (completed, total)

        Returns:
            List of LLMMetadata for successfully processed bookmarks

        Raises:
            ControllerError: If processor is not initialized
        """
        if self.processor is None:
            raise ControllerError("Processor not initialized")

        logger.info(f"Processing {len(bookmarks)} bookmarks to generate metadata")

        # Process all bookmarks
        results = await self.processor.process_bookmarks(
            bookmarks,
            concurrency=concurrency,
            force_refresh=force_refresh,
            progress_callback=progress_callback,
        )

        # Extract successful metadata
        metadata_list: list[LLMMetadata] = []
        errors: list[str] = []

        for result in results:
            if result.success and result.llm_metadata is not None:
                metadata_list.append(result.llm_metadata)
            elif result.error:
                errors.append(f"{result.bookmark.url}: {result.error}")

        # Log summary
        logger.info(
            f"Metadata generation complete: {len(metadata_list)}/{len(bookmarks)} successful"
        )

        if errors:
            logger.warning(f"Failed to process {len(errors)} bookmarks:")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(f"  {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")

        return metadata_list

    async def aggregate_metadata_collection(
        self,
        max_bookmarks: int | None = None,
        concurrency: int = 4,
        force_refresh: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[LLMMetadata]:
        """
        Complete pipeline from bookmark retrieval to metadata aggregation.

        This is the main method that implements T-21: Aggregate metadata collection.
        It retrieves bookmarks and processes them to build a list of LLMMetadata.

        Args:
            max_bookmarks: Maximum number of bookmarks to process
            concurrency: Maximum concurrent operations
            force_refresh: Whether to skip cache and force fresh processing
            progress_callback: Optional callback for progress updates (completed, total)

        Returns:
            List of LLMMetadata objects for all successfully processed bookmarks

        Raises:
            ControllerError: If any step in the pipeline fails
        """
        logger.info("Starting aggregate metadata collection pipeline")

        try:
            # Step 1: Retrieve bookmarks
            bookmarks = await self.get_bookmarks(max_bookmarks)

            if not bookmarks:
                logger.warning("No bookmarks found")
                return []

            # Step 2: Process bookmarks to metadata
            metadata_list = await self.process_bookmarks_to_metadata(
                bookmarks,
                concurrency=concurrency,
                force_refresh=force_refresh,
                progress_callback=progress_callback,
            )

            logger.info(
                f"Aggregate metadata collection complete: {len(metadata_list)} items"
            )
            return metadata_list

        except Exception as e:
            logger.error(f"Aggregate metadata collection failed: {e}")
            raise ControllerError(f"Pipeline failed: {e}") from e

    async def get_processing_stats(self) -> dict[str, object]:
        """
        Get statistics about the processing pipeline.

        Returns:
            Dictionary with processing statistics
        """
        if self.processor is None:
            return {"processor_initialized": False}

        stats = await self.processor.get_processing_stats()
        stats["processor_initialized"] = True
        return stats

    def export_metadata_to_json(
        self,
        metadata_list: list[LLMMetadata],
        output_path: str | Path,
        include_metadata: bool = True,
    ) -> None:
        """
        Export bookmark metadata to JSON file.

        Args:
            metadata_list: List of LLMMetadata to export
            output_path: Path to write JSON file
            include_metadata: Whether to include export metadata

        Raises:
            ControllerError: If export fails
        """
        try:
            output_path = Path(output_path)

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare export data
            export_data: dict[str, object] = {
                "bookmarks": [
                    {
                        "url": meta.url,
                        "name": meta.name,
                        "description": meta.description,
                        "tokens_used": meta.tokens_used,
                    }
                    for meta in metadata_list
                ]
            }

            if include_metadata:
                export_data["_metadata"] = {
                    "export_timestamp": asyncio.get_event_loop().time(),
                    "bookmark_count": len(metadata_list),
                    "total_tokens": sum(meta.tokens_used for meta in metadata_list),
                    "format_version": "1.0",
                }

            # Write JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(metadata_list)} bookmarks to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export metadata to JSON: {e}")
            raise ControllerError(f"JSON export failed: {e}") from e

    def export_taxonomy_to_json(
        self,
        taxonomy_data: dict[str, Any],
        output_path: str | Path,
        include_metadata: bool = True,
    ) -> None:
        """
        Export generated taxonomy to JSON file.

        Args:
            taxonomy_data: Taxonomy dictionary from LLM
            output_path: Path to write JSON file
            include_metadata: Whether to include export metadata

        Raises:
            ControllerError: If export fails
        """
        try:
            output_path = Path(output_path)

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare export data (copy to avoid modifying original)
            export_data: dict[str, object] = taxonomy_data.copy()

            if include_metadata:
                export_data["metadata"] = {
                    "export_date": datetime.now().isoformat(),
                    "total_bookmarks": len(taxonomy_data.get("bookmarks", [])),
                }

            output_path.write_text(json.dumps(export_data, indent=2))
            logger.info(f"Successfully exported taxonomy to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export taxonomy to JSON: {e}")
            raise ControllerError(f"JSON export failed: {e}") from e

    def export_folder_tree_to_json(
        self, root: FolderNode, output_path: str | Path, include_metadata: bool = True
    ) -> None:
        """
        Export FolderNode tree structure to JSON file.

        Args:
            root: Root FolderNode to export
            output_path: Path to write JSON file
            include_metadata: Whether to include export metadata

        Raises:
            ControllerError: If export fails
        """
        try:
            output_path = Path(output_path)

            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert FolderNode to dict recursively
            def folder_to_dict(node: FolderNode) -> dict[str, Any]:
                result: dict[str, Any] = {"name": node.name, "children": []}

                for child in node.children:
                    if isinstance(child, FolderNode):
                        result["children"].append(
                            {"type": "folder", "data": folder_to_dict(child)}
                        )
                    else:  # LLMMetadata
                        result["children"].append(
                            {
                                "type": "bookmark",
                                "data": {
                                    "url": child.url,
                                    "name": child.name,
                                    "description": child.description,
                                    "tokens_used": child.tokens_used,
                                },
                            }
                        )

                return result

            # Prepare export data
            export_data: dict[str, Any] = {"tree": folder_to_dict(root)}

            if include_metadata:
                # Calculate stats
                total_folders = self._count_folders_in_tree(root)
                total_bookmarks = self._count_bookmarks_in_tree(root)

                export_data["_metadata"] = {
                    "export_timestamp": asyncio.get_event_loop().time(),
                    "total_folders": total_folders,
                    "total_bookmarks": total_bookmarks,
                    "format_version": "1.0",
                }

            # Write JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported folder tree to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export folder tree to JSON: {e}")
            raise ControllerError(f"Folder tree JSON export failed: {e}") from e

    def _count_folders_in_tree(self, node: FolderNode) -> int:
        """Count total folders in tree."""
        count = 1  # Count this folder
        for child in node.children:
            if isinstance(child, FolderNode):
                count += self._count_folders_in_tree(child)
        return count

    def _count_bookmarks_in_tree(self, node: FolderNode) -> int:
        """Count total bookmarks in tree."""
        count = 0
        for child in node.children:
            if isinstance(child, FolderNode):
                count += self._count_bookmarks_in_tree(child)
            else:  # LLMMetadata
                count += 1
        return count

    async def apply_taxonomy(self, taxonomy_tree: FolderNode) -> None:
        """
        Apply the generated taxonomy to Safari bookmarks using the PersistenceManager.
        """
        if not self.persistence_manager:
            raise ControllerError("PersistenceManager not configured.")

        if self.persistence_manager.dry_run:
            logger.info("Dry run: Skipping application of taxonomy.")
            return

        logger.info("Applying generated taxonomy to Safari.")
        await self.persistence_manager.apply_taxonomy(taxonomy_tree)


# Convenience function for quick metadata aggregation
async def aggregate_bookmark_metadata(
    max_bookmarks: int | None = None,
    concurrency: int = 4,
    force_refresh: bool = False,
    use_cache: bool = True,
) -> list[LLMMetadata]:
    """
    High-level convenience function to run the metadata aggregation pipeline.

    This function provides a simplified interface for retrieving and processing
    bookmark metadata.

    Args:
        max_bookmarks: Maximum number of bookmarks to process
        concurrency: Maximum concurrent operations
        force_refresh: Whether to skip cache and force fresh processing
        use_cache: Whether to use caching

    Returns:
        List of LLMMetadata objects
    """
    processor = BookmarkProcessor(use_cache=use_cache)

    async with BookmarkController(processor=processor) as controller:
        return await controller.aggregate_metadata_collection(
            max_bookmarks=max_bookmarks,
            concurrency=concurrency,
            force_refresh=force_refresh,
        )
