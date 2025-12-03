"""
PVNDORA AI Marketplace - Main FastAPI Application

Single entry point for all webhooks and API routes.
Optimized for Vercel Hobby plan (max 12 serverless functions).
"""
import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Add src to path for imports
# Try multiple paths for Vercel compatibility
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path))
# Also try absolute path
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

try:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    # Import bot components
    from src.bot.handlers import router as bot_router
    from src.bot.middlewares import (
        AuthMiddleware,
        LanguageMiddleware, 
        ActivityMiddleware,
        AnalyticsMiddleware
    )
    from src.services.database import get_database
    from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data
except ImportError as e:
    import traceback
    print(f"ERROR: Failed to import modules: {e}")
    print(f"ERROR: sys.path = {sys.path}")
    print(f"ERROR: Traceback: {traceback.format_exc()}")
    raise

# Lazy-loaded singletons for reducing cold start
try:
    from core.routers.deps import (
        get_notification_service,
        get_payment_service,
        get_queue_publisher,
        verify_qstash
    )
    
    # Unified authentication
    from core.auth import verify_telegram_auth, verify_admin, verify_cron_secret
except ImportError as e:
    import traceback
    print(f"ERROR: Failed to import core modules: {e}")
    print(f"ERROR: sys.path = {sys.path}")
    print(f"ERROR: Traceback: {traceback.format_exc()}")
    raise


# ==================== BOT INITIALIZATION ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


def get_bot() -> Bot:
    """Get or create bot instance"""
    global bot
    if bot is None and TELEGRAM_TOKEN:
        bot = Bot(
            token=TELEGRAM_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return bot


def get_dispatcher() -> Dispatcher:
    """Get or create dispatcher instance"""
    global dp
    if dp is None:
        dp = Dispatcher()
        
        # Register middlewares (order matters!)
        dp.message.middleware(AuthMiddleware())
        dp.message.middleware(LanguageMiddleware())
        dp.message.middleware(ActivityMiddleware())
        dp.message.middleware(AnalyticsMiddleware())
        
        dp.callback_query.middleware(AuthMiddleware())
        dp.callback_query.middleware(LanguageMiddleware())
        dp.callback_query.middleware(ActivityMiddleware())
        
        # Register router
        dp.include_router(bot_router)
    
    return dp


# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    yield
    # Shutdown
    if bot:
        await bot.session.close()


app = FastAPI(
    title="PVNDORA AI Marketplace",
    description="AI-powered digital goods marketplace API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini Apps require this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (endpoints moved from this file for better organization)
from core.routers.admin import router as admin_router
from core.routers.webhooks import router as webhooks_router
from core.routers.workers import router as workers_router
# Note: products_router exists but index.py versions have more features
# (available_stock_with_discounts view, on-demand fulfillment logic)

app.include_router(admin_router, prefix="/api/admin")
app.include_router(webhooks_router)
app.include_router(workers_router)


# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "pvndora"}


@app.get("/api/webhook/test")
async def test_webhook():
    """Test webhook endpoint - verify bot is configured"""
    bot_instance = get_bot()
    dispatcher = get_dispatcher()
    
    return {
        "bot_configured": bot_instance is not None,
        "dispatcher_configured": dispatcher is not None,
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "webhook_url": f"{WEBAPP_URL}/webhook/telegram"
    }


# ==================== TELEGRAM WEBHOOK ====================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Telegram webhook updates"""
    import traceback
    
    # IMPORTANT: Return 200 immediately to avoid 307 redirects
    # Process update in background to avoid timeout
    try:
        # Get bot and dispatcher
        bot_instance = get_bot()
        dispatcher = get_dispatcher()
        
        if not bot_instance:
            print("ERROR: Bot instance is None - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=200,  # Return 200 even on error to prevent Telegram retries
                content={"ok": False, "error": "Bot not configured"}
            )
        
        # Parse update
        try:
            data = await request.json()
            update_id = data.get('update_id', 'unknown')
            print(f"DEBUG: Received update: {update_id}")
        except Exception as e:
            print(f"ERROR: Failed to parse JSON: {e}")
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid JSON: {str(e)}"}
            )
        
        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
            print(f"DEBUG: Update validated, type: {update.event_type if hasattr(update, 'event_type') else 'unknown'}")
        except Exception as e:
            print(f"ERROR: Failed to validate update: {e}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid update: {str(e)}"}
            )
        
        # Process update in background - FastAPI BackgroundTasks are guaranteed to run
        # Return 200 immediately to Telegram
        background_tasks.add_task(
            _process_update_async,
            bot_instance,
            dispatcher,
            update
        )
        
        print(f"DEBUG: Update {update_id} queued for background processing")
        
        # Return 200 OK immediately
        return JSONResponse(content={"ok": True})
    
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Webhook exception: {error_msg}")
        print(f"ERROR: Traceback: {error_trace}")
        # Always return 200 to prevent Telegram from retrying
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": error_msg}
        )


