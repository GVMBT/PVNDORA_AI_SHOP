"""
PVNDORA AI Marketplace - Main FastAPI Application

Single entry point for all webhooks, APIs, and workers.
Optimized for Vercel Hobby plan (max 12 serverless functions).

Routes:
- /api/webhook - Telegram webhook
- /api/webapp/* - Mini App API
- /api/webhook/payment/* - Payment provider webhooks
- /api/admin/* - Admin endpoints
- /api/workers/* - QStash workers
- /api/crons/* - Scheduled jobs
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from aiogram import types

# Core imports - use centralized bot/dispatcher from core/bot.py
from core.db import get_supabase, get_redis, RedisKeys
from core.bot import get_bot, get_dispatcher
from core.queue import publish_to_worker, verify_qstash_request, WorkerEndpoints
from core.models import (
    HealthCheck,
    ReviewCreate,
    PromoCodeCheck,
    BroadcastRequest,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("PVNDORA API starting up...")
    yield
    logger.info("PVNDORA API shutting down...")


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="PVNDORA AI Marketplace",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request Models
# ============================================================

class OrderCreateRequest(BaseModel):
    product_id: str
    quantity: int = 1
    promo_code: Optional[str] = None


class ReviewCreateRequest(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    text: Optional[str] = None


class PromoCheckRequest(BaseModel):
    code: str


class BanUserRequest(BaseModel):
    user_telegram_id: int
    reason: Optional[str] = None


class StockAddRequest(BaseModel):
    product_id: str
    content: str
    expires_at: Optional[str] = None


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "pvndora", "version": "1.0.0"}


# ============================================================
# Telegram Webhook
# ============================================================

@app.post("/api/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook handler.
    
    Validates update and processes via aiogram dispatcher.
    Uses BackgroundTasks for non-blocking response.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook received update_id: {data.get('update_id')}")
        
        try:
            current_bot = get_bot()
            current_dp = get_dispatcher()
        except ValueError as e:
            logger.error(f"Bot or Dispatcher not initialized: {e}")
            return {"ok": False, "error": "Bot not configured"}
        
        # Parse and feed update
        update = types.Update.model_validate(data, context={"bot": current_bot})
        
        # Process in background for faster response
        background_tasks.add_task(current_dp.feed_update, current_bot, update)
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


# ============================================================
# Mini App API
# ============================================================

@app.get("/api/webapp/products")
async def get_products(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get product catalog with availability and discounts."""
    supabase = await get_supabase()
    
    query = supabase.table("products").select(
        "*, available_stock_with_discounts(*)"
    ).eq("status", "active")
    
    if category:
        query = query.eq("type", category)
    
    result = await query.range(offset, offset + limit - 1).execute()
    return {"products": result.data or []}


@app.get("/api/webapp/products/{product_id}")
async def get_product_detail(product_id: str):
    """Get single product with social proof."""
    supabase = await get_supabase()
    
    # Get product with stock info
    result = await supabase.table("products").select(
        "*, available_stock_with_discounts(*)"
    ).eq("id", product_id).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get social proof (reviews, sales count)
    reviews_result = await supabase.table("reviews").select(
        "rating, text, created_at, users(first_name)"
    ).eq("product_id", product_id).order("created_at", desc=True).limit(5).execute()
    
    product = result.data
    product["reviews"] = reviews_result.data or []
    
    return product


@app.get("/api/webapp/orders")
async def get_user_orders(user_telegram_id: int):
    """Get user's order history."""
    supabase = await get_supabase()
    
    # Get user ID first
    user_result = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if not user_result.data:
        return {"orders": []}
    
    orders_result = await supabase.table("orders").select(
        "*, products(name, type)"
    ).eq("user_id", user_result.data["id"]).order(
        "created_at", desc=True
    ).limit(20).execute()
    
    return {"orders": orders_result.data or []}


