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
    
    async def send_payment_confirmed(
        self,
        telegram_id: int,
        order_id: str,
        amount: float,
        currency: str,
        status: str,
        has_instant_items: bool = True,
        preorder_count: int = 0
    ) -> None:
        """
        Send payment confirmation notification to user.
        
        Args:
            telegram_id: User's Telegram ID
            order_id: Order ID (short display)
            amount: Amount paid
            currency: Currency (RUB, USD, etc.)
            status: Order status ('paid' or 'prepaid')
            has_instant_items: Whether order has instant delivery items
            preorder_count: Number of preorder items waiting
        """
        from .base import get_user_language, _msg
        from core.services.currency import CURRENCY_SYMBOLS
        
        lang = await get_user_language(telegram_id)
        
        # Format amount
        symbol = CURRENCY_SYMBOLS.get(currency, currency)
        if currency in ["RUB", "UAH", "TRY", "INR"]:
            amount_formatted = f"{int(amount)} {symbol}"
        else:
            amount_formatted = f"{amount:.2f} {symbol}"
        
        short_id = order_id[:8] if len(order_id) > 8 else order_id
        
        # Build message based on order status
        if status == "paid" and has_instant_items:
            # Instant delivery - items coming soon
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Заказ: <code>#{short_id}</code>\n"
                f"Сумма: <b>{amount_formatted}</b>\n\n"
                f"📦 Товар будет доставлен в течение минуты.\n"
                f"Вы получите уведомление с данными для доступа.",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>PAYMENT CONFIRMED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Order: <code>#{short_id}</code>\n"
                f"Amount: <b>{amount_formatted}</b>\n\n"
                f"📦 Your item will be delivered within a minute.\n"
                f"You'll receive a notification with access details."
            )
        elif status == "prepaid" or preorder_count > 0:
            # Preorder - waiting for stock
            waiting_text = f"\n⏳ Ожидает поступления: {preorder_count} товар(ов)" if preorder_count > 0 else ""
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Заказ: <code>#{short_id}</code>\n"
                f"Сумма: <b>{amount_formatted}</b>\n\n"
                f"📋 Заказ добавлен в очередь доставки.{waiting_text}\n"
                f"Мы уведомим вас, когда товар будет готов к доставке.",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>PAYMENT CONFIRMED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Order: <code>#{short_id}</code>\n"
                f"Amount: <b>{amount_formatted}</b>\n\n"
                f"📋 Order added to delivery queue.\n"
                f"We'll notify you when your item is ready for delivery."
            )
        else:
            # Generic confirmation
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Заказ: <code>#{short_id}</code>\n"
                f"Сумма: <b>{amount_formatted}</b>",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"   ✅ <b>PAYMENT CONFIRMED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Order: <code>#{short_id}</code>\n"
                f"Amount: <b>{amount_formatted}</b>"
            )
        
        try:
            from core.services.telegram_messaging import send_telegram_message
            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent payment confirmed notification to {telegram_id} for order {order_id}")
        except Exception as e:
            logger.error(f"Failed to send payment confirmed notification to {telegram_id}: {e}")