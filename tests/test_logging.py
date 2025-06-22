"""Tests for the logging module."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from ombm.logging import (
    configure_logging,
    get_logger,
    log_bookmark_processing,
    log_error_with_context,
    log_execution_context,
    log_performance_metrics,
)


class TestLoggingConfiguration:
    """Test logging configuration."""

    def setup_method(self) -> None:
        """Reset logging configuration before each test."""
        # Clear any existing configuration
        structlog.reset_defaults()
        logging.getLogger().handlers.clear()

    def test_configure_logging_verbose_mode(self) -> None:
        """Test verbose logging configuration."""
        configure_logging(verbose=True, json_output=False)
        
        # Check that logging level is set to DEBUG
        assert logging.getLogger().level == logging.DEBUG

    def test_configure_logging_normal_mode(self) -> None:
        """Test normal logging configuration."""
        configure_logging(verbose=False, json_output=False)
        
        # Check that logging level is set to INFO
        assert logging.getLogger().level == logging.INFO

    def test_configure_logging_json_output(self) -> None:
        """Test JSON output configuration."""
        configure_logging(verbose=False, json_output=True)
        
        # Verify structlog is configured
        assert structlog.is_configured()

    def test_get_logger(self) -> None:
        """Test logger creation."""
        configure_logging()
        logger = get_logger("test_logger")
        
        # Logger should be a structlog logger (may be wrapped in proxy)
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error') 
        assert hasattr(logger, 'debug')

    @patch("sys.stderr", new_callable=StringIO)
    def test_json_log_output(self, mock_stderr: StringIO) -> None:
        """Test that logs emit JSON lines in debug run."""
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")
        
        # Emit a test log
        logger.info("Test message", key="value", number=42)
        
        # Get the log output
        log_output = mock_stderr.getvalue().strip()
        
        # Verify it's valid JSON
        log_data = json.loads(log_output)
        
        # Verify log structure
        assert log_data["event"] == "Test message"
        assert log_data["key"] == "value"
        assert log_data["number"] == 42
        assert log_data["level"] == "info"
        assert "timestamp" in log_data

    @patch("sys.stderr", new_callable=StringIO)
    def test_human_readable_output(self, mock_stderr: StringIO) -> None:
        """Test human-readable log output."""
        configure_logging(verbose=True, json_output=False)
        logger = get_logger("test")
        
        # Emit a test log
        logger.info("Test message")
        
        # Get the log output
        log_output = mock_stderr.getvalue()
        
        # Should contain the message but not be JSON
        assert "Test message" in log_output
        # Should not be parseable as JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(log_output)


class TestLoggingHelpers:
    """Test logging helper functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        configure_logging(verbose=True, json_output=True)
        self.logger = get_logger("test")

    def test_log_execution_context(self) -> None:
        """Test execution context logging."""
        bound_logger = log_execution_context(
            self.logger,
            "test_operation",
            user_id="123",
            session_id="abc"
        )
        
        # Verify logger is bound with context
        assert isinstance(bound_logger, structlog.stdlib.BoundLogger)

    @patch("sys.stderr", new_callable=StringIO)
    def test_log_bookmark_processing(self, mock_stderr: StringIO) -> None:
        """Test bookmark processing logging."""
        log_bookmark_processing(
            self.logger,
            url="https://example.com",
            title="Example Site",
            stage="scrape",
            duration=1.5
        )
        
        log_output = mock_stderr.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["event"] == "Processing bookmark"
        assert log_data["url"] == "https://example.com"
        assert log_data["title"] == "Example Site"
        assert log_data["stage"] == "scrape"
        assert log_data["duration"] == 1.5

    @patch("sys.stderr", new_callable=StringIO)
    def test_log_performance_metrics(self, mock_stderr: StringIO) -> None:
        """Test performance metrics logging."""
        log_performance_metrics(
            self.logger,
            operation="scrape_bookmarks",
            duration=10.5,
            items_processed=25,
            cache_hits=15
        )
        
        log_output = mock_stderr.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["event"] == "Performance metrics"
        assert log_data["operation"] == "scrape_bookmarks"
        assert log_data["duration_seconds"] == 10.5
        assert log_data["items_processed"] == 25
        assert log_data["cache_hits"] == 15
        assert log_data["items_per_second"] == 2.38  # 25 / 10.5 rounded

    @patch("sys.stderr", new_callable=StringIO)
    def test_log_error_with_context(self, mock_stderr: StringIO) -> None:
        """Test error logging with context."""
        test_error = ValueError("Test error message")
        
        log_error_with_context(
            self.logger,
            error=test_error,
            operation="test_operation",
            url="https://example.com"
        )
        
        log_output = mock_stderr.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["event"] == "Operation failed"
        assert log_data["operation"] == "test_operation"
        assert log_data["error_type"] == "ValueError"
        assert log_data["error_message"] == "Test error message"
        assert log_data["url"] == "https://example.com"
        assert log_data["level"] == "error"


class TestAcceptanceCriteria:
    """Test acceptance criteria: Logs emit JSON lines in debug run."""

    @patch("sys.stderr", new_callable=StringIO)
    def test_logs_emit_json_lines_in_debug_run(self, mock_stderr: StringIO) -> None:
        """Test that logs emit JSON lines in debug run (acceptance criteria)."""
        # Configure logging for debug/verbose mode with JSON output
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")
        
        # Emit various types of logs
        logger.info("Starting operation", operation="test", version="1.0")
        logger.debug("Debug information", step="initialization")
        logger.warning("Warning message", warning_type="test")
        logger.error("Error occurred", error_code=500)
        
        # Get all log output
        log_output = mock_stderr.getvalue()
        log_lines = [line.strip() for line in log_output.split('\n') if line.strip()]
        
        # Should have multiple log lines
        assert len(log_lines) >= 4
        
        # Each line should be valid JSON
        for line in log_lines:
            log_data = json.loads(line)
            
            # All logs should have required fields
            assert "event" in log_data
            assert "level" in log_data
            assert "timestamp" in log_data
            assert "logger" in log_data
        
        # Verify specific log content
        start_log = json.loads(log_lines[0])
        assert start_log["event"] == "Starting operation"
        assert start_log["operation"] == "test"
        assert start_log["version"] == "1.0"
        assert start_log["level"] == "info"

    def test_cli_verbose_flag_affects_logging(self) -> None:
        """Test that verbose flag affects log configuration."""
        from typer.testing import CliRunner
        from ombm.__main__ import app
        
        runner = CliRunner()
        
        # Test verbose mode
        result = runner.invoke(app, ["organize", "--verbose"])
        assert result.exit_code == 0
        assert "Verbose logging enabled" in result.stdout
        
        # Test normal mode (should not show verbose message)
        result = runner.invoke(app, ["organize"])
        assert result.exit_code == 0
        assert "Verbose logging enabled" not in result.stdout
