"""Main CLI entrypoint for OMBM."""

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator
from collections.abc import Callable

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ombm import __version__
from ombm.controller import BookmarkController
from ombm.logging import configure_logging, get_logger
from ombm.persistence import PersistenceManager
from ombm.renderer import TreeRenderer
from ombm.tree_builder import TaxonomyParser

app = typer.Typer(
    name="ombm",
    help="Organize My Bookmarks - A macOS CLI tool for semantically organizing Safari bookmarks",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"OMBM version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Organize My Bookmarks - Semantic organization of Safari bookmarks."""
    pass


@app.command()
def organize(
    max_bookmarks: Annotated[
        int,
        typer.Option(
            "--max",
            help="Maximum number of bookmarks to process",
        ),
    ] = 0,
    concurrency: Annotated[
        int,
        typer.Option(
            "--concurrency",
            help="Maximum concurrent tasks",
        ),
    ] = 4,
    save: Annotated[
        bool,
        typer.Option(
            "--save",
            help="Save changes to Safari (default is dry-run)",
        ),
    ] = False,
    json_out: Annotated[
        str,
        typer.Option(
            "--json-out",
            help="Write hierarchy to JSON file",
        ),
    ] = "",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Enable verbose logging",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help="Enable quiet mode (only warnings and errors)",
        ),
    ] = False,
    no_scrape: Annotated[
        bool,
        typer.Option(
            "--no-scrape",
            help="Use existing cache only",
        ),
    ] = False,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help="Override OpenAI model",
        ),
    ] = "gpt-4o",
    profile: Annotated[
        bool,
        typer.Option(
            "--profile",
            help="Display timing and memory stats",
        ),
    ] = False,
    json_logs: Annotated[
        bool,
        typer.Option(
            "--json-logs",
            help="Output logs as JSON lines",
        ),
    ] = False,
) -> None:
    """Organize Safari bookmarks into semantic folders."""
    # Validate conflicting options
    if verbose and quiet:
        console.print("[red]Error: --verbose and --quiet cannot be used together[/red]")
        raise typer.Exit(code=1)

    # Configure logging first
    configure_logging(verbose=verbose, quiet=quiet, json_output=json_logs)
    logger = get_logger(__name__)

    # Log startup
    logger.info(
        "Starting OMBM",
        version=__version__,
        max_bookmarks=max_bookmarks if max_bookmarks > 0 else "unlimited",
        concurrency=concurrency,
        model=model,
        save_mode=save,
        no_scrape=no_scrape,
        json_output=json_out,
        profile_enabled=profile,
        verbose_mode=verbose,
        quiet_mode=quiet,
    )

    # Only show startup info if not in quiet mode
    if not quiet:
        console.print("🔖 OMBM - Organize My Bookmarks")
        console.print(f"Version: {__version__}")

    if save:
        if not quiet:
            console.print("⚠️  Save mode enabled - changes will be written to Safari")
        logger.warning("Save mode enabled - changes will be written to Safari")
    else:
        if not quiet:
            console.print("🔍 Running in dry-run mode (no changes will be made)")
        logger.info("Running in dry-run mode")

    if not quiet:
        console.print(
            f"Max bookmarks: {max_bookmarks if max_bookmarks > 0 else 'unlimited'}"
        )
        console.print(f"Concurrency: {concurrency}")
        console.print(f"Model: {model}")

    if verbose and not quiet:
        console.print("🔍 Verbose logging enabled")
        logger.debug("Verbose logging enabled")

    if quiet and not verbose:
        console.print("🔇 Quiet mode enabled")
        logger.debug("Quiet mode enabled")

    if no_scrape:
        if not quiet:
            console.print("📚 Using cache-only mode")
        logger.info("Cache-only mode enabled")

    if json_out:
        if not quiet:
            console.print(f"📄 JSON output will be written to: {json_out}")
        logger.info("JSON output configured", output_file=json_out)

    if profile:
        if not quiet:
            console.print("📊 Performance profiling enabled")
        logger.info("Performance profiling enabled")

    try:
        asyncio.run(
            run_organization_pipeline(
                max_bookmarks=max_bookmarks,
                concurrency=concurrency,
                save=save,
                json_out=json_out,
                force_refresh=not no_scrape,
                quiet=quiet,
            )
        )
    except Exception as e:
        logger.error("An unexpected error occurred", error=e, exc_info=True)
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1) from e


