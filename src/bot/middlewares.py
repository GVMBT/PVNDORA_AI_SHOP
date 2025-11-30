"""Telegram Bot Middlewares"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from src.services.database import get_database
from src.i18n import detect_language


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for user authentication and ban check.
    Creates user if not exists, blocks banned users.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if not user:
            return await handler(event, data)
        
        db = get_database()
        
        # Get or create user
        db_user = await db.get_user_by_telegram_id(user.id)
        
        if db_user is None:
            # Check for referrer in start command
            referrer_id = None
            if isinstance(event, Message) and event.text:
                if event.text.startswith("/start ref_"):
                    try:
                        referrer_id = int(event.text.split("ref_")[1].split()[0])
                    except (ValueError, IndexError):
                        pass
            
            # Create new user
            db_user = await db.create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language_code=detect_language(user.language_code),
                referrer_telegram_id=referrer_id
            )
        
        # Check if banned
        if db_user.is_banned:
            if isinstance(event, Message):
                from src.i18n import get_text
                await event.answer(get_text("banned", db_user.language_code))
            return  # Stop processing
        
        # Add user to data for handlers
        data["db_user"] = db_user
        
        return await handler(event, data)


class LanguageMiddleware(BaseMiddleware):
    """
    Middleware for language detection and update.
    Updates user language if it changed in Telegram settings.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user and "db_user" in data:
            db_user = data["db_user"]
            new_lang = detect_language(user.language_code)
            
            # Update if language changed
            if new_lang != db_user.language_code:
                db = get_database()
                await db.update_user_language(user.id, new_lang)
                db_user.language_code = new_lang
        
        return await handler(event, data)


class ActivityMiddleware(BaseMiddleware):
    """
    Middleware for tracking user activity.
    Updates last_activity_at for re-engagement features.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user:
            db = get_database()
            await db.update_user_activity(user.id)
        
        return await handler(event, data)


class AnalyticsMiddleware(BaseMiddleware):
    """
    Middleware for logging analytics events.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db_user = data.get("db_user")
        
        # Log event type
        event_type = None
        metadata = {}
        
        if isinstance(event, Message):
            if event.text and event.text.startswith("/"):
                event_type = "command"
                metadata["command"] = event.text.split()[0]
            elif event.voice:
                event_type = "voice_message"
            else:
                event_type = "message"
        elif isinstance(event, CallbackQuery):
            event_type = "callback"
            metadata["data"] = event.data
        
        if event_type and db_user:
            db = get_database()
            await db.log_event(
                user_id=db_user.id,
                event_type=event_type,
                metadata=metadata
            )
        
        return await handler(event, data)

