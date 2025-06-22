"""Main CLI entrypoint for OMBM."""

from typing import Annotated

import typer
from rich.console import Console

from ombm import __version__
from ombm.logging import configure_logging, get_logger

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
    # Configure logging first
    configure_logging(verbose=verbose, json_output=json_logs)
    logger = get_logger(__name__)

    # Log startup
    logger.info(
        "Starting OMBM",
        version=__version__,
        max_bookmarks=max_bookmarks if max_bookmarks > 0 else None,
        concurrency=concurrency,
        model=model,
        save_mode=save,
        no_scrape=no_scrape,
        json_output=json_out,
        profile_enabled=profile,
    )

    console.print("🔖 OMBM - Organize My Bookmarks")
    console.print(f"Version: {__version__}")

    if save:
        console.print("⚠️  Save mode enabled - changes will be written to Safari")
        logger.warning("Save mode enabled - changes will be written to Safari")
    else:
        console.print("🔍 Running in dry-run mode (no changes will be made)")
        logger.info("Running in dry-run mode")

    console.print(
        f"Max bookmarks: {max_bookmarks if max_bookmarks > 0 else 'unlimited'}"
    )
    console.print(f"Concurrency: {concurrency}")
    console.print(f"Model: {model}")

    if verbose:
        console.print("🔍 Verbose logging enabled")
        logger.debug("Verbose logging enabled")

    if no_scrape:
        console.print("📚 Using cache-only mode")
        logger.info("Cache-only mode enabled")

    if json_out:
        console.print(f"📄 JSON output will be written to: {json_out}")
        logger.info("JSON output configured", output_file=json_out)

    if profile:
        console.print("📊 Performance profiling enabled")
        logger.info("Performance profiling enabled")

    # TODO: Implement actual bookmark organization logic
    console.print("\n🚧 Core functionality not yet implemented")
    console.print("This is a placeholder for the bookmark organization pipeline.")

    logger.info("Core functionality placeholder - implementation pending")


if __name__ == "__main__":
    app()
