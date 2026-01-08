"""
WebApp Misc Router

Promo codes, reviews, leaderboard, FAQ, and support ticket endpoints.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.services.database import get_database
from core.services.money import to_float
from core.services.currency_response import CurrencyFormatter
from core.db import get_redis
from core.auth import verify_telegram_auth
from core.logging import get_logger
from .models import PromoCheckRequest, WebAppReviewRequest

logger = get_logger(__name__)
router = APIRouter(tags=["webapp-misc"])


# --- Support Ticket Models ---
class CreateTicketRequest(BaseModel):
    message: str
    order_id: Optional[str] = None
    item_id: Optional[str] = None  # Specific order item ID (for item-level issues)
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
    """Submit a product review. Awards 5% cashback per review."""
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
    if order.status not in ["delivered", "partial"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")
    
    # Get order items to determine product_id
    order_items = await db.get_order_items_by_order(request.order_id)
    if not order_items:
        raise HTTPException(status_code=400, detail="Order has no products")
    
    # Determine which product is being reviewed
    product_id = None
    if request.product_id:
        # Client specified which product to review
        product_id = request.product_id
    elif request.order_item_id:
        # Client specified which order_item to review
        for item in order_items:
            if item.get("id") == request.order_item_id:
                product_id = item.get("product_id")
                break
    else:
        # Fallback: first item in order (legacy behavior for single-item orders)
        product_id = order_items[0].get("product_id")
    
    if not product_id:
        raise HTTPException(status_code=400, detail="Product not found in order")
    
    # Check if THIS specific product in THIS order already has a review
    existing = await asyncio.to_thread(
        lambda: db.client.table("reviews").select("id")
            .eq("order_id", request.order_id)
            .eq("product_id", product_id)
            .execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="This product already has a review")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("reviews").insert({
            "user_id": db_user.id, "order_id": request.order_id, "product_id": product_id,
            "rating": request.rating, "text": request.text, "cashback_given": False
        }).execute()
    )
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create review")
    
    review_id = result.data[0]["id"]
    cashback_amount = to_float(order.amount) * 0.05
    
    # Process cashback immediately (inline, not via QStash - more reliable)
    new_balance = to_float(db_user.balance) + cashback_amount
    
    # 1. Update user balance
    await asyncio.to_thread(
        lambda: db.client.table("users").update({"balance": new_balance}).eq("id", db_user.id).execute()
    )
    
    # 2. Create balance_transaction for history
    await asyncio.to_thread(
        lambda: db.client.table("balance_transactions").insert({
            "user_id": db_user.id, "type": "cashback", "amount": cashback_amount,
            "status": "completed", "description": "5% кэшбек за отзыв", "reference_id": request.order_id
        }).execute()
    )
    
    # 3. Mark review as processed
    await asyncio.to_thread(
        lambda: db.client.table("reviews").update({"cashback_given": True}).eq("id", review_id).execute()
    )
    
    # 4. Send notification (best-effort)
    try:
        from core.routers.deps import get_notification_service
        notification_service = get_notification_service()
        await notification_service.send_cashback_notification(
            telegram_id=db_user.telegram_id,
            cashback_amount=cashback_amount,
            new_balance=new_balance,
            reason="review"
        )
        logger.info(f"Cashback notification sent to user {db_user.telegram_id}")
    except Exception as e:
        logger.error(f"Failed to send cashback notification to user {db_user.telegram_id}: {e}", exc_info=True)
    
    return {
        "success": True, "review_id": review_id, "cashback_amount": round(cashback_amount, 2),
        "new_balance": round(new_balance, 2),
        "message": "Кэшбек начислен!"
    }


@router.get("/leaderboard")
async def get_webapp_leaderboard(period: str = "all", limit: int = 15, offset: int = 0, user=Depends(verify_telegram_auth)):
    """Get savings leaderboard. Supports period: all, month, week and pagination."""
    db = get_database()
    redis = get_redis()
    LEADERBOARD_SIZE = min(limit, 50)  # Cap at 50
    now = datetime.now(timezone.utc)
    
    # Get user's currency formatter for converting amounts
    formatter = await CurrencyFormatter.create(user.id, db, redis)
    
    date_filter = None
    period_modules_count_map = {}  # Initialize for period-based queries
    if period == "week":
        date_filter = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        date_filter = (now - timedelta(days=30)).isoformat()
    
    if date_filter:
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select(
                "user_id,amount,original_price,users(telegram_id,username,first_name,photo_url)"
            ).eq("status", "delivered").gte("created_at", date_filter).execute()
        )
        
        user_savings = {}
        user_ids_from_orders = set()  # Collect user_ids for modules count
        for order in (orders_result.data or []):
            uid = order.get("user_id")
            if not uid:
                continue
            user_ids_from_orders.add(uid)  # Track user_id for modules count
            orig = to_float(order.get("original_price") or order.get("amount") or 0)
            paid = to_float(order.get("amount") or 0)
            saved = max(0, orig - paid)
            
            if uid not in user_savings:
                user_data = order.get("users", {})
                user_savings[uid] = {
                    "user_id": uid,  # Store user_id for modules count lookup
                    "telegram_id": user_data.get("telegram_id"),
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "photo_url": user_data.get("photo_url"),
                    "total_saved": 0
                }
            user_savings[uid]["total_saved"] += saved
        
        result_data = sorted(user_savings.values(), key=lambda x: x["total_saved"], reverse=True)[:LEADERBOARD_SIZE]
        
        # Pre-fetch modules count for period-based queries (we already have user_ids)
        period_modules_count_map = {}
        if user_ids_from_orders:
            for uid in user_ids_from_orders:
                count_result = await asyncio.to_thread(
                    lambda uid_param=uid: db.client.table("orders")
                    .select("id", count="exact")
                    .eq("user_id", uid_param)
                    .eq("status", "delivered")
                    .execute()
                )
                period_modules_count_map[uid] = count_result.count or 0
    else:
        # Get users with savings (sorted by total_saved desc)
        # Use range() for proper pagination
        users_with_savings_count = await asyncio.to_thread(
            lambda: db.client.table("users").select("id", count="exact").gt("total_saved", 0).execute()
        )
        savings_count = users_with_savings_count.count or 0
        
        if offset < savings_count:
            # Still within users who have savings
            result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved,photo_url")
                .gt("total_saved", 0)
                .order("total_saved", desc=True)
                .range(offset, offset + LEADERBOARD_SIZE - 1)
                .execute()
            )
            result_data = result.data or []
            
            # If we need more to fill the page, get users with 0 savings
            if len(result_data) < LEADERBOARD_SIZE:
                remaining = LEADERBOARD_SIZE - len(result_data)
                fill_result = await asyncio.to_thread(
                    lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved,photo_url")
                    .eq("total_saved", 0)
                    .order("created_at", desc=True)
                    .range(0, remaining - 1)
                    .execute()
                )
                result_data.extend(fill_result.data or [])
        else:
            # We're past all users with savings, now showing users with 0 savings
            zero_offset = offset - savings_count
            fill_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved,photo_url")
                .eq("total_saved", 0)
                .order("created_at", desc=True)
                .range(zero_offset, zero_offset + LEADERBOARD_SIZE - 1)
                .execute()
            )
            result_data = fill_result.data or []
    
    total_count = await asyncio.to_thread(lambda: db.client.table("users").select("id", count="exact").execute())
    total_users = total_count.count or 0
    
    # CRITICAL: If offset exceeds total users, return empty result
    if offset >= total_users:
        db_user = await db.get_user_by_telegram_id(user.id)
        user_saved = float(db_user.total_saved) if db_user and hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        return {
            "leaderboard": [], 
            "user_rank": None, 
            "user_saved": formatter.convert(user_saved),
            "user_saved_usd": user_saved,
            "total_users": total_users, 
            "improved_today": 0,
            "has_more": False,
            "offset": offset,
            "limit": LEADERBOARD_SIZE,
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
        }
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select("user_id", count="exact").eq("status", "delivered").gte("created_at", today_start.isoformat()).execute()
    )
    improved_today = improved_result.count or 0
    
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank, user_saved = None, 0
    user_found_in_list = False
    
    # Collect user IDs to batch fetch delivered orders count
    # For period-based queries, user_ids are already in result_data
    # For all-time queries, we need to get them from telegram_ids
    user_ids_for_count = []
    telegram_id_to_user_id = {}
    modules_count_map = {}
    
    if date_filter:
        # For period-based queries, use pre-fetched modules_count_map
        modules_count_map = period_modules_count_map
        # Also build telegram_id_to_user_id mapping
        for entry in result_data:
            uid = entry.get("user_id")
            tg_id = entry.get("telegram_id")
            if uid and tg_id:
                telegram_id_to_user_id[tg_id] = uid
    else:
        # For all-time queries, get user_ids from telegram_ids
        for entry in result_data:
            tg_id = entry.get("telegram_id")
            if tg_id:
                # Get user_id from telegram_id
                user_result = await asyncio.to_thread(
                    lambda tid=tg_id: db.client.table("users").select("id").eq("telegram_id", tid).limit(1).execute()
                )
                if user_result.data and len(user_result.data) > 0:
                    user_id = user_result.data[0]["id"]
                    user_ids_for_count.append(user_id)
                    telegram_id_to_user_id[tg_id] = user_id
        
        # Batch fetch delivered orders count for all users
        if user_ids_for_count:
            # Count delivered orders for each user
            for uid in user_ids_for_count:
                count_result = await asyncio.to_thread(
                    lambda uid_param=uid: db.client.table("orders")
                    .select("id", count="exact")
                    .eq("user_id", uid_param)
                    .eq("status", "delivered")
                    .execute()
                )
                modules_count_map[uid] = count_result.count or 0
    
    leaderboard = []
    for i, entry in enumerate(result_data):
        # Cap rank at total_users to avoid inflated ranks
        actual_rank = min(i + 1 + offset, total_users)
        
        tg_id = entry.get("telegram_id")
        display_name = entry.get("username") or entry.get("first_name") or (f"User{str(tg_id)[-4:]}" if tg_id else "User")
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"
        
        is_current = tg_id == user.id if tg_id else False
        if is_current:
            user_found_in_list = True
            user_rank = actual_rank
            user_saved = float(entry.get("total_saved", 0))
        
        # Get modules count (delivered orders) for this user
        # For period-based queries, user_id is already in entry
        # For all-time queries, get it from telegram_id mapping
        user_id = entry.get("user_id") or (telegram_id_to_user_id.get(tg_id) if tg_id else None)
        modules_count = modules_count_map.get(user_id, 0) if user_id else 0
        
        leaderboard.append({
            "rank": actual_rank,
            "name": display_name, 
            "total_saved": formatter.convert(float(entry.get("total_saved", 0))),
            "total_saved_usd": float(entry.get("total_saved", 0)),
            "is_current_user": is_current,
            "telegram_id": tg_id,  # For avatar lookup
            "photo_url": entry.get("photo_url"),  # User profile photo from Telegram
            "modules_count": modules_count, # Count of delivered orders
        })
    
    # If user not in current page, calculate their actual rank
    if not user_found_in_list and db_user:
        user_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        if user_saved > 0:
            rank_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").gt("total_saved", user_saved).execute()
            )
            user_rank = (rank_result.count or 0) + 1
        else:
            # For users with no savings, find their position by created_at
            # This matches the fill_result ordering
            user_created = db_user.created_at
            if user_created:
                earlier_count = await asyncio.to_thread(
                    lambda: db.client.table("users").select("id", count="exact")
                    .eq("total_saved", 0)
                    .lt("created_at", user_created.isoformat())
                    .execute()
                )
                users_with_savings = await asyncio.to_thread(
                    lambda: db.client.table("users").select("id", count="exact").gt("total_saved", 0).execute()
                )
                user_rank = (users_with_savings.count or 0) + (earlier_count.count or 0) + 1
            else:
                user_rank = total_users
    
    # Calculate has_more based on actual data availability
    # has_more is True only if there are more users beyond current offset + returned count
    next_offset = offset + len(leaderboard)
    has_more = next_offset < total_users and len(leaderboard) == LEADERBOARD_SIZE
    
    return {
        "leaderboard": leaderboard, 
        "user_rank": user_rank, 
        "user_saved": formatter.convert(user_saved),
        "user_saved_usd": user_saved,
        "total_users": total_users, 
        "improved_today": improved_today,
        "has_more": has_more,
        "offset": offset,
        "limit": LEADERBOARD_SIZE,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
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
        .select("id, status, issue_type, description, admin_comment, created_at, order_id, item_id")
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
            "item_id": t.get("item_id"),  # Include item_id in response
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
    
    # Validate item_id if provided (must belong to the order)
    if request.item_id and request.order_id:
        item_result = await asyncio.to_thread(
            lambda: db.client.table("order_items")
            .select("id, order_id")
            .eq("id", request.item_id)
            .eq("order_id", request.order_id)
            .limit(1)
            .execute()
        )
        if not item_result.data:
            raise HTTPException(status_code=400, detail="Invalid item ID or item does not belong to the order")
    
    ticket_data = {
        "user_id": db_user.id,
        "order_id": request.order_id,
        "issue_type": request.issue_type,
        "description": request.message.strip(),
        "status": "open",
    }
    
    if request.item_id:
        ticket_data["item_id"] = request.item_id
    
    result = await asyncio.to_thread(
        lambda: db.client.table("tickets").insert(ticket_data).execute()
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
