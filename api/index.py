"""
PVNDORA AI Marketplace - Main FastAPI Application

Single entry point for all webhooks and API routes.
Optimized for Vercel Hobby plan (max 12 serverless functions).
"""

import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

# Add src to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

# Now we can import core and third-party modules
try:
    import httpx
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.types import Update
    from fastapi import BackgroundTasks, FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    from core.bot.admin import AdminAuthMiddleware
    from core.bot.admin import router as admin_bot_router
    from core.bot.discount import (
        ChannelSubscriptionMiddleware as DiscountChannelSubscriptionMiddleware,
    )
    from core.bot.discount import (
        DiscountAuthMiddleware,
        TermsAcceptanceMiddleware,
        discount_router,
    )
    from core.bot.handlers import router as bot_router
    from core.bot.middlewares import (
        ActivityMiddleware,
        AnalyticsMiddleware,
        AuthMiddleware,
        ChannelSubscriptionMiddleware,
        LanguageMiddleware,
    )

    # Include other routers
    from core.routers.admin.accounting import router as accounting_router
    from core.routers.admin.analytics import router as analytics_router
    from core.routers.admin.products import router as admin_products_router
    from core.routers.admin.users import router as admin_users_router
    from core.routers.deps import shutdown_services

    # WebApp router - single unified router from __init__.py
    from core.routers.webapp import router as webapp_router
    from core.routers.webhooks import router as webhooks_router
    from core.routers.workers.router import router as workers_router
    from core.services.database import close_database, init_database
except ImportError:
    # Use logging instead of print for better error tracking
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.exception("ERROR: Failed to import modules")
    logger.exception("sys.path = %s", sys.path)
    logger.exception("Traceback: %s", traceback.format_exc())
    raise

# Set up logging
logger = logging.getLogger(__name__)


# ==================== BOT INITIALIZATION ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


class BotState:
    """Container for bot state to avoid global variables"""

    bot: Bot | None = None
    dp: Dispatcher | None = None
    discount_bot: Bot | None = None
    discount_dp: Dispatcher | None = None
    admin_bot: Bot | None = None
    admin_dp: Dispatcher | None = None


def get_bot() -> Bot | None:
    """Get or create bot instance"""
    if BotState.bot is None and TELEGRAM_TOKEN:
        BotState.bot = Bot(
            token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return BotState.bot


def get_dispatcher() -> Dispatcher:
    """Get or create dispatcher instance"""
    if BotState.dp is None:
        BotState.dp = Dispatcher()

        # Register middlewares (order matters!)
        # Auth first, then subscription check, then language/activity
        BotState.dp.message.middleware(AuthMiddleware())
        BotState.dp.message.middleware(ChannelSubscriptionMiddleware())
        BotState.dp.message.middleware(LanguageMiddleware())
        BotState.dp.message.middleware(ActivityMiddleware())
        BotState.dp.message.middleware(AnalyticsMiddleware())

        BotState.dp.callback_query.middleware(AuthMiddleware())
        BotState.dp.callback_query.middleware(ChannelSubscriptionMiddleware())
        BotState.dp.callback_query.middleware(LanguageMiddleware())
        BotState.dp.callback_query.middleware(ActivityMiddleware())

        # Register router
        BotState.dp.include_router(bot_router)

    return BotState.dp


# ==================== FASTAPI APP ====================


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifespan handler"""
    # Startup - Initialize async database singleton
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as err:
        logger.error("Failed to initialize database: %s", err, exc_info=True)
        # Continue anyway - some endpoints may work without DB

    yield

    # Shutdown
    try:
        await shutdown_services()
    except Exception as err:
        logger.warning("Failed to shutdown services cleanly: %s", err, exc_info=True)

    try:
        await close_database()
    except Exception as err:
        logger.warning("Failed to close database: %s", err, exc_info=True)

    if BotState.bot:
        await BotState.bot.session.close()
    if BotState.discount_bot:
        await BotState.discount_bot.session.close()
    if BotState.admin_bot:
        await BotState.admin_bot.session.close()


app = FastAPI(
    title="PVNDORA AI Marketplace",
    description="AI-powered digital goods marketplace API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini Apps require this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Main Bot Telegram webhook updates"""
    try:
        bot_instance = get_bot()
        dispatcher = get_dispatcher()

        if not bot_instance:
            logger.error("Bot not configured - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Bot not configured"}
            )

        # Parse update
        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to parse JSON: %s", err)
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid JSON: {err!s}"},
            )

        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to validate update: %s", err)
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid update: {err!s}"},
            )

        # Process update in background - FastAPI BackgroundTasks are guaranteed to run
        # Return 200 immediately to Telegram
        background_tasks.add_task(_process_update_async, bot_instance, dispatcher, update)

        # Return 200 OK immediately
        return JSONResponse(content={"ok": True})

    except Exception as err:  # pylint: disable=broad-exception-caught
        error_msg = str(err)
        logger.exception("Webhook exception: %s", error_msg)
        # Always return 200 to prevent Telegram from retrying
        return JSONResponse(status_code=200, content={"ok": False, "error": error_msg})


async def _process_update_async(bot_instance: Bot, dispatcher: Dispatcher, update: Update):
    """Process update asynchronously"""
    update_id = update.update_id if hasattr(update, "update_id") else "unknown"
    try:
        await dispatcher.feed_update(bot_instance, update)
    except Exception:
        logger.exception("Failed to process update %s", update_id)


