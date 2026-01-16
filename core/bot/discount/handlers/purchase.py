"""Discount bot purchase handlers.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

# Type alias for dict type hints
DictStrAny = dict[str, Any]

from aiogram import F, Router

if TYPE_CHECKING:
    from core.services.database import Database
    from core.services.models import User
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message

from core.bot.discount.keyboards import (
    get_order_detail_keyboard,
    get_orders_keyboard,
    get_payment_keyboard,
)
from core.i18n import get_text

# Removed unused imports: InsuranceService, DiscountOrderService
from core.logging import get_logger
from core.services.database import User, get_database

from .catalog import get_user_currency_info

logger = get_logger(__name__)

router = Router(name="discount_purchase")

# CrystalPay config
CRYSTALPAY_LOGIN = os.environ.get("CRYSTALPAY_LOGIN", "")
CRYSTALPAY_SECRET = os.environ.get("CRYSTALPAY_SECRET", "")
CRYSTALPAY_API_URL = os.environ.get("CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3")


async def create_crystalpay_payment(
    amount_usd: float,
    currency: str,
    order_id: str,
    description: str,
) -> dict[str, Any] | None:
    """Create CrystalPay payment and return payment URL.

    Uses CrystalPay API v3.
    Docs: https://docs.crystalpay.io/

    Args:
        amount_usd: Amount in USD (base currency for discount prices)
        currency: Target currency (USD, RUB, EUR, etc.)
        order_id: Order ID
        description: Payment description

    """
    try:
        import os

        import httpx

        # Convert amount from USD to target currency if needed
        payment_amount = amount_usd
        if currency != "USD":
            try:
                from core.db import get_redis
                from core.services.currency import get_currency_service

                redis = get_redis()
                currency_service = get_currency_service(redis)
                exchange_rate = currency_service.get_exchange_rate(currency)
                payment_amount = amount_usd * exchange_rate
                logger.info(
                    f"CrystalPay: converted ${amount_usd} USD to {payment_amount:.2f} {currency} (rate: {exchange_rate})",
                )
            except Exception as e:
                logger.warning("Currency conversion failed: %s, using USD amount", type(e).__name__)
                currency = "USD"
                payment_amount = amount_usd

        # Build callback and redirect URLs
        base_url = os.environ.get("VERCEL_URL", "")
        if base_url and not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        if not base_url:
            base_url = os.environ.get("TELEGRAM_WEBHOOK_URL", "").rsplit("/api", 1)[0]

        callback_url = f"{base_url}/api/webhook/crystalpay"
        # For Telegram bot (not Mini App), redirect to simple page or directly to bot
        discount_bot_username = os.environ.get("DISCOUNT_BOT_USERNAME", "hub_discount_bot")
        redirect_url = f"https://t.me/{discount_bot_username}"

        payload = {
            "auth_login": CRYSTALPAY_LOGIN,
            "auth_secret": CRYSTALPAY_SECRET,
            "amount": round(payment_amount, 2),
            "currency": currency,
            "type": "purchase",
            "description": description,
            "extra": order_id,
            "lifetime": 60,  # 1 hour in minutes
            "callback_url": callback_url,
            "redirect_url": redirect_url,
        }

        logger.info(
            f"CrystalPay discount payment: order={order_id}, callback={callback_url}, redirect={redirect_url}",
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRYSTALPAY_API_URL}/invoice/create/",
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                data = cast(DictStrAny, response.json())
                if data.get("error", False) is False:
                    invoice_id = data.get("id")
                    payment_url = data.get("url")
                    from core.logging import sanitize_id_for_logging

                    logger.info(
                        "CrystalPay invoice created: %s for order %s",
                        sanitize_id_for_logging(invoice_id),
                        sanitize_id_for_logging(order_id),
                    )
                    return {"url": payment_url, "invoice_id": invoice_id}
                logger.error("CrystalPay API error: %s", type(data).__name__)

        return None
    except Exception:
        logger.exception("CrystalPay error")
        return None


async def get_product_by_short_id(db: "Database", short_id: str) -> dict[str, Any] | None:
    """Get product by short ID (first 8 chars of UUID)."""
    try:
        # Get all active products with discount_price (ilike doesn't work with UUID)
        result = (
            await db.client.table("products")
            .select("*")
            .eq("status", "active")
            .not_.is_("discount_price", "null")
            .execute()
        )

        # Filter by UUID prefix (first 8 chars, case-insensitive)
        products = result.data or []
        short_id_lower = short_id.lower().replace("-", "")

        for p in products:
            product_uuid_str = str(p["id"]).lower().replace("-", "")
            if product_uuid_str.startswith(short_id_lower):
                return cast(DictStrAny, p)

        return None
    except Exception:
        logger.exception("Failed to get product by short ID")
        return None


def _determine_user_currency(db_user) -> str:
    """Determine user's payment currency for CrystalPay (reduces cognitive complexity)."""
    user_currency = "USD"
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        redis = get_redis()
        currency_service = get_currency_service(redis)

        preferred_currency = getattr(db_user, "preferred_currency", None)
        user_lang = getattr(db_user, "language_code", "en") or "en"
        user_currency = currency_service.get_user_currency(user_lang, preferred_currency)

        supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
        if user_currency not in supported_currencies:
            logger.warning("Currency %s not supported by CrystalPay, using USD", user_currency)
            user_currency = "USD"
    except Exception as e:
        logger.warning("Failed to determine user currency: %s, using USD", type(e).__name__)
    return user_currency


