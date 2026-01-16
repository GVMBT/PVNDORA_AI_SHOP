"""Admin Alert Service - Notifications to administrators via Telegram bot.

Sends alerts for critical business events:
- New paid orders
- Low stock warnings
- Payment failures
- Withdrawal requests
- Support tickets
- Partner applications

All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import os
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)


class AlertSeverity:
    """Alert severity levels."""

    INFO = "info"  # Blue - informational
    WARNING = "warning"  # Yellow - attention needed
    ERROR = "error"  # Red - immediate action
    CRITICAL = "critical"  # Red with siren - urgent


# Alert icons by severity
SEVERITY_ICONS = {
    AlertSeverity.INFO: "ℹ️",
    AlertSeverity.WARNING: "⚠️",
    AlertSeverity.ERROR: "🔴",
    AlertSeverity.CRITICAL: "🚨",
}


class AdminAlertService:
    """Service for sending alerts to admin Telegram accounts."""

    def __init__(self) -> None:
        self.bot_token = os.environ.get("TELEGRAM_TOKEN", "")
        self._bot: Bot | None = None
        self._admin_ids: list[int] | None = None

    def _get_bot(self) -> Bot | None:
        """Get or create bot instance."""
        if self._bot is None and self.bot_token:
            self._bot = Bot(
                token=self.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
        return self._bot

    async def _get_admin_ids(self) -> list[int]:
        """Get list of admin Telegram IDs from database."""
        if self._admin_ids is not None:
            return self._admin_ids

        db = get_database()
        try:
            result = (
                await db.client.table("users")
                .select("telegram_id")
                .eq("is_admin", True)
                .eq("is_banned", False)
                .execute()
            )
            self._admin_ids = [
                u["telegram_id"]
                for u in result.data
                if isinstance(u, dict) and u.get("telegram_id") is not None
            ]
            return self._admin_ids
        except Exception:
            logger.exception("Failed to fetch admin IDs")
            # Fallback to env var if available
            admin_ids_str = os.environ.get("ADMIN_TELEGRAM_IDS", "")
            if admin_ids_str:
                self._admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
            else:
                self._admin_ids = []
            return self._admin_ids

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = AlertSeverity.INFO,
        metadata: dict | None = None,
    ) -> int:
        """Send alert to all admin users.

        Args:
            title: Alert title
            message: Alert message body
            severity: Alert severity level
            metadata: Optional additional data to include

        Returns:
            Number of admins notified

        """
        admin_ids = await self._get_admin_ids()
        if not admin_ids:
            logger.warning("No admin IDs configured, cannot send alert")
            return 0

        icon = SEVERITY_ICONS.get(severity, "📢")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        local_time = datetime.now(UTC).strftime("%H:%M")

        # Build structured alert message
        text = f"{icon} <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n{message}\n"

        if metadata:
            text += "\n<b>Детали:</b>\n"
            for k, v in metadata.items():
                text += f"• <code>{k}</code>: {v}\n"

        text += f"\n<i>⏰ {timestamp} ({local_time})</i>"

        sent_count = 0
        from core.services.telegram_messaging import send_telegram_message

        for admin_id in admin_ids:
            try:
                # Note: disable_notification not supported in telegram_messaging yet
                # Can be added if needed
                success = await send_telegram_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML",
                )
                if success:
                    sent_count += 1
            except Exception:
                logger.exception(f"Failed to send alert to admin {admin_id}")

        return sent_count

    # ==================== PREDEFINED ALERTS ====================

    async def alert_new_order(
        self,
        order_id: str,
        amount: float,
        currency: str,
        user_telegram_id: int,
        username: str | None,
        product_name: str,
        quantity: int = 1,
    ) -> int:
        """Alert admins about new paid order."""
        user_display = f"@{username}" if username else f"ID: {user_telegram_id}"

        return await self.send_alert(
            title="💰 Новый заказ оплачен",
            message=(
                f"<b>Товар:</b> {product_name}\n"
                f"<b>Количество:</b> {quantity}\n"
                f"<b>Сумма:</b> {amount:.2f} {currency}\n"
                f"<b>Покупатель:</b> {user_display}"
            ),
            severity=AlertSeverity.INFO,
            metadata={"order_id": order_id[:8]},
        )

    async def alert_low_stock(
        self,
        product_name: str,
        product_id: str,
        current_stock: int,
        threshold: int = 5,
    ) -> int:
        """Alert admins about low stock."""
        severity = AlertSeverity.WARNING if current_stock > 0 else AlertSeverity.ERROR
        status_icon = "🔴" if current_stock == 0 else "⚠️"
        status_text = "Товар закончился!" if current_stock == 0 else "Низкий запас"

        return await self.send_alert(
            title=f"{status_icon} {status_text}",
            message=(
                f"<b>Товар:</b> {product_name}\n"
                f"<b>Остаток:</b> <b>{current_stock}</b> шт.\n"
                f"<b>Порог:</b> {threshold} шт."
            ),
            severity=severity,
            metadata={"product_id": product_id[:8]},
        )

    async def alert_payment_failure(
        self,
        order_id: str,
        error: str,
        amount: float,
        gateway: str,
    ) -> int:
        """Alert admins about payment processing failure."""
        return await self.send_alert(
            title="🔴 Ошибка оплаты",
            message=(
                f"<b>Сумма:</b> ${amount:.2f}\n"
                f"<b>Шлюз:</b> {gateway}\n"
                f"<b>Ошибка:</b> <code>{error[:200]}</code>"
            ),
            severity=AlertSeverity.ERROR,
            metadata={"order_id": order_id[:8]},
        )

    async def alert_withdrawal_request(
        self,
        user_telegram_id: int,
        username: str | None,
        amount: float,
        method: str,
        request_id: str,
        user_balance: float | None = None,
    ) -> int:
        """Alert admins about new withdrawal request.

        Note: amount is in USDT (for TRC20 withdrawals).
        """
        user_display = f"@{username}" if username else f"ID: {user_telegram_id}"

        message = (
            f"<b>Сумма:</b> {amount:.2f} USDT\n"
            f"<b>Метод:</b> {method}\n"
            f"<b>Пользователь:</b> {user_display}"
        )

        if user_balance is not None:
            message += f"\n<b>Баланс:</b> ${user_balance:.2f}"

        return await self.send_alert(
            title="💸 Запрос на вывод средств",
            message=message,
            severity=AlertSeverity.WARNING,
            metadata={"request_id": request_id[:8], "user_id": str(user_telegram_id)},
        )

    async def alert_new_partner_application(
        self,
        user_telegram_id: int,
        username: str | None,
        source: str,
        audience_size: str,
    ) -> int:
        """Alert admins about new partner application."""
        user_display = f"@{username}" if username else f"ID: {user_telegram_id}"

        return await self.send_alert(
            title="🏆 Заявка на партнёрство",
            message=(
                f"<b>Пользователь:</b> {user_display}\n"
                f"<b>Источник:</b> {source}\n"
                f"<b>Аудитория:</b> {audience_size}"
            ),
            severity=AlertSeverity.INFO,
            metadata={"user_id": str(user_telegram_id)},
        )

    async def alert_support_ticket(
        self,
        ticket_id: str,
        user_telegram_id: int,
        issue_type: str,
        order_id: str | None = None,
    ) -> int:
        """Alert admins about new support ticket."""
        metadata = {"ticket_id": ticket_id[:8]}
        if order_id:
            metadata["order_id"] = order_id[:8]

        return await self.send_alert(
            title="🎫 Новый тикет поддержки",
            message=(
                f"<b>Тип:</b> {issue_type}\n<b>Пользователь:</b> <code>{user_telegram_id}</code>"
            ),
            severity=AlertSeverity.INFO,
            metadata=metadata,
        )


# Singleton instance
_alert_service: AdminAlertService | None = None


def get_admin_alert_service() -> AdminAlertService:
    """Get singleton AdminAlertService instance."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AdminAlertService()
    return _alert_service


# Convenience functions for quick alerts
async def alert_admins(
    title: str,
    message: str,
    severity: str = AlertSeverity.INFO,
    metadata: dict | None = None,
) -> int:
    """Quick function to send alert to admins."""
    service = get_admin_alert_service()
    return await service.send_alert(title, message, severity, metadata)
