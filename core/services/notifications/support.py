"""
Support Notifications

Notifications for support tickets and customer service.
"""

import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from core.logging import get_logger

from .base import NotificationServiceBase, _msg, get_user_language

logger = get_logger(__name__)


class SupportNotificationsMixin(NotificationServiceBase):
    """Mixin for support-related notifications."""

    async def send_ticket_approved_notification(
        self, telegram_id: int, ticket_id: str, issue_type: str, language: str = "en"
    ) -> None:
        """Send notification when ticket is approved"""
        lang = await get_user_language(telegram_id)
        short_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id

        if issue_type == "replacement":
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Решение:</b> Замена\n"
                f"◈ <b>Статус:</b> В обработке\n\n"
                f"<i>Новый аккаунт придёт в течение 24ч</i>",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Resolution:</b> Replacement\n"
                f"◈ <b>Status:</b> Processing\n\n"
                f"<i>New account will arrive within 24h</i>",
            )
        elif issue_type == "refund":
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Решение:</b> Возврат средств\n"
                f"◈ <b>Статус:</b> Зачислено на баланс ✓",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Resolution:</b> Refund\n"
                f"◈ <b>Status:</b> Credited to balance ✓",
            )
        else:
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"Ваш запрос принят в обработку.",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"Your request is being processed.",
            )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent approval notification to {telegram_id} for ticket {ticket_id}")
        except Exception:
            logger.exception(f"Failed to send approval notification to {telegram_id}")

    async def send_ticket_rejected_notification(
        self, telegram_id: int, ticket_id: str, reason: str, language: str = "en"
    ) -> None:
        """Send notification when ticket is rejected"""
        lang = await get_user_language(telegram_id)
        short_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      ✗ <b>ТИКЕТ ОТКЛОНЁН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<i>#{short_id}</i>\n\n"
            f"К сожалению, запрос не может быть выполнен.\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Есть вопросы? Напишите в поддержку.",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      ✗ <b>TICKET REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<i>#{short_id}</i>\n\n"
            f"Unfortunately, your request cannot be fulfilled.\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Questions? Contact support.",
        )

        button_text = "🆘 Поддержка" if lang == "ru" else "🆘 Support"

        # Create keyboard with support button
        webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button_text, web_app=WebAppInfo(url=f"{webapp_url}/support")
                    )
                ]
            ]
        )

        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard

            await send_telegram_message_with_keyboard(
                chat_id=telegram_id, text=message, keyboard=keyboard, parse_mode="HTML"
            )
            logger.info(f"Sent rejection notification to {telegram_id} for ticket {ticket_id}")
        except Exception:
            logger.exception(f"Failed to send rejection notification to {telegram_id}")
