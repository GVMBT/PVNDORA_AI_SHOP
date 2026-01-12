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
from functools import lru_cache

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


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Convenience exports
__all__ = ["get_logger", "LOG_FORMAT", "LOG_FORMAT_SIMPLE"]
