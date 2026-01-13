"""Discount bot purchase handlers.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import os
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message

from core.i18n import get_text

# Removed unused imports: InsuranceService, DiscountOrderService
from core.logging import get_logger
from core.services.database import User, get_database

from ..keyboards import (
    get_order_detail_keyboard,
    get_orders_keyboard,
    get_payment_keyboard,
)
from .catalog import get_user_currency_info

logger = get_logger(__name__)

router = Router(name="discount_purchase")

# CrystalPay config
CRYSTALPAY_LOGIN = os.environ.get("CRYSTALPAY_LOGIN", "")
CRYSTALPAY_SECRET = os.environ.get("CRYSTALPAY_SECRET", "")
CRYSTALPAY_API_URL = os.environ.get("CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3")


async def create_crystalpay_payment(
    amount_usd: float, currency: str, order_id: str, description: str
) -> str | None:
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
                exchange_rate = await currency_service.get_exchange_rate(currency)
                payment_amount = amount_usd * exchange_rate
                logger.info(
                    f"CrystalPay: converted ${amount_usd} USD to {payment_amount:.2f} {currency} (rate: {exchange_rate})"
                )
            except Exception as e:
                logger.warning(f"Currency conversion failed: {e}, using USD amount")
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
            f"CrystalPay discount payment: order={order_id}, callback={callback_url}, redirect={redirect_url}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRYSTALPAY_API_URL}/invoice/create/", json=payload, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("error", False) is False:
                    invoice_id = data.get("id")
                    payment_url = data.get("url")
                    logger.info(f"CrystalPay invoice created: {invoice_id} for order {order_id}")
                    return {"url": payment_url, "invoice_id": invoice_id}
                logger.error(f"CrystalPay API error: {data}")

        return None
    except Exception:
        logger.exception("CrystalPay error")
        return None


async def get_product_by_short_id(db, short_id: str) -> dict | None:
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
                return p

        return None
    except Exception:
        logger.exception("Failed to get product by short ID")
        return None


async def _determine_user_currency(db_user) -> str:
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
            logger.warning(f"Currency {user_currency} not supported by CrystalPay, using USD")
            user_currency = "USD"
    except Exception as e:
        logger.warning(f"Failed to determine user currency: {e}, using USD")
    return user_currency


async def _get_display_prices(
    total_price: float, discount_price: float, insurance_price: float, user_currency: str
) -> tuple[float, float, float, str]:
    """Convert prices to display currency (reduces cognitive complexity)."""
    if user_currency == "USD":
        return total_price, discount_price, insurance_price, "$"

    try:
        from core.db import get_redis
        from core.services.currency import CURRENCY_SYMBOLS, get_currency_service

        redis = get_redis()
        currency_service = get_currency_service(redis)
        rate = await currency_service.get_exchange_rate(user_currency)

        return (
            total_price * rate,
            discount_price * rate,
            insurance_price * rate,
            CURRENCY_SYMBOLS.get(user_currency, user_currency),
        )
    except Exception as e:
        logger.warning(f"Failed to convert price for display: {e}")
        return total_price, discount_price, insurance_price, "$"


async def get_insurance_option(db, short_id: str) -> dict | None:
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
                return option

        return None
    except Exception as e:
        logger.warning(f"Failed to get insurance option: {e}")
        return None


@router.callback_query(F.data.startswith("discount:buy:"))
async def cb_buy_product(callback: CallbackQuery, db_user: User):
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

    # Get insurance option
    insurance = await get_insurance_option(db, insurance_short_id)
    insurance_price = 0
    insurance_id = None

    if insurance:
        insurance_price = discount_price * (float(insurance.get("price_percent", 0)) / 100)
        insurance_id = insurance["id"]

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
        user_uuid = user_result.data["id"]

        # Create order with source_channel='discount'
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
                    "user_telegram_id": db_user.telegram_id,
                    "expires_at": expires_at.isoformat(),
                }
            )
            .execute()
        )

        order = order_result.data[0]
        order_id = order["id"]

        # Create order item
        await db.client.table("order_items").insert(
            {
                "order_id": order_id,
                "product_id": product["id"],
                "quantity": 1,
                "price": discount_price,
                "insurance_id": insurance_id,
            }
        ).execute()

        # Determine user currency
        user_currency = await _determine_user_currency(db_user)

        # Create payment
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
        await db.client.table("orders").update(
            {
                "payment_url": payment_url,
                "payment_id": invoice_id,  # Required for webhook to find order
            }
        ).eq("id", order_id).execute()

        # Format price in user's currency for display
        display_amount, display_discount_price, display_insurance_price, display_currency_symbol = (
            await _get_display_prices(total_price, discount_price, insurance_price, user_currency)
        )

        # Send payment message
        text = get_text("discount.order.header", lang, order_id=order_id[:8])
        text += get_text("discount.order.product", lang, name=product.get("name", "Product")) + "\n"
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

        await callback.message.edit_text(
            text, reply_markup=get_payment_keyboard(payment_url, lang), parse_mode=ParseMode.HTML
        )
        await callback.answer()

    except Exception:
        logger.exception("Order creation error")
        await callback.answer(get_text("discount.order.creationError", lang), show_alert=True)


@router.message(F.text.in_(["📦 Мои заказы", "📦 My Orders"]))
async def msg_orders(message: Message, db_user: User):
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

        orders = orders_result.data or []

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
async def cb_orders(callback: CallbackQuery, db_user: User):
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

        orders = orders_result.data or []

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


@router.callback_query(F.data.startswith("discount:order:"))
async def cb_order_detail(callback: CallbackQuery, db_user: User):
    """Show order details."""
    lang = db_user.language_code
    db = get_database()

    order_short_id = callback.data.split(":")[2]

    try:
        # Get user's discount orders and filter by short ID prefix
        # (ilike doesn't work with UUID fields in PostgREST)
        user_result = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", db_user.telegram_id)
            .single()
            .execute()
        )

        if not user_result.data:
            await callback.answer("User not found", show_alert=True)
            return

        user_uuid = user_result.data["id"]

        orders_result = (
            await db.client.table("orders")
            .select("*")
            .eq("user_id", user_uuid)
            .eq("source_channel", "discount")
            .execute()
        )

        # Filter by short ID prefix
        order = None
        short_id_lower = order_short_id.lower().replace("-", "")
        for o in orders_result.data or []:
            order_uuid = str(o["id"]).lower().replace("-", "")
            if order_uuid.startswith(short_id_lower):
                order = o
                break

        if not order:
            await callback.answer(
                "Заказ не найден" if lang == "ru" else "Order not found", show_alert=True
            )
            return

        # Get order items
        items_result = (
            await db.client.table("order_items")
            .select("*, products(name)")
            .eq("order_id", order["id"])
            .execute()
        )

        items = items_result.data or []

        # Check if has insurance
        has_insurance = any(item.get("insurance_id") for item in items)
        order["has_insurance"] = has_insurance

        # Get currency info
        currency, exchange_rate = await get_user_currency_info(db_user)
        # Use currency symbols from single source of truth
        from core.services.currency import CURRENCY_SYMBOLS

        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)

        amount_usd = float(order.get("amount", 0) or 0)
        display_amount = amount_usd * exchange_rate

        status_text = {
            "pending": "⏳ Ожидает оплаты" if lang == "ru" else "⏳ Pending payment",
            "paid": "💳 Оплачен" if lang == "ru" else "💳 Paid",
            "prepaid": "💳 Ожидает поставки" if lang == "ru" else "💳 Awaiting supply",
            "delivered": "✅ Доставлен" if lang == "ru" else "✅ Delivered",
            "cancelled": "❌ Отменён" if lang == "ru" else "❌ Cancelled",
            "refunded": "↩️ Возврат" if lang == "ru" else "↩️ Refunded",
        }.get(order["status"], order["status"])

        text = (
            f"📦 <b>Заказ #{order['id'][:8]}</b>\n\n"
            f"Статус: {status_text}\n"
            f"Сумма: {currency_symbol}{display_amount:.0f}\n"
            f"Создан: {order['created_at'][:10]}\n\n"
        )

        for item in items:
            product_name = (
                item.get("products", {}).get("name", "Product")
                if isinstance(item.get("products"), dict)
                else "Product"
            )
            text += f"• {product_name}\n"
            if item.get("insurance_id"):
                text += "  🛡 Со страховкой\n" if lang == "ru" else "  🛡 With insurance\n"

        if order["status"] == "paid":
            # Show scheduled delivery
            scheduled = order.get("scheduled_delivery_at")
            if scheduled:
                text += (
                    f"\n📦 Доставка ожидается: {scheduled[:16].replace('T', ' ')}\n"
                    if lang == "ru"
                    else f"\n📦 Expected delivery: {scheduled[:16].replace('T', ' ')}\n"
                )
            else:
                text += (
                    "\n📦 Доставка в течение 1-4 часов\n"
                    if lang == "ru"
                    else "\n📦 Delivery in 1-4 hours\n"
                )

        await callback.message.edit_text(
            text, reply_markup=get_order_detail_keyboard(order, lang), parse_mode=ParseMode.HTML
        )
        await callback.answer()

    except Exception:
        logger.exception("Order detail error")
        await callback.answer("Ошибка" if lang == "ru" else "Error", show_alert=True)


@router.callback_query(F.data.startswith("discount:status:"))
async def cb_order_status(callback: CallbackQuery, db_user: User):
    """Check order status (redirects to order detail)."""
    order_short_id = callback.data.split(":")[2]

    # Simulate redirect by updating callback data
    callback.data = f"discount:order:{order_short_id}"
    await cb_order_detail(callback, db_user)