async def _get_display_prices(
    total_price: float,
    discount_price: float,
    insurance_price: float,
    user_currency: str,
) -> tuple[float, float, float, str]:
    """Convert prices to display currency (reduces cognitive complexity)."""
    if user_currency == "USD":
        return total_price, discount_price, insurance_price, "$"

    try:
        from core.db import get_redis
        from core.services.currency import CURRENCY_SYMBOLS, get_currency_service

        redis = get_redis()
        currency_service = get_currency_service(redis)
        rate = currency_service.get_exchange_rate(user_currency)

        return (
            total_price * rate,
            discount_price * rate,
            insurance_price * rate,
            CURRENCY_SYMBOLS.get(user_currency, user_currency),
        )
    except Exception as e:
        logger.warning("Failed to convert price for display: %s", type(e).__name__)
        return total_price, discount_price, insurance_price, "$"


# Helper: Calculate insurance price and ID (reduces cognitive complexity)
def _calculate_insurance_info(
    insurance: dict[str, Any] | None,
    discount_price: float,
) -> tuple[float, str | None]:
    """Calculate insurance price and return (price, id)."""
    if not insurance:
        return 0.0, None
    insurance_price = discount_price * (float(insurance.get("price_percent", 0)) / 100)
    return insurance_price, insurance["id"]


# Helper: Create order and order item (reduces cognitive complexity)
async def _create_discount_order(
    db: Any,
    user_uuid: str,
    telegram_id: int,
    total_price: float,
    discount_price: float,
    product_id: str,
    insurance_id: str | None,
) -> str:
    """Create order and order item, return order_id."""
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    order_result = (
        await db.client.table("orders")
        .insert(
            {
                "user_id": user_uuid,
                "amount": total_price,
                "original_price": discount_price,
                "discount_percent": 0,
                "status": "pending",
                "payment_method": "crypto",
                "payment_gateway": "crystalpay",
                "source_channel": "discount",
                "user_telegram_id": telegram_id,
                "expires_at": expires_at.isoformat(),
            },
        )
        .execute()
    )

    order_id = str(order_result.data[0]["id"])

    await (
        db.client.table("order_items")
        .insert(
            {
                "order_id": order_id,
                "product_id": product_id,
                "quantity": 1,
                "price": discount_price,
                "insurance_id": insurance_id,
            },
        )
        .execute()
    )

    return order_id


# Helper: Build payment message text (reduces cognitive complexity)
def _build_payment_message(
    lang: str,
    order_id: str,
    product_name: str,
    display_currency_symbol: str,
    display_discount_price: float,
    display_insurance_price: float,
    display_amount: float,
    insurance: dict[str, Any] | None,
) -> str:
    """Build payment message text from components."""
    text = get_text("discount.order.header", lang, order_id=order_id[:8])
    text += get_text("discount.order.product", lang, name=product_name) + "\n"
    text += (
        get_text(
            "discount.order.price",
            lang,
            amount=f"{display_currency_symbol}{display_discount_price:.0f}",
        )
        + "\n"
    )

    if insurance:
        text += (
            get_text(
                "discount.order.insurance",
                lang,
                amount=f"{display_currency_symbol}{display_insurance_price:.0f}",
                days=insurance.get("duration_days", 7),
            )
            + "\n"
        )

    text += f"\n<b>{get_text('discount.order.total', lang, amount=f'{display_currency_symbol}{display_amount:.0f}')}</b>\n\n"
    text += get_text("discount.order.linkExpires", lang) + "\n"
    text += get_text("discount.order.deliveryTime", lang)

    return text


