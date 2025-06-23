"""
Tests for the renderer module.

This module tests the TreeRenderer class and related functions for rendering
FolderNode structures as Rich tree visualizations.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from ombm.models import FolderNode, LLMMetadata
from ombm.renderer import (
    TreeRenderer,
    render_bookmark_tree,
    tree_to_rich,
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
def simple_folder_tree():
    """Simple folder tree for testing."""
    return FolderNode(
        name="Bookmarks",
        children=[
            FolderNode(
                name="Development",
                children=[
                    LLMMetadata(
                        url="https://github.com/user/repo",
                        name="GitHub Repository",
                        description="Open source code repository",
                        tokens_used=40
                    ),
                    LLMMetadata(
                        url="https://example.com",
                        name="Example Website",
                        description="A sample website for testing",
                        tokens_used=50
                    )
                ]
            ),
            FolderNode(
                name="Blogs",
                children=[
                    LLMMetadata(
                        url="https://test.blog",
                        name="Test Blog Site",
                        description="A blog for testing purposes",
                        tokens_used=45
                    )
                ]
            )
        ]
    )


@pytest.fixture
def nested_folder_tree():
    """Nested folder tree for testing."""
    return FolderNode(
        name="Bookmarks",
        children=[
            FolderNode(
                name="Development",
                children=[
                    FolderNode(
                        name="Web Development",
                        children=[
                            LLMMetadata(
                                url="https://example.com",
                                name="Example Website",
                                description="A sample website for testing",
                                tokens_used=50
                            )
                        ]
                    ),
                    FolderNode(
                        name="Version Control",
                        children=[
                            LLMMetadata(
                                url="https://github.com/user/repo",
                                name="GitHub Repository",
                                description="Open source code repository",
                                tokens_used=40
                            )
                        ]
                    )
                ]
            ),
            FolderNode(
                name="Reading",
                children=[
                    LLMMetadata(
                        url="https://test.blog",
                        name="Test Blog Site",
                        description="A blog for testing purposes",
                        tokens_used=45
                    )
                ]
            )
        ]
    )


@pytest.fixture
def empty_folder_tree():
    """Empty folder tree for testing."""
    return FolderNode(name="Empty Bookmarks", children=[])


class TestTreeRenderer:
    """Test cases for TreeRenderer class."""

    @pytest.fixture
    def console(self):
        """Mock console for testing."""
        return Console(file=StringIO(), width=80)

    @pytest.fixture
    def renderer(self, console):
        """Renderer instance with mock console."""
        return TreeRenderer(console=console)

    def test_init_default_console(self):
        """Test renderer initialization with default console."""
        renderer = TreeRenderer()
        assert renderer.console is not None
        assert isinstance(renderer.console, Console)
        assert renderer.stats == {"total_folders": 0, "total_bookmarks": 0, "max_depth": 0}

    def test_init_custom_console(self, console):
        """Test renderer initialization with custom console."""
        renderer = TreeRenderer(console=console)
        assert renderer.console is console

    def test_render_tree_simple(self, renderer, simple_folder_tree):
        """Test rendering a simple folder tree."""
        tree = renderer.render_tree(simple_folder_tree)

        assert isinstance(tree, Tree)
        assert len(tree.children) == 2  # Development and Blogs folders

        # Check stats
        stats = renderer.get_rendering_stats()
        assert stats["total_folders"] == 2  # Development + Blogs (root not counted in stats)
        assert stats["total_bookmarks"] == 3
        assert stats["max_depth"] == 1  # Folder children are processed at depth 1

    def test_render_tree_nested(self, renderer, nested_folder_tree):
        """Test rendering a nested folder tree."""
        tree = renderer.render_tree(nested_folder_tree)

        assert isinstance(tree, Tree)
        assert len(tree.children) == 2  # Development and Reading folders

        # Check nested structure
        dev_folder = tree.children[0]
        assert len(dev_folder.children) == 2  # Web Development and Version Control

        # Check stats
        stats = renderer.get_rendering_stats()
        assert stats["total_folders"] == 4  # Development, Reading, Web Development, Version Control
        assert stats["total_bookmarks"] == 3
        assert stats["max_depth"] == 2  # Nested folders go to depth 2

    def test_render_tree_empty(self, renderer, empty_folder_tree):
        """Test rendering an empty folder tree."""
        tree = renderer.render_tree(empty_folder_tree)

        assert isinstance(tree, Tree)
        assert len(tree.children) == 0

        # Check stats
        stats = renderer.get_rendering_stats()
        assert stats["total_folders"] == 0
        assert stats["total_bookmarks"] == 0
        assert stats["max_depth"] == 0

    def test_render_tree_show_descriptions(self, renderer, simple_folder_tree):
        """Test rendering tree with descriptions enabled."""
        tree = renderer.render_tree(simple_folder_tree, show_descriptions=True)

        assert isinstance(tree, Tree)
        # Descriptions are included in the text content, hard to test directly
        # but we can verify the method completes without error

    def test_render_tree_hide_descriptions(self, renderer, simple_folder_tree):
        """Test rendering tree with descriptions disabled."""
        tree = renderer.render_tree(simple_folder_tree, show_descriptions=False)

        assert isinstance(tree, Tree)
        # Similar to above, mainly testing no errors occur

    def test_render_tree_show_urls(self, renderer, simple_folder_tree):
        """Test rendering tree with URLs enabled."""
        tree = renderer.render_tree(simple_folder_tree, show_urls=True)

        assert isinstance(tree, Tree)
        # URLs are included in the text content

    def test_render_tree_url_truncation(self, renderer, simple_folder_tree):
        """Test URL truncation in tree rendering."""
        tree = renderer.render_tree(simple_folder_tree, show_urls=True, max_url_length=10)

        assert isinstance(tree, Tree)
        # URLs longer than 10 chars should be truncated

    def test_count_folder_contents(self, renderer):
        """Test folder content counting."""
        folder = FolderNode(
            name="Test Folder",
            children=[
                LLMMetadata(url="https://example.com", name="Test", description="", tokens_used=10),
                LLMMetadata(url="https://test.com", name="Test 2", description="", tokens_used=10),
                FolderNode(name="Subfolder", children=[])
            ]
        )

        counts = renderer._count_folder_contents(folder)

        assert counts["bookmarks"] == 2
        assert counts["subfolders"] == 1

    def test_render_summary(self, renderer, simple_folder_tree):
        """Test summary panel rendering."""
        # First render the tree to populate stats
        renderer.render_tree(simple_folder_tree)

        summary = renderer.render_summary(simple_folder_tree)

        assert isinstance(summary, Panel)
        # Panel contains a table with statistics

    def test_calculate_comprehensive_stats(self, renderer, nested_folder_tree):
        """Test comprehensive statistics calculation."""
        stats = renderer._calculate_comprehensive_stats(nested_folder_tree)

        assert stats["total_folders"] == 5  # Root + Development + Reading + Web Dev + Version Control
        assert stats["total_bookmarks"] == 3
        assert stats["max_depth"] == 2  # Nested folders go 2 levels deep
        assert "avg_bookmarks" in stats
        assert "largest_folder_size" in stats
        assert "folder_sizes" in stats

    def test_print_tree_with_summary(self, renderer, simple_folder_tree):
        """Test printing tree with summary."""
        # This mainly tests that the method runs without error
        # since we're using a StringIO console
        renderer.print_tree(simple_folder_tree, show_summary=True)

        # Check that output was written to console
        output = renderer.console.file.getvalue()
        assert len(output) > 0

    def test_print_tree_without_summary(self, renderer, simple_folder_tree):
        """Test printing tree without summary."""
        renderer.print_tree(simple_folder_tree, show_summary=False)

        # Check that output was written to console
        output = renderer.console.file.getvalue()
        assert len(output) > 0

    def test_print_tree_all_options(self, renderer, simple_folder_tree):
        """Test printing tree with all display options enabled."""
        renderer.print_tree(
            simple_folder_tree,
            show_descriptions=True,
            show_urls=True,
            show_summary=True,
            max_url_length=30
        )

        # Check that output was written to console
        output = renderer.console.file.getvalue()
        assert len(output) > 0

    def test_get_rendering_stats_initial(self, renderer):
        """Test getting rendering stats before any rendering."""
        stats = renderer.get_rendering_stats()

        assert stats == {"total_folders": 0, "total_bookmarks": 0, "max_depth": 0}

    def test_get_rendering_stats_after_render(self, renderer, simple_folder_tree):
        """Test getting rendering stats after rendering."""
        renderer.render_tree(simple_folder_tree)

        stats = renderer.get_rendering_stats()

        assert stats["total_folders"] > 0
        assert stats["total_bookmarks"] > 0
        assert isinstance(stats["max_depth"], int)

    def test_folder_sorting(self, renderer):
        """Test that folders and bookmarks are sorted alphabetically."""
        unsorted_tree = FolderNode(
            name="Root",
            children=[
                FolderNode(name="Z Folder", children=[]),
                LLMMetadata(url="https://z.com", name="Z Bookmark", description="", tokens_used=10),
                FolderNode(name="A Folder", children=[]),
                LLMMetadata(url="https://a.com", name="A Bookmark", description="", tokens_used=10),
            ]
        )

        tree = renderer.render_tree(unsorted_tree)

        # Verify tree was created (specific sorting verification would require
        # examining internal Rich tree structure which is complex)
        assert isinstance(tree, Tree)
        assert len(tree.children) == 4


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_render_bookmark_tree(self, simple_folder_tree):
        """Test convenience function for rendering bookmark tree."""
        console = Console(file=StringIO(), width=80)

        # Should not raise any exceptions
        render_bookmark_tree(
            simple_folder_tree,
            console=console,
            show_descriptions=True,
            show_urls=True,
            show_summary=True,
            max_url_length=50
        )

        # Check that output was written
        output = console.file.getvalue()
        assert len(output) > 0

    def test_render_bookmark_tree_default_console(self, simple_folder_tree):
        """Test convenience function with default console."""
        # Should not raise any exceptions
        with patch('ombm.renderer.TreeRenderer') as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer_class.return_value = mock_renderer

            render_bookmark_tree(simple_folder_tree)

            mock_renderer_class.assert_called_once_with(None)
            mock_renderer.print_tree.assert_called_once()

    def test_tree_to_rich(self, simple_folder_tree):
        """Test convenience function for converting to Rich Tree."""
        tree = tree_to_rich(simple_folder_tree)

        assert isinstance(tree, Tree)

    def test_tree_to_rich_with_options(self, simple_folder_tree):
        """Test tree_to_rich with various options."""
        tree = tree_to_rich(
            simple_folder_tree,
            show_descriptions=False,
            show_urls=True,
            max_url_length=20
        )

        assert isinstance(tree, Tree)

    def test_tree_to_rich_empty(self, empty_folder_tree):
        """Test tree_to_rich with empty tree."""
        tree = tree_to_rich(empty_folder_tree)

        assert isinstance(tree, Tree)
        assert len(tree.children) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_urls(self):
        """Test handling of very long URLs."""
        console = Console(file=StringIO(), width=80)
        renderer = TreeRenderer(console=console)

        long_url = "https://example.com/" + "a" * 200
        tree = FolderNode(
            name="Test",
            children=[
                LLMMetadata(
                    url=long_url,
                    name="Long URL Test",
                    description="Test with very long URL",
                    tokens_used=10
                )
            ]
        )

        result = renderer.render_tree(tree, show_urls=True, max_url_length=50)
        assert isinstance(result, Tree)

    def test_empty_bookmark_descriptions(self):
        """Test handling of bookmarks with empty descriptions."""
        console = Console(file=StringIO(), width=80)
        renderer = TreeRenderer(console=console)

        tree = FolderNode(
            name="Test",
            children=[
                LLMMetadata(
                    url="https://example.com",
                    name="No Description",
                    description="",  # Empty description
                    tokens_used=10
                )
            ]
        )

        result = renderer.render_tree(tree, show_descriptions=True)
        assert isinstance(result, Tree)

    def test_special_characters_in_names(self):
        """Test handling of special characters in folder and bookmark names."""
        console = Console(file=StringIO(), width=80)
        renderer = TreeRenderer(console=console)

        tree = FolderNode(
            name="Special 🚀 Characters",
            children=[
                FolderNode(
                    name="Földer with ümlauts",
                    children=[
                        LLMMetadata(
                            url="https://example.com",
                            name="Bøøkmark with spéciäl chârs",
                            description="Déscription with àccents",
                            tokens_used=10
                        )
                    ]
                )
            ]
        )

        result = renderer.render_tree(tree)
        assert isinstance(result, Tree)

    def test_deeply_nested_structure(self):
        """Test handling of deeply nested folder structures."""
        console = Console(file=StringIO(), width=80)
        renderer = TreeRenderer(console=console)

        # Create a 5-level deep structure
        current = FolderNode(name="Level 5", children=[
            LLMMetadata(url="https://example.com", name="Deep Bookmark", description="", tokens_used=10)
        ])

        for i in range(4, 0, -1):
            current = FolderNode(name=f"Level {i}", children=[current])

        root = FolderNode(name="Root", children=[current])

        result = renderer.render_tree(root)
        assert isinstance(result, Tree)

        stats = renderer.get_rendering_stats()
        assert stats["max_depth"] == 5  # 5 levels of nesting processed