@app.post("/api/webapp/orders")
async def create_order(
    order_data: OrderCreateRequest,
    user_telegram_id: int,
    background_tasks: BackgroundTasks
):
    """Create a new order with availability check."""
    supabase = await get_supabase()
    
    # Call RPC for atomic order creation
    result = await supabase.rpc("create_order_with_availability_check", {
        "p_product_id": order_data.product_id,
        "p_user_telegram_id": user_telegram_id,
        "p_quantity": order_data.quantity,
        "p_promo_code": order_data.promo_code
    }).execute()
    
    if not result.data or not result.data[0].get("order_id"):
        raise HTTPException(status_code=400, detail="Failed to create order")
    
    order_result = result.data[0]
    
    return {
        "order_id": order_result["order_id"],
        "amount": order_result["amount"],
        "order_type": order_result["order_type"]
    }


@app.get("/api/webapp/leaderboard")
async def get_leaderboard(user_telegram_id: Optional[int] = None):
    """Get Money Saved leaderboard from Redis."""
    redis = get_redis()
    
    # Get top 10 from sorted set
    leaderboard_raw = await redis.zrevrange(
        RedisKeys.LEADERBOARD_SAVINGS, 0, 9, withscores=True
    )
    
    # Format leaderboard
    supabase = await get_supabase()
    leaderboard = []
    
    for rank, (user_id, score) in enumerate(leaderboard_raw, 1):
        # Get user info
        user_result = await supabase.table("users").select(
            "first_name, username"
        ).eq("telegram_id", int(user_id)).single().execute()
        
        if user_result.data:
            leaderboard.append({
                "rank": rank,
                "user_id": int(user_id),
                "first_name": user_result.data.get("first_name", "Anonymous"),
                "username": user_result.data.get("username"),
                "total_saved": float(score)
            })
    
    # Get user's rank if provided
    user_rank = None
    user_saved = 0.0
    if user_telegram_id:
        user_rank = await redis.zrevrank(
            RedisKeys.LEADERBOARD_SAVINGS, str(user_telegram_id)
        )
        if user_rank is not None:
            user_rank += 1  # 0-indexed to 1-indexed
            user_saved = await redis.zscore(
                RedisKeys.LEADERBOARD_SAVINGS, str(user_telegram_id)
            ) or 0.0
    
    return {
        "leaderboard": leaderboard,
        "user_rank": user_rank,
        "user_saved": user_saved
    }


@app.get("/api/webapp/faq")
async def get_faq(language_code: str = "en"):
    """Get FAQ entries."""
    supabase = await get_supabase()
    
    result = await supabase.table("faq").select("*").eq(
        "language_code", language_code
    ).eq("is_active", True).order("order_index").execute()
    
    return {"faq": result.data or []}


@app.post("/api/webapp/reviews")
async def submit_review(
    review: ReviewCreateRequest,
    user_telegram_id: int,
    background_tasks: BackgroundTasks
):
    """Submit a product review and trigger cashback."""
    supabase = await get_supabase()
    
    # Get user and order info
    user_result = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    order_result = await supabase.table("orders").select(
        "id, product_id, amount"
    ).eq("id", review.order_id).single().execute()
    
    if not order_result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Create review
    review_data = {
        "user_id": user_result.data["id"],
        "order_id": review.order_id,
        "product_id": order_result.data["product_id"],
        "rating": review.rating,
        "text": review.text
    }
    
    result = await supabase.table("reviews").insert(review_data).execute()
    
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to submit review")
    
    # Trigger cashback via QStash
    background_tasks.add_task(
        publish_to_worker,
        WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
        {
            "review_id": result.data[0]["id"],
            "order_id": review.order_id,
            "user_telegram_id": user_telegram_id,
            "amount": order_result.data["amount"]
        }
    )
    
    return {"ok": True, "review_id": result.data[0]["id"]}


@app.post("/api/webapp/promo/check")
async def check_promo_code(promo: PromoCheckRequest):
    """Validate a promo code."""
    supabase = await get_supabase()
    
    result = await supabase.rpc("check_promo_code", {
        "p_code": promo.code
    }).execute()
    
    if result.data and result.data[0]:
        return result.data[0]
    
    return {
        "is_valid": False,
        "discount_percent": 0,
        "error_message": "Invalid or expired promo code"
    }


