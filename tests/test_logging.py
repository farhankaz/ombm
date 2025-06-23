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

    def test_configure_logging_quiet_mode(self) -> None:
        """Test quiet logging configuration."""
        configure_logging(verbose=False, quiet=True, json_output=False)

        # Check that logging level is set to WARNING
        assert logging.getLogger().level == logging.WARNING

    def test_configure_logging_quiet_takes_precedence(self) -> None:
        """Test that quiet mode takes precedence over verbose mode."""
        configure_logging(verbose=True, quiet=True, json_output=False)

        # Check that logging level is set to WARNING (quiet takes precedence)
        assert logging.getLogger().level == logging.WARNING

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
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

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

    def test_log_execution_context(self) -> None:
        """Test execution context logging."""
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")

        bound_logger = log_execution_context(
            logger, "test_operation", user_id="123", session_id="abc"
        )

        # Verify logger is bound with context
        assert isinstance(bound_logger, structlog.stdlib.BoundLogger)

    def test_log_bookmark_processing(self) -> None:
        """Test bookmark processing logging (function call succeeds)."""
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")

        # Should not raise any exceptions
        log_bookmark_processing(
            logger,
            url="https://example.com",
            title="Example Site",
            stage="scrape",
            duration=1.5,
        )

    def test_log_performance_metrics(self) -> None:
        """Test performance metrics logging (function call succeeds)."""
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")

        # Should not raise any exceptions
        log_performance_metrics(
            logger,
            operation="scrape_bookmarks",
            duration=10.5,
            items_processed=25,
            cache_hits=15,
        )

    def test_log_error_with_context(self) -> None:
        """Test error logging with context (function call succeeds)."""
        configure_logging(verbose=True, json_output=True)
        logger = get_logger("test")

        test_error = ValueError("Test error message")

        # Should not raise any exceptions
        log_error_with_context(
            logger,
            error=test_error,
            operation="test_operation",
            url="https://example.com",
        )
