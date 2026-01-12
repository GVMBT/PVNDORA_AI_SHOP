"""
Orders Router Module

Main router for order-related endpoints.
Combines CRUD and payment endpoints.
"""

from fastapi import APIRouter

from .crud import crud_router
from .payments import payments_router

router = APIRouter()

# Include CRUD endpoints (order history, status)
router.include_router(crud_router)

# Include payment endpoints (order creation)
router.include_router(payments_router)
