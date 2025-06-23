"""
Tree builder module for OMBM - converts taxonomy JSON to FolderNode structures.

This module provides functionality to parse LLM-generated taxonomy JSON
and convert it into structured FolderNode objects for tree rendering.
"""

import logging

from .models import FolderNode, LLMMetadata

logger = logging.getLogger(__name__)


class TreeBuilderError(Exception):
    """Base exception for tree builder-related errors."""

    pass


class TaxonomyParser:
    """
    Parser that converts LLM taxonomy JSON responses into FolderNode structures.

    This class handles the conversion of the hierarchical JSON structure returned
    by the LLM into typed FolderNode objects that can be used for tree rendering.
    """

    def __init__(self):
        """Initialize the taxonomy parser."""
        self.processed_urls: set[str] = set()
        self.missing_bookmarks: list[str] = []
        self.duplicate_bookmarks: list[str] = []

    def parse_taxonomy(
        self, taxonomy_json: dict, original_metadata: list[LLMMetadata]
    ) -> FolderNode:
        """
        Parse taxonomy JSON into a FolderNode tree structure.

        Args:
            taxonomy_json: JSON dictionary from LLM taxonomy generation
            original_metadata: Original list of metadata for validation

        Returns:
            Root FolderNode containing the complete hierarchy

        Raises:
            TreeBuilderError: If parsing fails or validation errors occur
        """
        logger.info("Parsing taxonomy JSON into FolderNode structure")

        # Reset tracking state
        self.processed_urls.clear()
        self.missing_bookmarks.clear()
        self.duplicate_bookmarks.clear()

        # Create URL -> metadata mapping for lookup
        url_to_metadata = {meta.url: meta for meta in original_metadata}

        try:
            # Validate JSON structure
            if "folders" not in taxonomy_json:
                raise TreeBuilderError("Taxonomy JSON missing 'folders' field")

            folders_data = taxonomy_json["folders"]
            if not isinstance(folders_data, list):
                raise TreeBuilderError("'folders' field must be a list")

            # Parse folders recursively
            folder_children = []
            for folder_data in folders_data:
                folder_node = self._parse_folder(folder_data, url_to_metadata)
                folder_children.append(folder_node)

            # Create root node
            root = FolderNode(name="Bookmarks", children=folder_children)

            # Validate that all bookmarks were processed
            self._validate_completeness(original_metadata)

            # Log statistics
            total_folders = self._count_folders(root)
            total_bookmarks = len(self.processed_urls)

            logger.info(
                f"Parsed taxonomy: {total_folders} folders, {total_bookmarks} bookmarks"
            )

            if self.missing_bookmarks:
                logger.warning(
                    f"Missing bookmarks not found in taxonomy: {len(self.missing_bookmarks)}"
                )

            if self.duplicate_bookmarks:
                logger.warning(
                    f"Duplicate bookmarks found: {len(self.duplicate_bookmarks)}"
                )

            return root

        except Exception as e:
            logger.error(f"Failed to parse taxonomy JSON: {e}")
            raise TreeBuilderError(f"Taxonomy parsing failed: {e}") from e

    def _parse_folder(
        self, folder_data: dict, url_to_metadata: dict[str, LLMMetadata]
    ) -> FolderNode:
        """
        Parse a single folder from the JSON data.

        Args:
            folder_data: Dictionary containing folder information
            url_to_metadata: Mapping of URLs to metadata objects

        Returns:
            FolderNode representing this folder

        Raises:
            TreeBuilderError: If folder data is invalid
        """
        # Validate folder structure
        if not isinstance(folder_data, dict):
            raise TreeBuilderError("Folder data must be a dictionary")

        if "name" not in folder_data:
            raise TreeBuilderError("Folder missing 'name' field")

        folder_name = str(folder_data["name"]).strip()
        if not folder_name:
            raise TreeBuilderError("Folder name cannot be empty")

        # Parse children
        children: list[FolderNode | LLMMetadata] = []

        # Parse bookmarks in this folder
        if "bookmarks" in folder_data:
            bookmarks_data = folder_data["bookmarks"]
            if not isinstance(bookmarks_data, list):
                raise TreeBuilderError("'bookmarks' field must be a list")

            for bookmark_data in bookmarks_data:
                bookmark = self._parse_bookmark(bookmark_data, url_to_metadata)
                if bookmark:
                    children.append(bookmark)

        # Parse subfolders
        if "subfolders" in folder_data:
            subfolders_data = folder_data["subfolders"]
            if not isinstance(subfolders_data, list):
                raise TreeBuilderError("'subfolders' field must be a list")

            for subfolder_data in subfolders_data:
                subfolder = self._parse_folder(subfolder_data, url_to_metadata)
                children.append(subfolder)

        return FolderNode(name=folder_name, children=children)

    def _parse_bookmark(
        self, bookmark_data: dict, url_to_metadata: dict[str, LLMMetadata]
    ) -> LLMMetadata | None:
        """
        Parse a single bookmark from the JSON data.

        Args:
            bookmark_data: Dictionary containing bookmark information
            url_to_metadata: Mapping of URLs to metadata objects

        Returns:
            LLMMetadata object or None if bookmark is invalid
        """
        try:
            # Validate bookmark structure
            if not isinstance(bookmark_data, dict):
                logger.warning("Bookmark data must be a dictionary, skipping")
                return None

            if "url" not in bookmark_data:
                logger.warning("Bookmark missing 'url' field, skipping")
                return None

            url = str(bookmark_data["url"]).strip()
            if not url:
                logger.warning("Bookmark URL cannot be empty, skipping")
                return None

            # Check for duplicates
            if url in self.processed_urls:
                self.duplicate_bookmarks.append(url)
                logger.warning(f"Duplicate bookmark found: {url}")
                return None

            # Look up the corresponding metadata
            if url not in url_to_metadata:
                logger.warning(f"Bookmark URL not found in original metadata: {url}")
                return None

            # Mark as processed
            self.processed_urls.add(url)

            # Return the original metadata (it has the correct structure)
            return url_to_metadata[url]

        except Exception as e:
            logger.warning(f"Error parsing bookmark: {e}")
            return None

    def _validate_completeness(self, original_metadata: list[LLMMetadata]) -> None:
        """
        Validate that all original bookmarks were included in the taxonomy.

        Args:
            original_metadata: Original list of metadata to check against
        """
        original_urls = {meta.url for meta in original_metadata}

        # Find missing bookmarks
        missing = original_urls - self.processed_urls
        self.missing_bookmarks = list(missing)

        if missing:
            logger.warning(f"Missing {len(missing)} bookmarks from taxonomy")
            for url in list(missing)[:5]:  # Log first 5
                logger.warning(f"  Missing: {url}")

    def _count_folders(self, node: FolderNode) -> int:
        """
        Recursively count the number of folders in a tree.

        Args:
            node: Root node to count from

        Returns:
            Total number of folders in the tree
        """
        count = 1  # Count this folder

        for child in node.children:
            if isinstance(child, FolderNode):
                count += self._count_folders(child)

        return count

    def get_parsing_stats(self) -> dict[str, int | list[str]]:
        """
        Get statistics about the parsing process.

        Returns:
            Dictionary with parsing statistics
        """
        return {
            "processed_bookmarks": len(self.processed_urls),
            "missing_bookmarks": len(self.missing_bookmarks),
            "duplicate_bookmarks": len(self.duplicate_bookmarks),
            "missing_urls": self.missing_bookmarks.copy(),
            "duplicate_urls": self.duplicate_bookmarks.copy(),
        }


