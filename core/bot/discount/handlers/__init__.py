"""Discount bot handlers."""

from .catalog import router as catalog_router
from .issues import router as issues_router
from .purchase import router as purchase_router
from .start import router as start_router

__all__ = [
    "catalog_router",
    "issues_router",
    "purchase_router",
    "start_router",
]