async def _process_update_async(bot_instance: Bot, dispatcher: Dispatcher, update: Update):
    """Process update asynchronously"""
    import traceback
    update_id = update.update_id if hasattr(update, 'update_id') else 'unknown'
    print(f"DEBUG: Starting background processing of update {update_id}")
    try:
        await dispatcher.feed_update(bot_instance, update)
        print(f"DEBUG: Update {update_id} processed successfully")
    except Exception as e:
        print(f"ERROR: Failed to process update {update_id}: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")


# ==================== PRODUCTS API ====================

class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    type: str
    status: str
    stock_count: int
    warranty_hours: int
    rating: float = 0
    reviews_count: int = 0


@app.get("/api/products")
async def get_products():
    """Get all available products"""
    db = get_database()
    products = await db.get_products(status="active")
    
    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)
        result.append(ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            type=p.type,
            status=p.status,
            stock_count=p.stock_count,
            warranty_hours=p.warranty_hours,
            rating=rating_info["average"],
            reviews_count=rating_info["count"]
        ))
    
    return result


@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID"""
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    rating_info = await db.get_product_rating(product_id)
    reviews = await db.get_product_reviews(product_id, limit=5)
    
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "type": product.type,
        "status": product.status,
        "stock_count": product.stock_count,
        "warranty_hours": product.warranty_hours,
        "instructions": product.instructions,
        "terms": product.terms,
        "rating": rating_info["average"],
        "reviews_count": rating_info["count"],
        "reviews": reviews
    }


# ==================== WEBAPP API (Mini App) ====================

@app.get("/api/webapp/products/{product_id}")
async def get_webapp_product(product_id: str):
    """
    Get product with discount and social proof for Mini App.
    Public endpoint - product info is not sensitive.
    """
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get available stock with discounts
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("available_stock_with_discounts").select(
            "*"
        ).eq("product_id", product_id).limit(1).execute()
    )
    
    discount_percent = 0
    if stock_result.data:
        discount_percent = stock_result.data[0].get("discount_percent", 0)
    
    # Get social proof
    rating_info = await db.get_product_rating(product_id)
    
    # Calculate final price
    original_price = float(product.price)
    final_price = original_price * (1 - discount_percent / 100)
    
    # Get fulfillment info for on-demand products
    fulfillment_time_hours = getattr(product, 'fulfillment_time_hours', 48)
    can_fulfill_on_demand = product.status == 'active'
    
    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "original_price": original_price,
            "price": original_price,  # For backward compatibility
            "discount_percent": discount_percent,
            "final_price": round(final_price, 2),
            "warranty_days": product.warranty_hours // 24 if hasattr(product, 'warranty_hours') else 1,
            "duration_days": getattr(product, 'duration_days', None),
            "available_count": product.stock_count,
            "available": product.stock_count > 0,
            "can_fulfill_on_demand": can_fulfill_on_demand,
            "fulfillment_time_hours": fulfillment_time_hours if can_fulfill_on_demand else None,
            "type": product.type,
            "instructions": product.instructions,
            "rating": rating_info["average"],
            "reviews_count": rating_info["count"]
        }
    }


@app.get("/api/webapp/products")
async def get_webapp_products():
    """
    Get all products for Mini App catalog.
    Public endpoint - products are not sensitive data.
    """
    db = get_database()
    products = await db.get_products(status="active")
    
    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)
        
        # Get fulfillment info
        fulfillment_time_hours = getattr(p, 'fulfillment_time_hours', 48)
        
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "type": p.type,
            "status": p.status,
            "stock_count": p.stock_count,
            "available": p.stock_count > 0,
            "can_fulfill_on_demand": p.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours,
            "warranty_days": p.warranty_hours // 24 if hasattr(p, 'warranty_hours') and p.warranty_hours else 1,
            "duration_days": getattr(p, 'duration_days', None),
            "rating": rating_info["average"],
            "reviews_count": rating_info["count"]
        })
    
    return {"products": result, "count": len(result)}


@app.get("/api/webapp/orders")
async def get_webapp_orders(user = Depends(verify_telegram_auth)):
    """
    Get user's order history for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()
    
    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.get_user_orders(db_user.id, limit=50)
    
    result = []
    for o in orders:
        product = await db.get_product_by_id(o.product_id)
        product_name = product.name if product else "Unknown Product"
        
        result.append({
            "id": o.id,
            "product_id": o.product_id,
            "product_name": product_name,
            "amount": o.amount,
            "original_price": o.original_price,
            "discount_percent": o.discount_percent,
            "status": o.status,
            "order_type": getattr(o, 'order_type', 'instant'),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivered_at": o.delivered_at.isoformat() if hasattr(o, 'delivered_at') and o.delivered_at else None,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "warranty_until": o.warranty_until.isoformat() if hasattr(o, 'warranty_until') and o.warranty_until else None
        })
    
    return {"orders": result, "count": len(result)}


