"""User-related tool handlers."""
import asyncio
from typing import Dict, Any

from .helpers import create_error_response, resolve_product_id
from core.logging import get_logger

logger = get_logger(__name__)


async def handle_get_user_orders(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get user's recent orders."""
    limit = arguments.get("limit", 5)
    orders = await db.get_user_orders(user_id, limit=limit)
    
    return {
        "count": len(orders),
        "orders": [
            {
                "id": o.id[:8],
                "product_id": o.product_id,
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "expires_at": o.expires_at.isoformat() if o.expires_at else None
            }
            for o in orders
        ]
    }


async def handle_add_to_wishlist(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Add a product to user's wishlist."""
    product_id_or_name = arguments.get("product_id", "")
    resolved_id, error = await resolve_product_id(product_id_or_name, db)
    if error:
        return {"success": False, "reason": error}
    
    product = await db.get_product_by_id(resolved_id)
    if not product:
        return {"success": False, "reason": "Product not found"}
    
    # Check if item already exists
    existing_check = await asyncio.to_thread(
        lambda: db.client.table("wishlist").select("id").eq("user_id", user_id).eq("product_id", resolved_id).execute()
    )
    
    if existing_check.data:
        return {"success": False, "reason": "Already in wishlist"}
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("wishlist").insert({
                "user_id": user_id,
                "product_id": resolved_id,
                "reminded": False
            }).execute()
        )
        
        if result.data:
            return {
                "success": True,
                "product_name": product.name,
                "message": "Added to wishlist"
            }
        return {"success": False, "reason": "Failed to add to wishlist"}
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return {"success": False, "reason": "Already in wishlist"}
        return create_error_response(e, "Database error.")


async def handle_get_wishlist(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get user's wishlist with saved products."""
    try:
        wishlist_items = await asyncio.to_thread(
            lambda: db.client.table("wishlist").select(
                "id,product_id,products(name,price,stock_count:stock_items(count))"
            ).eq("user_id", user_id).execute()
        )
        
        return {
            "count": len(wishlist_items.data),
            "items": [
                {
                    "id": item["product_id"],
                    "name": item.get("products", {}).get("name", "Unknown"),
                    "price": item.get("products", {}).get("price", 0),
                    "in_stock": (item.get("products", {}).get("stock_count") or [{}])[0].get("count", 0) > 0
                }
                for item in wishlist_items.data
            ]
        }
    except Exception as e:
        logger.error(f"get_wishlist failed: {e}", exc_info=True)
        return {"count": 0, "items": [], "error": str(e)}


async def handle_get_referral_info(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get user's referral link and statistics."""
    try:
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "telegram_id,balance,personal_ref_percent"
            ).eq("id", user_id).execute()
        )
        
        if not user_result.data:
            return {"success": False}
        
        user = user_result.data[0]
        
        # Count Level 1 referrals (direct)
        level1_refs = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "id", count="exact"
            ).eq("referrer_id", user_id).execute()
        )
        level1_count = level1_refs.count if level1_refs.count else 0
        
        # Count Level 2 and 3 referrals
        level2_count = 0
        level3_count = 0
        if level1_count > 0 and level1_refs.data:
            level1_ids = [r["id"] for r in level1_refs.data]
            for l1_id in level1_ids:
                l2_refs = await asyncio.to_thread(
                    lambda lid=l1_id: db.client.table("users").select(
                        "id", count="exact"
                    ).eq("referrer_id", lid).execute()
                )
                level2_count += l2_refs.count if l2_refs.count else 0
                
                if l2_refs.data:
                    for l2 in l2_refs.data:
                        l3_refs = await asyncio.to_thread(
                            lambda lid=l2["id"]: db.client.table("users").select(
                                "id", count="exact"
                            ).eq("referrer_id", lid).execute()
                        )
                        level3_count += l3_refs.count if l3_refs.count else 0
        
        return {
            "success": True,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user['telegram_id']}",
            "referral_levels": {
                "level_1": {"count": level1_count, "percent": 20},
                "level_2": {"count": level2_count, "percent": 10},
                "level_3": {"count": level3_count, "percent": 5}
            },
            "total_referrals": level1_count + level2_count + level3_count,
            "balance": user["balance"]
        }
    except Exception as e:
        logger.error(f"get_referral_info failed: {e}")
        return create_error_response(e, "Failed to get referral info.")


async def handle_apply_promo_code(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Check and apply a promo code for discount."""
    code = arguments.get("code", "").strip().upper()
    promo = await db.validate_promo_code(code)
    
    if promo:
        return {
            "valid": True,
            "code": code,
            "discount_percent": promo["discount_percent"],
            "message": f"Promo code applied! {promo['discount_percent']}% discount"
        }
    return {
        "valid": False,
        "message": "Invalid or expired promo code"
    }


# Export handlers mapping
USER_HANDLERS = {
    "get_user_orders": handle_get_user_orders,
    "add_to_wishlist": handle_add_to_wishlist,
    "get_wishlist": handle_get_wishlist,
    "get_referral_info": handle_get_referral_info,
    "apply_promo_code": handle_apply_promo_code,
}

