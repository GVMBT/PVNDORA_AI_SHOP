"""
FastAPI Routers Package

Логическое разделение endpoints без создания новых serverless функций.
Все роутеры включаются в api/index.py.
"""

from core.routers.webhooks import router as webhooks_router
from core.routers.admin import router as admin_router
from core.routers.workers import router as workers_router
from core.routers.webapp import router as webapp_router

__all__ = [
    "webhooks_router",
    "admin_router",
    "workers_router",
    "webapp_router",
]