@app.get("/api/webapp/leaderboard")
async def get_webapp_leaderboard(
    period: str = "all",
    user = Depends(verify_telegram_auth)
):
    """
    Get savings leaderboard for Mini App.
    Supports period: all, month, week
    """
    db = get_database()
    LEADERBOARD_SIZE = 25
    
    # Calculate date cutoff for period
    now = datetime.now(timezone.utc)
    date_filter = None
    if period == "week":
        date_filter = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        date_filter = (now - timedelta(days=30)).isoformat()
    
    # For period-based, we need to sum from orders
    if date_filter:
        # Get savings from orders in period
        query = db.client.table("orders").select(
            "user_id,amount,original_price,users(telegram_id,username,first_name)"
        ).eq("status", "completed").gte("created_at", date_filter)
        
        orders_result = await asyncio.to_thread(lambda: query.execute())
        
        # Aggregate savings by user
        user_savings = {}
        for order in (orders_result.data or []):
            uid = order.get("user_id")
            if not uid:
                continue
            orig = float(order.get("original_price") or order.get("amount") or 0)
            paid = float(order.get("amount") or 0)
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
        
        # Sort and limit
        sorted_users = sorted(
            user_savings.values(),
            key=lambda x: x["total_saved"],
            reverse=True
        )[:LEADERBOARD_SIZE]
        result_data = sorted_users
    else:
        # All-time: use total_saved from users table
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "telegram_id,username,first_name,total_saved"
            ).gt("total_saved", 0).order(
                "total_saved", desc=True
            ).limit(LEADERBOARD_SIZE).execute()
        )
        result_data = result.data or []
        
        # Fill with recent users if needed
        if len(result_data) < LEADERBOARD_SIZE:
            remaining = LEADERBOARD_SIZE - len(result_data)
            fill_result = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "telegram_id,username,first_name,total_saved"
                ).eq("total_saved", 0).order(
                    "created_at", desc=True
                ).limit(remaining).execute()
            )
            result_data.extend(fill_result.data or [])
    
    # Get total users count
    total_count = await asyncio.to_thread(
        lambda: db.client.table("users").select("id", count="exact").execute()
    )
    total_users = total_count.count or 0
    
    # Count users who improved today (made a purchase today)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "user_id", count="exact"
        ).eq("status", "completed").gte(
            "created_at", today_start.isoformat()
        ).execute()
    )
    improved_today = improved_result.count or 0
    
    # Get current user's stats
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank = None
    user_saved = 0
    
    if db_user:
        user_saved = float(db_user.total_saved) if hasattr(
            db_user, 'total_saved') and db_user.total_saved else 0
        
        if user_saved > 0:
            rank_result = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "id", count="exact"
                ).gt("total_saved", user_saved).execute()
            )
            user_rank = (rank_result.count or 0) + 1
        else:
            total_with_savings = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "id", count="exact"
                ).gt("total_saved", 0).execute()
            )
            user_rank = (total_with_savings.count or 0) + 1
    
    leaderboard = []
    for i, entry in enumerate(result_data):
        tg_id = entry.get("telegram_id")
        display_name = entry.get("username") or entry.get("first_name") or \
            f"User{str(tg_id)[-4:]}" if tg_id else "User"
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"
        
        leaderboard.append({
            "rank": i + 1,
            "name": display_name,
            "total_saved": float(entry.get("total_saved", 0)),
            "is_current_user": tg_id == user.id if tg_id else False
        })
    
    return {
        "leaderboard": leaderboard,
        "user_rank": user_rank,
        "user_saved": user_saved,
        "total_users": total_users,
        "improved_today": improved_today
    }


@app.get("/api/webapp/faq")
async def get_webapp_faq(language_code: str = "en", user = Depends(verify_telegram_auth)):
    """
    Get FAQ entries for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()
    faq_entries = await db.get_faq(language_code)
    
    # Group by category
    categories = {}
    for entry in faq_entries:
        category = entry.get("category", "general")
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "question": entry["question"],
            "answer": entry["answer"]
        })
    
    return {
        "categories": categories,
        "total": len(faq_entries)
    }


# ==================== PROFILE ENDPOINTS ====================

@app.get("/api/webapp/profile")
async def get_webapp_profile(user = Depends(verify_telegram_auth)):
    """Get user profile with referral stats, balance, and history."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get referral stats from view
    stats_result = await asyncio.to_thread(
        lambda: db.client.table("user_referral_stats").select("*").eq(
            "user_id", db_user.id
        ).execute()
    )
    
    referral_stats = None
    if stats_result.data:
        s = stats_result.data[0]
        referral_stats = {
            "level1_count": s.get("level1_count", 0),
            "level2_count": s.get("level2_count", 0),
            "level3_count": s.get("level3_count", 0),
            "level1_earnings": float(s.get("level1_earnings", 0)),
            "level2_earnings": float(s.get("level2_earnings", 0)),
            "level3_earnings": float(s.get("level3_earnings", 0)),
        }
    
    # Get recent bonus history
    bonus_result = await asyncio.to_thread(
        lambda: db.client.table("referral_bonuses").select("*").eq(
            "user_id", db_user.id
        ).order("created_at", desc=True).limit(10).execute()
    )
    
    # Get withdrawal history
    withdrawal_result = await asyncio.to_thread(
        lambda: db.client.table("withdrawal_requests").select("*").eq(
            "user_id", db_user.id
        ).order("created_at", desc=True).limit(10).execute()
    )
    
    return {
        "profile": {
            "balance": float(db_user.balance) if db_user.balance else 0,
            "total_referral_earnings": float(
                db_user.total_referral_earnings
            ) if hasattr(db_user, 'total_referral_earnings') and \
                db_user.total_referral_earnings else 0,
            "total_saved": float(db_user.total_saved) if db_user.total_saved else 0,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None
        },
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or []
    }