@asynccontextmanager
async def progress_context(total: int, show_progress: bool = True) -> AsyncGenerator[Callable[[int, int], None], None]:
    """Context manager for progress tracking during bookmark processing."""
    if not show_progress or total < 10:
        # Don't show progress bar for small numbers or when disabled
        yield lambda _completed, _total: None
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        console=Console(),
        expand=True,
    ) as progress:
        task_id = progress.add_task("Processing bookmarks...", total=total)

        def update_progress(completed: int, total: int) -> None:
            progress.update(task_id, completed=completed)

        yield update_progress


async def run_organization_pipeline(
    max_bookmarks: int,
    concurrency: int,
    save: bool,
    json_out: str,
    force_refresh: bool,
    quiet: bool = False,
) -> None:
    """The main async pipeline for organizing bookmarks."""
    console = Console()

    persistence_manager = PersistenceManager(dry_run=not save)

    async with BookmarkController(
        persistence_manager=persistence_manager
    ) as controller:
        # Step 1: Get bookmarks to determine total for progress bar
        bookmarks = await controller.get_bookmarks(
            max_bookmarks=max_bookmarks if max_bookmarks > 0 else None
        )

        if not bookmarks:
            console.print("[yellow]No bookmarks to process. Exiting.[/yellow]")
            return

        # Step 1: Aggregate metadata with progress bar
        if not quiet:
            console.print(
                f"\n[bold]Step 1: Processing {len(bookmarks)} bookmarks...[/bold]"
            )

        async with progress_context(
            len(bookmarks), show_progress=not quiet
        ) as progress_callback:
            metadata_list = await controller.aggregate_metadata_collection(
                max_bookmarks=max_bookmarks if max_bookmarks > 0 else None,
                concurrency=concurrency,
                force_refresh=force_refresh,
                progress_callback=progress_callback,
            )

        if not metadata_list:
            console.print("[yellow]No metadata generated. Exiting.[/yellow]")
            return

        # Step 2: Generate Taxonomy
        if not quiet:
            console.print("[bold]Step 2: Generating taxonomy...[/bold]")
        if controller.processor and controller.processor._llm_service:
            taxonomy_json = await controller.processor._llm_service.propose_taxonomy(
                metadata_list
            )
            # Step 3: Parse taxonomy into a tree structure
            if not quiet:
                console.print("[bold]Step 3: Building folder tree...[/bold]")
            parser = TaxonomyParser()
            taxonomy_tree = parser.parse_taxonomy(taxonomy_json, metadata_list)

            # Step 4: Render the output tree
            if not quiet:
                console.print("\n[bold green]Proposed Organization:[/bold green]")
            renderer = TreeRenderer()
            renderer.render_tree(taxonomy_tree)

            # Step 5: Save to Safari if requested
            if save:
                if not quiet:
                    console.print("\n[bold]Step 4: Saving changes to Safari...[/bold]")
                await controller.apply_taxonomy(taxonomy_tree)
                console.print("[green]Changes saved successfully![/green]")

            # Step 6: Export to JSON if requested
            if json_out:
                if not quiet:
                    console.print(f"\n[bold]Exporting tree to {json_out}...[/bold]")
                controller.export_folder_tree_to_json(taxonomy_tree, json_out)
                console.print(f"[green]Successfully exported to {json_out}[/green]")
        else:
            console.print("[red]Error: Processor not available.[/red]")


if __name__ == "__main__":
    app()
