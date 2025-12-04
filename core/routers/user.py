"""
User API Router

User-specific endpoints (referral, wishlist, reviews).
These are non-webapp endpoints with /api prefix.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.services.database import get_database
from core.auth import verify_telegram_auth

router = APIRouter(prefix="/api", tags=["user"])


class SubmitReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: str | None = None


# NOTE: /api/user/referral and /api/webapp/referral/share-link remain in api/index.py
# because they require bot_instance which is initialized there


# ==================== WISHLIST ====================

@router.get("/wishlist")
async def get_wishlist(user=Depends(verify_telegram_auth)):
    """Get user's wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    products = await db.get_wishlist(db_user.id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock_count": p.stock_count
        }
        for p in products
    ]


@router.post("/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user=Depends(verify_telegram_auth)):
    """Add product to wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.add_to_wishlist(db_user.id, product_id)
    return {"success": True}


@router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user=Depends(verify_telegram_auth)):
    """Remove product from wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.remove_from_wishlist(db_user.id, product_id)
    return {"success": True}


# ==================== REVIEWS ====================

@router.post("/reviews")
async def submit_review(request: SubmitReviewRequest, user=Depends(verify_telegram_auth)):
    """Submit product review with 5% cashback"""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Not your order")
    
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="Order not completed")
    
    existing = db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Review already submitted")
    
    await db.create_review(
        user_id=db_user.id,
        order_id=request.order_id,
        product_id=order.product_id,
        rating=request.rating,
        text=request.text
    )
    
    cashback = order.amount * 0.05
    await db.update_user_balance(db_user.id, cashback)
    
    db.client.table("reviews").update({
        "cashback_given": True
    }).eq("order_id", request.order_id).execute()
    
    return {
        "success": True,
        "cashback": cashback,
        "new_balance": db_user.balance + cashback
    }
