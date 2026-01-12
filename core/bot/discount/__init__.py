"""Discount Bot - Button-based Telegram bot for discount channel.

This bot provides:
- Button-based catalog navigation (no Mini App)
- Insurance options with replacements
- Delayed delivery (1-4 hours via QStash)
- Migration offers to PVNDORA

Entry point: discount_router
"""

from aiogram import Router

from .handlers.catalog import router as catalog_router
from .handlers.issues import router as issues_router
from .handlers.purchase import router as purchase_router
from .handlers.start import router as start_router
from .middlewares import (
    ChannelSubscriptionMiddleware,
    DiscountAuthMiddleware,
    TermsAcceptanceMiddleware,
)

# Main router for discount bot
discount_router = Router(name="discount")

# Include all handlers
discount_router.include_router(start_router)
discount_router.include_router(catalog_router)
discount_router.include_router(purchase_router)
discount_router.include_router(issues_router)

__all__ = [
    "ChannelSubscriptionMiddleware",
    "DiscountAuthMiddleware",
    "TermsAcceptanceMiddleware",
    "discount_router",
]
