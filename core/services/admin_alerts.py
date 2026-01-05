"""
Admin Alert Service - Notifications to administrators via Telegram bot.

Sends alerts for critical business events:
- New paid orders
- Low stock warnings
- Payment failures
- Withdrawal requests
- Support tickets
- Partner applications
"""

import os
import asyncio
from typing import Optional, List
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)


class AlertSeverity:
    """Alert severity levels."""
    INFO = "info"        # Blue - informational
    WARNING = "warning"  # Yellow - attention needed
    ERROR = "error"      # Red - immediate action
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
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_TOKEN", "")
        self._bot: Optional[Bot] = None
        self._admin_ids: Optional[List[int]] = None
        
    def _get_bot(self) -> Optional[Bot]:
        """Get or create bot instance."""
        if self._bot is None and self.bot_token:
            self._bot = Bot(
                token=self.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        return self._bot
    
    async def _get_admin_ids(self) -> List[int]:
        """Get list of admin Telegram IDs from database."""
        if self._admin_ids is not None:
            return self._admin_ids
            
        db = get_database()
        try:
            result = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("telegram_id")
                .eq("is_admin", True)
                .eq("is_banned", False)
                .execute()
            )
            self._admin_ids = [u["telegram_id"] for u in result.data if u.get("telegram_id")]
            return self._admin_ids
        except Exception as e:
            logger.error(f"Failed to fetch admin IDs: {e}")
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
        metadata: Optional[dict] = None
    ) -> int:
        """
        Send alert to all admin users.
        
        Args:
            title: Alert title
            message: Alert message body
            severity: Alert severity level
            metadata: Optional additional data to include
            
        Returns:
            Number of admins notified
        """
        bot = self._get_bot()
        if not bot:
            logger.warning("Bot not configured, cannot send admin alert")
            return 0
        
        admin_ids = await self._get_admin_ids()
        if not admin_ids:
            logger.warning("No admin IDs configured, cannot send alert")
            return 0
        
        icon = SEVERITY_ICONS.get(severity, "📢")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        # Build alert message
        text = (
            f"{icon} <b>{title}</b>\n\n"
            f"{message}\n\n"
        )
        
        if metadata:
            text += "<i>Metadata:</i>\n"
            for k, v in metadata.items():
                text += f"• <code>{k}</code>: {v}\n"
            text += "\n"
        
        text += f"<i>⏰ {timestamp}</i>"
        
        sent_count = 0
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    disable_notification=(severity == AlertSeverity.INFO)
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_id}: {e}")
        
        return sent_count
    
    # ==================== PREDEFINED ALERTS ====================
    
    async def alert_new_order(
        self,
        order_id: str,
        amount: float,
        currency: str,
        user_telegram_id: int,
        username: Optional[str],
        product_name: str,
        quantity: int = 1
    ) -> int:
        """Alert admins about new paid order."""
        user_display = f"@{username}" if username else f"ID: {user_telegram_id}"
        
        return await self.send_alert(
            title="💰 Новый заказ оплачен",
            message=(
                f"<b>{product_name}</b> × {quantity}\n\n"
                f"Сумма: <b>{amount:.2f} {currency}</b>\n"
                f"Покупатель: {user_display}"
            ),
            severity=AlertSeverity.INFO,
            metadata={"order_id": order_id[:8]}
        )
    
    async def alert_low_stock(
        self,
        product_name: str,
        product_id: str,
        current_stock: int,
        threshold: int = 5
    ) -> int:
        """Alert admins about low stock."""
        severity = AlertSeverity.WARNING if current_stock > 0 else AlertSeverity.ERROR
        return await self.send_alert(
            title="Низкий запас товара" if current_stock > 0 else "Товар закончился!",
            message=(
                f"<b>{product_name}</b>\n\n"
                f"Остаток: <b>{current_stock}</b> шт.\n"
                f"Порог: {threshold} шт."
            ),
            severity=severity,
            metadata={"product_id": product_id[:8]}
        )
    
    async def alert_payment_failure(
        self,
        order_id: str,
        error: str,
        amount: float,
        gateway: str
    ) -> int:
        """Alert admins about payment processing failure."""
        return await self.send_alert(
            title="Ошибка оплаты",
            message=(
                f"Не удалось обработать платёж\n\n"
                f"Сумма: ${amount:.2f}\n"
                f"Шлюз: {gateway}\n"
                f"Ошибка: <code>{error[:200]}</code>"
            ),
            severity=AlertSeverity.ERROR,
            metadata={"order_id": order_id[:8]}
        )
    
    async def alert_withdrawal_request(
        self,
        user_telegram_id: int,
        amount: float,
        method: str,
        request_id: str
    ) -> int:
        """Alert admins about new withdrawal request."""
        return await self.send_alert(
            title="Запрос на вывод средств",
            message=(
                f"Новый запрос на вывод <b>${amount:.2f}</b>\n\n"
                f"Метод: {method}\n"
                f"Пользователь: <code>{user_telegram_id}</code>"
            ),
            severity=AlertSeverity.WARNING,
            metadata={"request_id": request_id[:8]}
        )
    
    async def alert_new_partner_application(
        self,
        user_telegram_id: int,
        username: Optional[str],
        source: str,
        audience_size: str
    ) -> int:
        """Alert admins about new partner application."""
        return await self.send_alert(
            title="Заявка на партнёрство",
            message=(
                f"Новая заявка на VIP-партнёрство\n\n"
                f"Пользователь: {'@' + username if username else 'N/A'} (<code>{user_telegram_id}</code>)\n"
                f"Источник аудитории: {source}\n"
                f"Размер аудитории: {audience_size}"
            ),
            severity=AlertSeverity.INFO
        )
    
    async def alert_support_ticket(
        self,
        ticket_id: str,
        user_telegram_id: int,
        issue_type: str,
        order_id: Optional[str] = None
    ) -> int:
        """Alert admins about new support ticket."""
        metadata = {"ticket_id": ticket_id[:8]}
        if order_id:
            metadata["order_id"] = order_id[:8]
            
        return await self.send_alert(
            title="Новый тикет поддержки",
            message=(
                f"Создан тикет типа <b>{issue_type}</b>\n\n"
                f"Пользователь: <code>{user_telegram_id}</code>"
            ),
            severity=AlertSeverity.INFO,
            metadata=metadata
        )


# Singleton instance
_alert_service: Optional[AdminAlertService] = None


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
    metadata: Optional[dict] = None
) -> int:
    """Quick function to send alert to admins."""
    service = get_admin_alert_service()
    return await service.send_alert(title, message, severity, metadata)