# ============================================================
# Payment Webhooks
# ============================================================

@app.post("/api/webhook/payment/aaio")
async def aaio_payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """AAIO payment webhook handler."""
    from core.payments import verify_aaio_signature
    
    data = await request.form()
    
    if not verify_aaio_signature(dict(data)):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    order_id = data.get("order_id")
    
    # Trigger goods delivery via QStash
    background_tasks.add_task(
        publish_to_worker,
        WorkerEndpoints.DELIVER_GOODS,
        {"order_id": order_id, "provider": "aaio"}
    )
    
    return {"ok": True}


@app.post("/api/webhook/payment/yukassa")
async def yukassa_payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """YooKassa payment webhook handler."""
    from core.payments import verify_yukassa_signature
    
    data = await request.json()
    
    # YooKassa sends notification object
    if data.get("event") == "payment.succeeded":
        payment = data.get("object", {})
        order_id = payment.get("metadata", {}).get("order_id")
        
        if order_id:
            background_tasks.add_task(
                publish_to_worker,
                WorkerEndpoints.DELIVER_GOODS,
                {"order_id": order_id, "provider": "yukassa"}
            )
    
    return {"ok": True}


# ============================================================
# Admin API
# ============================================================

@app.post("/api/admin/broadcast")
async def admin_broadcast(
    broadcast: BroadcastRequest,
    background_tasks: BackgroundTasks
):
    """Send broadcast message to all users."""
    # TODO: Add admin authentication
    
    background_tasks.add_task(
        publish_to_worker,
        WorkerEndpoints.SEND_BROADCAST,
        {
            "message": broadcast.message,
            "parse_mode": broadcast.parse_mode
        }
    )
    
    return {"ok": True, "status": "queued"}


@app.post("/api/admin/ban")
async def admin_ban_user(ban_request: BanUserRequest):
    """Ban a user."""
    # TODO: Add admin authentication
    
    supabase = await get_supabase()
    
    result = await supabase.table("users").update({
        "is_banned": True
    }).eq("telegram_id", ban_request.user_telegram_id).execute()
    
    if result.data:
        # Notify user
        current_bot = get_bot()
        if current_bot:
            try:
                await current_bot.send_message(
                    ban_request.user_telegram_id,
                    "⛔ Your access has been restricted. Contact @admin to appeal."
                )
            except Exception:
                pass
    
    return {"ok": True}


@app.post("/api/admin/stock")
async def admin_add_stock(
    stock: StockAddRequest,
    background_tasks: BackgroundTasks
):
    """Add stock item and notify waitlist."""
    # TODO: Add admin authentication
    
    supabase = await get_supabase()
    
    stock_data = {
        "product_id": stock.product_id,
        "content": stock.content
    }
    if stock.expires_at:
        stock_data["expires_at"] = stock.expires_at
    
    result = await supabase.table("stock_items").insert(stock_data).execute()
    
    if result.data:
        # Notify waitlist
        background_tasks.add_task(
            publish_to_worker,
            WorkerEndpoints.NOTIFY_WAITLIST,
            {"product_id": stock.product_id}
        )
    
    return {"ok": True, "stock_item_id": result.data[0]["id"] if result.data else None}


# ============================================================
# QStash Workers
# ============================================================

