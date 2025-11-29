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
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from aiogram import types

# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown


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
    allow_origins=["*"],  # Telegram Mini App can come from any origin
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


class BroadcastRequest(BaseModel):
    message: str
    parse_mode: str = "HTML"


class BanUserRequest(BaseModel):
    user_telegram_id: int
    reason: Optional[str] = None


class StockAddRequest(BaseModel):
    product_id: str
    content: str
    expires_at: Optional[str] = None


# ============================================================
# Dependencies
# ============================================================

async def get_supabase_client():
    """Get Supabase client."""
    from core.db import get_supabase
    return await get_supabase()


async def verify_init_data(request: Request) -> dict:
    """
    Verify Telegram Mini App initData.
    
    Returns user data if valid, raises 401 otherwise.
    """
    init_data = request.headers.get("X-Init-Data", "")
    
    if not init_data:
        # Try from query params
        init_data = request.query_params.get("initData", "")
    
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")
    
    # Parse init data
    try:
        params = dict(x.split("=") for x in init_data.split("&"))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid initData format")
    
    # Verify hash
    bot_token = os.environ.get("TELEGRAM_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=500, detail="Bot token not configured")
    
    received_hash = params.pop("hash", "")
    
    # Create data check string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    
    # Calculate secret key
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(received_hash, calculated_hash):
        raise HTTPException(status_code=401, detail="Invalid initData hash")
    
    # Parse user data
    user_data = json.loads(params.get("user", "{}"))
    
    return {
        "user_id": user_data.get("id"),
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name"),
        "language_code": user_data.get("language_code", "en")
    }


async def verify_admin(request: Request, supabase = Depends(get_supabase_client)) -> dict:
    """Verify admin access."""
    user_data = await verify_init_data(request)
    
    # Check admin status
    result = await supabase.table("users").select("is_admin").eq(
        "telegram_id", user_data["user_id"]
    ).single().execute()
    
    if not result.data or not result.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_data


async def verify_qstash(request: Request) -> dict:
    """Verify QStash signature and return body."""
    from core.queue import verify_qstash_request
    return await verify_qstash_request(request)


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "PVNDORA",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# Telegram Webhook
# ============================================================

@app.post("/api/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook handler.
    
    Processes updates via Aiogram dispatcher with BackgroundTasks
    for non-blocking AI responses.
    """
    try:
        from core.bot import get_bot, get_dispatcher
        
        bot = get_bot()
        dp = get_dispatcher()
        
        data = await request.json()
        update = types.Update(**data)
        
        # Process in background for fast response
        background_tasks.add_task(dp.feed_update, bot, update)
        
        return {"ok": True}
    
    except Exception as e:
        # Log error but return success to prevent Telegram retries
        print(f"Webhook error: {e}")
        return {"ok": True}


# ============================================================
# Mini App API
# ============================================================

@app.get("/api/webapp/products/{product_id}")
async def get_product(
    product_id: str,
    user_data: dict = Depends(verify_init_data),
    supabase = Depends(get_supabase_client)
):
    """Get product details with availability and social proof."""
    # Get product
    product = await supabase.table("products").select("*").eq(
        "id", product_id
    ).single().execute()
    
    if not product.data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get stock availability
    stock = await supabase.table("available_stock_with_discounts").select(
        "*"
    ).eq("product_id", product_id).execute()
    
    available_count = len(stock.data) if stock.data else 0
    
    # Get discount from first available item
    discount_percent = 0
    final_price = product.data["price"]
    if stock.data:
        discount_percent = stock.data[0].get("discount_percent", 0)
        final_price = stock.data[0].get("final_price", product.data["price"])
    
    # Get social proof
    reviews = await supabase.table("reviews").select(
        "rating, text, created_at, users(first_name)"
    ).eq("product_id", product_id).order(
        "created_at", desc=True
    ).limit(5).execute()
    
    # Calculate average rating
    ratings = [r["rating"] for r in (reviews.data or [])]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Get sales count
    sales = await supabase.table("orders").select(
        "id", count="exact"
    ).eq("product_id", product_id).eq("status", "delivered").execute()
    
    return {
        "product": {
            **product.data,
            "available_count": available_count,
            "discount_percent": discount_percent,
            "final_price": final_price,
            "can_fulfill_on_demand": product.data.get("fulfillment_time_hours", 0) > 0
        },
        "social_proof": {
            "rating": round(avg_rating, 1),
            "review_count": len(ratings),
            "sales_count": sales.count or 0,
            "recent_reviews": [
                {
                    "rating": r["rating"],
                    "text": r.get("text"),
                    "author": r.get("users", {}).get("first_name", "User"),
                    "date": r["created_at"]
                }
                for r in (reviews.data or [])
            ]
        }
    }


@app.get("/api/webapp/products")
async def list_products(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    supabase = Depends(get_supabase_client)
):
    """List products with filtering."""
    query = supabase.table("products").select("*").eq("status", "active")
    
    if category:
        query = query.eq("type", category)
    
    result = await query.order("created_at", desc=True).range(
        offset, offset + limit - 1
    ).execute()
    
    return {"products": result.data or [], "count": len(result.data or [])}


@app.post("/api/webapp/orders")
async def create_order(
    body: OrderCreateRequest,
    user_data: dict = Depends(verify_init_data),
    supabase = Depends(get_supabase_client)
):
    """Create order via RPC function."""
    result = await supabase.rpc("create_order_with_availability_check", {
        "p_product_id": body.product_id,
        "p_user_telegram_id": user_data["user_id"],
        "p_quantity": body.quantity
    }).execute()
    
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create order")
    
    order = result.data[0] if isinstance(result.data, list) else result.data
    
    return {
        "order_id": order["order_id"],
        "order_type": order["order_type"],
        "amount": order["amount"],
        "status": order["status"]
    }


@app.get("/api/webapp/orders")
async def get_orders(
    limit: int = 20,
    user_data: dict = Depends(verify_init_data),
    supabase = Depends(get_supabase_client)
):
    """Get user's order history."""
    result = await supabase.table("orders").select(
        "id, amount, status, order_type, created_at, expires_at, products(name)"
    ).eq("user_telegram_id", user_data["user_id"]).order(
        "created_at", desc=True
    ).limit(limit).execute()
    
    return {"orders": result.data or []}


@app.get("/api/webapp/leaderboard")
async def get_leaderboard(
    limit: int = 100,
    user_data: dict = Depends(verify_init_data),
    supabase = Depends(get_supabase_client)
):
    """Get Money Saved leaderboard."""
    from core.db import get_redis
    
    redis = get_redis()
    
    # Get from Redis sorted set
    leaders = await redis.zrange(
        "leaderboard:savings",
        0,
        limit - 1,
        withscores=True,
        rev=True
    )
    
    # Get user data for each leader
    leaderboard = []
    for i, (user_id, score) in enumerate(leaders):
        user = await supabase.table("users").select(
            "first_name, username"
        ).eq("telegram_id", int(user_id)).single().execute()
        
        if user.data:
            leaderboard.append({
                "rank": i + 1,
                "user_id": int(user_id),
                "first_name": user.data.get("first_name", "User"),
                "username": user.data.get("username"),
                "total_saved": float(score)
            })
    
    # Get user's rank
    user_rank = await redis.zrevrank(
        "leaderboard:savings",
        str(user_data["user_id"])
    )
    
    user_saved = await redis.zscore(
        "leaderboard:savings",
        str(user_data["user_id"])
    )
    
    return {
        "leaderboard": leaderboard,
        "user_rank": (user_rank + 1) if user_rank is not None else None,
        "user_saved": float(user_saved) if user_saved else 0
    }


@app.get("/api/webapp/faq")
async def get_faq(
    language_code: str = "en",
    supabase = Depends(get_supabase_client)
):
    """Get FAQ list."""
    result = await supabase.table("faq").select("*").eq(
        "language_code", language_code
    ).order("priority").execute()
    
    # Fallback to English if no results
    if not result.data:
        result = await supabase.table("faq").select("*").eq(
            "language_code", "en"
        ).order("priority").execute()
    
    return {"faq": result.data or []}


@app.post("/api/webapp/reviews")
async def submit_review(
    body: ReviewCreateRequest,
    user_data: dict = Depends(verify_init_data),
    supabase = Depends(get_supabase_client)
):
    """Submit product review."""
    # Get user ID
    user = await supabase.table("users").select("id").eq(
        "telegram_id", user_data["user_id"]
    ).single().execute()
    
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get order to verify ownership
    order = await supabase.table("orders").select("product_id, amount").eq(
        "id", body.order_id
    ).eq("user_telegram_id", user_data["user_id"]).single().execute()
    
    if not order.data:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if already reviewed
    existing = await supabase.table("reviews").select("id").eq(
        "order_id", body.order_id
    ).execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="Already reviewed")
    
    # Create review
    review = await supabase.table("reviews").insert({
        "user_id": user.data["id"],
        "order_id": body.order_id,
        "product_id": order.data["product_id"],
        "rating": body.rating,
        "text": body.text
    }).execute()
    
    # Trigger cashback processing
    from core.queue import publish_to_worker, WorkerEndpoints
    
    await publish_to_worker(
        endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
        body={
            "user_telegram_id": user_data["user_id"],
            "order_id": body.order_id,
            "order_amount": order.data["amount"]
        }
    )
    
    return {"success": True, "review_id": review.data[0]["id"]}


@app.post("/api/webapp/promo/check")
async def check_promo_code(
    body: PromoCheckRequest,
    supabase = Depends(get_supabase_client)
):
    """Validate promo code."""
    result = await supabase.table("promo_codes").select("*").eq(
        "code", body.code.upper()
    ).single().execute()
    
    if not result.data:
        return {
            "is_valid": False,
            "error": "Invalid promo code"
        }
    
    promo = result.data
    
    # Check expiration
    if promo.get("expires_at"):
        expires = datetime.fromisoformat(promo["expires_at"].replace("Z", "+00:00"))
        if expires < datetime.now(expires.tzinfo):
            return {
                "is_valid": False,
                "error": "Promo code expired"
            }
    
    # Check usage limit
    if promo.get("usage_limit"):
        if promo.get("usage_count", 0) >= promo["usage_limit"]:
            return {
                "is_valid": False,
                "error": "Promo code limit reached"
            }
    
    return {
        "is_valid": True,
        "code": promo["code"],
        "discount_percent": promo.get("discount_percent", 0),
        "discount_amount": promo.get("discount_amount", 0),
        "min_order_amount": promo.get("min_order_amount", 0)
    }


# ============================================================
# Payment Webhooks
# ============================================================

@app.post("/api/webhook/payment/aaio")
async def aaio_webhook(request: Request):
    """AAIO payment webhook."""
    try:
        from core.payments import verify_aaio_signature
        from core.queue import publish_to_worker, WorkerEndpoints
        
        form = await request.form()
        data = dict(form)
        
        # Verify signature
        if not verify_aaio_signature(data):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Check status
        if data.get("status") != "success":
            return {"ok": True}
        
        order_id = data.get("order_id")
        
        # Publish to delivery worker
        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={
                "order_id": order_id,
                "payment_provider": "aaio",
                "payment_data": data
            },
            deduplication_id=f"deliver_{order_id}"
        )
        
        return {"ok": True}
    
    except Exception as e:
        print(f"AAIO webhook error: {e}")
        return {"ok": True}


