"""PVNDORA AI Marketplace - Main FastAPI Application.

Single entry point for all webhooks and API routes.
Optimized for Vercel Hobby plan (max 12 serverless functions).
"""

# Aikido Zen Runtime Protection - MUST be imported before any other code
# This provides runtime security and firewall protection
# Documentation: https://docs.aikido.dev/zen
import logging
import os

_logger = logging.getLogger(__name__)
AIKIDO_ZEN_AVAILABLE = False
_aikido_zen_module = None

try:
    import aikido_zen  # type: ignore[import-untyped]
    _aikido_zen_module = aikido_zen
    # Try to call protect() immediately if token is available
    # This ensures Zen is active before middleware is added
    token = os.environ.get("AIKIDO_TOKEN")
    if token:
        try:
            aikido_zen.protect()
            AIKIDO_ZEN_AVAILABLE = True
            _logger.info("Aikido Zen module imported and protect() called successfully")
        except Exception as e:
            _logger.error(f"Aikido Zen protect() failed: {type(e).__name__}: {e}", exc_info=True)
    else:
        _logger.warning("Aikido Zen module imported but AIKIDO_TOKEN not set")
except ImportError:
    # Aikido Zen is optional - don't fail if not installed
    # Install with: pip install aikido-zen
    _logger.warning("Aikido Zen not installed (ImportError)")
except Exception as e:
    _logger.error(f"Aikido Zen import failed: {type(e).__name__}: {e}", exc_info=True)

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
    from core.bot.discount import DiscountAuthMiddleware, TermsAcceptanceMiddleware, discount_router
    from core.bot.handlers import router as bot_router
    from core.bot.middlewares import (
        ActivityMiddleware,
        AnalyticsMiddleware,
        AuthMiddleware,
        ChannelSubscriptionMiddleware,
        LanguageMiddleware,
    )
    from core.middleware.rate_limit import RateLimitMiddleware
    from core.middleware.security import SecurityHeadersMiddleware

    # Include other routers
    from core.routers.admin.accounting import router as accounting_router
    from core.routers.admin.analytics import router as analytics_router
    from core.routers.admin.broadcast import router as admin_broadcast_router
    from core.routers.admin.migration import router as admin_migration_router
    from core.routers.admin.orders import router as admin_orders_router
    from core.routers.admin.products import router as admin_products_router
    from core.routers.admin.promo import router as admin_promo_router
    from core.routers.admin.rag import router as admin_rag_router
    from core.routers.admin.referral import router as admin_referral_router
    from core.routers.admin.replacements import router as admin_replacements_router
    from core.routers.admin.tickets import router as admin_tickets_router
    from core.routers.admin.users import router as admin_users_router
    from core.routers.admin.withdrawals import router as admin_withdrawals_router
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

# Constants for error messages (avoid string duplication)
ERROR_PARSE_JSON = "Failed to parse JSON: %s"
ERROR_VALIDATE_UPDATE = "Failed to validate update: %s"
ADMIN_API_PREFIX = "/api/admin"

# ==================== BOT INITIALIZATION ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


class BotState:
    """Container for bot state to avoid global variables."""

    bot: Bot | None = None
    dp: Dispatcher | None = None
    discount_bot: Bot | None = None
    discount_dp: Dispatcher | None = None
    admin_bot: Bot | None = None
    admin_dp: Dispatcher | None = None