# ==================== DISCOUNT BOT WEBHOOK ====================

# Discount bot configuration
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


def get_discount_bot() -> Bot | None:
    """Get or create discount bot instance"""
    if BotState.discount_bot is None and DISCOUNT_BOT_TOKEN:
        BotState.discount_bot = Bot(
            token=DISCOUNT_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return BotState.discount_bot


def get_discount_dispatcher() -> Dispatcher | None:
    """Get or create discount dispatcher instance"""
    if BotState.discount_dp is None and DISCOUNT_BOT_TOKEN:
        BotState.discount_dp = Dispatcher()

        # Register middlewares (order matters!)
        BotState.discount_dp.message.middleware(DiscountAuthMiddleware())
        BotState.discount_dp.message.middleware(DiscountChannelSubscriptionMiddleware())
        BotState.discount_dp.message.middleware(TermsAcceptanceMiddleware())

        BotState.discount_dp.callback_query.middleware(DiscountAuthMiddleware())
        BotState.discount_dp.callback_query.middleware(DiscountChannelSubscriptionMiddleware())

        # Register discount bot router
        BotState.discount_dp.include_router(discount_router)

    return BotState.discount_dp


@app.post("/webhook/discount")
async def discount_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Discount Bot Telegram webhook updates"""
    try:
        bot_instance = get_discount_bot()
        dispatcher = get_discount_dispatcher()

        if not bot_instance or not dispatcher:
            logger.error("Discount bot not configured - DISCOUNT_BOT_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Discount bot not configured"}
            )

        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to parse JSON: %s", err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid JSON: {err!s}"}
            )

        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to validate update: %s", err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid update: {err!s}"}
            )

        # Process update in background
        background_tasks.add_task(_process_update_async, bot_instance, dispatcher, update)

        return JSONResponse(content={"ok": True})

    except Exception as err:  # pylint: disable=broad-exception-caught
        error_msg = str(err)
        logger.exception("Discount webhook exception: %s", error_msg)
        return JSONResponse(status_code=200, content={"ok": False, "error": error_msg})


@app.post("/api/webhook/discount/set")
async def set_discount_webhook():
    """Set Discount Bot Telegram webhook"""
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
                    "drop_pending_updates": True,
                },
            )
            result = response.json()

            if result.get("ok"):
                return {
                    "ok": True,
                    "message": "Discount webhook set successfully",
                    "url": webhook_url,
                }
            return {"ok": False, "error": result.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== ADMIN BOT WEBHOOK ====================

# Admin bot configuration
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")


def get_admin_bot() -> Bot | None:
    """Get or create admin bot instance"""
    if BotState.admin_bot is None and ADMIN_BOT_TOKEN:
        BotState.admin_bot = Bot(
            token=ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return BotState.admin_bot


def get_admin_dispatcher() -> Dispatcher | None:
    """Get or create admin dispatcher instance"""
    if BotState.admin_dp is None and ADMIN_BOT_TOKEN:
        BotState.admin_dp = Dispatcher(storage=MemoryStorage())

        # Register middleware - only admin auth required
        BotState.admin_dp.message.middleware(AdminAuthMiddleware())
        BotState.admin_dp.callback_query.middleware(AdminAuthMiddleware())

        # Register admin bot router
        BotState.admin_dp.include_router(admin_bot_router)

    return BotState.admin_dp


@app.post("/webhook/admin")
async def admin_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Admin Bot Telegram webhook updates"""
    try:
        bot_instance = get_admin_bot()
        dispatcher = get_admin_dispatcher()

        if not bot_instance or not dispatcher:
            logger.error("Admin bot not configured - ADMIN_BOT_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Admin bot not configured"}
            )

        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to parse JSON: %s", err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid JSON: {err!s}"}
            )

        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to validate update: %s", err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid update: {err!s}"}
            )

        # Process update in background
        background_tasks.add_task(_process_update_async, bot_instance, dispatcher, update)

        return JSONResponse(content={"ok": True})

    except Exception as err:  # pylint: disable=broad-exception-caught
        error_msg = str(err)
        logger.exception("Admin webhook exception: %s", error_msg)
        return JSONResponse(status_code=200, content={"ok": False, "error": error_msg})


@app.post("/api/webhook/admin/set")
async def set_admin_webhook():
    """Set Admin Bot Telegram webhook"""
    if not ADMIN_BOT_TOKEN:
        return {"error": "ADMIN_BOT_TOKEN not configured"}

    webhook_url = f"{WEBAPP_URL}/webhook/admin"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "callback_query"],
                    "drop_pending_updates": True,
                },
            )
            result = response.json()

            if result.get("ok"):
                return {"ok": True, "message": "Admin webhook set successfully", "url": webhook_url}
            return {"ok": False, "error": result.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app when 'app' variable is present
# No need to export handler - FastAPI is auto-detected


app.include_router(webhooks_router, prefix="/api")
app.include_router(workers_router, prefix="/api")
# WebApp router - already has prefix /api/webapp in __init__.py
app.include_router(webapp_router)

# Admin routers
app.include_router(admin_products_router, prefix="/api/admin")
app.include_router(admin_users_router, prefix="/api/admin")
app.include_router(accounting_router, prefix="/api/admin")
app.include_router(analytics_router, prefix="/api/admin")