@app.post("/api/workers/deliver-goods")
async def worker_deliver_goods(request: Request):
    """Deliver goods after payment confirmation."""
    data = await verify_qstash_request(request)
    
    order_id = data.get("order_id")
    supabase = await get_supabase()
    
    # Get order with stock item
    order_result = await supabase.table("orders").select(
        "*, stock_items(content), products(instructions), users(telegram_id)"
    ).eq("id", order_id).single().execute()
    
    if not order_result.data:
        return {"ok": False, "error": "Order not found"}
    
    order = order_result.data
    stock_item = order.get("stock_items", {})
    product = order.get("products", {})
    user = order.get("users", {})
    
    # Send credentials to user
    current_bot = get_bot()
    if current_bot and user.get("telegram_id"):
        message = f"""✅ <b>Order Delivered!</b>

📦 Order: #{order_id[:8]}

🔐 <b>Your credentials:</b>
<code>{stock_item.get('content', 'N/A')}</code>

📋 <b>Instructions:</b>
{product.get('instructions', 'Follow the standard setup process.')}

⏰ <b>Expires:</b> {order.get('expires_at', 'N/A')}

Questions? Just ask me here!"""
        
        await current_bot.send_message(user["telegram_id"], message)
    
    # Update order status
    await supabase.table("orders").update({
        "status": "delivered",
        "delivered_at": datetime.utcnow().isoformat()
    }).eq("id", order_id).execute()
    
    # Trigger referral calculation
    await publish_to_worker(
        WorkerEndpoints.CALCULATE_REFERRAL,
        {"order_id": order_id}
    )
    
    return {"ok": True}


@app.post("/api/workers/calculate-referral")
async def worker_calculate_referral(request: Request):
    """Calculate and credit referral bonus."""
    data = await verify_qstash_request(request)
    
    order_id = data.get("order_id")
    supabase = await get_supabase()
    
    # Get order and user with referrer
    order_result = await supabase.table("orders").select(
        "amount, users(referrer_id, personal_ref_percent)"
    ).eq("id", order_id).single().execute()
    
    if not order_result.data:
        return {"ok": False}
    
    order = order_result.data
    user = order.get("users", {})
    referrer_id = user.get("referrer_id")
    
    if not referrer_id:
        return {"ok": True, "message": "No referrer"}
    
    # Calculate bonus
    ref_percent = user.get("personal_ref_percent", 20)
    bonus = order["amount"] * (ref_percent / 100)
    
    # Credit referrer balance
    await supabase.rpc("add_to_user_balance", {
        "p_user_id": referrer_id,
        "p_amount": bonus
    }).execute()
    
    # Notify referrer
    referrer_result = await supabase.table("users").select(
        "telegram_id"
    ).eq("id", referrer_id).single().execute()
    
    if referrer_result.data:
        current_bot = get_bot()
        if current_bot:
            await current_bot.send_message(
                referrer_result.data["telegram_id"],
                f"💰 Referral bonus credited: +{bonus:.0f}₽"
            )
    
    return {"ok": True, "bonus": bonus}


@app.post("/api/workers/process-review-cashback")
async def worker_process_review_cashback(request: Request):
    """Process 5% cashback for review."""
    data = await verify_qstash_request(request)
    
    review_id = data.get("review_id")
    user_telegram_id = data.get("user_telegram_id")
    amount = data.get("amount", 0)
    
    cashback = amount * 0.05  # 5% cashback
    
    supabase = await get_supabase()
    
    # Get user ID
    user_result = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if user_result.data:
        # Credit cashback
        await supabase.rpc("add_to_user_balance", {
            "p_user_id": user_result.data["id"],
            "p_amount": cashback
        }).execute()
        
        # Mark review as cashback given
        await supabase.table("reviews").update({
            "cashback_given": True
        }).eq("id", review_id).execute()
        
        # Notify user
        current_bot = get_bot()
        if current_bot:
            await current_bot.send_message(
                user_telegram_id,
                f"🎁 Thanks for your review! +{cashback:.0f}₽ cashback credited!"
            )
    
    return {"ok": True, "cashback": cashback}


