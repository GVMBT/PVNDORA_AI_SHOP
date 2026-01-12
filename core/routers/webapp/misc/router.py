"""
Misc Router - Main Entry Point

Aggregates all misc-related endpoints (FAQ, Promo, Reviews, Leaderboard, Support).
"""

from fastapi import APIRouter

from .faq import faq_router
from .leaderboard import leaderboard_router
from .reviews import reviews_router
from .support import support_router

router = APIRouter(tags=["webapp-misc"])

# Include all sub-routers
router.include_router(faq_router)
router.include_router(reviews_router)
router.include_router(leaderboard_router)
router.include_router(support_router)
