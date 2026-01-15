"""FAQ and Promo Code endpoints.

FAQ entries and promo code validation.
"""

from fastapi import APIRouter, Depends

from core.auth import verify_telegram_auth
from core.logging import get_logger
from core.routers.webapp.models import PromoCheckRequest
from core.services.database import get_database

logger = get_logger(__name__)
faq_router = APIRouter(tags=["webapp-misc-faq"])


@faq_router.get("/faq")
async def get_webapp_faq(language_code: str = "en", user=Depends(verify_telegram_auth)):
    """Get FAQ entries for the specified language."""
    db = get_database()
    faq_entries = await db.get_faq(language_code)

    # Return flat list with all fields needed by frontend
    faq_list = []
    for entry in faq_entries:
        faq_list.append(
            {
                "id": entry.get("id"),
                "question": entry.get("question"),
                "answer": entry.get("answer"),
                "category": entry.get("category", "general"),
            },
        )

    return {"faq": faq_list, "total": len(faq_list)}


@faq_router.post("/promo/check")
async def check_webapp_promo(request: PromoCheckRequest, user=Depends(verify_telegram_auth)):
    """Check if promo code is valid.

    Returns product_id if promo is product-specific:
    - product_id IS NULL: applies to entire cart
    - product_id IS NOT NULL: applies only to that product
    """
    db = get_database()
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)

    if promo:
        return {
            "valid": True,
            "code": code,
            "discount_percent": promo["discount_percent"],
            "product_id": promo.get("product_id"),  # NULL = cart-wide, NOT NULL = product-specific
            "expires_at": promo.get("expires_at"),
            "usage_remaining": (promo.get("usage_limit") or 999) - (promo.get("usage_count") or 0),
        }
    return {"valid": False, "code": code, "message": "Invalid or expired promo code"}