@app.post("/api/workers/notify-waitlist")
async def worker_notify_waitlist(request: Request):
    """Notify waitlist users about product availability."""
    data = await verify_qstash_request(request)
    
    product_id = data.get("product_id")
    supabase = await get_supabase()
    
    # Get product info
    product_result = await supabase.table("products").select("name").eq(
        "id", product_id
    ).single().execute()
    
    product_name = product_result.data.get("name", "Product") if product_result.data else "Product"
    
    # Get waitlist entries
    waitlist_result = await supabase.table("waitlist").select(
        "users(telegram_id)"
    ).eq("product_name", product_name).execute()
    
    current_bot = get_bot()
    notified = 0
    
    if waitlist_result.data and current_bot:
        for entry in waitlist_result.data:
            user = entry.get("users", {})
            if user.get("telegram_id"):
                try:
                    await current_bot.send_message(
                        user["telegram_id"],
                        f"🔔 <b>{product_name}</b> is back in stock!\n\nHurry up and grab it!"
                    )
                    notified += 1
                except Exception:
                    pass
    
    # Clear waitlist for this product
    await supabase.table("waitlist").delete().eq("product_name", product_name).execute()
    
    return {"ok": True, "notified": notified}


@app.post("/api/workers/send-broadcast")
async def worker_send_broadcast(request: Request):
    """Send broadcast message to all users."""
    data = await verify_qstash_request(request)
    
    message = data.get("message")
    parse_mode = data.get("parse_mode", "HTML")
    
    supabase = await get_supabase()
    current_bot = get_bot()
    
    if not current_bot:
        return {"ok": False, "error": "Bot not available"}
    
    # Get all active users (excluding do_not_disturb)
    users_result = await supabase.table("users").select("telegram_id").eq(
        "do_not_disturb", False
    ).eq("is_banned", False).execute()
    
    sent = 0
    failed = 0
    
    for user in users_result.data or []:
        try:
            await current_bot.send_message(
                user["telegram_id"],
                message,
                parse_mode=parse_mode
            )
            sent += 1
        except Exception:
            failed += 1
    
    return {"ok": True, "sent": sent, "failed": failed}


# ============================================================
# Cron Jobs (Vercel Hobby: 2 per day max)
# ============================================================

@app.get("/api/crons/daily-maintenance")
async def cron_daily_maintenance():
    """
    Combined daily maintenance job.
    
    Handles:
    - Subscription expiry reminders
    - Wishlist reminders
    - Review requests
    """
    supabase = await get_supabase()
    current_bot = get_bot()
    
    if not current_bot:
        return {"ok": False, "error": "Bot not available"}
    
    results = {"subscriptions": 0, "wishlist": 0, "reviews": 0}
    
    # 1. Subscription expiry reminders (3 days before)
    expiry_date = (datetime.utcnow() + timedelta(days=3)).date().isoformat()
    
    expiring_result = await supabase.table("orders").select(
        "users(telegram_id), products(name)"
    ).eq("status", "delivered").lt("expires_at", expiry_date).execute()
    
    for order in expiring_result.data or []:
        user = order.get("users", {})
        product = order.get("products", {})
        if user.get("telegram_id"):
            try:
                await current_bot.send_message(
                    user["telegram_id"],
                    f"⏰ Your <b>{product.get('name', 'subscription')}</b> expires in 3 days!\n\nRenew now with 10% discount?"
                )
                results["subscriptions"] += 1
            except Exception:
                pass
    
    # 2. Wishlist reminders (items added 3+ days ago, not reminded yet)
    wishlist_result = await supabase.table("wishlist").select(
        "id, product_name, users(telegram_id)"
    ).eq("reminded", False).lt(
        "created_at", (datetime.utcnow() - timedelta(days=3)).isoformat()
    ).limit(50).execute()
    
    for item in wishlist_result.data or []:
        user = item.get("users", {})
        if user.get("telegram_id"):
            try:
                await current_bot.send_message(
                    user["telegram_id"],
                    f"❤️ Still thinking about <b>{item.get('product_name')}</b>?\n\nIt's waiting for you!"
                )
                # Mark as reminded
                await supabase.table("wishlist").update({"reminded": True}).eq("id", item["id"]).execute()
                results["wishlist"] += 1
            except Exception:
                pass
    
    # 3. Review requests (1+ hour after delivery)
    review_cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
    orders_result = await supabase.table("orders").select(
        "id, users(telegram_id)"
    ).eq("status", "delivered").is_("review_requested_at", "null").lt(
        "delivered_at", review_cutoff
    ).limit(50).execute()
    
    for order in orders_result.data or []:
        user = order.get("users", {})
        if user.get("telegram_id"):
            try:
                await current_bot.send_message(
                    user["telegram_id"],
                    "⭐ How was your purchase?\n\nLeave a review and get 5% cashback!"
                )
                # Mark review requested
                await supabase.table("orders").update({
                    "review_requested_at": datetime.utcnow().isoformat()
                }).eq("id", order["id"]).execute()
                results["reviews"] += 1
            except Exception:
                pass
    
    return {"ok": True, "results": results}


