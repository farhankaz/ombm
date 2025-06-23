"""Tests for the main CLI entrypoint."""

from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from ombm import __version__
from ombm.__main__ import app


class TestMainCLI:
    """Test suite for main CLI functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @pytest.fixture(autouse=True)
    def mock_pipeline(self, monkeypatch):
        """Mock the main organization pipeline to prevent it from running."""
        mock = AsyncMock()
        monkeypatch.setattr("ombm.__main__.run_organization_pipeline", mock)
        return mock

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

    def test_organize_command_dry_run(self, mock_pipeline: AsyncMock) -> None:
        """Test organize command in dry-run mode."""
        result = self.runner.invoke(app, ["organize"])
        assert result.exit_code == 0
        mock_pipeline.assert_called_once()
        # Verify that `save` is False in the call
        call_args = mock_pipeline.call_args[1]
        assert not call_args["save"]

    def test_organize_command_with_options(self, mock_pipeline: AsyncMock) -> None:
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
            ],
        )
        assert result.exit_code == 0
        mock_pipeline.assert_called_once()
        call_args = mock_pipeline.call_args[1]
        assert call_args["max_bookmarks"] == 100
        assert call_args["concurrency"] == 8

    def test_organize_command_save_mode(self, mock_pipeline: AsyncMock) -> None:
        """Test organize command with save flag."""
        result = self.runner.invoke(app, ["organize", "--save"])
        assert result.exit_code == 0
        mock_pipeline.assert_called_once()
        call_args = mock_pipeline.call_args[1]
        assert call_args["save"]
