"""
Tests for the tree_builder module.

This module tests the TaxonomyParser class and related functions for parsing
LLM-generated taxonomy JSON into FolderNode structures.
"""

import pytest

from ombm.models import FolderNode, LLMMetadata
from ombm.tree_builder import (
    TaxonomyParser,
    TreeBuilderError,
    parse_taxonomy_to_tree,
    validate_taxonomy_json,
)


@pytest.fixture
def sample_metadata():
    """Sample LLM metadata for testing."""
    return [
        LLMMetadata(
            url="https://example.com",
            name="Example Website",
            description="A sample website for testing",
            tokens_used=50
        ),
        LLMMetadata(
            url="https://test.blog",
            name="Test Blog Site",
            description="A blog for testing purposes",
            tokens_used=45
        ),
        LLMMetadata(
            url="https://github.com/user/repo",
            name="GitHub Repository",
            description="Open source code repository",
            tokens_used=40
        ),
    ]


@pytest.fixture
def valid_taxonomy_json():
    """Valid taxonomy JSON structure for testing."""
    return {
        "folders": [
            {
                "name": "Development",
                "bookmarks": [
                    {
                        "url": "https://github.com/user/repo",
                        "name": "GitHub Repository",
                        "description": "Open source code repository"
                    }
                ],
                "subfolders": [
                    {
                        "name": "Web Development",
                        "bookmarks": [
                            {
                                "url": "https://example.com",
                                "name": "Example Website",
                                "description": "A sample website for testing"
                            }
                        ],
                        "subfolders": []
                    }
                ]
            },
            {
                "name": "Blogs",
                "bookmarks": [
                    {
                        "url": "https://test.blog",
                        "name": "Test Blog Site",
                        "description": "A blog for testing purposes"
                    }
                ],
                "subfolders": []
            }
        ]
    }