@app.get("/api/crons/fulfillment-check")
async def cron_fulfillment_check():
    """
    Check for fulfillment timeouts and trigger refunds.
    
    Also handles re-engagement for inactive users.
    """
    supabase = await get_supabase()
    current_bot = get_bot()
    
    results = {"refunds": 0, "reengagement": 0}
    
    # 1. Fulfillment timeouts (prepaid orders past deadline)
    timeout_result = await supabase.table("orders").select(
        "id, users(telegram_id), amount"
    ).eq("status", "prepaid").lt(
        "fulfillment_deadline", datetime.utcnow().isoformat()
    ).execute()
    
    for order in timeout_result.data or []:
        # Trigger refund
        await publish_to_worker(
            WorkerEndpoints.PROCESS_REFUND,
            {"order_id": order["id"], "reason": "Fulfillment timeout"}
        )
        results["refunds"] += 1
    
    # 2. Re-engagement (inactive 24h, max 1x per 72h)
    inactive_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    reengagement_cutoff = (datetime.utcnow() - timedelta(hours=72)).isoformat()
    
    inactive_result = await supabase.table("users").select(
        "telegram_id"
    ).lt("last_activity_at", inactive_cutoff).or_(
        f"last_reengagement_at.is.null,last_reengagement_at.lt.{reengagement_cutoff}"
    ).eq("do_not_disturb", False).eq("is_banned", False).limit(20).execute()
    
    if current_bot:
        for user in inactive_result.data or []:
            try:
                await current_bot.send_message(
                    user["telegram_id"],
                    "👋 Haven't heard from you in a while!\n\nCheck out our latest deals?"
                )
                # Update last reengagement
                await supabase.table("users").update({
                    "last_reengagement_at": datetime.utcnow().isoformat()
                }).eq("telegram_id", user["telegram_id"]).execute()
                results["reengagement"] += 1
            except Exception:
                pass
    
    return {"ok": True, "results": results}


@app.post("/api/workers/process-refund")
async def worker_process_refund(request: Request):
    """Process order refund."""
    data = await verify_qstash_request(request)
    
    order_id = data.get("order_id")
    reason = data.get("reason", "Requested by user")
    
    supabase = await get_supabase()
    
    # Get order
    order_result = await supabase.table("orders").select(
        "amount, user_id, users(telegram_id)"
    ).eq("id", order_id).single().execute()
    
    if not order_result.data:
        return {"ok": False, "error": "Order not found"}
    
    order = order_result.data
    
    # Credit refund to balance
    await supabase.rpc("add_to_user_balance", {
        "p_user_id": order["user_id"],
        "p_amount": order["amount"]
    }).execute()
    
    # Update order status
    await supabase.table("orders").update({
        "status": "refunded"
    }).eq("id", order_id).execute()
    
    # Notify user
    user = order.get("users", {})
    current_bot = get_bot()
    if current_bot and user.get("telegram_id"):
        await current_bot.send_message(
            user["telegram_id"],
            f"↩️ Refund processed: +{order['amount']:.0f}₽ to your balance.\n\nReason: {reason}"
        )
    
    return {"ok": True, "amount": order["amount"]}


# ============================================================
# Export for Vercel
# ============================================================
# Vercel auto-detects FastAPI app named 'app'