class WithdrawalRequest(BaseModel):
    amount: float
    method: str  # card, phone, crypto
    details: str


@app.post("/api/webapp/profile/withdraw")
async def request_withdrawal(
    request: WithdrawalRequest,
    user = Depends(verify_telegram_auth)
):
    """Request balance withdrawal."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    MIN_WITHDRAWAL = 500
    balance = float(db_user.balance) if db_user.balance else 0
    
    if request.amount < MIN_WITHDRAWAL:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum withdrawal is {MIN_WITHDRAWAL}₽"
        )
    
    if request.amount > balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    if request.method not in ['card', 'phone', 'crypto']:
        raise HTTPException(status_code=400, detail="Invalid payment method")
    
    # Create withdrawal request
    await asyncio.to_thread(
        lambda: db.client.table("withdrawal_requests").insert({
            "user_id": db_user.id,
            "amount": request.amount,
            "payment_method": request.method,
            "payment_details": {"details": request.details}
        }).execute()
    )
    
    # Deduct from balance (hold)
    new_balance = balance - request.amount
    await asyncio.to_thread(
        lambda: db.client.table("users").update({
            "balance": new_balance
        }).eq("id", db_user.id).execute()
    )
    
    return {"success": True, "message": "Withdrawal request submitted"}


@app.get("/api/webapp/cart")
async def get_webapp_cart(user = Depends(verify_telegram_auth)):
    """
    Get user's shopping cart for Mini App.
    Requires Telegram initData authentication.
    """
    from core.cart import get_cart_manager
    
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        if not cart:
            return {
                "cart": None,
                "items": [],
                "total": 0.0,
                "subtotal": 0.0,
                "instant_total": 0.0,
                "prepaid_total": 0.0,
                "promo_code": None,
                "promo_discount_percent": 0.0
            }
        
        # Get product details for each item
        db = get_database()
        items_with_details = []
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            items_with_details.append({
                "product_id": item.product_id,
                "product_name": product.name if product else "Unknown Product",
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "unit_price": item.unit_price,
                "final_price": item.final_price,
                "total_price": item.total_price,
                "discount_percent": item.discount_percent
            })
        
        return {
            "cart": {
                "user_telegram_id": cart.user_telegram_id,
                "created_at": cart.created_at,
                "updated_at": cart.updated_at
            },
            "items": items_with_details,
            "total": cart.total,
            "subtotal": cart.subtotal,
            "instant_total": cart.instant_total,
            "prepaid_total": cart.prepaid_total,
            "promo_code": cart.promo_code,
            "promo_discount_percent": cart.promo_discount_percent
        }
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")


class PromoCheckRequest(BaseModel):
    code: str


@app.post("/api/webapp/promo/check")
async def check_webapp_promo(request: PromoCheckRequest, user = Depends(verify_telegram_auth)):
    """
    Check if promo code is valid for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()
    
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)
    
    if promo:
        return {
            "valid": True,
            "code": code,
            "discount_percent": promo["discount_percent"],
            "expires_at": promo.get("expires_at"),
            "usage_remaining": (promo.get("usage_limit") or 999) - (promo.get("usage_count") or 0)
        }
    
    return {
        "valid": False,
        "code": code,
        "message": "Invalid or expired promo code"
    }


class WebAppReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: Optional[str] = None


