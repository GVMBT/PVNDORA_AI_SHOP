"""
Order Notifications

Notifications for order lifecycle events.
"""

from core.i18n import get_text
from core.logging import get_logger
from core.services.database import get_database

from .base import NotificationServiceBase

logger = get_logger(__name__)

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def _sanitize_id_for_logging(id_value: str) -> str:
    """Sanitize ID for safe logging (truncate to first 8 chars)."""
    return id_value[:8] if id_value else "N/A"


def _format_amount(amount: float, currency: str) -> str:
    """Format amount with currency symbol (reduces cognitive complexity)."""
    from core.services.currency import CURRENCY_SYMBOLS

    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    if currency in ["RUB", "UAH", "TRY", "INR"]:
        return f"{int(amount)} {symbol}"
    return f"{amount:.2f} {symbol}"


def _categorize_order_items(items_data: list) -> tuple[list[str], list[str]]:
    """Categorize order items into instant and prepaid (reduces cognitive complexity)."""
    instant_items = []
    prepaid_items = []

    for item in items_data:
        product_name = (
            item.get("products", {}).get("name")
            if isinstance(item.get("products"), dict)
            else "Product"
        )
        quantity = item.get("quantity", 1)
        fulfillment_type = item.get("fulfillment_type", "instant")

        item_text = f"• {product_name}" + (f" × {quantity}" if quantity > 1 else "")

        if fulfillment_type == "preorder":
            prepaid_items.append(item_text)
        else:
            instant_items.append(item_text)

    return instant_items, prepaid_items


def _build_items_list_text(lang: str, instant_items: list[str], prepaid_items: list[str]) -> str:
    """Build items list text for notification (reduces cognitive complexity)."""
    if instant_items and prepaid_items:
        items_list_text = "\n"
        items_list_text += "📦 <b>В наличии:</b>\n" if lang == "ru" else "📦 <b>In stock:</b>\n"
        items_list_text += "\n".join(instant_items) + "\n\n"
        items_list_text += "⏳ <b>По предзаказу:</b>\n" if lang == "ru" else "⏳ <b>Preorder:</b>\n"
        items_list_text += "\n".join(prepaid_items) + "\n"
        return items_list_text

    all_items = instant_items + prepaid_items
    if all_items:
        return "\n" + "\n".join(all_items) + "\n"

    return ""


def _build_delivery_info(lang: str, instant_items: list, prepaid_items: list) -> str:
    """Build delivery info text based on item types (reduces cognitive complexity)."""
    from .base import _msg

    if instant_items and prepaid_items:
        instant_count = len(instant_items)
        prepaid_count = len(prepaid_items)
        return _msg(
            lang,
            f"\n📦 <b>ДОСТАВКА</b>\n"
            f"• В наличии ({instant_count}): доставка в течение минуты\n"
            f"• По предзаказу ({prepaid_count}): уведомим при поступлении\n\n"
            f"Вы получите уведомления с данными для доступа по мере готовности товаров.",
            f"\n📦 <b>DELIVERY</b>\n"
            f"• In stock ({instant_count}): delivery within a minute\n"
            f"• Preorder ({prepaid_count}): we'll notify when ready\n\n"
            f"You'll receive notifications with access details as items become available.",
        )

    if instant_items:
        return _msg(
            lang,
            "\n📦 Товар будет доставлен в течение минуты.\n"
            "Вы получите уведомление с данными для доступа.",
            "\n📦 Your item will be delivered within a minute.\n"
            "You'll receive a notification with access details.",
        )

    if prepaid_items:
        prepaid_count = len(prepaid_items)
        return _msg(
            lang,
            f"\n📋 Заказ добавлен в очередь доставки.\n"
            f"⏳ Ожидает поступления: {prepaid_count} товар(ов)\n"
            f"Мы уведомим вас, когда товар будет готов к доставке.",
            f"\n📋 Order added to delivery queue.\n"
            f"⏳ Waiting for stock: {prepaid_count} item(s)\n"
            f"We'll notify you when your item is ready for delivery.",
        )

    return ""


class OrderNotificationsMixin(NotificationServiceBase):
    """Mixin for order-related notifications."""

    async def send_review_request(self, order_id: str) -> None:
        """Send review request 1 hour after purchase"""
        db = get_database()

        order = await db.get_order_by_id(order_id)
        if not order or order.status != "delivered":
            return

        # Get user
        user_result = (
            await db.client.table("users")
            .select("telegram_id,language_code")
            .eq("id", order.user_id)
            .execute()
        )
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
                chat_id=user["telegram_id"], text=message, keyboard=keyboard
            )
        except Exception:
            logger.exception("Failed to send review request")

    async def _fetch_order_items(self, order_id: str) -> tuple[list[str], list[str]]:
        """Fetch and categorize order items (reduces cognitive complexity)."""
        instant_items: list[str] = []
        prepaid_items: list[str] = []

        try:
            db = get_database()
            items_result = (
                await db.client.table("order_items")
                .select("quantity, fulfillment_type, products(name)")
                .eq("order_id", order_id)
                .execute()
            )
            if items_result.data:
                instant_items, prepaid_items = _categorize_order_items(items_result.data)
        except Exception as e:
            sanitized_order_id = _sanitize_id_for_logging(order_id)
            logger.warning(
                "Failed to fetch order items for notification %s: %s", sanitized_order_id, e
            )

        return instant_items, prepaid_items

    async def send_expiration_reminder(
        self, telegram_id: int, product_name: str, days_left: int, language: str
    ) -> None:
        """Send subscription expiration reminder"""
        message = get_text("subscription_expiring", language, product=product_name, days=days_left)

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message)
        except Exception:
            logger.exception("Failed to send expiration reminder")

    async def send_payment_confirmed(
        self,
        telegram_id: int,
        order_id: str,
        amount: float,
        currency: str,
        status: str,
        _has_instant_items: bool = True,
        _preorder_count: int = 0,
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
        from .base import _msg, get_user_language

        lang = await get_user_language(telegram_id)
        amount_formatted = _format_amount(amount, currency)
        short_id = order_id[:8] if len(order_id) > 8 else order_id

        # Fetch and categorize order items
        instant_items, prepaid_items = await self._fetch_order_items(order_id)
        items_list_text = _build_items_list_text(lang, instant_items, prepaid_items)

        delivery_info = _build_delivery_info(lang, instant_items, prepaid_items)

        # Build message
        message = _msg(
            lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   ✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Заказ: <code>#{short_id}</code>\n"
            f"Сумма: <b>{amount_formatted}</b>{items_list_text}{delivery_info}",
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   ✅ <b>PAYMENT CONFIRMED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Order: <code>#{short_id}</code>\n"
            f"Amount: <b>{amount_formatted}</b>{items_list_text}{delivery_info}",
        )

        try:
            from core.services.telegram_messaging import send_telegram_message

            await send_telegram_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(
                f"Sent payment confirmed notification to {telegram_id} for order {order_id}"
            )
        except Exception:
            logger.exception("Failed to send payment confirmed notification to %s", telegram_id)
