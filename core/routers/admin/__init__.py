"""
Admin API Router

Admin-only endpoints for managing products, users, orders, and stock.
Combines all sub-routers into a single router with tag "admin".
"""
from fastapi import APIRouter

from .products import router as products_router
from .users import router as users_router
from .orders import router as orders_router
from .analytics import router as analytics_router
from .referral import router as referral_router
from .rag import router as rag_router
from .tickets import router as tickets_router
from .promo import router as promo_router
from .replacements import router as replacements_router
from .broadcast import router as broadcast_router

# Create main router
router = APIRouter(tags=["admin"])

# Include all sub-routers
router.include_router(products_router)
router.include_router(users_router)
router.include_router(orders_router)
router.include_router(analytics_router)
router.include_router(referral_router)
router.include_router(rag_router)
router.include_router(tickets_router)
router.include_router(promo_router)
router.include_router(replacements_router)
router.include_router(broadcast_router)

# Export for backward compatibility
__all__ = ["router"]