@app.post("/api/webhook/payment/yukassa")
async def yukassa_webhook(request: Request):
    """YooKassa payment webhook."""
    try:
        from core.payments import verify_yukassa_signature
        from core.queue import publish_to_worker, WorkerEndpoints
        
        body = await request.body()
        signature = request.headers.get("X-Idempotency-Key", "")
        
        data = json.loads(body)
        
        # Check event type
        if data.get("event") != "payment.succeeded":
            return {"ok": True}
        
        payment = data.get("object", {})
        order_id = payment.get("metadata", {}).get("order_id")
        
        if not order_id:
            return {"ok": True}
        
        # Publish to delivery worker
        await publish_to_worker(
            endpoint=WorkerEndpoints.DELIVER_GOODS,
            body={
                "order_id": order_id,
                "payment_provider": "yukassa",
                "payment_data": payment
            },
            deduplication_id=f"deliver_{order_id}"
        )
        
        return {"ok": True}
    
    except Exception as e:
        print(f"YooKassa webhook error: {e}")
        return {"ok": True}


# ============================================================
# Admin API
# ============================================================

@app.post("/api/admin/broadcast")
async def admin_broadcast(
    body: BroadcastRequest,
    admin_data: dict = Depends(verify_admin),
    supabase = Depends(get_supabase_client)
):
    """Send broadcast message to all users."""
    from core.queue import publish_to_queue, WorkerEndpoints
    
    # Get users (excluding do_not_disturb)
    users = await supabase.table("users").select(
        "telegram_id"
    ).eq("do_not_disturb", False).eq("is_banned", False).execute()
    
    user_ids = [u["telegram_id"] for u in (users.data or [])]
    
    # Queue broadcast
    await publish_to_queue(
        queue_name="broadcast",
        endpoint=WorkerEndpoints.SEND_BROADCAST,
        body={
            "user_ids": user_ids,
            "message": body.message,
            "parse_mode": body.parse_mode
        }
    )
    
    return {"success": True, "total_users": len(user_ids)}