async def get_insurance_option(db: "Database", short_id: str) -> dict[str, Any] | None:
    """Get insurance option by short ID."""
    if not short_id or short_id == "0":
        return None

    try:
        # Get all active insurance options and filter by prefix
        # (ilike doesn't work with UUID fields in PostgREST)
        result = (
            await db.client.table("insurance_options").select("*").eq("is_active", True).execute()
        )

        if not result.data:
            return None

        # Filter by UUID prefix
        short_id_lower = short_id.lower().replace("-", "")
        for option in result.data:
            option_uuid = str(option["id"]).lower().replace("-", "")
            if option_uuid.startswith(short_id_lower):
                return cast(DictStrAny, option)

        return None
    except Exception as e:
        logger.warning("Failed to get insurance option: %s", type(e).__name__)
        return None


@router.callback_query(F.data.startswith("discount:buy:"))
async def cb_buy_product(callback: CallbackQuery, db_user: User) -> None:
    """Initiate purchase flow."""
    lang = db_user.language_code
    db = get_database()

    parts = callback.data.split(":")
    product_short_id = parts[2]
    insurance_short_id = parts[3] if len(parts) > 3 else "0"

    # Get product
    product = await get_product_by_short_id(db, product_short_id)
    if not product:
        await callback.answer(get_text("discount.order.productNotFound", lang), show_alert=True)
        return

    discount_price = float(product.get("discount_price", 0))
    if discount_price <= 0:
        await callback.answer(get_text("discount.order.productUnavailable", lang), show_alert=True)
        return

    # Get insurance option and calculate prices
    insurance = await get_insurance_option(db, insurance_short_id)
    insurance_price, insurance_id = _calculate_insurance_info(insurance, discount_price)
    total_price = discount_price + insurance_price

    # Create order
    try:
        # Get user UUID
        user_result = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", db_user.telegram_id)
            .single()
            .execute()
        )
        if not isinstance(user_result.data, dict):
            await callback.answer("User not found", show_alert=True)
            return
        user_uuid_raw = user_result.data.get("id")
        user_uuid = str(user_uuid_raw) if user_uuid_raw is not None else ""

        # Create order and order item
        order_id = await _create_discount_order(
            db,
            user_uuid,
            db_user.telegram_id,
            total_price,
            discount_price,
            product["id"],
            insurance_id,
        )

        # Determine user currency and create payment
        user_currency = _determine_user_currency(db_user)
        description = f"Order {order_id[:8]} - {product.get('name', 'Product')}"
        if insurance:
            description += f" + {insurance.get('duration_days', 7)}d insurance"

        payment_result = await create_crystalpay_payment(
            amount_usd=total_price,
            currency=user_currency,
            order_id=order_id,
            description=description,
        )

        if not payment_result:
            await callback.answer(get_text("discount.order.paymentError", lang), show_alert=True)
            return

        payment_url = payment_result["url"]
        invoice_id = payment_result.get("invoice_id")

        # Update order with payment URL and invoice_id (critical for webhook lookup!)
        await (
            db.client.table("orders")
            .update(
                {
                    "payment_url": payment_url,
                    "payment_id": invoice_id,  # Required for webhook to find order
                },
            )
            .eq("id", order_id)
            .execute()
        )

        # Format price in user's currency for display
        (
            display_amount,
            display_discount_price,
            display_insurance_price,
            display_currency_symbol,
        ) = await _get_display_prices(total_price, discount_price, insurance_price, user_currency)

        # Build and send payment message
        text = _build_payment_message(
            lang,
            order_id,
            product.get("name", "Product"),
            display_currency_symbol,
            display_discount_price,
            display_insurance_price,
            display_amount,
            insurance,
        )

        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_url, lang),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()

    except Exception:
        logger.exception("Order creation error")
        await callback.answer(get_text("discount.order.creationError", lang), show_alert=True)


