"""Tests for the main CLI entrypoint."""

from unittest.mock import AsyncMock, patch

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

    def test_verbose_mode_logging(self, mock_pipeline: AsyncMock) -> None:
        """Test that verbose mode affects logging configuration."""
        with patch("ombm.__main__.configure_logging") as mock_config:
            result = self.runner.invoke(app, ["organize", "--verbose"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with(
                verbose=True, quiet=False, json_output=False
            )

    def test_quiet_mode_logging(self, mock_pipeline: AsyncMock) -> None:
        """Test that quiet mode affects logging configuration."""
        with patch("ombm.__main__.configure_logging") as mock_config:
            result = self.runner.invoke(app, ["organize", "--quiet"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with(
                verbose=False, quiet=True, json_output=False
            )

    def test_verbose_and_quiet_conflict(self, mock_pipeline: AsyncMock) -> None:
        """Test that verbose and quiet flags cannot be used together."""
        result = self.runner.invoke(app, ["organize", "--verbose", "--quiet"])
        assert result.exit_code == 1
        assert "--verbose and --quiet cannot be used together" in result.stdout
        mock_pipeline.assert_not_called()

    def test_quiet_mode_console_output(self, mock_pipeline: AsyncMock) -> None:
        """Test that quiet mode suppresses most console output."""
        result = self.runner.invoke(app, ["organize", "--quiet"])
        assert result.exit_code == 0

        # Should not contain normal startup messages
        assert "🔖 OMBM - Organize My Bookmarks" not in result.stdout
        assert "Version:" not in result.stdout
        assert "Max bookmarks:" not in result.stdout
        assert "Concurrency:" not in result.stdout
        assert "Model:" not in result.stdout
        assert "🔍 Running in dry-run mode" not in result.stdout

        # Should contain quiet mode indicator
        assert "🔇 Quiet mode enabled" in result.stdout

    def test_verbose_mode_console_output(self, mock_pipeline: AsyncMock) -> None:
        """Test that verbose mode shows additional output."""
        result = self.runner.invoke(app, ["organize", "--verbose"])
        assert result.exit_code == 0

        # Should contain normal startup messages
        assert "🔖 OMBM - Organize My Bookmarks" in result.stdout
        assert "🔍 Verbose logging enabled" in result.stdout

    def test_normal_mode_console_output(self, mock_pipeline: AsyncMock) -> None:
        """Test that normal mode shows standard output."""
        result = self.runner.invoke(app, ["organize"])
        assert result.exit_code == 0

        # Should contain normal startup messages
        assert "🔖 OMBM - Organize My Bookmarks" in result.stdout
        assert "Version:" in result.stdout
        assert "🔍 Running in dry-run mode" in result.stdout

        # Should not contain verbose or quiet indicators
        assert "🔍 Verbose logging enabled" not in result.stdout
        assert "🔇 Quiet mode enabled" not in result.stdout

    def test_json_logs_with_verbose(self, mock_pipeline: AsyncMock) -> None:
        """Test verbose mode with JSON logs."""
        with patch("ombm.__main__.configure_logging") as mock_config:
            result = self.runner.invoke(app, ["organize", "--verbose", "--json-logs"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with(
                verbose=True, quiet=False, json_output=True
            )

    def test_json_logs_with_quiet(self, mock_pipeline: AsyncMock) -> None:
        """Test quiet mode with JSON logs."""
        with patch("ombm.__main__.configure_logging") as mock_config:
            result = self.runner.invoke(app, ["organize", "--quiet", "--json-logs"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with(
                verbose=False, quiet=True, json_output=True
            )
