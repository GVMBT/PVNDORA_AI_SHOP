"""Withdrawal Notifications.

Notifications for withdrawal-related events.
"""

from core.logging import get_logger

from .base import NotificationServiceBase, _msg, get_user_language

logger = get_logger(__name__)


class WithdrawalNotificationsMixin(NotificationServiceBase):
    """Mixin for withdrawal-related notifications."""

    async def send_withdrawal_approved_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        method: str,
    ) -> None:
        """Notify user that their withdrawal request was approved."""
        lang = await get_user_language(telegram_id)

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✓ <b>ВЫВОД ОДОБРЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> {amount:.2f} {currency}\n"
            f"◈ <b>Метод:</b> {method}\n"
            f"◈ <b>Статус:</b> Ожидает отправки\n\n"
            f"<i>Средства поступят в течение 24ч</i>",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✓ <b>WITHDRAWAL APPROVED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> {amount:.2f} {currency}\n"
            f"◈ <b>Method:</b> {method}\n"
            f"◈ <b>Status:</b> Pending send\n\n"
            f"<i>Funds will arrive within 24h</i>",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal approved notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send withdrawal approved notification to {telegram_id}")

    async def send_withdrawal_rejected_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        reason: str,
    ) -> None:
        """Notify user that their withdrawal request was rejected."""
        lang = await get_user_language(telegram_id)

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>ВЫВОД ОТКЛОНЁН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> {amount:.2f} {currency}\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Средства возвращены на баланс ✓",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>WITHDRAWAL REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> {amount:.2f} {currency}\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Funds returned to balance ✓",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal rejected notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send withdrawal rejected notification to {telegram_id}")

    async def send_withdrawal_completed_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        method: str,
    ) -> None:
        """Notify user that their withdrawal has been completed."""
        lang = await get_user_language(telegram_id)

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>ВЫВОД ВЫПОЛНЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> {amount:.2f} {currency}\n"
            f"◈ <b>Метод:</b> {method}\n"
            f"◈ <b>Статус:</b> Отправлено ✓\n\n"
            f"<i>Спасибо за использование PVNDORA</i>",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>WITHDRAWAL COMPLETE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> {amount:.2f} {currency}\n"
            f"◈ <b>Method:</b> {method}\n"
            f"◈ <b>Status:</b> Sent ✓\n\n"
            f"<i>Thank you for using PVNDORA</i>",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal completed notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send withdrawal completed notification to {telegram_id}")