def get_bot() -> Bot | None:
    """Get or create bot instance."""
    if BotState.bot is None and TELEGRAM_TOKEN:
        BotState.bot = Bot(
            token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return BotState.bot


def get_dispatcher() -> Dispatcher:
    """Get or create dispatcher instance."""
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
    """Application lifespan handler."""
    # Startup - Initialize async database singleton
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as err:
        logger.error("Failed to initialize database: %s", err, exc_info=True)
        # Continue anyway - some endpoints may work without DB

    # Check Aikido Zen status (already initialized at module level)
    if AIKIDO_ZEN_AVAILABLE:
        logger.info("Aikido Zen Runtime Protection: ACTIVE")
    elif _aikido_zen_module is not None:
        token = os.environ.get("AIKIDO_TOKEN")
        if token:
            logger.warning("Aikido Zen module available but protect() failed (check logs above)")
        else:
            logger.warning("Aikido Zen installed but AIKIDO_TOKEN not set - protection disabled")
    else:
        import importlib.util
        if importlib.util.find_spec("aikido_zen") is not None:
            logger.warning("Aikido Zen module found but import failed (check logs above)")
        else:
            logger.info("Aikido Zen not installed - runtime protection disabled")

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

# Digma Observability - MUST be setup before adding routers
# Automatically tracks: N+1 queries, chatty logic, dead code, performance
try:
    from core.observability.digma_setup import setup_digma

    setup_digma(app)
except ImportError:
    logger.info("Digma observability not available (OpenTelemetry not installed)")
except Exception as e:
    logger.warning(f"Failed to setup Digma observability: {e}")

# Query Monitor Middleware - отслеживает N+1 queries и Chatty Logic в runtime
# Должен быть добавлен ПЕРЕД SecurityHeadersMiddleware для доступа к request.state
try:
    from core.middleware.query_monitor import QueryMonitorMiddleware, set_query_monitor

    query_monitor = QueryMonitorMiddleware(app, threshold_nplusone=5, threshold_chatty=20)
    app.add_middleware(QueryMonitorMiddleware, threshold_nplusone=5, threshold_chatty=20)
    set_query_monitor(query_monitor)
    logger.info("Query Monitor middleware enabled (N+1 and Chatty Logic detection)")
except ImportError:
    logger.info("Query Monitor middleware not available")
except Exception as e:
    logger.warning(f"Failed to setup Query Monitor middleware: {e}")

# Security Headers Middleware - MUST be first (outermost)
# Adds CSP, HSTS, X-Frame-Options, and other security headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting Middleware - protects auth endpoints from brute force
# Uses Redis if available, falls back to in-memory cache
try:
    from core.db import get_redis

    redis_client = get_redis()
    if redis_client:
        app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
        logger.info("Rate limiting enabled with Redis")
    else:
        app.add_middleware(RateLimitMiddleware)
        logger.warning("Rate limiting enabled with in-memory cache (not distributed)")
except (ImportError, ValueError, Exception) as e:
    # Continue without rate limiting if Redis unavailable or not configured
    logger.warning(f"Rate limiting unavailable: {e}, continuing without it")
    app.add_middleware(RateLimitMiddleware)  # Use in-memory fallback

# Aikido Zen Middleware - MUST be added after authentication middleware
# This enables request blocking for security threats
# NOTE: Admin endpoints are protected by verify_admin() - Zen should not block them
try:
    if AIKIDO_ZEN_AVAILABLE:
        from aikido_zen.middleware import AikidoStarletteMiddleware  # type: ignore

        app.add_middleware(AikidoStarletteMiddleware)
        logger.info("Aikido Zen middleware added successfully")

        # Check if whitelist is configured
        whitelist = os.environ.get("AIKIDO_WHITELIST")
        if whitelist:
            logger.info(f"Aikido Zen whitelist configured: {whitelist}")
        else:
            logger.warning(
                "Aikido Zen whitelist not set. If admin endpoints are blocked, "
                "set AIKIDO_WHITELIST=/api/admin/* in Vercel Environment Variables",
            )
    else:
        logger.warning("Aikido Zen middleware not added (AIKIDO_ZEN_AVAILABLE=False)")
except (ImportError, NameError) as e:
    # Aikido middleware not available - continue without it
    logger.warning(f"Aikido Zen middleware import failed: {e}")
except Exception as e:
    logger.error(f"Aikido Zen middleware setup failed: {e}", exc_info=True)

# CORS for Mini App
# ⚠️ SECURITY NOTE: allow_origins=["*"] is required for Telegram Mini Apps
# Telegram Mini Apps can be opened from any domain via t.me links.
# This is safe because:
# 1. Authentication is verified via Telegram initData (HMAC-SHA256 signed)
# 2. All authenticated endpoints verify Telegram signature
# 3. Credentials are only sent with requests (credentials=True allows cookies/tokens)
# 4. Without credentials=True, browsers won't send Authorization headers from cross-origin
#
# Alternative (if we had fixed origins): allow_origins=["https://t.me", "https://web.telegram.org"]
# But Telegram Mini Apps can be opened from various Telegram clients/domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini Apps require this (see security note above)
    allow_credentials=True,  # Required for Authorization headers from Telegram Mini Apps
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/webhook")
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Main Bot Telegram webhook updates."""
    try:
        bot_instance = get_bot()
        dispatcher = get_dispatcher()

        if not bot_instance:
            logger.error("Bot not configured - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Bot not configured"},
            )

        # Parse update
        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_PARSE_JSON, err)
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid JSON: {err!s}"},
            )

        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_VALIDATE_UPDATE, err)
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


async def _process_update_async(bot_instance: Bot, dispatcher: Dispatcher, update: Update) -> None:
    """Process update asynchronously."""
    update_id = update.update_id if hasattr(update, "update_id") else "unknown"
    try:
        await dispatcher.feed_update(bot_instance, update)
    except Exception:
        logger.exception("Failed to process update %s", update_id)


# ==================== DISCOUNT BOT WEBHOOK ====================

# Discount bot configuration
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


def get_discount_bot() -> Bot | None:
    """Get or create discount bot instance."""
    if BotState.discount_bot is None and DISCOUNT_BOT_TOKEN:
        BotState.discount_bot = Bot(
            token=DISCOUNT_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return BotState.discount_bot


def get_discount_dispatcher() -> Dispatcher | None:
    """Get or create discount dispatcher instance."""
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
    """Handle Discount Bot Telegram webhook updates."""
    try:
        bot_instance = get_discount_bot()
        dispatcher = get_discount_dispatcher()

        if not bot_instance or not dispatcher:
            logger.error("Discount bot not configured - DISCOUNT_BOT_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Discount bot not configured"},
            )

        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_PARSE_JSON, err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid JSON: {err!s}"},
            )

        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_VALIDATE_UPDATE, err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid update: {err!s}"},
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
    """Set Discount Bot Telegram webhook."""
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
    """Get or create admin bot instance."""
    if BotState.admin_bot is None and ADMIN_BOT_TOKEN:
        BotState.admin_bot = Bot(
            token=ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return BotState.admin_bot


def get_admin_dispatcher() -> Dispatcher | None:
    """Get or create admin dispatcher instance."""
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
    """Handle Admin Bot Telegram webhook updates."""
    try:
        bot_instance = get_admin_bot()
        dispatcher = get_admin_dispatcher()

        if not bot_instance or not dispatcher:
            logger.error("Admin bot not configured - ADMIN_BOT_TOKEN may be missing")
            return JSONResponse(
                status_code=200, content={"ok": False, "error": "Admin bot not configured"},
            )

        try:
            data = await request.json()
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_PARSE_JSON, err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid JSON: {err!s}"},
            )

        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
        except Exception as err:  # pylint: disable=broad-exception-caught
            logger.warning(ERROR_VALIDATE_UPDATE, err)
            return JSONResponse(
                status_code=200, content={"ok": False, "error": f"Invalid update: {err!s}"},
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
    """Set Admin Bot Telegram webhook."""
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
# workers_router already has prefix="/api/workers" in core/routers/workers/router.py
app.include_router(workers_router)
# WebApp router - already has prefix /api/webapp in __init__.py
app.include_router(webapp_router)

# Admin routers
app.include_router(admin_products_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_users_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_orders_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_tickets_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_promo_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_withdrawals_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_broadcast_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_migration_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_rag_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_referral_router, prefix=ADMIN_API_PREFIX)
app.include_router(admin_replacements_router, prefix=ADMIN_API_PREFIX)
app.include_router(accounting_router, prefix=ADMIN_API_PREFIX)
app.include_router(analytics_router, prefix=ADMIN_API_PREFIX)
