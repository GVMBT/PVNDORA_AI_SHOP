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
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

# Import models from separate file
from api.models import SubmitReviewRequest

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
except ImportError as e:
    import traceback
    print(f"ERROR: Failed to import modules: {e}")
    print(f"ERROR: sys.path = {sys.path}")
    print(f"ERROR: Traceback: {traceback.format_exc()}")
    raise

# Unified authentication
try:
    from core.auth import verify_telegram_auth
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
from core.routers.webapp import router as webapp_router

app.include_router(admin_router, prefix="/api/admin")
app.include_router(webhooks_router)
app.include_router(workers_router)
app.include_router(webapp_router)  # WebApp API endpoints


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


# Products/Orders/Profile API moved to core/routers/webapp.py

# ==================== USER API ====================

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


# FAQ moved to core/routers/webapp.py (/api/webapp/faq)

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


# Cron jobs moved to core/routers/cron.py
# QStash workers moved to core/routers/workers.py
# Admin endpoints moved to core/routers/admin.py

# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app when 'app' variable is present
# No need to export handler - FastAPI is auto-detected
