"""Structured logging configuration for OMBM."""

import logging
import sys
from typing import Any

import structlog


def configure_logging(verbose: bool = False, json_output: bool = False) -> None:
    """Configure structured logging for OMBM.

    Args:
        verbose: Enable verbose logging (DEBUG level)
        json_output: Output logs as JSON lines
    """
    # Set log level based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # JSON output for programmatic consumption
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable console output
        processors.append(
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_execution_context(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    **kwargs: Any
) -> structlog.stdlib.BoundLogger:
    """Add execution context to logger.

    Args:
        logger: Logger instance
        operation: Operation being performed
        **kwargs: Additional context fields

    Returns:
        Logger with bound context
    """
    context = {
        "operation": operation,
        **kwargs
    }
    return logger.bind(**context)


def log_bookmark_processing(
    logger: structlog.stdlib.BoundLogger,
    url: str,
    title: str,
    stage: str,
    **kwargs: Any
) -> None:
    """Log bookmark processing with structured data.

    Args:
        logger: Logger instance
        url: Bookmark URL
        title: Bookmark title
        stage: Processing stage (scrape, llm, cache, etc.)
        **kwargs: Additional context
    """
    logger.info(
        "Processing bookmark",
        url=url,
        title=title,
        stage=stage,
        **kwargs
    )


def log_performance_metrics(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    duration: float,
    items_processed: int = 0,
    **kwargs: Any
) -> None:
    """Log performance metrics with structured data.

    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        items_processed: Number of items processed
        **kwargs: Additional metrics
    """
    metrics = {
        "operation": operation,
        "duration_seconds": round(duration, 3),
        "items_processed": items_processed,
        **kwargs
    }

    if items_processed > 0:
        metrics["items_per_second"] = round(items_processed / duration, 2)

    logger.info("Performance metrics", **metrics)


def log_error_with_context(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    operation: str,
    **kwargs: Any
) -> None:
    """Log error with structured context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation that failed
        **kwargs: Additional context
    """
    logger.error(
        "Operation failed",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        **kwargs,
        exc_info=True
    )
