"""Miscellaneous Notifications.

Notifications for broadcast, waitlist, partner applications, etc.
"""

from core.i18n import get_text
from core.logging import get_logger
from core.services.database import get_database

from .base import NotificationServiceBase, _msg, get_user_language

logger = get_logger(__name__)


class MiscNotificationsMixin(NotificationServiceBase):
    """Mixin for miscellaneous notifications."""

    async def send_waitlist_notification(
        self,
        telegram_id: int,
        product_name: str,
        language: str,
        _product_id: str | None = None,
        in_stock: bool = False,
    ) -> None:
        """Notify user that waitlisted product is available again.

        Args:
            telegram_id: User's Telegram ID
            product_name: Name of the product
            language: User's language code
            product_id: Product ID (optional, for creating order link)
            in_stock: Whether product is currently in stock

        """
        # Build message based on stock status
        if in_stock:
            # Product is available immediately
            message = get_text("waitlist_notify_in_stock", language, product=product_name)
        else:
            # Product is active but out of stock - can order prepaid
            message = get_text("waitlist_notify_prepaid", language, product=product_name)

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode=None)
        except Exception:
            logger.exception("Failed to send waitlist notification")

    async def send_broadcast(self, message: str, exclude_dnd: bool = True) -> int:
        """Send broadcast message to all users.

        Args:
            message: Message text
            exclude_dnd: Exclude users with do_not_disturb=True

        Returns:
            Number of successfully sent messages

        """
        db = get_database()

        # Get users
        query = db.client.table("users").select("telegram_id").eq("is_banned", False)
        if exclude_dnd:
            query = query.eq("do_not_disturb", False)

        result = await query.execute()

        sent_count = 0
        from core.services.telegram_messaging import send_telegram_message

        for user in result.data:
            try:
                success = await send_telegram_message(
                    chat_id=user["telegram_id"],
                    text=message,
                    parse_mode=None,
                )
                if success:
                    sent_count += 1
            except Exception:
                logger.exception(f"Failed to send broadcast to {user['telegram_id']}")

        return sent_count

    async def send_partner_application_approved_notification(self, telegram_id: int) -> None:
        """Notify user that their partner application was approved."""
        lang = await get_user_language(telegram_id)

        message = _msg(
            lang,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "    🏆 <b>VIP-ПАРТНЁР PVNDORA</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Поздравляем! Ваша заявка одобрена.\n\n"
            "<b>Теперь вам доступны:</b>\n"
            "▸ Повышенные комиссии\n"
            "▸ Персональный менеджер\n"
            "▸ Приоритетная поддержка\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Добро пожаловать в команду</i> 💎",
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "    🏆 <b>PVNDORA VIP PARTNER</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Congratulations! Your application was approved.\n\n"
            "<b>You now have access to:</b>\n"
            "▸ Increased commissions\n"
            "▸ Personal manager\n"
            "▸ Priority support\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Welcome to the team</i> 💎",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent partner approved notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send partner approved notification to {telegram_id}")

    async def send_partner_application_rejected_notification(
        self,
        telegram_id: int,
        reason: str | None = None,
    ) -> None:
        """Notify user that their partner application was rejected."""
        lang = await get_user_language(telegram_id)

        reason_text_ru = reason or "Заявка не соответствует требованиям программы."
        reason_text_en = reason or "Application does not meet program requirements."

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason_text_ru}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Подайте повторно позже или\n"
            f"напишите в поддержку.",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>APPLICATION REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason_text_en}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Reapply later or contact\n"
            f"support for details.",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent partner rejected notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send partner rejected notification to {telegram_id}")

    async def send_partner_status_revoked_notification(
        self,
        telegram_id: int,
        reason: str | None = None,
    ) -> None:
        """Notify user that their VIP partner status has been revoked."""
        lang = await get_user_language(telegram_id)

        reason_text_ru = reason or "VIP статус был отозван администратором."
        reason_text_en = reason or "VIP status has been revoked by administrator."

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ⚠️ <b>VIP СТАТУС ОТОЗВАН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason_text_ru}</i>\n\n"
            f"Ваши заработанные средства сохранены.\n"
            f"Уровни реферальной программы остаются\n"
            f"в соответствии с достигнутым оборотом.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"По вопросам обращайтесь в поддержку.",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ⚠️ <b>VIP STATUS REVOKED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason_text_en}</i>\n\n"
            f"Your earned funds are preserved.\n"
            f"Referral program levels remain\n"
            f"according to achieved turnover.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"For questions, contact support.",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent partner status revoked notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send partner status revoked notification to {telegram_id}")

    async def send_system_notification(self, telegram_id: int, message: str) -> None:
        """Send a generic system notification to user."""
        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent system notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send system notification to {telegram_id}")