@app.post("/api/admin/ban-user")
async def admin_ban_user(
    body: BanUserRequest,
    admin_data: dict = Depends(verify_admin),
    supabase = Depends(get_supabase_client)
):
    """Ban a user."""
    await supabase.table("users").update({
        "is_banned": True
    }).eq("telegram_id", body.user_telegram_id).execute()
    
    return {"success": True}


@app.post("/api/admin/add-stock")
async def admin_add_stock(
    body: StockAddRequest,
    admin_data: dict = Depends(verify_admin),
    supabase = Depends(get_supabase_client)
):
    """Add stock item (supplier function)."""
    # Get product
    product = await supabase.table("products").select(
        "supplier_id"
    ).eq("id", body.product_id).single().execute()
    
    if not product.data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Add stock item
    result = await supabase.table("stock_items").insert({
        "product_id": body.product_id,
        "supplier_id": product.data["supplier_id"],
        "content": body.content,
        "status": "available",
        "expires_at": body.expires_at
    }).execute()
    
    # Notify waitlist
    from core.queue import publish_to_worker, WorkerEndpoints
    
    await publish_to_worker(
        endpoint=WorkerEndpoints.NOTIFY_WAITLIST,
        body={"product_id": body.product_id}
    )
    
    return {"success": True, "stock_item_id": result.data[0]["id"]}