@router.message(F.text.in_(["📦 Мои заказы", "📦 My Orders"]))
async def msg_orders(message: Message, db_user: User) -> None:
    """Show user orders."""
    lang = db_user.language_code
    db = get_database()

    try:
        # Get user currency info
        currency, exchange_rate = await get_user_currency_info(db_user)

        # Get user UUID
        user_result = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", db_user.telegram_id)
            .single()
            .execute()
        )
        user_uuid = user_result.data["id"]

        # Get orders from discount channel
        orders_result = (
            await db.client.table("orders")
            .select("*")
            .eq("user_id", user_uuid)
            .eq("source_channel", "discount")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        orders_raw = orders_result.data or []
        orders = [item if isinstance(item, dict) else {} for item in orders_raw]

        if not orders:
            text = (
                ("📦 <b>Мои заказы</b>\n\nУ вас пока нет заказов.")
                if lang == "ru"
                else ("📦 <b>My Orders</b>\n\nYou don't have any orders yet.")
            )
            await message.answer(text, parse_mode=ParseMode.HTML)
            return

        text = (
            ("📦 <b>Мои заказы</b>\n\nВыберите заказ для подробностей:")
            if lang == "ru"
            else ("📦 <b>My Orders</b>\n\nSelect an order for details:")
        )

        await message.answer(
            text,
            reply_markup=get_orders_keyboard(orders, lang, exchange_rate, currency),
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        logger.exception("Orders fetch error")
        await message.answer("Ошибка загрузки заказов" if lang == "ru" else "Error loading orders")


@router.callback_query(F.data == "discount:orders")
async def cb_orders(callback: CallbackQuery, db_user: User) -> None:
    """Show user orders from callback."""
    lang = db_user.language_code
    db = get_database()

    try:
        # Get user currency info
        currency, exchange_rate = await get_user_currency_info(db_user)

        user_result = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", db_user.telegram_id)
            .single()
            .execute()
        )
        user_uuid = user_result.data["id"]

        orders_result = (
            await db.client.table("orders")
            .select("*")
            .eq("user_id", user_uuid)
            .eq("source_channel", "discount")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        orders_raw = orders_result.data or []
        orders = [item if isinstance(item, dict) else {} for item in orders_raw]

        text = ("📦 <b>Мои заказы</b>\n\n") if lang == "ru" else ("📦 <b>My Orders</b>\n\n")

        if not orders:
            text += "У вас пока нет заказов." if lang == "ru" else "You don't have any orders yet."
        else:
            text += "Выберите заказ:" if lang == "ru" else "Select an order:"

        await callback.message.edit_text(
            text,
            reply_markup=(
                get_orders_keyboard(orders, lang, exchange_rate, currency) if orders else None
            ),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()

    except Exception:
        logger.exception("Orders fetch error")
        await callback.answer("Ошибка" if lang == "ru" else "Error", show_alert=True)


# Helper: Find order by short ID (reduces cognitive complexity)
async def _find_order_by_short_id(
    db: Any,
    user_uuid: str,
    order_short_id: str,
) -> dict[str, Any] | None:
    """Find order by short ID prefix."""
    orders_result = (
        await db.client.table("orders")
        .select("*")
        .eq("user_id", user_uuid)
        .eq("source_channel", "discount")
        .execute()
    )

    short_id_lower = order_short_id.lower().replace("-", "")
    for o in orders_result.data or []:
        order_uuid = str(o["id"]).lower().replace("-", "")
        if order_uuid.startswith(short_id_lower):
            return cast(DictStrAny, o)
    return None


# Helper: Get status text (reduces cognitive complexity)
def _get_status_text(status: str, lang: str) -> str:
    """Get localized status text."""
    status_map = {
        "pending": ("⏳ Ожидает оплаты", "⏳ Pending payment"),
        "paid": ("💳 Оплачен", "💳 Paid"),
        "prepaid": ("💳 Ожидает поставки", "💳 Awaiting supply"),
        "delivered": ("✅ Доставлен", "✅ Delivered"),
        "cancelled": ("❌ Отменён", "❌ Cancelled"),
        "refunded": ("↩️ Возврат", "↩️ Refunded"),
    }
    ru_text, en_text = status_map.get(status, (status, status))
    return ru_text if lang == "ru" else en_text


# Helper: Format order items text (reduces cognitive complexity)
def _format_order_items_text(items: list[DictStrAny], lang: str) -> str:
    """Format order items list as text."""
    text = ""
    for item in items:
        product_name = (
            item.get("products", {}).get("name", "Product")
            if isinstance(item.get("products"), dict)
            else "Product"
        )
        text += f"• {product_name}\n"
        if item.get("insurance_id"):
            text += "  🛡 Со страховкой\n" if lang == "ru" else "  🛡 With insurance\n"
    return text


# Helper: Format delivery info (reduces cognitive complexity)
def _format_delivery_info(order: dict[str, Any], lang: str) -> str:
    """Format delivery information text."""
    scheduled = order.get("scheduled_delivery_at")
    if scheduled:
        return (
            f"\n📦 Доставка ожидается: {scheduled[:16].replace('T', ' ')}\n"
            if lang == "ru"
            else f"\n📦 Expected delivery: {scheduled[:16].replace('T', ' ')}\n"
        )
    return "\n📦 Доставка в течение 1-4 часов\n" if lang == "ru" else "\n📦 Delivery in 1-4 hours\n"


# Helper: Build order detail message (reduces cognitive complexity)
def _build_order_detail_message(
    order: DictStrAny,
    items: list[DictStrAny],
    currency_symbol: str,
    display_amount: float,
    lang: str,
) -> str:
    """Build order detail message text."""
    status_text = _get_status_text(order["status"], lang)

    text = (
        f"📦 <b>Заказ #{order['id'][:8]}</b>\n\n"
        f"Статус: {status_text}\n"
        f"Сумма: {currency_symbol}{display_amount:.0f}\n"
        f"Создан: {order['created_at'][:10]}\n\n"
    )

    text += _format_order_items_text(items, lang)

    if order["status"] == "paid":
        text += _format_delivery_info(order, lang)

    return text


@router.callback_query(F.data.startswith("discount:order:"))
async def cb_order_detail(callback: CallbackQuery, db_user: User) -> None:
    """Show order details."""
    lang = db_user.language_code
    db = get_database()

    order_short_id = callback.data.split(":")[2]

    try:
        # Get user UUID
        user_result = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", db_user.telegram_id)
            .single()
            .execute()
        )

        if not isinstance(user_result.data, dict):
            await callback.answer("User not found", show_alert=True)
            return

        user_uuid_raw = user_result.data.get("id")
        user_uuid = str(user_uuid_raw) if user_uuid_raw is not None else ""

        # Find order by short ID
        order = await _find_order_by_short_id(db, user_uuid, str(order_short_id))
        if not order:
            await callback.answer(
                "Заказ не найден" if lang == "ru" else "Order not found",
                show_alert=True,
            )
            return

        # Get order items
        items_result = (
            await db.client.table("order_items")
            .select("*, products(name)")
            .eq("order_id", order["id"])
            .execute()
        )

        items_raw = items_result.data or []
        items = [item if isinstance(item, dict) else {} for item in items_raw]
        has_insurance = any(
            isinstance(item, dict) and item.get("insurance_id") for item in items
        )
        if isinstance(order, dict):
            order["has_insurance"] = has_insurance

        # Get currency info
        currency, exchange_rate = await get_user_currency_info(db_user)
        from core.services.currency import CURRENCY_SYMBOLS

        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)
        amount_usd = float(order.get("amount", 0) or 0)
        display_amount = amount_usd * exchange_rate

        # Build and send message
        text = _build_order_detail_message(order, items, currency_symbol, display_amount, lang)

        await callback.message.edit_text(
            text,
            reply_markup=get_order_detail_keyboard(order, lang),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()

    except Exception:
        logger.exception("Order detail error")
        await callback.answer("Ошибка" if lang == "ru" else "Error", show_alert=True)


@router.callback_query(F.data.startswith("discount:status:"))
async def cb_order_status(callback: CallbackQuery, db_user: User) -> None:
    """Check order status (redirects to order detail)."""
    order_short_id = callback.data.split(":")[2]

    # Simulate redirect by updating callback data
    callback.data = f"discount:order:{order_short_id}"
    await cb_order_detail(callback, db_user)
