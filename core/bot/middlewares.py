"""Telegram Bot Middlewares"""

import os
from collections.abc import Awaitable, Callable
from datetime import UTC
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

from core.i18n import detect_language
from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

# Required channel for subscription check (set via env var)
REQUIRED_CHANNEL = os.environ.get("PVNDORA_REQUIRED_CHANNEL", "@pvndora_news")


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for user authentication and ban check.
    Creates user if not exists, blocks banned users.
    """

    async def _should_refresh_photo(self, db_user) -> bool:
        """Check if user photo should be refreshed (reduces cognitive complexity)."""
        # No photo - need to fetch
        if not getattr(db_user, "photo_url", None):
            return True

        # Check if photo_url is an old Telegram file link (they expire)
        photo_url = getattr(db_user, "photo_url", "") or ""
        if "api.telegram.org/file/" not in photo_url:
            return False

        # Telegram file links can expire, refresh periodically
        # Check last_activity - if > 6 hours since last photo update
        from datetime import datetime, timedelta

        last_update = getattr(db_user, "last_activity_at", None)
        if not last_update:
            return False

        try:
            if isinstance(last_update, str):
                # Use built-in fromisoformat (Python 3.7+) instead of dateutil
                # Handle 'Z' suffix (UTC) - convert to +00:00 format
                iso_str = (
                    last_update.replace("Z", "+00:00") if last_update.endswith("Z") else last_update
                )
                last_update = datetime.fromisoformat(iso_str)
                # Ensure timezone-aware
                if last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=UTC)
            age = datetime.now(UTC) - last_update
            return age > timedelta(hours=6)
        except Exception:
            return False

    async def _update_user_photo(self, db, telegram_id: int, data: dict[str, Any]) -> None:
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
                            photo_url = (
                                f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                            )
                            await db.update_user_photo(telegram_id, photo_url)
        except Exception:
            # Photo fetching is non-critical, continue without it
            pass

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Get user from event
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if not user:
            return await handler(event, data)

        db = get_database()

        # Get or create user
        db_user = await db.get_user_by_telegram_id(user.id)

        if db_user is None:
            # Check for referrer in start command
            referrer_id = None
            if isinstance(event, Message) and event.text and event.text.startswith("/start ref_"):
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
                referrer_telegram_id=referrer_id,
            )

            # Fetch and save user's profile photo for new users
            await self._update_user_photo(db, user.id, data)
        # For existing users, update photo if needed
        elif await self._should_refresh_photo(db_user):
            await self._update_user_photo(db, user.id, data)

        # Check if banned
        if db_user.is_banned:
            if isinstance(event, Message):
                from core.i18n import get_text

                await event.answer(get_text("banned", db_user.language_code))
            return None  # Stop processing

        # Add user to data for handlers
        data["db_user"] = db_user

        return await handler(event, data)


class ChannelSubscriptionMiddleware(BaseMiddleware):
    """
    Require channel subscription before using the bot.
    This helps with retention and protects against bans.
    """

    # Commands that don't require subscription
    EXEMPT_COMMANDS = {"/start", "/help"}
    EXEMPT_CALLBACKS = {"pvndora:check_sub"}

    def _is_exempt(self, event: TelegramObject) -> bool:
        """Check if event is exempt from subscription check (reduces cognitive complexity)."""
        return (
            isinstance(event, Message)
            and event.text
            and any(event.text.startswith(cmd) for cmd in self.EXEMPT_COMMANDS)
        ) or (
            isinstance(event, CallbackQuery)
            and event.data
            and any(cb in event.data for cb in self.EXEMPT_CALLBACKS)
        )

    def _get_subscription_text(self, lang: str) -> str:
        """Get subscription required text (reduces cognitive complexity)."""
        if lang == "ru":
            return (
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     📢 <b>ТРЕБУЕТСЯ ПОДПИСКА</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Для доступа к боту подпишитесь\n"
                f"на наш канал {REQUIRED_CHANNEL}\n\n"
                f"<i>После подписки нажмите кнопку ниже</i>"
            )
        return (
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     📢 <b>SUBSCRIPTION REQUIRED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Please subscribe to our channel\n"
            f"{REQUIRED_CHANNEL} to use this bot.\n\n"
            f"<i>After subscribing, click the button below</i>"
        )

    async def _show_subscription_prompt(self, event: TelegramObject, lang: str):
        """Show subscription prompt (reduces cognitive complexity)."""
        text = self._get_subscription_text(lang)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 Подписаться" if lang == "ru" else "📢 Subscribe",
                        url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ Я подписался" if lang == "ru" else "✅ I subscribed",
                        callback_data="pvndora:check_sub",
                    )
                ],
            ]
        )

        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
        elif isinstance(event, CallbackQuery):
            alert_text = "Подпишитесь на канал!" if lang == "ru" else "Subscribe first!"
            await event.answer(alert_text, show_alert=True)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if self._is_exempt(event):
            return await handler(event, data)

        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if not user:
            return await handler(event, data)

        bot: Bot = data.get("bot")
        if not bot or not REQUIRED_CHANNEL:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user.id)

            if member.status in ("left", "kicked"):
                db_user = data.get("db_user")
                lang = db_user.language_code if db_user else "en"
                await self._show_subscription_prompt(event, lang)
                return None

        except Exception as e:
            logger.warning("Failed to check channel subscription: %s", e)

        return await handler(event, data)


class LanguageMiddleware(BaseMiddleware):
    """
    Middleware for language detection and update.
    Updates user language if it changed in Telegram settings.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
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
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
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
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
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
            await db.log_event(user_id=db_user.id, event_type=event_type, metadata=metadata)

        return await handler(event, data)
