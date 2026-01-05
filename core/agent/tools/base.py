"""
Base module for agent tools.

Contains database and user context management shared across all tool modules.
"""
from dataclasses import dataclass
from core.logging import get_logger

logger = get_logger(__name__)

# Global DB instance - set during agent initialization
_db = None


# Global user context - set before each agent call
@dataclass
class _UserContext:
    user_id: str = ""
    telegram_id: int = 0
    language: str = "en"
    currency: str = "USD"


_user_ctx = _UserContext()


def set_db(db):
    """Set the database instance for tools."""
    global _db
    _db = db


def get_db():
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call set_db() first.")
    return _db


def set_user_context(user_id: str, telegram_id: int, language: str, currency: str):
    """Set user context for all tools. Called by agent before each chat."""
    global _user_ctx
    _user_ctx = _UserContext(
        user_id=user_id,
        telegram_id=telegram_id,
        language=language,
        currency=currency
    )
    logger.debug(f"User context set: {_user_ctx}")


def get_user_context() -> _UserContext:
    """Get current user context."""
    return _user_ctx
