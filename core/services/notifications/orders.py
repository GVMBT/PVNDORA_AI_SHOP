"""
Order Notifications

Notifications for order lifecycle events.
"""
from core.services.database import get_database
from core.i18n import get_text
from core.logging import get_logger
from .base import NotificationServiceBase

logger = get_logger(__name__)


class OrderNotificationsMixin(NotificationServiceBase):
    """Mixin for order-related notifications."""
    
    async def send_review_request(self, order_id: str) -> None:
        """Send review request 1 hour after purchase"""
        db = get_database()
        
        order = await db.get_order_by_id(order_id)
        if not order or order.status != "delivered":
            return
        
        # Get user
        user_result = await db.client.table("users").select("telegram_id,language_code").eq("id", order.user_id).execute()
        if not user_result.data:
            return
        
        user = user_result.data[0]
        language = user.get("language_code", "en")
        
        message = get_text("review_request", language)
        
        from core.bot.keyboards import get_order_keyboard
        keyboard = get_order_keyboard(language, order_id)
        
        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard
            await send_telegram_message_with_keyboard(
                chat_id=user["telegram_id"],
                text=message,
                keyboard=keyboard,
                parse_mode=None
            )
        except Exception as e:
            logger.error(f"Failed to send review request: {e}")
    
    async def send_expiration_reminder(
        self,
        telegram_id: int,
        product_name: str,
        days_left: int,
        language: str
    ) -> None:
        """Send subscription expiration reminder"""
        message = get_text(
            "subscription_expiring",
            language,
            product=product_name,
            days=days_left
        )
        
        try:
            from core.services.telegram_messaging import send_telegram_message
            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode=None)
        except Exception as e:
            logger.error(f"Failed to send expiration reminder: {e}")