@app.post("/api/webapp/reviews")
async def submit_webapp_review(request: WebAppReviewRequest, user = Depends(verify_telegram_auth)):
    """
    Submit a product review from Mini App.
    Awards 5% cashback for first review on an order.
    """
    db = get_database()
    
    # Validate rating
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Get user
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get order and verify ownership
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order belongs to user
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    
    # Check if order is completed
    if order.status not in ["completed", "delivered"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")
    
    # Check if already reviewed
    existing_review = await asyncio.to_thread(
        lambda: db.client.table("reviews").select("id").eq(
            "order_id", request.order_id
        ).execute()
    )
    
    if existing_review.data:
        raise HTTPException(status_code=400, detail="Order already reviewed")
    
    # Create review
    review_data = {
        "user_id": db_user.id,
        "order_id": request.order_id,
        "product_id": order.product_id,
        "rating": request.rating,
        "text": request.text,
        "cashback_given": False
    }
    
    result = await asyncio.to_thread(
        lambda: db.client.table("reviews").insert(review_data).execute()
    )
    
    # Calculate and award 5% cashback
    cashback_amount = float(order.amount) * 0.05
    
    await asyncio.to_thread(
        lambda: db.client.table("users").update({
            "balance": db_user.balance + cashback_amount
        }).eq("id", db_user.id).execute()
    )
    
    # Mark cashback as given
    await asyncio.to_thread(
        lambda: db.client.table("reviews").update({
            "cashback_given": True
        }).eq("id", result.data[0]["id"]).execute()
    )
    
    return {
        "success": True,
        "review_id": result.data[0]["id"],
        "cashback_awarded": round(cashback_amount, 2),
        "new_balance": round(float(db_user.balance) + cashback_amount, 2)
    }


# ==================== ORDERS API ====================

class CreateOrderRequest(BaseModel):
    product_id: Optional[str] = None
    quantity: Optional[int] = 1
    promo_code: Optional[str] = None
    # For cart-based orders
    use_cart: Optional[bool] = False


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


@app.post("/api/webapp/orders")
async def create_webapp_order(
    request: CreateOrderRequest,
    user = Depends(verify_telegram_auth)
):
    """
    Create new order from Mini App.
    Supports both single product and cart-based orders.
    """
    db = get_database()
    
    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine payment method based on language
    # Priority: cardlink (if configured) > aaio > stripe
    cardlink_configured = bool(os.environ.get("CARDLINK_API_TOKEN") and os.environ.get("CARDLINK_SHOP_ID"))
    if cardlink_configured and db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "cardlink"
    elif db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "aaio"
    else:
        payment_method = "stripe"
    
    payment_service = get_payment_service()
    
    # Cart-based order
    if request.use_cart or (not request.product_id):
        from core.cart import get_cart_manager
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        # Validate all products in cart
        total_amount = 0.0
        total_original = 0.0
        order_items = []
        
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            
            # Check stock for instant items
            if item.instant_quantity > 0:
                available_stock = await db.get_available_stock_count(item.product_id)
                if available_stock < item.instant_quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock for {product.name}. Available: {available_stock}, Requested: {item.instant_quantity}"
                    )
            
            # Calculate price with discount
            original_price = product.price * item.quantity
            discount_percent = item.discount_percent
            
            # Apply promo code if present
            if cart.promo_code and cart.promo_discount_percent > 0:
                discount_percent = max(discount_percent, cart.promo_discount_percent)
            
            final_price = original_price * (1 - discount_percent / 100)
            
            total_amount += final_price
            total_original += original_price
            
            order_items.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price,
                "original_price": original_price,
                "discount_percent": discount_percent
            })
        
        # Create order for first item (or create a combined order)
        # For now, create order for first item and include others in metadata
        first_item = order_items[0]
        
        order = await db.create_order(
            user_id=db_user.id,
            product_id=first_item["product_id"],
            amount=total_amount,
            original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_method=payment_method
        )
        
        # Store additional items in order metadata (if supported)
        # For now, we'll create separate orders for each item
        # TODO: Implement multi-item order support in database
        
        # Generate payment URL with total amount
        product_names = ", ".join([item["product_name"] for item in order_items[:3]])
        if len(order_items) > 3:
            product_names += f" и еще {len(order_items) - 3}"
        
        payment_url = await payment_service.create_payment(
            order_id=order.id,
            amount=total_amount,
            product_name=product_names,
            method=payment_method,
            user_email=f"{user.id}@telegram.user"
        )
        
        # Use promo code if valid
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        
        # Clear cart after successful order creation
        await cart_manager.clear_cart(user.id)
        
        return OrderResponse(
            order_id=order.id,
            amount=total_amount,
            original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_url=payment_url,
            payment_method=payment_method
        )
    
    # Single product order
    else:
        if not request.product_id:
            raise HTTPException(status_code=400, detail="product_id is required for single product orders")
        
        # Get product
        product = await db.get_product_by_id(request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        quantity = request.quantity or 1
        
        # Check stock
        available_stock = await db.get_available_stock_count(request.product_id)
        if available_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock. Available: {available_stock}, Requested: {quantity}"
            )
        
        # Calculate price with potential discount
        original_price = product.price * quantity
        discount_percent = 0
        
        # Check for stock item discount (age-based)
        stock_item = await db.get_available_stock_item(request.product_id)
        if stock_item:
            discount_percent = await db.calculate_discount(stock_item, product)
        
        # Check promo code
        if request.promo_code:
            promo = await db.validate_promo_code(request.promo_code)
            if promo:
                # Use higher discount
                discount_percent = max(discount_percent, promo["discount_percent"])
        
        # Calculate final price
        final_price = original_price * (1 - discount_percent / 100)
        
        # Create order
        order = await db.create_order(
            user_id=db_user.id,
            product_id=request.product_id,
            amount=final_price,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_method=payment_method
        )
        
        # Generate payment URL
        payment_url = await payment_service.create_payment(
            order_id=order.id,
            amount=final_price,
            product_name=product.name,
            method=payment_method,
            user_email=f"{user.id}@telegram.user"  # Placeholder
        )
        
        # Use promo code if valid
        if request.promo_code:
            await db.use_promo_code(request.promo_code)
        
        return OrderResponse(
            order_id=order.id,
            amount=final_price,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_url=payment_url,
            payment_method=payment_method
        )