# ============================================================
# QStash Workers (continued in next file section)
# ============================================================

@app.post("/api/workers/deliver-goods")
async def worker_deliver_goods(request: Request):
    """Deliver purchased goods to user."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    
    order_id = data.get("order_id")
    
    supabase = await get_supabase()
    bot = get_bot()
    
    # Get order with stock item
    order = await supabase.table("orders").select(
        "*, stock_items(content, expires_at), products(name, instructions)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    order_data = order.data
    stock_item = order_data.get("stock_items", {})
    product = order_data.get("products", {})
    
    # Complete purchase via RPC
    await supabase.rpc("complete_purchase", {
        "p_order_id": order_id
    }).execute()
    
    # Send to user
    content = stock_item.get("content", "")
    instructions = product.get("instructions", "")
    product_name = product.get("name", "Product")
    
    message = (
        f"🎉 <b>Your {product_name} is ready!</b>\n\n"
        f"<code>{content}</code>\n\n"
    )
    
    if instructions:
        message += f"📝 <b>Instructions:</b>\n{instructions}\n\n"
    
    expires_at = stock_item.get("expires_at")
    if expires_at:
        message += f"⏰ Expires: {expires_at}\n\n"
    
    message += "Thank you for your purchase! Leave a review for 5% cashback 💰"
    
    try:
        await bot.send_message(
            chat_id=order_data["user_telegram_id"],
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to send delivery message: {e}")
    
    # Update leaderboard
    from core.queue import publish_to_worker, WorkerEndpoints
    
    await publish_to_worker(
        endpoint=WorkerEndpoints.UPDATE_LEADERBOARD,
        body={
            "user_telegram_id": order_data["user_telegram_id"],
            "order_id": order_id
        }
    )
    
    return {"success": True}


@app.post("/api/workers/notify-supplier")
async def worker_notify_supplier(request: Request):
    """Notify supplier of a sale."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    order_id = data.get("order_id")
    
    # Get order with supplier info
    order = await supabase.table("orders").select(
        "*, products(name, suppliers(telegram_id, name))"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    supplier = order.data.get("products", {}).get("suppliers", {})
    product_name = order.data.get("products", {}).get("name", "Product")
    
    if supplier.get("telegram_id"):
        try:
            await bot.send_message(
                chat_id=supplier["telegram_id"],
                text=(
                    f"💰 <b>New Sale!</b>\n\n"
                    f"Product: {product_name}\n"
                    f"Amount: {order.data['amount']}₽\n"
                    f"Order ID: {order_id[:8]}..."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to notify supplier: {e}")
    
    return {"success": True}


@app.post("/api/workers/notify-supplier-prepaid")
async def worker_notify_supplier_prepaid(request: Request):
    """Notify supplier of prepaid order needing fulfillment."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    supabase = await get_supabase()
    bot = get_bot()
    
    order_id = data.get("order_id")
    
    # Get order details
    order = await supabase.table("orders").select(
        "*, products(name, fulfillment_time_hours, suppliers(telegram_id))"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    product = order.data.get("products", {})
    supplier = product.get("suppliers", {})
    deadline = order.data.get("fulfillment_deadline")
    
    if supplier.get("telegram_id"):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📦 Fulfill Order",
                callback_data=f"fulfill:{order_id}"
            )]
        ])
        
        try:
            await bot.send_message(
                chat_id=supplier["telegram_id"],
                text=(
                    f"⚡ <b>Prepaid Order - Action Required!</b>\n\n"
                    f"Product: {product.get('name', 'Product')}\n"
                    f"Order ID: {order_id[:8]}...\n"
                    f"Deadline: {deadline}\n\n"
                    f"Please fulfill this order before the deadline."
                ),
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Failed to notify supplier: {e}")
    
    return {"success": True}


@app.post("/api/workers/notify-waitlist")
async def worker_notify_waitlist(request: Request):
    """Notify waitlist users that product is available."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    supabase = await get_supabase()
    bot = get_bot()
    
    product_id = data.get("product_id")
    
    # Get product and waitlist
    product = await supabase.table("products").select("name").eq(
        "id", product_id
    ).single().execute()
    
    waitlist = await supabase.table("waitlist").select(
        "user_id, users(telegram_id)"
    ).eq("product_id", product_id).execute()
    
    if not product.data or not waitlist.data:
        return {"success": True}
    
    product_name = product.data["name"]
    bot_info = await bot.me()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🛒 Buy {product_name}",
            url=f"https://t.me/{bot_info.username}?start=product_{product_id}"
        )]
    ])
    
    for item in waitlist.data:
        user = item.get("users", {})
        if user.get("telegram_id"):
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=(
                        f"🎉 <b>Good news!</b>\n\n"
                        f"{product_name} is now available!\n"
                        f"Get it before it sells out again."
                    ),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                pass
    
    # Clear waitlist for this product
    await supabase.table("waitlist").delete().eq(
        "product_id", product_id
    ).execute()
    
    return {"success": True}


