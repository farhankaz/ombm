"""
This module handles the persistence of the organized bookmarks back into Safari
using AppleScript.
"""

import asyncio
import shutil
from datetime import datetime
from pathlib import Path

import jinja2
from structlog.stdlib import get_logger

from ombm.models import FolderNode, LLMMetadata

log = get_logger()


class PersistenceManager:
    """
    Manages the execution of AppleScript to interact with Safari bookmarks.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.template_env = jinja2.Environment(
            loader=jinja2.PackageLoader("ombm", "applescript"),
            autoescape=False,
        )
        log.info("PersistenceManager initialized", dry_run=self.dry_run)
        self.backup_dir = Path.home() / ".ombm" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def backup_bookmarks(self) -> Path:
        """
        Creates a backup of the Safari Bookmarks.plist file.
        """
        source_path = Path.home() / "Library/Safari/Bookmarks.plist"

        if self.dry_run:
            log.info("DRY RUN: Skipping bookmark backup.")
            # Return a dummy path for dry run
            return Path("/tmp/dry_run_backup.plist")

        if not source_path.exists():
            log.warning(
                "Could not find Bookmarks.plist, skipping backup.",
                path=str(source_path),
            )
            # Return a path indicating no backup was made
            return Path("/tmp/no_backup_made.plist")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bookmarks_{timestamp}.plist"
        backup_path = self.backup_dir / backup_filename

        log.info(
            "Backing up Safari bookmarks", source=source_path, destination=backup_path
        )
        shutil.copy(source_path, backup_path)
        log.info("Bookmark backup created successfully", path=backup_path)
        return backup_path

    async def _run_applescript(self, script_name: str, **kwargs: str) -> str:
        """
        Renders and executes an AppleScript template.

        Args:
            script_name: The name of the AppleScript template file.
            **kwargs: Arguments to pass to the template.

        Returns:
            The standard output of the script execution.
        """
        template = self.template_env.get_template(f"{script_name}.applescript.j2")
        script = template.render(**kwargs)

        if self.dry_run:
            log.info(
                "DRY RUN: AppleScript execution skipped.",
                script_name=script_name,
                # script=script,
            )
            return "dry-run"

        log.info("Executing AppleScript", script_name=script_name)
        process = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode().strip()
            log.error(
                "AppleScript execution failed",
                script_name=script_name,
                return_code=process.returncode,
                error=error_message,
            )
            raise RuntimeError(f"AppleScript failed: {error_message}")

        result = stdout.decode().strip()
        log.info(
            "AppleScript execution successful", script_name=script_name, result=result
        )
        return result

    async def apply_taxonomy(self, taxonomy_tree: FolderNode) -> None:
        """
        Applies the generated taxonomy to Safari bookmarks.

        This involves creating folders and moving bookmarks.
        """
        log.info("Applying taxonomy to Safari", dry_run=self.dry_run)
        if self.dry_run:
            log.info("DRY RUN: Skipping taxonomy application.")
            return
        await self._traverse_and_apply(taxonomy_tree)

    async def _traverse_and_apply(
        self, node: FolderNode, parent_path: str = ""
    ) -> None:
        """
        Recursively traverses the taxonomy tree and applies changes.
        """
        current_path = f"{parent_path}/{node.name}" if parent_path else node.name
        log.info("Processing folder", path=current_path)

        # Create the folder
        await self._run_applescript("create_folder", folder_name=node.name)

        for child in node.children:
            if isinstance(child, FolderNode):
                await self._traverse_and_apply(child, current_path)
            elif isinstance(child, LLMMetadata):
                log.info(
                    "Moving bookmark",
                    bookmark=child.name,
                    url=child.url,
                    folder=node.name,
                )
                await self._run_applescript(
                    "move_bookmark", bookmark_url=child.url, folder_name=node.name
                )