@app.post("/api/orders")
async def create_order(
    request: CreateOrderRequest,
    user = Depends(verify_telegram_auth)
):
    """Create new order and get payment URL (legacy endpoint, redirects to webapp)"""
    return await create_webapp_order(request, user)


@app.get("/api/orders")
async def get_user_orders(user = Depends(verify_telegram_auth)):
    """Get user's orders"""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.get_user_orders(db_user.id)
    return orders


# Payment webhooks moved to core/routers/webhooks.py

# ==================== USER API ====================

@app.get("/api/user/profile")
async def get_user_profile(user = Depends(verify_telegram_auth)):
    """Get user profile"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": db_user.id,
        "telegram_id": db_user.telegram_id,
        "username": db_user.username,
        "first_name": db_user.first_name,
        "balance": db_user.balance,
        "language_code": db_user.language_code,
        "referral_percent": db_user.personal_ref_percent,
        "is_admin": db_user.is_admin or False
    }


@app.get("/api/user/referral")
async def get_referral_info(user = Depends(verify_telegram_auth)):
    """Get referral link and stats"""
    bot_instance = get_bot()
    
    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")
    
    bot_info = await bot_instance.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    return {
        "link": referral_link,
        "percent": db_user.personal_ref_percent if db_user else 20,
        "balance": db_user.balance if db_user else 0
    }


@app.post("/api/webapp/referral/share-link")
async def create_referral_share_link(user = Depends(verify_telegram_auth)):
    """
    Create a prepared inline message for sharing.
    Returns prepared_message_id to be used with Telegram.WebApp.shareMessage()
    """
    from aiogram.types import InlineQueryResultPhoto, InlineKeyboardMarkup, InlineKeyboardButton
    import traceback
    
    bot_instance = get_bot()
    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")
        
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Calculate savings or get from DB
    total_saved = int(float(db_user.total_saved)) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
    display_name = db_user.first_name or db_user.username or "User"
    
    # Calculate leaderboard rank
    user_rank = None
    if total_saved > 0:
        rank_result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "id", count="exact"
            ).gt("total_saved", total_saved).execute()
        )
        user_rank = (rank_result.count or 0) + 1
    
    # Referral link
    bot_info = await bot_instance.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    
    # Dynamic Image URL powered by Vercel OG
    import urllib.parse
    from datetime import timezone
    timestamp = int(datetime.now(timezone.utc).timestamp())
    avatar_url = getattr(user, "photo_url", None)
    if not avatar_url:
        initials_seed = urllib.parse.quote(display_name)
        avatar_url = f"https://api.dicebear.com/7.x/initials/png?seed={initials_seed}&backgroundColor=1f1f2e,4c1d95&fontWeight=700"
    
    query_params = {
        "name": display_name,
        "saved": total_saved,
        "lang": db_user.language_code or "ru",
        "avatar": avatar_url,
        "t": timestamp,
        "handle": f"@{bot_info.username}"
    }
    if user_rank:
        query_params["rank"] = user_rank
    
    query_string = urllib.parse.urlencode(query_params, doseq=False)
    photo_url = f"{WEBAPP_URL}/og/referral?{query_string}"
    
    result_id = f"share_{user.id}_{timestamp}"
    
    # Лаконичный caption от первого лица
    if db_user.language_code == "ru":
        caption_text = "Оплачиваю тарифы нейросетей за 20% от их стоимости"
        button_text = "🎁 Попробовать"
    else:
        caption_text = "Paying for AI subscriptions at 20% of their cost"
        button_text = "🎁 Try it"
    
    # Using InlineQueryResultPhoto for "Major-style" large image
    photo = InlineQueryResultPhoto(
        id=result_id,
        photo_url=photo_url,
        thumbnail_url=photo_url,  # Use same URL for thumb
        title="🎁 PVNDORA AI",
        description=caption_text,
        caption=caption_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=button_text, url=ref_link)
            ]]
        )
    )
    
    try:
        print(f"DEBUG: Attempting to save prepared message for user {user.id}")
        prepared_message = await bot_instance.save_prepared_inline_message(
            user_id=user.id,
            result=photo,
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True
        )
        print(f"DEBUG: Prepared message saved successfully, ID: {prepared_message.id}")
        return {"prepared_message_id": prepared_message.id}
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Failed to save prepared message: {error_msg}")
        print(f"ERROR: Traceback: {error_trace}")
        
        if "object has no attribute 'save_prepared_inline_message'" in error_msg:
             raise HTTPException(status_code=501, detail="Feature not supported by bot backend version")
        
        # Check if it's a Telegram API error
        if "Bad Request" in error_msg or "400" in error_msg:
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_msg}")
        
        raise HTTPException(status_code=500, detail=f"Failed to save prepared message: {error_msg}")


# ==================== FAQ API ====================

@app.get("/api/faq")
async def get_faq(language_code: str = "en"):
    """Get FAQ entries"""
    db = get_database()
    faq = await db.get_faq(language_code)
    return {"faq": faq}


# ==================== WISHLIST API ====================

@app.get("/api/wishlist")
async def get_wishlist(user = Depends(verify_telegram_auth)):
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


@app.post("/api/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user = Depends(verify_telegram_auth)):
    """Add product to wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.add_to_wishlist(db_user.id, product_id)
    return {"success": True}


