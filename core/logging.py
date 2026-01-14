"""
Centralized logging configuration for PVNDORA.

Usage:
    from core.logging import get_logger
    logger = get_logger(__name__)

    logger.info("Operation completed")
    logger.error("Failed operation", exc_info=True)
"""

import logging
import os
import sys
from functools import cache

# Default format for logs
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)s - %(name)s - %(message)s"


def _get_log_level() -> int:
    """Get log level from environment or default to INFO."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _configure_root_logger() -> None:
    """Configure root logger with appropriate handlers."""
    root = logging.getLogger()

    # Only configure if no handlers exist
    if root.handlers:
        return

    # Set root level
    root.setLevel(_get_log_level())

    # Console handler with appropriate format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(_get_log_level())

    # Use simple format in production (Vercel), detailed locally
    is_production = os.environ.get("VERCEL") == "1"
    formatter = logging.Formatter(LOG_FORMAT_SIMPLE if is_production else LOG_FORMAT)
    handler.setFormatter(formatter)

    root.addHandler(handler)

    # Disable verbose HTTP logging from httpx/supabase (set to WARNING level)
    # This reduces log noise from API requests
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
    logging.getLogger("httpcore.connection").setLevel(logging.WARNING)


# Configure once on module import
_configure_root_logger()


@cache
def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def _escape_log_injection(value: str) -> str:
    """
    Escape characters that could be used for log injection attacks (CWE-117).

    Replaces newlines, carriage returns, and other control characters
    that could manipulate log format or inject fake log entries.

    Args:
        value: String to escape

    Returns:
        Escaped string safe for logging
    """
    # Replace characters that could break log format or inject entries
    return (
        value.replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\x00", "")  # Remove null bytes
    )


def sanitize_id_for_logging(id_value: str | None) -> str:
    """
    Sanitize ID for safe logging (truncate to first 8 chars to avoid logging user-controlled data).

    Also escapes log injection characters (CWE-117).

    Args:
        id_value: ID value to sanitize (can be None)

    Returns:
        Sanitized ID string (first 8 chars) or "N/A" if None
    """
    if not id_value:
        return "N/A"
    # Convert to string and escape injection characters first
    safe_value = _escape_log_injection(str(id_value))
    return safe_value[:8] if len(safe_value) > 8 else safe_value


def sanitize_string_for_logging(value: str | None, max_length: int = 50) -> str:
    """
    Sanitize string for safe logging (truncate to max_length to avoid logging large user-controlled data).

    Also escapes log injection characters (CWE-117).

    Args:
        value: String value to sanitize (can be None)
        max_length: Maximum length to keep (default: 50)

    Returns:
        Sanitized string or "N/A" if None
    """
    if not value:
        return "N/A"
    # Escape injection characters first
    safe_value = _escape_log_injection(str(value))
    if len(safe_value) <= max_length:
        return safe_value
    return safe_value[:max_length] + "..."


# Convenience exports
__all__ = [
    "LOG_FORMAT",
    "LOG_FORMAT_SIMPLE",
    "get_logger",
    "sanitize_id_for_logging",
    "sanitize_string_for_logging",
]
