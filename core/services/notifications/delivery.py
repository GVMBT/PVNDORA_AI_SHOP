"""Delivery Notifications.

Notifications for order delivery and credentials.
"""

import os
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from core.i18n import get_text
from core.logging import get_logger

from .base import NotificationServiceBase, _msg, get_user_language

logger = get_logger(__name__)


class DeliveryNotificationsMixin(NotificationServiceBase):
    """Mixin for delivery-related notifications."""

    async def _send_credentials(
        self,
        telegram_id: int,
        credentials: str,
        instructions: str | None,
        expires_at: datetime | None,
        order_id: str,
        language: str,
    ) -> None:
        """Send credentials to user via Telegram."""
        # Format expiration
        expires_str = "N/A"
        if expires_at:
            expires_str = expires_at.strftime("%d.%m.%Y %H:%M UTC")

        # Build message
        message = get_text(
            "order_success",
            language,
            credentials=f"<code>{credentials}</code>",
            instructions=(
                instructions or get_text("no_instructions", language)
                if hasattr(get_text, "no_instructions")
                else "See product documentation"
            ),
            expires=expires_str,
        )

        # Add order keyboard
        from core.bot.keyboards import get_order_keyboard

        keyboard = get_order_keyboard(language, order_id)

        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard

            await send_telegram_message_with_keyboard(
                chat_id=telegram_id, text=message, keyboard=keyboard, parse_mode="HTML",
            )
        except Exception:
            logger.exception(f"Failed to send credentials to {telegram_id}")

    async def send_replacement_notification(
        self,
        telegram_id: int,
        product_name: str,
        item_id: str,
        credentials: str | None = None,
    ) -> None:
        """Send notification about account replacement with credentials."""
        lang = await get_user_language(telegram_id)
        short_id = item_id[:8] if len(item_id) > 8 else item_id

        # Format credentials section
        creds_section_ru = ""
        creds_section_en = ""
        if credentials:
            creds_section_ru = f"◈ <b>Новые данные:</b>\n<code>{credentials}</code>\n\n"
            creds_section_en = f"◈ <b>New credentials:</b>\n<code>{credentials}</code>\n\n"

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     🔄 <b>ЗАМЕНА ВЫПОЛНЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Товар:</b> {product_name}\n"
            f"◈ <b>ID:</b> <code>{short_id}</code>\n\n"
            f"{creds_section_ru}"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Посмотреть → «Мои заказы»</i>",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     🔄 <b>REPLACEMENT DONE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Product:</b> {product_name}\n"
            f"◈ <b>ID:</b> <code>{short_id}</code>\n\n"
            f"{creds_section_en}"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>View → «My Orders»</i>",
        )

        # Add WebApp button
        webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Мои заказы" if lang == "ru" else "📦 My Orders",
                        web_app=WebAppInfo(url=f"{webapp_url}/orders"),
                    ),
                ],
            ],
        )

        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard

            await send_telegram_message_with_keyboard(
                chat_id=telegram_id, text=message, keyboard=keyboard, parse_mode="HTML",
            )
            logger.info(f"Sent replacement notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send replacement notification to {telegram_id}")

    def _format_expires_info(self, expires_at: datetime | None, lang: str) -> str:
        """Format expiration info (reduces cognitive complexity)."""
        from .base import _msg

        if not expires_at:
            return ""
        expires_str = expires_at.strftime("%d.%m.%Y")
        return _msg(
            lang,
            f"\n◈ <b>Активен до:</b> {expires_str}",
            f"\n◈ <b>Valid until:</b> {expires_str}",
        )

    def _format_order_ref(self, order_id: str | None, lang: str) -> str:
        """Format order reference (reduces cognitive complexity)."""
        from .base import _msg

        if not order_id:
            return ""
        short_id = order_id[:8]
        return _msg(lang, f"<i>#{short_id}</i>\n\n", f"<i>#{short_id}</i>\n\n")

    def _format_content_items(self, content: str) -> str:
        """Format content items with product names and credentials (reduces cognitive complexity)."""
        if not content:
            return ""

        items = content.split("\n\n")
        formatted_items = []

        for item in items:
            if ":\n" in item:
                parts = item.split(":\n", 1)
                if len(parts) == 2:
                    product_name = parts[0].strip()
                    credentials = parts[1].strip()
                    formatted_items.append(f"<b>{product_name}:</b>\n<code>{credentials}</code>")
                else:
                    formatted_items.append(f"<code>{item}</code>")
            else:
                formatted_items.append(f"<code>{item}</code>")

        return "\n\n".join(formatted_items)

    async def send_delivery(
        self,
        telegram_id: int,
        _product_name: str,  # Kept for API compatibility
        content: str,
        expires_at: datetime | None = None,
        order_id: str | None = None,
    ) -> None:
        """Send delivery notification with product credentials."""
        from .base import _msg, get_user_language

        lang = await get_user_language(telegram_id)

        expires_info = self._format_expires_info(expires_at, lang)
        order_ref = self._format_order_ref(order_id, lang)
        formatted_content = self._format_content_items(content)

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      💎 <b>ДОСТАВКА ЗАВЕРШЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"{order_ref}"
            f"🔐 <b>ДАННЫЕ ДОСТУПА</b>\n"
            f"{formatted_content}{expires_info}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Инструкции и детали — в разделе «Мои заказы»</i>\n\n"
            f"⭐ Оставьте отзыв → получите <b>5% кэшбэк</b>",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      💎 <b>DELIVERY COMPLETE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"{order_ref}"
            f"🔐 <b>ACCESS CREDENTIALS</b>\n"
            f"{formatted_content}{expires_info}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Instructions & details — in «My Orders»</i>\n\n"
            f"⭐ Leave a review → get <b>5% cashback</b>",
        )

        # Add WebApp button for viewing order
        keyboard = None
        if order_id:
            webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📦 Мои заказы" if lang == "ru" else "📦 My Orders",
                            web_app=WebAppInfo(url=f"{webapp_url}/orders"),
                        ),
                    ],
                ],
            )

        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard

            if keyboard:
                await send_telegram_message_with_keyboard(
                    chat_id=telegram_id, text=message, keyboard=keyboard, parse_mode="HTML",
                )
            else:
                from core.services.telegram_messaging import send_telegram_message

                await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
        except Exception:
            logger.exception("Failed to send delivery notification")
