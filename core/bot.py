"""
Bot Module - Aiogram Dispatcher Setup

Configures:
- Bot instance with DefaultBotProperties
- Dispatcher with RedisStorage (Upstash)
- Middleware stack (I18n, Ban check, DI)
- Router registration
"""

import os
from typing import Optional, Any, Callable, Awaitable

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.state import State

from core.db import get_redis, RedisKeys


# Environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")


# ============================================================
# Custom Redis Storage for Upstash HTTP Redis
# ============================================================

class UpstashRedisStorage(BaseStorage):
    """
    FSM Storage using Upstash HTTP Redis.
    
    Compatible with aiogram 3.x FSM system.
    """
    
    def __init__(self):
        self.redis = get_redis()
    
    def _make_key(self, key: StorageKey, suffix: str) -> str:
        """Generate Redis key for FSM data."""
        return f"fsm:{suffix}:{key.bot_id}:{key.chat_id}:{key.user_id}"
    
    async def set_state(
        self,
        key: StorageKey,
        state: Optional[State] = None
    ) -> None:
        """Set FSM state."""
        redis_key = self._make_key(key, "state")
        if state is None:
            await self.redis.delete(redis_key)
        else:
            await self.redis.set(redis_key, state.state, ex=86400)  # 24h TTL
    
    async def get_state(self, key: StorageKey) -> Optional[str]:
        """Get FSM state."""
        redis_key = self._make_key(key, "state")
        return await self.redis.get(redis_key)
    
    async def set_data(self, key: StorageKey, data: dict) -> None:
        """Set FSM data."""
        import json
        redis_key = self._make_key(key, "data")
        if not data:
            await self.redis.delete(redis_key)
        else:
            await self.redis.set(redis_key, json.dumps(data), ex=86400)
    
    async def get_data(self, key: StorageKey) -> dict:
        """Get FSM data."""
        import json
        redis_key = self._make_key(key, "data")
        data = await self.redis.get(redis_key)
        if data:
            return json.loads(data)
        return {}
    
    async def close(self) -> None:
        """Close storage (no-op for HTTP Redis)."""
        pass


# ============================================================
# Middleware
# ============================================================

class I18nMiddleware(BaseMiddleware):
    """
    Internationalization middleware.
    
    Extracts user language and adds to handler data.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict
    ) -> Any:
        # Extract language code
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user
        
        if user:
            lang = user.language_code or "en"
            # Normalize to supported languages
            supported = ["en", "ru", "uk", "de", "fr", "es", "tr", "ar", "hi"]
            if lang not in supported:
                # Try base language (e.g., "en-US" -> "en")
                lang = lang.split("-")[0] if "-" in lang else "en"
                if lang not in supported:
                    lang = "en"
            data["language_code"] = lang
            data["user_telegram_id"] = user.id
        else:
            data["language_code"] = "en"
            data["user_telegram_id"] = None
        
        return await handler(event, data)


class BanCheckMiddleware(BaseMiddleware):
    """
    Ban check middleware.
    
    Blocks banned users from interacting with bot.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict
    ) -> Any:
        user_id = data.get("user_telegram_id")
        
        if user_id:
            # Check ban status in database
            from core.db import get_supabase
            try:
                supabase = await get_supabase()
                result = await supabase.table("users").select(
                    "is_banned"
                ).eq("telegram_id", user_id).single().execute()
                
                if result.data and result.data.get("is_banned"):
                    # User is banned
                    if isinstance(event, Message):
                        await event.answer(
                            "⛔ Access restricted. Contact @admin to appeal.",
                            parse_mode=ParseMode.HTML
                        )
                    return None
            except Exception:
                # User not found or error - allow through
                pass
        
        return await handler(event, data)


class DependencyInjectionMiddleware(BaseMiddleware):
    """
    Dependency injection middleware.
    
    Injects database clients and AI into handler data.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict
    ) -> Any:
        from core.db import get_supabase, get_redis
        from core.ai import get_ai_consultant
        from core.cart import get_cart_manager
        
        # Inject dependencies
        data["supabase"] = await get_supabase()
        data["redis"] = get_redis()
        data["ai_consultant"] = get_ai_consultant()
        data["cart_manager"] = get_cart_manager()
        
        return await handler(event, data)


class ActivityTrackingMiddleware(BaseMiddleware):
    """
    Track user activity for re-engagement system.
    
    Updates last_activity_at on each interaction.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict
    ) -> Any:
        user_id = data.get("user_telegram_id")
        
        if user_id:
            try:
                from core.db import get_supabase
                supabase = await get_supabase()
                await supabase.table("users").update({
                    "last_activity_at": "now()"
                }).eq("telegram_id", user_id).execute()
            except Exception:
                pass  # Non-critical, don't block
        
        return await handler(event, data)


# ============================================================
# Bot and Dispatcher Setup
# ============================================================

_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None


def get_bot() -> Bot:
    """Get Bot instance (singleton)."""
    global _bot
    
    if _bot is None:
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN must be set")
        
        _bot = Bot(
            token=TELEGRAM_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )
    
    return _bot


def get_dispatcher() -> Dispatcher:
    """Get Dispatcher instance (singleton) with full middleware stack."""
    global _dp
    
    if _dp is None:
        # Create storage
        storage = UpstashRedisStorage()
        
        # Create dispatcher
        _dp = Dispatcher(storage=storage)
        
        # Register middleware (order matters!)
        _dp.message.middleware(I18nMiddleware())
        _dp.message.middleware(BanCheckMiddleware())
        _dp.message.middleware(DependencyInjectionMiddleware())
        _dp.message.middleware(ActivityTrackingMiddleware())
        
        _dp.callback_query.middleware(I18nMiddleware())
        _dp.callback_query.middleware(BanCheckMiddleware())
        _dp.callback_query.middleware(DependencyInjectionMiddleware())
        
        _dp.inline_query.middleware(I18nMiddleware())
        
        # Register routers
        from core.handlers import messages_router, callbacks_router, inline_router
        _dp.include_router(messages_router)
        _dp.include_router(callbacks_router)
        _dp.include_router(inline_router)
    
    return _dp


async def setup_bot_commands():
    """
    Set bot commands menu.
    
    Note: Full multilingual setup is done via scripts/setup_bot.py
    This is a fallback for runtime.
    """
    bot = get_bot()
    
    commands = [
        ("start", "Start the bot"),
        ("catalog", "Browse products"),
        ("cart", "View cart"),
        ("my_orders", "Order history"),
        ("wishlist", "Saved items"),
        ("help", "Get help"),
    ]
    
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command=cmd, description=desc)
        for cmd, desc in commands
    ])