def parse_taxonomy_to_tree(
    taxonomy_json: dict, original_metadata: list[LLMMetadata]
) -> FolderNode:
    """
    Convenience function to parse taxonomy JSON into a FolderNode tree.

    Args:
        taxonomy_json: JSON dictionary from LLM taxonomy generation
        original_metadata: Original list of metadata for validation

    Returns:
        Root FolderNode containing the complete hierarchy

    Raises:
        TreeBuilderError: If parsing fails
    """
    parser = TaxonomyParser()
    return parser.parse_taxonomy(taxonomy_json, original_metadata)


def validate_taxonomy_json(taxonomy_json: dict) -> bool:
    """
    Validate that taxonomy JSON has the expected structure.

    Args:
        taxonomy_json: JSON dictionary to validate

    Returns:
        True if structure is valid, False otherwise
    """
    try:
        if not isinstance(taxonomy_json, dict):
            return False

        if "folders" not in taxonomy_json:
            return False

        folders = taxonomy_json["folders"]
        if not isinstance(folders, list):
            return False

        # Validate each folder has required fields
        for folder in folders:
            if not isinstance(folder, dict):
                return False

            if "name" not in folder:
                return False

            # Check optional fields are correct types if present
            if "bookmarks" in folder and not isinstance(folder["bookmarks"], list):
                return False

            if "subfolders" in folder and not isinstance(folder["subfolders"], list):
                return False

        return True

    except Exception:
        return False
