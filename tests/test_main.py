"""Tests for the main CLI entrypoint."""

from typer.testing import CliRunner

from ombm import __version__
from ombm.__main__ import app


class TestMainCLI:
    """Test the main CLI functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_flag(self) -> None:
        """Test --version flag displays version."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_message(self) -> None:
        """Test help message is displayed."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Organize My Bookmarks" in result.stdout

    def test_organize_command_help(self) -> None:
        """Test organize command help."""
        result = self.runner.invoke(app, ["organize", "--help"])
        assert result.exit_code == 0
        assert "Organize Safari bookmarks" in result.stdout

    def test_organize_command_dry_run(self) -> None:
        """Test organize command in dry-run mode."""
        result = self.runner.invoke(app, ["organize"])
        assert result.exit_code == 0
        assert "dry-run mode" in result.stdout
        assert "not yet implemented" in result.stdout

    def test_organize_command_with_options(self) -> None:
        """Test organize command with various options."""
        result = self.runner.invoke(
            app,
            [
                "organize",
                "--max",
                "100",
                "--concurrency",
                "8",
                "--verbose",
                "--model",
                "gpt-3.5-turbo",
            ],
        )
        assert result.exit_code == 0
        assert "Max bookmarks: 100" in result.stdout
        assert "Concurrency: 8" in result.stdout
        assert "Model: gpt-3.5-turbo" in result.stdout
        assert "Verbose logging enabled" in result.stdout

    def test_organize_command_save_mode(self) -> None:
        """Test organize command with save flag."""
        result = self.runner.invoke(app, ["organize", "--save"])
        assert result.exit_code == 0
        assert "Save mode enabled" in result.stdout
