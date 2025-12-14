"""Telegram Bot Middlewares"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from core.services.database import get_database
from core.i18n import detect_language


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for user authentication and ban check.
    Creates user if not exists, blocks banned users.
    """
    
    async def _update_user_photo(self, db, telegram_id: int, data: Dict[str, Any]) -> None:
        """Fetch and save user's profile photo from Telegram."""
        try:
            bot = data.get("bot")
            if bot:
                photos = await bot.get_user_profile_photos(user_id=telegram_id, limit=1)
                if photos.total_count > 0 and photos.photos:
                    photo_sizes = photos.photos[0]
                    if photo_sizes:
                        largest_photo = photo_sizes[-1]  # Last is largest
                        file = await bot.get_file(largest_photo.file_id)
                        if file.file_path:
                            photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                            await db.update_user_photo(telegram_id, photo_url)
        except Exception:
            # Photo fetching is non-critical, continue without it
            pass
    
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
            
            # Fetch and save user's profile photo for new users
            await self._update_user_photo(db, user.id, data)
        else:
            # For existing users, update photo if they don't have one
            # OR refresh every 6 hours to capture avatar updates
            should_refresh = False
            
            if not getattr(db_user, 'photo_url', None):
                should_refresh = True
            else:
                # Check if photo_url is an old Telegram file link (they expire)
                photo_url = getattr(db_user, 'photo_url', '') or ''
                if 'api.telegram.org/file/' in photo_url:
                    # Telegram file links can expire, refresh periodically
                    # Check last_activity - if > 6 hours since last photo update
                    from datetime import datetime, timezone, timedelta
                    last_update = getattr(db_user, 'last_activity_at', None)
                    if last_update:
                        try:
                            if isinstance(last_update, str):
                                from dateutil.parser import isoparse
                                last_update = isoparse(last_update)
                            age = datetime.now(timezone.utc) - last_update
                            if age > timedelta(hours=6):
                                should_refresh = True
                        except Exception:
                            pass
            
            if should_refresh:
                await self._update_user_photo(db, user.id, data)
        
        # Check if banned
        if db_user.is_banned:
            if isinstance(event, Message):
                from core.i18n import get_text
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

