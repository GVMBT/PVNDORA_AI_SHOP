"""
WebApp Misc Router

Promo codes, reviews, leaderboard, FAQ, and support ticket endpoints.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.services.database import get_database
from src.services.money import to_float
from core.auth import verify_telegram_auth
from .models import PromoCheckRequest, WebAppReviewRequest

router = APIRouter(tags=["webapp-misc"])


# --- Support Ticket Models ---
class CreateTicketRequest(BaseModel):
    message: str
    order_id: Optional[str] = None
    issue_type: str = "general"  # general, payment, delivery, refund, other


class TicketMessageRequest(BaseModel):
    ticket_id: str
    message: str


@router.get("/faq")
async def get_webapp_faq(language_code: str = "en", user=Depends(verify_telegram_auth)):
    """Get FAQ entries for the specified language."""
    db = get_database()
    faq_entries = await db.get_faq(language_code)
    
    # Return flat list with all fields needed by frontend
    faq_list = []
    for entry in faq_entries:
        faq_list.append({
            "id": entry.get("id"),
            "question": entry.get("question"),
            "answer": entry.get("answer"),
            "category": entry.get("category", "general")
        })
    
    return {"faq": faq_list, "total": len(faq_list)}


@router.post("/promo/check")
async def check_webapp_promo(request: PromoCheckRequest, user=Depends(verify_telegram_auth)):
    """Check if promo code is valid."""
    db = get_database()
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)
    
    if promo:
        return {
            "valid": True, "code": code, "discount_percent": promo["discount_percent"],
            "expires_at": promo.get("expires_at"),
            "usage_remaining": (promo.get("usage_limit") or 999) - (promo.get("usage_count") or 0)
        }
    return {"valid": False, "code": code, "message": "Invalid or expired promo code"}


@router.post("/reviews")
async def submit_webapp_review(request: WebAppReviewRequest, user=Depends(verify_telegram_auth)):
    """Submit a product review. Awards 5% cashback."""
    db = get_database()
    
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    if order.status not in ["completed", "delivered"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")
    
    existing = await asyncio.to_thread(
        lambda: db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Order already reviewed")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("reviews").insert({
            "user_id": db_user.id, "order_id": request.order_id, "product_id": order.product_id,
            "rating": request.rating, "text": request.text, "cashback_given": False
        }).execute()
    )
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create review")
    
    review_id = result.data[0]["id"]
    cashback_amount = to_float(order.amount) * 0.05
    await asyncio.to_thread(
        lambda: db.client.table("users").update({"balance": to_float(db_user.balance) + cashback_amount}).eq("id", db_user.id).execute()
    )
    await asyncio.to_thread(
        lambda: db.client.table("reviews").update({"cashback_given": True}).eq("id", review_id).execute()
    )
    
    return {
        "success": True, "review_id": review_id, "cashback_awarded": round(cashback_amount, 2),
        "new_balance": round(to_float(db_user.balance) + cashback_amount, 2)
    }


@router.get("/leaderboard")
async def get_webapp_leaderboard(period: str = "all", user=Depends(verify_telegram_auth)):
    """Get savings leaderboard. Supports period: all, month, week"""
    db = get_database()
    LEADERBOARD_SIZE = 25
    now = datetime.now(timezone.utc)
    
    date_filter = None
    if period == "week":
        date_filter = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        date_filter = (now - timedelta(days=30)).isoformat()
    
    if date_filter:
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select(
                "user_id,amount,original_price,users(telegram_id,username,first_name)"
            ).eq("status", "completed").gte("created_at", date_filter).execute()
        )
        
        user_savings = {}
        for order in (orders_result.data or []):
            uid = order.get("user_id")
            if not uid:
                continue
            orig = to_float(order.get("original_price") or order.get("amount") or 0)
            paid = to_float(order.get("amount") or 0)
            saved = max(0, orig - paid)
            
            if uid not in user_savings:
                user_data = order.get("users", {})
                user_savings[uid] = {
                    "telegram_id": user_data.get("telegram_id"),
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "total_saved": 0
                }
            user_savings[uid]["total_saved"] += saved
        
        result_data = sorted(user_savings.values(), key=lambda x: x["total_saved"], reverse=True)[:LEADERBOARD_SIZE]
    else:
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved").gt("total_saved", 0).order("total_saved", desc=True).limit(LEADERBOARD_SIZE).execute()
        )
        result_data = result.data or []
        
        if len(result_data) < LEADERBOARD_SIZE:
            fill_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved").eq("total_saved", 0).order("created_at", desc=True).limit(LEADERBOARD_SIZE - len(result_data)).execute()
            )
            result_data.extend(fill_result.data or [])
    
    total_count = await asyncio.to_thread(lambda: db.client.table("users").select("id", count="exact").execute())
    total_users = total_count.count or 0
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select("user_id", count="exact").eq("status", "completed").gte("created_at", today_start.isoformat()).execute()
    )
    improved_today = improved_result.count or 0
    
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank, user_saved = None, 0
    
    if db_user:
        user_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        if user_saved > 0:
            rank_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").gt("total_saved", user_saved).execute()
            )
            user_rank = (rank_result.count or 0) + 1
        else:
            total_with_savings = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").gt("total_saved", 0).execute()
            )
            user_rank = (total_with_savings.count or 0) + 1
    
    leaderboard = []
    for i, entry in enumerate(result_data):
        tg_id = entry.get("telegram_id")
        display_name = entry.get("username") or entry.get("first_name") or (f"User{str(tg_id)[-4:]}" if tg_id else "User")
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"
        
        leaderboard.append({
            "rank": i + 1, "name": display_name, "total_saved": float(entry.get("total_saved", 0)),
            "is_current_user": tg_id == user.id if tg_id else False
        })
    
    return {
        "leaderboard": leaderboard, "user_rank": user_rank, "user_saved": user_saved,
        "total_users": total_users, "improved_today": improved_today
    }


# ==================== SUPPORT TICKETS ====================

@router.get("/support/tickets")
async def get_user_tickets(user=Depends(verify_telegram_auth)):
    """Get current user's support tickets."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("tickets")
        .select("id, status, issue_type, description, admin_comment, created_at, order_id")
        .eq("user_id", db_user.id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    
    tickets = []
    for t in (result.data or []):
        tickets.append({
            "id": t["id"],
            "status": t["status"],
            "issue_type": t.get("issue_type", "general"),
            "message": t.get("description", ""),
            "admin_reply": t.get("admin_comment"),
            "order_id": t.get("order_id"),
            "created_at": t["created_at"],
        })
    
    return {"tickets": tickets, "count": len(tickets)}


@router.post("/support/tickets")
async def create_user_ticket(request: CreateTicketRequest, user=Depends(verify_telegram_auth)):
    """Create a new support ticket."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if len(request.message.strip()) < 10:
        raise HTTPException(status_code=400, detail="Message too short (min 10 characters)")
    
    # Validate order_id if provided
    if request.order_id:
        order = await db.get_order_by_id(request.order_id)
        if not order or order.user_id != db_user.id:
            raise HTTPException(status_code=400, detail="Invalid order ID")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("tickets").insert({
            "user_id": db_user.id,
            "order_id": request.order_id,
            "issue_type": request.issue_type,
            "description": request.message.strip(),
            "status": "open",
        }).execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create ticket")
    
    ticket = result.data[0]
    return {
        "success": True,
        "ticket_id": ticket["id"],
        "message": "Ticket created successfully. Our team will respond soon."
    }


@router.get("/support/tickets/{ticket_id}")
async def get_user_ticket(ticket_id: str, user=Depends(verify_telegram_auth)):
    """Get specific ticket details."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("tickets")
        .select("*")
        .eq("id", ticket_id)
        .eq("user_id", db_user.id)
        .single()
        .execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    t = result.data
    return {
        "ticket": {
            "id": t["id"],
            "status": t["status"],
            "issue_type": t.get("issue_type", "general"),
            "message": t.get("description", ""),
            "admin_reply": t.get("admin_comment"),
            "order_id": t.get("order_id"),
            "created_at": t["created_at"],
        }
    }
