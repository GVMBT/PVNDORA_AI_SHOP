"""
Admin Bot Middlewares

Restricts access to authorized admins only.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)


class AdminAuthMiddleware(BaseMiddleware):
    """
    Verify that the user is an admin before processing any request.
    Uses the `is_admin` field from the users table.
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
            return None  # Ignore events without user

        telegram_id = user.id

        # Check if user is admin in database
        db = get_database()
        result = (
            await db.client.table("users")
            .select("id, telegram_id, username, is_admin")
            .eq("telegram_id", telegram_id)
            .execute()
        )

        if not result.data or not result.data[0].get("is_admin"):
            # Not an admin - send rejection message
            logger.warning(f"Unauthorized admin bot access attempt from {telegram_id}")

            if isinstance(event, Message):
                await event.answer(
                    "⛔ <b>Доступ запрещён</b>\n\n"
                    "Этот бот доступен только администраторам PVNDORA.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён", show_alert=True)

            return None  # Block further processing

        # Admin verified - inject db_user into data
        data["db_user"] = result.data[0]
        data["admin_id"] = result.data[0]["id"]

        return await handler(event, data)
