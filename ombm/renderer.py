"""
Tree renderer module for OMBM - pretty-prints bookmark hierarchies using Rich.

This module provides functionality to render FolderNode structures as
beautiful tree visualizations in the terminal using the Rich library.
"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .models import FolderNode, LLMMetadata

logger = logging.getLogger(__name__)


class TreeRenderer:
    """
    Renderer that converts FolderNode structures into Rich tree visualizations.

    This class handles the conversion of typed FolderNode objects into
    Rich Tree objects for beautiful terminal display.
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize the tree renderer.

        Args:
            console: Rich Console instance (created if None)
        """
        self.console = console or Console()
        self.stats = {
            "total_folders": 0,
            "total_bookmarks": 0,
            "max_depth": 0,
        }

    def render_tree(
        self,
        root: FolderNode,
        show_descriptions: bool = True,
        show_urls: bool = False,
        max_url_length: int = 60,
    ) -> Tree:
        """
        Render a FolderNode structure as a Rich Tree.

        Args:
            root: Root FolderNode to render
            show_descriptions: Whether to show bookmark descriptions
            show_urls: Whether to show bookmark URLs
            max_url_length: Maximum length for displayed URLs

        Returns:
            Rich Tree object ready for display
        """
        logger.debug("Rendering FolderNode structure as Rich Tree")

        # Reset stats
        self.stats = {"total_folders": 0, "total_bookmarks": 0, "max_depth": 0}

        # Create root tree
        tree = Tree(f"[bold blue]{root.name}[/bold blue]", guide_style="dim cyan")

        # Render children recursively
        self._render_children(
            tree,
            root.children,
            depth=0,
            show_descriptions=show_descriptions,
            show_urls=show_urls,
            max_url_length=max_url_length,
        )

        logger.debug(
            f"Rendered tree: {self.stats['total_folders']} folders, "
            f"{self.stats['total_bookmarks']} bookmarks, "
            f"max depth: {self.stats['max_depth']}"
        )

        return tree

    def _render_children(
        self,
        parent_tree: Tree,
        children: list[FolderNode | LLMMetadata],
        depth: int,
        show_descriptions: bool,
        show_urls: bool,
        max_url_length: int,
    ) -> None:
        """
        Recursively render children nodes.

        Args:
            parent_tree: Parent Rich Tree to add children to
            children: List of child nodes to render
            depth: Current depth in the tree
            show_descriptions: Whether to show bookmark descriptions
            show_urls: Whether to show bookmark URLs
            max_url_length: Maximum length for displayed URLs
        """
        # Update max depth
        self.stats["max_depth"] = max(self.stats["max_depth"], depth)

        # Sort children: folders first, then bookmarks alphabetically
        folders = [child for child in children if isinstance(child, FolderNode)]
        bookmarks = [child for child in children if isinstance(child, LLMMetadata)]

        folders.sort(key=lambda f: f.name.lower())
        bookmarks.sort(key=lambda b: b.name.lower())

        # Render folders
        for folder in folders:
            self.stats["total_folders"] += 1

            # Count items in this folder
            folder_stats = self._count_folder_contents(folder)

            # Create folder label with counts
            folder_label = Text()
            folder_label.append(f"📁 {folder.name}", style="bold yellow")

            if folder_stats["bookmarks"] > 0 or folder_stats["subfolders"] > 0:
                count_text = []
                if folder_stats["bookmarks"] > 0:
                    count_text.append(
                        f"{folder_stats['bookmarks']} bookmark{'s' if folder_stats['bookmarks'] != 1 else ''}"
                    )
                if folder_stats["subfolders"] > 0:
                    count_text.append(
                        f"{folder_stats['subfolders']} folder{'s' if folder_stats['subfolders'] != 1 else ''}"
                    )

                folder_label.append(f" ({', '.join(count_text)})", style="dim")

            # Add folder to tree
            folder_tree = parent_tree.add(folder_label)

            # Render folder children
            self._render_children(
                folder_tree,
                folder.children,
                depth + 1,
                show_descriptions,
                show_urls,
                max_url_length,
            )

        # Render bookmarks
        for bookmark in bookmarks:
            self.stats["total_bookmarks"] += 1
            self._render_bookmark(
                parent_tree, bookmark, show_descriptions, show_urls, max_url_length
            )

    def _render_bookmark(
        self,
        parent_tree: Tree,
        bookmark: LLMMetadata,
        show_descriptions: bool,
        show_urls: bool,
        max_url_length: int,
    ) -> None:
        """
        Render a single bookmark.

        Args:
            parent_tree: Parent Rich Tree to add bookmark to
            bookmark: LLMMetadata to render
            show_descriptions: Whether to show description
            show_urls: Whether to show URL
            max_url_length: Maximum length for displayed URLs
        """
        # Create bookmark label
        bookmark_text = Text()
        bookmark_text.append("🔖 ", style="blue")
        bookmark_text.append(bookmark.name, style="bold")

        # Add description if requested
        if show_descriptions and bookmark.description:
            bookmark_text.append(f"\n   {bookmark.description}", style="dim italic")

        # Add URL if requested
        if show_urls:
            url_display = bookmark.url
            if len(url_display) > max_url_length:
                url_display = url_display[: max_url_length - 3] + "..."
            bookmark_text.append(f"\n   🔗 {url_display}", style="dim cyan")

        parent_tree.add(bookmark_text)

    def _count_folder_contents(self, folder: FolderNode) -> dict[str, int]:
        """
        Count the contents of a folder (direct children only).

        Args:
            folder: FolderNode to count

        Returns:
            Dictionary with counts of bookmarks and subfolders
        """
        bookmarks = sum(
            1 for child in folder.children if isinstance(child, LLMMetadata)
        )
        subfolders = sum(
            1 for child in folder.children if isinstance(child, FolderNode)
        )

        return {"bookmarks": bookmarks, "subfolders": subfolders}

    def render_summary(self, root: FolderNode) -> Panel:
        """
        Render a summary panel with tree statistics.

        Args:
            root: Root FolderNode to analyze

        Returns:
            Rich Panel with summary information
        """
        # Calculate comprehensive stats
        stats = self._calculate_comprehensive_stats(root)

        # Create summary table
        table = Table(show_header=False, box=None, pad_edge=False)
        table.add_column("Metric", style="bold")
        table.add_column("Count", justify="right")

        table.add_row("Total Folders:", str(stats["total_folders"]))
        table.add_row("Total Bookmarks:", str(stats["total_bookmarks"]))
        table.add_row("Max Depth:", str(stats["max_depth"]))
        table.add_row("Average per Folder:", f"{stats['avg_bookmarks']:.1f}")

        if stats["largest_folder_size"] > 0:
            table.add_row("Largest Folder:", f"{stats['largest_folder_size']} items")

        return Panel(
            table,
            title="[bold]Bookmark Organization Summary[/bold]",
            title_align="left",
            border_style="blue",
        )

    def _calculate_comprehensive_stats(
        self, node: FolderNode, depth: int = 0
    ) -> dict[str, int | float]:
        """
        Calculate comprehensive statistics for the tree.

        Args:
            node: Current node to analyze
            depth: Current depth in tree

        Returns:
            Dictionary with comprehensive statistics
        """
        folder_sizes: list[int] = []

        def _collect_stats(node: FolderNode, depth: int) -> dict[str, int]:
            nonlocal folder_sizes
            folder_size = 0
            total_folders = 1
            total_bookmarks = 0
            max_depth = depth

            for child in node.children:
                if isinstance(child, FolderNode):
                    child_stats = _collect_stats(child, depth + 1)
                    total_folders += child_stats["total_folders"]
                    total_bookmarks += child_stats["total_bookmarks"]
                    max_depth = max(max_depth, child_stats["max_depth"])
                else:  # LLMMetadata
                    total_bookmarks += 1
                    folder_size += 1

            folder_sizes.append(folder_size)
            return {
                "total_folders": total_folders,
                "total_bookmarks": total_bookmarks,
                "max_depth": max_depth,
            }

        stats = _collect_stats(node, depth)

        # Calculate derived stats
        avg_bookmarks = (
            stats["total_bookmarks"] / stats["total_folders"]
            if stats["total_folders"] > 0
            else 0.0
        )
        largest_folder_size: int = max(folder_sizes or [0])

        return {
            "total_folders": stats["total_folders"],
            "total_bookmarks": stats["total_bookmarks"],
            "max_depth": stats["max_depth"],
            "avg_bookmarks": avg_bookmarks,
            "largest_folder_size": largest_folder_size,
        }

    def print_tree(
        self,
        root: FolderNode,
        show_descriptions: bool = True,
        show_urls: bool = False,
        show_summary: bool = True,
        max_url_length: int = 60,
    ) -> None:
        """
        Print the tree to the console.

        Args:
            root: Root FolderNode to render
            show_descriptions: Whether to show bookmark descriptions
            show_urls: Whether to show bookmark URLs
            show_summary: Whether to show summary panel
            max_url_length: Maximum length for displayed URLs
        """
        # Render and print the tree
        tree = self.render_tree(
            root,
            show_descriptions=show_descriptions,
            show_urls=show_urls,
            max_url_length=max_url_length,
        )

        self.console.print()
        self.console.print(tree)

        # Print summary if requested
        if show_summary:
            summary = self.render_summary(root)
            self.console.print()
            self.console.print(summary)

    def get_rendering_stats(self) -> dict[str, int]:
        """
        Get statistics from the last rendering operation.

        Returns:
            Dictionary with rendering statistics
        """
        return self.stats.copy()


def render_bookmark_tree(
    root: FolderNode,
    console: Console | None = None,
    show_descriptions: bool = True,
    show_urls: bool = False,
    show_summary: bool = True,
    max_url_length: int = 60,
) -> None:
    """
    Convenience function to render and print a bookmark tree.

    Args:
        root: Root FolderNode to render
        console: Rich Console instance (created if None)
        show_descriptions: Whether to show bookmark descriptions
        show_urls: Whether to show bookmark URLs
        show_summary: Whether to show summary panel
        max_url_length: Maximum length for displayed URLs
    """
    renderer = TreeRenderer(console)
    renderer.print_tree(
        root,
        show_descriptions=show_descriptions,
        show_urls=show_urls,
        show_summary=show_summary,
        max_url_length=max_url_length,
    )


def tree_to_rich(
    root: FolderNode,
    show_descriptions: bool = True,
    show_urls: bool = False,
    max_url_length: int = 60,
) -> Tree:
    """
    Convenience function to convert FolderNode to Rich Tree.

    Args:
        root: Root FolderNode to convert
        show_descriptions: Whether to show bookmark descriptions
        show_urls: Whether to show bookmark URLs
        max_url_length: Maximum length for displayed URLs

    Returns:
        Rich Tree object
    """
    renderer = TreeRenderer()
    return renderer.render_tree(
        root,
        show_descriptions=show_descriptions,
        show_urls=show_urls,
        max_url_length=max_url_length,
    )
