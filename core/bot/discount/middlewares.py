"""Discount bot middlewares.

- DiscountAuthMiddleware: User auth with discount_tier_source tracking
- ChannelSubscriptionMiddleware: Require channel subscription
- TermsAcceptanceMiddleware: Require terms acceptance before use
"""

import os
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.i18n import detect_language
from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

# Required channel for subscription check
REQUIRED_CHANNEL = os.environ.get("DISCOUNT_REQUIRED_CHANNEL", "@pvndora_news")


class DiscountAuthMiddleware(BaseMiddleware):
    """
    Auth middleware for discount bot.
    Creates user with discount_tier_source=True if new.
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

        if not user:
            return await handler(event, data)

        db = get_database()

        # Get or create user
        db_user = await db.get_user_by_telegram_id(user.id)

        if db_user is None:
            # Create new user with discount_tier_source=True
            db_user = await db.create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language_code=detect_language(user.language_code),
            )

            # Mark as discount tier origin
            try:
                await db.client.table("users").update({"discount_tier_source": True}).eq(
                    "id", db_user.id
                ).execute()
            except Exception:
                logger.exception("Failed to mark discount_tier_source")
        else:
            # Update language if changed in Telegram
            new_lang = detect_language(user.language_code)
            if new_lang != db_user.language_code:
                try:
                    await db.update_user_language(user.id, new_lang)
                    db_user.language_code = new_lang
                except Exception as e:
                    logger.warning(f"Failed to update user language: {e}")

        # Check if banned
        if db_user.is_banned:
            if isinstance(event, Message):
                from core.i18n import get_text

                await event.answer(get_text("banned", db_user.language_code))
            return None

        data["db_user"] = db_user

        return await handler(event, data)


class ChannelSubscriptionMiddleware(BaseMiddleware):
    """
    Require channel subscription before using the bot.
    This protects against ban - channel is harder to take down.
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

        if not user:
            return await handler(event, data)

        # Skip for callback checking subscription
        if isinstance(event, CallbackQuery) and event.data and "check_sub" in event.data:
            return await handler(event, data)

        bot: Bot = data.get("bot")
        if not bot or not REQUIRED_CHANNEL:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user.id)

            if member.status in ("left", "kicked"):
                # Not subscribed - show subscription required message
                db_user = data.get("db_user")
                lang = db_user.language_code if db_user else "en"

                text = (
                    (
                        f"📢 Для использования бота подпишитесь на канал {REQUIRED_CHANNEL}\n\n"
                        f"После подписки нажмите кнопку ниже."
                    )
                    if lang == "ru"
                    else (
                        f"📢 Please subscribe to {REQUIRED_CHANNEL} to use this bot.\n\n"
                        f"After subscribing, click the button below."
                    )
                )

                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
                                callback_data="discount:check_sub",
                            )
                        ],
                    ]
                )

                if isinstance(event, Message):
                    await event.answer(text, reply_markup=keyboard)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Подпишитесь на канал!" if lang == "ru" else "Subscribe first!",
                        show_alert=True,
                    )

                return None  # Stop processing

        except Exception as e:
            logger.warning(f"Failed to check channel subscription: {e}")
            # Continue anyway on error

        return await handler(event, data)


class TermsAcceptanceMiddleware(BaseMiddleware):
    """
    Require terms acceptance before first use.
    """

    # Commands that don't require terms acceptance
    EXEMPT_COMMANDS = {"/start", "/terms"}
    EXEMPT_CALLBACKS = {"discount:terms:read", "discount:terms:accept", "discount:check_sub"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Check exemptions
        if isinstance(event, Message):
            if event.text and any(event.text.startswith(cmd) for cmd in self.EXEMPT_COMMANDS):
                return await handler(event, data)
        elif (
            isinstance(event, CallbackQuery)
            and event.data
            and any(cb in event.data for cb in self.EXEMPT_CALLBACKS)
        ):
            return await handler(event, data)

        db_user = data.get("db_user")
        if not db_user:
            return await handler(event, data)

        # Check if terms accepted
        db = get_database()

        try:
            result = (
                await db.client.table("users")
                .select("terms_accepted")
                .eq("id", db_user.id)
                .single()
                .execute()
            )

            terms_accepted = result.data.get("terms_accepted", False) if result.data else False

            if not terms_accepted:
                # Show terms acceptance prompt
                lang = db_user.language_code

                text = (
                    (
                        "📜 <b>Условия использования</b>\n\n"
                        "Перед использованием бота необходимо принять условия:\n\n"
                        "• Мы предоставляем доступ к ознакомительным версиям сервисов\n"
                        "• Замены доступны только при наличии страховки\n"
                        "• Мы не несем ответственности за использование аккаунтов\n"
                        "• Доставка в течение 1-4 часов после оплаты\n\n"
                        "Нажмите кнопку ниже, чтобы принять условия."
                    )
                    if lang == "ru"
                    else (
                        "📜 <b>Terms of Service</b>\n\n"
                        "Before using the bot, please accept the terms:\n\n"
                        "• We provide access to trial versions of services\n"
                        "• Replacements available only with insurance\n"
                        "• We are not responsible for account usage\n"
                        "• Delivery within 1-4 hours after payment\n\n"
                        "Click the button below to accept."
                    )
                )

                from .keyboards import get_terms_keyboard

                if isinstance(event, Message):
                    await event.answer(
                        text, reply_markup=get_terms_keyboard(lang), parse_mode="HTML"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Примите условия использования!" if lang == "ru" else "Accept terms first!",
                        show_alert=True,
                    )

                return None  # Stop processing

        except Exception:
            logger.exception("Failed to check terms acceptance")
            # Continue on error

        return await handler(event, data)
