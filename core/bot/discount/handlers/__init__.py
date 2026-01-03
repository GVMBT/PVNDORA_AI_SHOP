"""Discount bot handlers."""
from .start import router as start_router
from .catalog import router as catalog_router
from .purchase import router as purchase_router
from .issues import router as issues_router

__all__ = [
    "start_router",
    "catalog_router",
    "purchase_router",
    "issues_router",
]
