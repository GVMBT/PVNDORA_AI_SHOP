"""WebApp API Router.

Mini App endpoints for Telegram WebApp frontend.
Combines all sub-routers into a single router with prefix /api/webapp.
"""

from fastapi import APIRouter

from .ai_chat import router as ai_chat_router
from .auth import router as auth_router
from .cart import router as cart_router
from .misc import router as misc_router
from .orders import router as orders_router
from .partner import router as partner_router
from .profile import router as profile_router
from .public import router as public_router
from .realtime import router as realtime_router
from .studio import studio_router

# Create main router with prefix
router = APIRouter(prefix="/api/webapp", tags=["webapp"])

# Include all sub-routers
router.include_router(auth_router)
router.include_router(public_router)
router.include_router(profile_router)
router.include_router(partner_router)
router.include_router(orders_router)
router.include_router(cart_router)
router.include_router(misc_router)
router.include_router(ai_chat_router)
router.include_router(realtime_router)
router.include_router(studio_router)

# Export for backward compatibility
__all__ = ["router"]