@app.delete("/api/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user = Depends(verify_telegram_auth)):
    """Remove product from wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.remove_from_wishlist(db_user.id, product_id)
    return {"success": True}


# Admin API moved to core/routers/admin.py

# ==================== REVIEWS API ====================

class SubmitReviewRequest(BaseModel):
    order_id: str
    rating: int  # 1-5
    text: Optional[str] = None


@app.post("/api/reviews")
async def submit_review(
    request: SubmitReviewRequest,
    user = Depends(verify_telegram_auth)
):
    """Submit product review with 5% cashback"""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get order
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Not your order")
    
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="Order not completed")
    
    # Check if review already exists
    existing = db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Review already submitted")
    
    # Create review
    await db.create_review(
        user_id=db_user.id,
        order_id=request.order_id,
        product_id=order.product_id,
        rating=request.rating,
        text=request.text
    )
    
    # Calculate 5% cashback
    cashback = order.amount * 0.05
    await db.update_user_balance(db_user.id, cashback)
    
    # Mark cashback as given
    db.client.table("reviews").update({
        "cashback_given": True
    }).eq("order_id", request.order_id).execute()
    
    return {
        "success": True,
        "cashback": cashback,
        "new_balance": db_user.balance + cashback
    }


# ==================== CRON JOBS (Vercel Cron) ====================

@app.get("/api/cron/review-requests")
async def cron_review_requests(authorization: str = Header(None)):
    """
    Send review requests for orders completed 1 hour ago.
    Called by Vercel Cron every 15 minutes.
    """
    # Verify cron secret
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    db = get_database()
    
    # Get orders completed ~1 hour ago (between 45-75 minutes)
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=75)
    end_time = now - timedelta(minutes=45)
    
    orders = db.client.table("orders").select("id").eq(
        "status", "completed"
    ).gte("delivered_at", start_time.isoformat()).lte(
        "delivered_at", end_time.isoformat()
    ).execute()
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for order in orders.data:
        # Check if review already exists
        existing = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
        if not existing.data:
            await notification_service.send_review_request(order["id"])
            sent_count += 1
    
    return {"sent": sent_count}


@app.get("/api/cron/expiration-reminders")
async def cron_expiration_reminders(authorization: str = Header(None)):
    """
    Send reminders for subscriptions expiring in 3 days.
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    db = get_database()
    
    # Get orders expiring in 3 days
    orders = await db.get_expiring_orders(days_before=3)
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for order in orders:
        # Get user and product info
        user_result = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("id", order.user_id).execute()
        
        product = await db.get_product_by_id(order.product_id)
        
        if user_result.data and product:
            user = user_result.data[0]
            days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0
            
            await notification_service.send_expiration_reminder(
                telegram_id=user["telegram_id"],
                product_name=product.name,
                days_left=days_left,
                language=user.get("language_code", "en")
            )
            sent_count += 1
    
    return {"sent": sent_count}


@app.get("/api/cron/wishlist-reminders")
async def cron_wishlist_reminders(authorization: str = Header(None)):
    """
    Send reminders for items in wishlist for 3+ days.
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    db = get_database()
    
    # Get wishlist items older than 3 days that haven't been reminded
    cutoff = datetime.utcnow() - timedelta(days=3)
    
    items = db.client.table("wishlist").select(
        "id,user_id,product_id,products(name,stock_count:stock_items(count))"
    ).eq("reminded", False).lt("created_at", cutoff.isoformat()).execute()
    
    notification_service = get_notification_service()
    
    sent_count = 0
    for item in items.data:
        # Get user
        user_result = db.client.table("users").select(
            "telegram_id,language_code,do_not_disturb"
        ).eq("id", item["user_id"]).execute()
        
        if not user_result.data:
            continue
        
        user = user_result.data[0]
        if user.get("do_not_disturb"):
            continue
        
        product_name = item.get("products", {}).get("name", "Product")
        
        from src.i18n import get_text
        message = get_text(
            "wishlist_reminder",
            user.get("language_code", "en"),
            product=product_name
        )
        
        bot = notification_service._get_bot()
        if bot:
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=message)
                
                # Mark as reminded
                db.client.table("wishlist").update({
                    "reminded": True
                }).eq("id", item["id"]).execute()
                
                sent_count += 1
            except Exception as e:
                print(f"Failed to send wishlist reminder: {e}")
    
    return {"sent": sent_count}


@app.get("/api/cron/re-engagement")
async def cron_re_engagement(authorization: str = Header(None)):
    """
    Send re-engagement messages to inactive users (7+ days).
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    db = get_database()
    
    # Get users inactive for 7+ days
    cutoff = datetime.utcnow() - timedelta(days=7)
    
    users = db.client.table("users").select(
        "telegram_id,language_code"
    ).eq("is_banned", False).eq("do_not_disturb", False).lt(
        "last_activity_at", cutoff.isoformat()
    ).limit(50).execute()
    
    notification_service = get_notification_service()
    bot = notification_service._get_bot()
    
    if not bot:
        return {"sent": 0}
    
    sent_count = 0
    for user in users.data:
        lang = user.get("language_code", "en")
        
        # Personalized re-engagement message
        message = {
            "ru": "👋 Давно не виделись! У нас появились новые предложения. Может, поможем найти что-то интересное?",
            "en": "👋 Long time no see! We have new offers. Can we help you find something interesting?",
        }.get(lang, "👋 Long time no see! We have new offers. Can we help you find something interesting?")
        
        try:
            await bot.send_message(chat_id=user["telegram_id"], text=message)
            sent_count += 1
        except Exception:
            pass  # User may have blocked the bot
    
    return {"sent": sent_count}


@app.get("/api/cron/daily-tasks")
async def cron_daily_tasks(authorization: str = Header(None)):
    """
    Combined daily cron job for Hobby plan (max 2 crons, once per day).
    Runs ALL scheduled tasks:
    - Review requests (orders completed yesterday)
    - Expiration reminders (subscriptions expiring in 3 days)
    - Wishlist reminders (items saved 3+ days ago)
    - Re-engagement (users inactive 7+ days)
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    results = {
        "review_requests": 0,
        "expiration_reminders": 0,
        "wishlist_reminders": 0,
        "re_engagement": 0,
        "rag_indexed": 0
    }
    
    notification_service = get_notification_service()
    db = get_database()
    bot = notification_service._get_bot()
    
    # -1. Index products for RAG (semantic search)
    try:
        from core.rag import get_product_search
        search = get_product_search()
        if search.is_available:
            indexed = await search.index_all_products()
            results["rag_indexed"] = indexed
    except Exception as e:
        print(f"RAG indexing error: {e}")
    
    if not bot:
        return {"error": "Bot not configured", "results": results}
    
    # 0. Review requests (orders completed yesterday)
    try:
        yesterday_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        
        orders = db.client.table("orders").select("id").eq(
            "status", "completed"
        ).gte("delivered_at", yesterday_start.isoformat()).lt(
            "delivered_at", yesterday_end.isoformat()
        ).is_("review_requested_at", "null").execute()
        
        for order in orders.data:
            existing_review = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
            if not existing_review.data:
                await notification_service.send_review_request(order["id"])
                db.client.table("orders").update(
                    {"review_requested_at": datetime.utcnow().isoformat()}
                ).eq("id", order["id"]).execute()
                results["review_requests"] += 1
    except Exception as e:
        print(f"Review requests error: {e}")
    
    # 1. Expiration reminders (subscriptions expiring in 3 days)
    try:
        orders = await db.get_expiring_orders(days_before=3)
        for order in orders:
            user_result = db.client.table("users").select(
                "telegram_id,language_code"
            ).eq("id", order.user_id).execute()
            product = await db.get_product_by_id(order.product_id)
            
            if user_result.data and product:
                user = user_result.data[0]
                days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0
                await notification_service.send_expiration_reminder(
                    telegram_id=user["telegram_id"],
                    product_name=product.name,
                    days_left=days_left,
                    language=user.get("language_code", "en")
                )
                results["expiration_reminders"] += 1
    except Exception as e:
        print(f"Expiration reminders error: {e}")
    
    # 2. Wishlist reminders (items saved 3+ days ago)
    try:
        from src.i18n import get_text
        cutoff = datetime.utcnow() - timedelta(days=3)
        items = db.client.table("wishlist").select(
            "id,user_id,products(name)"
        ).eq("reminded", False).lt("created_at", cutoff.isoformat()).limit(20).execute()
        
        for item in items.data:
            user_result = db.client.table("users").select(
                "telegram_id,language_code,do_not_disturb"
            ).eq("id", item["user_id"]).execute()
            
            if user_result.data and not user_result.data[0].get("do_not_disturb"):
                user = user_result.data[0]
                try:
                    msg = get_text("wishlist_reminder", user.get("language_code", "en"), 
                                  product=item.get("products", {}).get("name", "Product"))
                    await bot.send_message(chat_id=user["telegram_id"], text=msg)
                    db.client.table("wishlist").update({"reminded": True}).eq("id", item["id"]).execute()
                    results["wishlist_reminders"] += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"Wishlist reminders error: {e}")
    
    # 3. Re-engagement (users inactive 7+ days)
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        users = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("is_banned", False).eq("do_not_disturb", False).lt(
            "last_activity_at", cutoff.isoformat()
        ).limit(30).execute()
        
        for user in users.data:
            lang = user.get("language_code", "en")
            msg = {
                "ru": "👋 Давно не виделись! У нас появились новые предложения.",
                "en": "👋 Long time no see! We have new offers."
            }.get(lang, "👋 Long time no see! We have new offers.")
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=msg)
                results["re_engagement"] += 1
            except Exception:
                pass
    except Exception as e:
        print(f"Re-engagement error: {e}")
    
    return results


# QStash workers moved to core/routers/workers.py
# Admin endpoints moved to core/routers/admin.py

# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app when 'app' variable is present
# No need to export handler - FastAPI is auto-detected
