"""
FastAPI Routers Package

Логическое разделение endpoints без создания новых serverless функций.
Все роутеры включаются в api/index.py.
"""

from core.routers.webhooks import router as webhooks_router
from core.routers.products import router as products_router
from core.routers.admin import router as admin_router
from core.routers.workers import router as workers_router

__all__ = [
    "webhooks_router",
    "products_router", 
    "admin_router",
    "workers_router",
]

