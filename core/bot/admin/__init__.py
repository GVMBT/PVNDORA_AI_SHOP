"""Admin Bot Module for PVNDORA.

Manages broadcast messaging, stats, and administrative functions.
"""

from .handlers import router
from .middlewares import AdminAuthMiddleware

__all__ = ["AdminAuthMiddleware", "router"]