@app.post("/api/workers/calculate-referral")
async def worker_calculate_referral(request: Request):
    """Calculate and credit referral bonus."""
    data = await verify_qstash(request)
    
    from core.db import get_supabase
    
    supabase = await get_supabase()
    
    order_id = data.get("order_id")
    
    # Get order with user's referrer
    order = await supabase.table("orders").select(
        "amount, user_telegram_id, users(referrer_telegram_id)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    user = order.data.get("users", {})
    referrer_id = user.get("referrer_telegram_id")
    
    if not referrer_id:
        return {"success": True, "message": "No referrer"}
    
    # Get referrer's bonus percentage
    referrer = await supabase.table("users").select(
        "id, balance, personal_ref_percent"
    ).eq("telegram_id", referrer_id).single().execute()
    
    if not referrer.data:
        return {"success": True, "message": "Referrer not found"}
    
    # Calculate bonus
    bonus_percent = referrer.data.get("personal_ref_percent", 20)
    bonus_amount = order.data["amount"] * (bonus_percent / 100)
    
    # Credit to referrer's balance
    new_balance = referrer.data["balance"] + bonus_amount
    
    await supabase.table("users").update({
        "balance": new_balance
    }).eq("id", referrer.data["id"]).execute()
    
    return {
        "success": True,
        "referrer_id": referrer_id,
        "bonus_amount": bonus_amount
    }


@app.post("/api/workers/update-leaderboard")
async def worker_update_leaderboard(request: Request):
    """Update Money Saved leaderboard."""
    data = await verify_qstash(request)
    
    from core.db import get_supabase, get_redis
    
    supabase = await get_supabase()
    redis = get_redis()
    
    user_telegram_id = data.get("user_telegram_id")
    order_id = data.get("order_id")
    
    # Get order with product MSRP
    order = await supabase.table("orders").select(
        "amount, products(msrp, price)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        return {"error": "Order not found"}
    
    product = order.data.get("products", {})
    msrp = product.get("msrp") or product.get("price", 0)
    paid = order.data["amount"]
    
    savings = msrp - paid
    
    if savings > 0:
        # Update Redis sorted set
        await redis.zincrby(
            "leaderboard:savings",
            savings,
            str(user_telegram_id)
        )
        
        # Update user's total_saved
        await supabase.table("users").update({
            "total_saved": supabase.rpc("increment_saved", {"amount": savings})
        }).eq("telegram_id", user_telegram_id).execute()
    
    return {"success": True, "savings": savings}


@app.post("/api/workers/process-refund")
async def worker_process_refund(request: Request):
    """Process order refund."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment timeout")
    
    # Process refund via RPC
    result = await supabase.rpc("process_refund", {
        "p_order_id": order_id,
        "p_reason": reason
    }).execute()
    
    if not result.data:
        return {"error": "Refund failed"}
    
    refund_data = result.data[0] if isinstance(result.data, list) else result.data
    
    # Get order for notification
    order = await supabase.table("orders").select(
        "user_telegram_id, products(name)"
    ).eq("id", order_id).single().execute()
    
    if order.data:
        product_name = order.data.get("products", {}).get("name", "Product")
        
        try:
            await bot.send_message(
                chat_id=order.data["user_telegram_id"],
                text=(
                    f"↩️ <b>Refund Processed</b>\n\n"
                    f"Order for {product_name} has been refunded.\n"
                    f"Amount: {refund_data.get('refund_amount', 0)}₽\n"
                    f"Reason: {reason}\n\n"
                    f"The amount has been credited to your balance."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    return {"success": True, "refund_amount": refund_data.get("refund_amount")}


@app.post("/api/workers/process-review-cashback")
async def worker_process_review_cashback(request: Request):
    """Process 5% cashback for review."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    user_telegram_id = data.get("user_telegram_id")
    order_amount = data.get("order_amount", 0)
    
    # Calculate 5% cashback
    cashback = order_amount * 0.05
    
    # Credit to user's balance
    await supabase.table("users").update({
        "balance": supabase.rpc("increment_balance", {"amount": cashback})
    }).eq("telegram_id", user_telegram_id).execute()
    
    # Mark review as cashback paid
    if data.get("review_id"):
        await supabase.table("reviews").update({
            "cashback_paid": True
        }).eq("id", data["review_id"]).execute()
    
    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=(
                f"💰 <b>Cashback Credited!</b>\n\n"
                f"Thank you for your review!\n"
                f"{cashback:.0f}₽ has been added to your balance."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    return {"success": True, "cashback": cashback}


@app.post("/api/workers/send-broadcast")
async def worker_send_broadcast(request: Request):
    """Send broadcast messages in batches."""
    data = await verify_qstash(request)
    
    from core.bot import get_bot
    
    bot = get_bot()
    
    user_ids = data.get("user_ids", [])
    message = data.get("message", "")
    parse_mode = data.get("parse_mode", "HTML")
    
    sent = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode
            )
            sent += 1
        except Exception:
            failed += 1
    
    return {"sent": sent, "failed": failed}


# ============================================================
# Cron Jobs
# ============================================================

@app.post("/api/crons/check-expired-subs")
async def cron_check_expired_subs(request: Request):
    """Check for expiring subscriptions and send reminders."""
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    # Get orders expiring in 3 days
    three_days = (datetime.utcnow() + timedelta(days=3)).isoformat()
    today = datetime.utcnow().isoformat()
    
    expiring = await supabase.table("orders").select(
        "id, user_telegram_id, expires_at, products(name, id)"
    ).eq("status", "delivered").gte(
        "expires_at", today
    ).lte("expires_at", three_days).execute()
    
    bot_info = await bot.me()
    
    for order in (expiring.data or []):
        product = order.get("products", {})
        product_id = product.get("id")
        product_name = product.get("name", "Subscription")
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Renew Now",
                url=f"https://t.me/{bot_info.username}?start=product_{product_id}"
            )]
        ])
        
        try:
            await bot.send_message(
                chat_id=order["user_telegram_id"],
                text=(
                    f"⏰ <b>Subscription Expiring Soon!</b>\n\n"
                    f"Your {product_name} expires on {order['expires_at'][:10]}.\n"
                    f"Renew now to keep access!"
                ),
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            pass
    
    return {"checked": len(expiring.data or [])}


@app.post("/api/crons/check-inactive-users")
async def cron_check_inactive_users(request: Request):
    """Send re-engagement messages to inactive users."""
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    # Users inactive for 24+ hours, not messaged in 72 hours
    inactive_since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    last_reengagement = (datetime.utcnow() - timedelta(hours=72)).isoformat()
    
    inactive = await supabase.table("users").select(
        "telegram_id, first_name"
    ).lt("last_activity_at", inactive_since).or_(
        f"last_reengagement_at.is.null,last_reengagement_at.lt.{last_reengagement}"
    ).eq("do_not_disturb", False).eq("is_banned", False).limit(100).execute()
    
    for user in (inactive.data or []):
        try:
            await bot.send_message(
                chat_id=user["telegram_id"],
                text=(
                    f"👋 Hey {user.get('first_name', 'there')}!\n\n"
                    f"We miss you! Check out our latest deals and new products.\n"
                    f"Just say hi and I'll show you what's new! 🎁"
                ),
                parse_mode="HTML"
            )
            
            # Update last_reengagement_at
            await supabase.table("users").update({
                "last_reengagement_at": datetime.utcnow().isoformat()
            }).eq("telegram_id", user["telegram_id"]).execute()
            
        except Exception:
            pass
    
    return {"messaged": len(inactive.data or [])}


@app.post("/api/crons/check-fulfillment-timeout")
async def cron_check_fulfillment_timeout(request: Request):
    """Check for timed out prepaid orders and process refunds."""
    from core.db import get_supabase
    from core.queue import publish_to_worker, WorkerEndpoints
    
    supabase = await get_supabase()
    
    now = datetime.utcnow().isoformat()
    
    # Get timed out prepaid orders
    timed_out = await supabase.table("orders").select(
        "id"
    ).eq("status", "prepaid").lt("fulfillment_deadline", now).execute()
    
    for order in (timed_out.data or []):
        await publish_to_worker(
            endpoint=WorkerEndpoints.PROCESS_REFUND,
            body={
                "order_id": order["id"],
                "reason": "Fulfillment timeout - supplier did not deliver in time"
            },
            deduplication_id=f"refund_{order['id']}"
        )
    
    return {"timed_out": len(timed_out.data or [])}


@app.post("/api/crons/check-wishlist-reminders")
async def cron_check_wishlist_reminders(request: Request):
    """Send reminders for wishlist items after 3 days."""
    from core.bot import get_bot
    from core.db import get_supabase
    
    supabase = await get_supabase()
    bot = get_bot()
    
    three_days_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()
    
    # Get wishlist items added 3+ days ago, not reminded yet
    wishlist = await supabase.table("wishlist").select(
        "id, product_name, product_id, users(telegram_id, first_name)"
    ).lt("created_at", three_days_ago).is_("reminded_at", None).limit(100).execute()
    
    bot_info = await bot.me()
    
    for item in (wishlist.data or []):
        user = item.get("users", {})
        
        if user.get("telegram_id"):
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🛒 Buy {item['product_name']}",
                    url=f"https://t.me/{bot_info.username}?start=product_{item['product_id']}"
                )]
            ])
            
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=(
                        f"❤️ <b>Wishlist Reminder</b>\n\n"
                        f"You saved {item['product_name']} to your wishlist.\n"
                        f"Still interested? It might sell out soon!"
                    ),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
                # Mark as reminded
                await supabase.table("wishlist").update({
                    "reminded_at": datetime.utcnow().isoformat()
                }).eq("id", item["id"]).execute()
                
            except Exception:
                pass
    
    return {"reminded": len(wishlist.data or [])}


