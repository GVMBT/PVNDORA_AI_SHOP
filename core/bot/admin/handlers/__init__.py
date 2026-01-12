"""
Admin Bot Handlers

Combines all admin command and callback handlers.
"""

from aiogram import Router

from .broadcast import router as broadcast_router
from .stats import router as stats_router

router = Router(name="admin")

# Include all sub-routers
router.include_router(broadcast_router)
router.include_router(stats_router)
