"""Profile Router - Main Entry Point.

Aggregates all profile-related endpoints.
"""

from fastapi import APIRouter

from .balance import balance_router
from .profile import profile_router
from .withdrawals import withdrawals_router

router = APIRouter(tags=["webapp-profile"])

# Include all sub-routers
router.include_router(profile_router)
router.include_router(balance_router)
router.include_router(withdrawals_router)