@app.post("/api/crons/request-reviews")
async def cron_request_reviews(request: Request):
    """Request reviews 1 hour after purchase."""
    from core.bot import get_bot
    from core.db import get_supabase
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    supabase = await get_supabase()
    bot = get_bot()
    
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    
    # Get delivered orders from 1-2 hours ago, not yet requested
    orders = await supabase.table("orders").select(
        "id, user_telegram_id, products(name)"
    ).eq("status", "delivered").gte(
        "updated_at", two_hours_ago
    ).lte("updated_at", one_hour_ago).is_(
        "review_requested_at", None
    ).limit(100).execute()
    
    for order in (orders.data or []):
        product_name = order.get("products", {}).get("name", "Product")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⭐ Leave Review (5% cashback)",
                callback_data=f"review:{order['id']}"
            )]
        ])
        
        try:
            await bot.send_message(
                chat_id=order["user_telegram_id"],
                text=(
                    f"⭐ <b>How was your purchase?</b>\n\n"
                    f"We'd love to hear about your experience with {product_name}!\n"
                    f"Leave a review and get <b>5% cashback</b> 💰"
                ),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            # Mark as requested
            await supabase.table("orders").update({
                "review_requested_at": datetime.utcnow().isoformat()
            }).eq("id", order["id"]).execute()
            
        except Exception:
            pass
    
    return {"requested": len(orders.data or [])}


@app.post("/api/crons/send-personalized-offers")
async def cron_send_personalized_offers(request: Request):
    """Send personalized offers based on user interests."""
    from core.bot import get_bot
    from core.db import get_supabase
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    supabase = await get_supabase()
    bot = get_bot()
    
    # Get users with viewed but not purchased products
    # This is a simplified version - production would use more sophisticated logic
    
    # Get recent views without purchases
    views = await supabase.table("analytics_events").select(
        "user_id, metadata, users(telegram_id, first_name)"
    ).eq("event_type", "view").order(
        "timestamp", desc=True
    ).limit(100).execute()
    
    # Group by user and find products they viewed but didn't buy
    user_interests = {}
    for view in (views.data or []):
        user = view.get("users", {})
        if not user.get("telegram_id"):
            continue
        
        product_id = view.get("metadata", {}).get("product_id")
        if product_id:
            if user["telegram_id"] not in user_interests:
                user_interests[user["telegram_id"]] = {
                    "first_name": user.get("first_name", "there"),
                    "products": set()
                }
            user_interests[user["telegram_id"]]["products"].add(product_id)
    
    bot_info = await bot.me()
    sent = 0
    
    for user_id, data in user_interests.items():
        # Get one product to suggest
        product_ids = list(data["products"])[:1]
        if not product_ids:
            continue
        
        product = await supabase.table("products").select(
            "id, name, price"
        ).eq("id", product_ids[0]).single().execute()
        
        if not product.data:
            continue
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🛒 Get {product.data['name']}",
                url=f"https://t.me/{bot_info.username}?start=product_{product.data['id']}"
            )]
        ])
        
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"👋 Hey {data['first_name']}!\n\n"
                    f"Still thinking about {product.data['name']}?\n"
                    f"Price: {product.data['price']:.0f}₽\n\n"
                    f"Don't miss out!"
                ),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            sent += 1
        except Exception:
            pass
    
    return {"sent": sent}
