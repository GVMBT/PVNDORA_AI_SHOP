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

# Models moved to core/routers/user.py

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
    from core.bot.handlers import router as bot_router
    from core.bot.middlewares import (
        AuthMiddleware,
        LanguageMiddleware, 
        ActivityMiddleware,
        AnalyticsMiddleware
    )
    from core.services.database import get_database
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
    try:
        from core.routers.deps import shutdown_services
        await shutdown_services()
    except Exception as e:
        # Use basic logging for shutdown errors (logger may not be configured)
        import logging
        logging.warning(f"Failed to shutdown services cleanly: {e}", exc_info=True)
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
from core.routers.user import router as user_router

app.include_router(admin_router, prefix="/api/admin")
app.include_router(webhooks_router)
app.include_router(workers_router)
app.include_router(webapp_router)  # WebApp API endpoints
app.include_router(user_router)  # User API (wishlist, reviews)


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


@app.get("/api/webhook/status")
async def webhook_status():
    """Check Telegram webhook status - calls Telegram API directly"""
    import httpx
    
    if not TELEGRAM_TOKEN:
        return {"error": "TELEGRAM_TOKEN not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo")
            result = response.json()
            
            if result.get("ok"):
                info = result["result"]
                return {
                    "ok": True,
                    "url": info.get("url", "NOT SET"),
                    "pending_updates": info.get("pending_update_count", 0),
                    "last_error_date": info.get("last_error_date"),
                    "last_error_message": info.get("last_error_message"),
                    "max_connections": info.get("max_connections"),
                    "expected_url": f"{WEBAPP_URL}/webhook/telegram",
                    "url_matches": info.get("url") == f"{WEBAPP_URL}/webhook/telegram"
                }
            else:
                return {"ok": False, "error": result.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/webhook/set")
async def set_webhook_endpoint():
    """Set Telegram webhook - call this to configure the webhook"""
    import httpx
    
    if not TELEGRAM_TOKEN:
        return {"error": "TELEGRAM_TOKEN not configured"}
    
    webhook_url = f"{WEBAPP_URL}/webhook/telegram"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "callback_query", "my_chat_member"],
                    "drop_pending_updates": True
                }
            )
            result = response.json()
            
            if result.get("ok"):
                return {
                    "ok": True,
                    "message": "Webhook set successfully",
                    "url": webhook_url
                }
            else:
                return {"ok": False, "error": result.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== TELEGRAM WEBHOOK ====================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Telegram webhook updates"""
    import logging
    logger = logging.getLogger(__name__)
    
    # IMPORTANT: Return 200 immediately to avoid 307 redirects
    # Process update in background to avoid timeout
    try:
        # Get bot and dispatcher
        bot_instance = get_bot()
        dispatcher = get_dispatcher()
        
        if not bot_instance:
            logger.error("Bot instance is None - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=200,  # Return 200 even on error to prevent Telegram retries
                content={"ok": False, "error": "Bot not configured"}
            )
        
        # Parse update
        try:
            data = await request.json()
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid JSON: {str(e)}"}
            )
        
        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as e:
            logger.warning(f"Failed to validate update: {e}")
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
        
        # Return 200 OK immediately
        return JSONResponse(content={"ok": True})
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Webhook exception: {error_msg}")
        # Always return 200 to prevent Telegram from retrying
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": error_msg}
        )


async def _process_update_async(bot_instance: Bot, dispatcher: Dispatcher, update: Update):
    """Process update asynchronously"""
    import logging
    logger = logging.getLogger(__name__)
    update_id = update.update_id if hasattr(update, 'update_id') else 'unknown'
    try:
        await dispatcher.feed_update(bot_instance, update)
    except Exception as e:
        logger.error(f"Failed to process update {update_id}: {e}")


# Products/Orders/Profile API moved to core/routers/webapp.py
# User API (referral, wishlist, reviews) moved to core/routers/user.py
# FAQ moved to core/routers/webapp.py (/api/webapp/faq)

# Cron jobs moved to core/routers/cron.py
# QStash workers moved to core/routers/workers.py
# Admin endpoints moved to core/routers/admin.py


# ==================== DISCOUNT BOT WEBHOOK ====================

# Discount bot configuration
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")

discount_bot: Optional[Bot] = None
discount_dp: Optional[Dispatcher] = None


def get_discount_bot() -> Optional[Bot]:
    """Get or create discount bot instance"""
    global discount_bot
    if discount_bot is None and DISCOUNT_BOT_TOKEN:
        discount_bot = Bot(
            token=DISCOUNT_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return discount_bot


def get_discount_dispatcher() -> Optional[Dispatcher]:
    """Get or create discount dispatcher instance"""
    global discount_dp
    if discount_dp is None and DISCOUNT_BOT_TOKEN:
        from core.bot.discount import (
            discount_router,
            DiscountAuthMiddleware,
            ChannelSubscriptionMiddleware,
            TermsAcceptanceMiddleware,
        )
        
        discount_dp = Dispatcher()
        
        # Register middlewares (order matters!)
        discount_dp.message.middleware(DiscountAuthMiddleware())
        discount_dp.message.middleware(ChannelSubscriptionMiddleware())
        discount_dp.message.middleware(TermsAcceptanceMiddleware())
        
        discount_dp.callback_query.middleware(DiscountAuthMiddleware())
        discount_dp.callback_query.middleware(ChannelSubscriptionMiddleware())
        
        # Register discount bot router
        discount_dp.include_router(discount_router)
    
    return discount_dp


@app.post("/webhook/discount")
async def discount_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Discount Bot Telegram webhook updates"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        bot_instance = get_discount_bot()
        dispatcher = get_discount_dispatcher()
        
        if not bot_instance or not dispatcher:
            logger.error("Discount bot not configured - DISCOUNT_BOT_TOKEN may be missing")
            return JSONResponse(
                status_code=200,
                content={"ok": False, "error": "Discount bot not configured"}
            )
        
        try:
            data = await request.json()
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return JSONResponse(
                status_code=200,
                content={"ok": False, "error": f"Invalid JSON: {str(e)}"}
            )
        
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as e:
            logger.warning(f"Failed to validate update: {e}")
            return JSONResponse(
                status_code=200,
                content={"ok": False, "error": f"Invalid update: {str(e)}"}
            )
        
        # Process update in background
        background_tasks.add_task(
            _process_update_async,
            bot_instance,
            dispatcher,
            update
        )
        
        return JSONResponse(content={"ok": True})
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Discount webhook exception: {error_msg}")
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": error_msg}
        )


@app.post("/api/webhook/discount/set")
async def set_discount_webhook():
    """Set Discount Bot Telegram webhook"""
    import httpx
    
    if not DISCOUNT_BOT_TOKEN:
        return {"error": "DISCOUNT_BOT_TOKEN not configured"}
    
    webhook_url = f"{WEBAPP_URL}/webhook/discount"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{DISCOUNT_BOT_TOKEN}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "callback_query"],
                    "drop_pending_updates": True
                }
            )
            result = response.json()
            
            if result.get("ok"):
                return {
                    "ok": True,
                    "message": "Discount webhook set successfully",
                    "url": webhook_url
                }
            else:
                return {"ok": False, "error": result.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app when 'app' variable is present
# No need to export handler - FastAPI is auto-detected