class TestTaxonomyParser:
    """Test cases for TaxonomyParser class."""

    @pytest.fixture
    def parser(self):
        """Fresh parser instance for each test."""
        return TaxonomyParser()

    def test_parse_taxonomy_success(self, parser, valid_taxonomy_json, sample_metadata):
        """Test successful taxonomy parsing."""
        result = parser.parse_taxonomy(valid_taxonomy_json, sample_metadata)

        assert isinstance(result, FolderNode)
        assert result.name == "Bookmarks"
        assert len(result.children) == 2

        # Check Development folder
        dev_folder = result.children[0]
        assert isinstance(dev_folder, FolderNode)
        assert dev_folder.name == "Development"
        assert len(dev_folder.children) == 2  # 1 bookmark + 1 subfolder

        # Check nested Web Development folder
        web_dev_folder = dev_folder.children[1]
        assert isinstance(web_dev_folder, FolderNode)
        assert web_dev_folder.name == "Web Development"
        assert len(web_dev_folder.children) == 1

        # Check that bookmarks are LLMMetadata instances
        github_bookmark = dev_folder.children[0]
        assert isinstance(github_bookmark, LLMMetadata)
        assert github_bookmark.url == "https://github.com/user/repo"

    def test_parse_taxonomy_missing_folders(self, parser, sample_metadata):
        """Test parsing taxonomy JSON missing 'folders' field."""
        invalid_json = {"invalid": "structure"}

        with pytest.raises(TreeBuilderError, match="missing 'folders' field"):
            parser.parse_taxonomy(invalid_json, sample_metadata)

    def test_parse_taxonomy_folders_not_list(self, parser, sample_metadata):
        """Test parsing taxonomy JSON where 'folders' is not a list."""
        invalid_json = {"folders": "not_a_list"}

        with pytest.raises(TreeBuilderError, match="'folders' field must be a list"):
            parser.parse_taxonomy(invalid_json, sample_metadata)

    def test_parse_folder_missing_name(self, parser, sample_metadata):
        """Test parsing folder without name field."""
        invalid_json = {
            "folders": [
                {"bookmarks": [], "subfolders": []}  # Missing name
            ]
        }

        with pytest.raises(TreeBuilderError, match="missing 'name' field"):
            parser.parse_taxonomy(invalid_json, sample_metadata)

    def test_parse_folder_empty_name(self, parser, sample_metadata):
        """Test parsing folder with empty name."""
        invalid_json = {
            "folders": [
                {"name": "", "bookmarks": [], "subfolders": []}
            ]
        }

        with pytest.raises(TreeBuilderError, match="cannot be empty"):
            parser.parse_taxonomy(invalid_json, sample_metadata)

    def test_parse_bookmark_missing_url(self, parser, sample_metadata):
        """Test parsing bookmark without URL."""
        invalid_json = {
            "folders": [
                {
                    "name": "Test Folder",
                    "bookmarks": [
                        {"name": "Test", "description": "Test"}  # Missing URL
                    ],
                    "subfolders": []
                }
            ]
        }

        result = parser.parse_taxonomy(invalid_json, sample_metadata)

        # Should skip invalid bookmark but continue parsing
        assert isinstance(result, FolderNode)
        test_folder = result.children[0]
        assert len(test_folder.children) == 0  # Bookmark was skipped

    def test_parse_bookmark_duplicate_url(self, parser, sample_metadata):
        """Test parsing with duplicate bookmark URLs."""
        duplicate_json = {
            "folders": [
                {
                    "name": "Folder 1",
                    "bookmarks": [
                        {
                            "url": "https://example.com",
                            "name": "Example 1",
                            "description": "First instance"
                        }
                    ],
                    "subfolders": []
                },
                {
                    "name": "Folder 2",
                    "bookmarks": [
                        {
                            "url": "https://example.com",  # Duplicate
                            "name": "Example 2",
                            "description": "Second instance"
                        }
                    ],
                    "subfolders": []
                }
            ]
        }

        result = parser.parse_taxonomy(duplicate_json, sample_metadata)

        # First occurrence should be kept, second should be skipped
        folder1 = result.children[0]
        folder2 = result.children[1]

        assert len(folder1.children) == 1  # Has the bookmark
        assert len(folder2.children) == 0  # Duplicate was skipped

        # Check duplicate tracking
        assert len(parser.duplicate_bookmarks) == 1
        assert "https://example.com" in parser.duplicate_bookmarks

    def test_parse_bookmark_not_in_metadata(self, parser):
        """Test parsing bookmark URL not in original metadata."""
        taxonomy_json = {
            "folders": [
                {
                    "name": "Test Folder",
                    "bookmarks": [
                        {
                            "url": "https://unknown.com",
                            "name": "Unknown Site",
                            "description": "Not in metadata"
                        }
                    ],
                    "subfolders": []
                }
            ]
        }

        metadata = [
            LLMMetadata(
                url="https://example.com",
                name="Example",
                description="Known site",
                tokens_used=30
            )
        ]

        result = parser.parse_taxonomy(taxonomy_json, metadata)

        # Unknown bookmark should be skipped
        test_folder = result.children[0]
        assert len(test_folder.children) == 0

    def test_validate_completeness_missing_bookmarks(self, parser, sample_metadata):
        """Test completeness validation with missing bookmarks."""
        # Taxonomy that doesn't include all bookmarks
        incomplete_json = {
            "folders": [
                {
                    "name": "Partial",
                    "bookmarks": [
                        {
                            "url": "https://example.com",
                            "name": "Example Website",
                            "description": "A sample website for testing"
                        }
                    ],
                    "subfolders": []
                }
            ]
        }

        result = parser.parse_taxonomy(incomplete_json, sample_metadata)

        # Should still parse successfully but log missing bookmarks
        assert isinstance(result, FolderNode)
        assert len(parser.missing_bookmarks) == 2  # 2 missing from sample_metadata

    def test_get_parsing_stats(self, parser, valid_taxonomy_json, sample_metadata):
        """Test parsing statistics collection."""
        parser.parse_taxonomy(valid_taxonomy_json, sample_metadata)

        stats = parser.get_parsing_stats()

        assert "processed_bookmarks" in stats
        assert "missing_bookmarks" in stats
        assert "duplicate_bookmarks" in stats
        assert "missing_urls" in stats
        assert "duplicate_urls" in stats

        assert stats["processed_bookmarks"] == 3
        assert isinstance(stats["missing_urls"], list)
        assert isinstance(stats["duplicate_urls"], list)

    def test_count_folders(self, parser, valid_taxonomy_json, sample_metadata):
        """Test folder counting functionality."""
        result = parser.parse_taxonomy(valid_taxonomy_json, sample_metadata)

        folder_count = parser._count_folders(result)

        # Root + Development + Web Development + Blogs = 4
        assert folder_count == 4


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_parse_taxonomy_to_tree(self, valid_taxonomy_json, sample_metadata):
        """Test convenience function for parsing taxonomy."""
        result = parse_taxonomy_to_tree(valid_taxonomy_json, sample_metadata)

        assert isinstance(result, FolderNode)
        assert result.name == "Bookmarks"
        assert len(result.children) == 2

    def test_validate_taxonomy_json_valid(self, valid_taxonomy_json):
        """Test validation of valid taxonomy JSON."""
        assert validate_taxonomy_json(valid_taxonomy_json) is True

    def test_validate_taxonomy_json_not_dict(self):
        """Test validation of non-dictionary input."""
        assert validate_taxonomy_json("not_a_dict") is False
        assert validate_taxonomy_json([]) is False
        assert validate_taxonomy_json(None) is False

    def test_validate_taxonomy_json_missing_folders(self):
        """Test validation of JSON missing folders field."""
        invalid_json = {"other_field": "value"}
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_folders_not_list(self):
        """Test validation of JSON where folders is not a list."""
        invalid_json = {"folders": "not_a_list"}
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_folder_not_dict(self):
        """Test validation of JSON with non-dict folder."""
        invalid_json = {"folders": ["not_a_dict"]}
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_folder_missing_name(self):
        """Test validation of JSON with folder missing name."""
        invalid_json = {
            "folders": [
                {"bookmarks": [], "subfolders": []}  # Missing name
            ]
        }
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_invalid_bookmarks_type(self):
        """Test validation of JSON with invalid bookmarks type."""
        invalid_json = {
            "folders": [
                {
                    "name": "Test",
                    "bookmarks": "not_a_list",  # Should be list
                    "subfolders": []
                }
            ]
        }
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_invalid_subfolders_type(self):
        """Test validation of JSON with invalid subfolders type."""
        invalid_json = {
            "folders": [
                {
                    "name": "Test",
                    "bookmarks": [],
                    "subfolders": "not_a_list"  # Should be list
                }
            ]
        }
        assert validate_taxonomy_json(invalid_json) is False

    def test_validate_taxonomy_json_optional_fields_missing(self):
        """Test validation with optional fields missing (should be valid)."""
        minimal_json = {
            "folders": [
                {"name": "Test Folder"}  # No bookmarks or subfolders
            ]
        }
        assert validate_taxonomy_json(minimal_json) is True

    def test_validate_taxonomy_json_exception_handling(self):
        """Test validation handles exceptions gracefully."""
        # Create an object that will cause an exception during validation
        class BadObject:
            def __getitem__(self, key):
                raise Exception("Test exception")

        bad_input = BadObject()
        assert validate_taxonomy_json(bad_input) is False
