"""
Profile Module

User profile, balance, and withdrawal operations.
Re-exports main router for backward compatibility.
"""

from .router import router

__all__ = ["router"]
