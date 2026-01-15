"""Orders Module.

Order creation, history, and payment processing.
Re-exports main router for backward compatibility.
"""

from .router import router

__all__ = ["router"]
