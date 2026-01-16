"""Payment Notifications.

Notifications for payment-related events (cashback, refund, topup).
"""

from typing import Any

from core.i18n import get_text
from core.logging import get_logger
from core.services.database import get_database

from .base import NotificationServiceBase, _msg, get_user_language

logger = get_logger(__name__)


class PaymentNotificationsMixin(NotificationServiceBase):
    """Mixin for payment-related notifications."""

    async def _refund_to_balance(
        self, order: Any, user: dict[str, Any], language: str, reason: str
    ) -> None:
        """Refund order amount to user balance."""
        db = get_database()

        # Credit to balance
        await db.update_user_balance(order.user_id, order.amount)

        # Update order status
        await db.update_order_status(order.id, "refunded")

        # Notify user
        message = get_text("error_payment", language)
        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=user["telegram_id"], text=message, parse_mode=None)
        except Exception:
            logger.exception("Failed to send refund notification")

        logger.info(f"Refunded order {order.id} to balance: {reason}")

    async def send_cashback_notification(
        self,
        telegram_id: int,
        cashback_amount: float,
        new_balance: float,
        currency: str = "USD",
        reason: str = "review",
    ) -> None:
        """Send notification about cashback credit.

        Args:
            telegram_id: User's Telegram ID
            cashback_amount: Cashback amount in user's balance_currency
            new_balance: New balance in user's balance_currency
            currency: User's balance currency (RUB, USD, etc.) - CRITICAL!
            reason: Reason for cashback (review, etc.)

        """
        lang = await get_user_language(telegram_id)

        # Format amounts with correct currency symbol
        from core.services.currency import CURRENCY_SYMBOLS

        # Format cashback amount
        if currency in ["RUB", "UAH", "TRY", "INR"]:
            cashback_formatted = (
                f"{int(cashback_amount)} {CURRENCY_SYMBOLS.get(currency, currency)}"
            )
        else:
            cashback_formatted = f"{cashback_amount:.2f} {CURRENCY_SYMBOLS.get(currency, currency)}"

        # Format balance
        if currency in ["RUB", "UAH", "TRY", "INR"]:
            balance_formatted = f"{int(new_balance)} {CURRENCY_SYMBOLS.get(currency, currency)}"
        else:
            balance_formatted = f"{new_balance:.2f} {CURRENCY_SYMBOLS.get(currency, currency)}"

        if reason == "review":
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>КЭШБЕК ЗАЧИСЛЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Спасибо за ваш отзыв!\n\n"
                f"◈ <b>Начислено:</b> +{cashback_formatted}\n"
                f"◈ <b>Баланс:</b> {balance_formatted}\n\n"
                f"<i>Ваше мнение помогает другим оперативникам</i> ✓",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>CASHBACK CREDITED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Thank you for your review!\n\n"
                f"◈ <b>Credited:</b> +{cashback_formatted}\n"
                f"◈ <b>Balance:</b> {balance_formatted}\n\n"
                f"<i>Your feedback helps other operatives</i> ✓",
            )
        else:
            message = _msg(
                lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>КЭШБЕК ЗАЧИСЛЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"◈ <b>Начислено:</b> +{cashback_formatted}\n"
                f"◈ <b>Баланс:</b> {balance_formatted}",
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>CASHBACK CREDITED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"◈ <b>Credited:</b> +{cashback_formatted}\n"
                f"◈ <b>Balance:</b> {balance_formatted}",
            )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent cashback notification to {telegram_id}: {cashback_formatted}")
        except Exception:
            logger.exception("Failed to send cashback notification")

    async def send_refund_notification(
        self,
        telegram_id: int,
        product_name: str,
        amount: float,
        currency: str = "USD",
        reason: str = "Fulfillment deadline exceeded",
    ) -> None:
        """Send refund notification to user.

        Args:
            telegram_id: User's Telegram ID
            product_name: Name of the product
            amount: Refund amount in user's balance currency
            currency: User's balance currency (USD, RUB, etc.)
            reason: Reason for refund

        """
        try:
            from core.services.currency import CURRENCY_SYMBOLS

            # Format amount with correct currency symbol
            symbol = CURRENCY_SYMBOLS.get(currency, currency)
            if currency in ["RUB", "UAH", "TRY", "INR"]:
                amount_formatted = f"{int(amount)} {symbol}"
            else:
                amount_formatted = f"{amount:.2f} {symbol}"

            message = (
                f"💰 <b>Возврат средств</b>\n\n"
                f"Товар «{product_name}» не был доставлен в срок.\n\n"
                f"Сумма <b>{amount_formatted}</b> возвращена на ваш баланс.\n\n"
                f"<i>Причина: {reason}</i>\n\n"
                f"Приносим извинения за неудобства! 🙏"
            )

            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent refund notification to {telegram_id}: {amount_formatted}")
        except Exception:
            logger.exception("Failed to send refund notification")

    async def send_topup_success_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        new_balance: float,
    ) -> None:
        """Notify user that their balance was topped up."""
        lang = await get_user_language(telegram_id)

        # Format balance with correct currency (not hardcoded $)
        balance_str = (
            f"{new_balance:.2f} {currency}"
            if currency not in ["RUB", "UAH", "TRY", "INR"]
            else f"{int(new_balance)} {currency}"
        )

        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💰 <b>БАЛАНС ПОПОЛНЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Зачислено:</b> +{amount:.2f} {currency}\n"
            f"◈ <b>Баланс:</b> {balance_str}\n\n"
            f"<i>Средства доступны для покупок</i> ✓",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💰 <b>BALANCE TOPPED UP</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Credited:</b> +{amount:.2f} {currency}\n"
            f"◈ <b>Balance:</b> {balance_str}\n\n"
            f"<i>Funds available for purchases</i> ✓",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent topup success notification to {telegram_id}")
        except Exception:
            logger.exception(f"Failed to send topup success notification to {telegram_id}")
