"""Discount bot purchase handlers."""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core.services.database import User, get_database
from core.services.domains import InsuranceService, DiscountOrderService
from core.logging import get_logger
from core.i18n import get_text
from ..keyboards import (
    get_payment_keyboard,
    get_order_queued_keyboard,
    get_orders_keyboard,
    get_order_detail_keyboard,
)

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
    description: str
) -> Optional[str]:
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
        import httpx
        import os
        
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
                logger.info(f"CrystalPay: converted ${amount_usd} USD to {payment_amount:.2f} {currency} (rate: {exchange_rate})")
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
        redirect_url = f"{base_url}/payment/result?order_id={order_id}&source=discount"
        
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
        
        logger.info(f"CrystalPay discount payment: order={order_id}, callback={callback_url}, redirect={redirect_url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRYSTALPAY_API_URL}/invoice/create/",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("error", False) is False:
                    return data.get("url")
                else:
                    logger.error(f"CrystalPay API error: {data}")
        
        return None
    except Exception as e:
        logger.error(f"CrystalPay error: {e}")
        return None


async def get_product_by_short_id(db, short_id: str) -> Optional[dict]:
    """Get product by short ID (first 8 chars of UUID)."""
    try:
        # Get all active products with discount_price (ilike doesn't work with UUID)
        result = await asyncio.to_thread(
            lambda: db.client.table("products").select("*").eq(
                "status", "active"
            ).not_.is_("discount_price", "null").execute()
        )
        
        # Filter by UUID prefix (first 8 chars, case-insensitive)
        products = result.data or []
        short_id_lower = short_id.lower().replace("-", "")
        
        for p in products:
            product_uuid_str = str(p["id"]).lower().replace("-", "")
            if product_uuid_str.startswith(short_id_lower):
                return p
        
        return None
    except Exception as e:
        logger.error(f"Failed to get product by short ID: {e}")
        return None


async def get_insurance_option(db, short_id: str) -> Optional[dict]:
    """Get insurance option by short ID."""
    if not short_id or short_id == "0":
        return None
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("insurance_options").select("*").ilike(
                "id", f"{short_id}%"
            ).limit(1).execute()
        )
        return result.data[0] if result.data else None
    except Exception:
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
        await callback.answer(
            get_text("discount.order.productNotFound", lang),
            show_alert=True
        )
        return
    
    discount_price = float(product.get("discount_price", 0))
    if discount_price <= 0:
        await callback.answer(
            get_text("discount.order.productUnavailable", lang),
            show_alert=True
        )
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
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("id").eq(
                "telegram_id", db_user.telegram_id
            ).single().execute()
        )
        user_uuid = user_result.data["id"]
        
        # Create order with source_channel='discount'
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        order_result = await asyncio.to_thread(
            lambda: db.client.table("orders").insert({
                "user_id": user_uuid,
                "amount": total_price,
                "original_price": discount_price,
                "discount_percent": 0,
                "status": "pending",
                "payment_method": "crypto",
                "payment_gateway": "crystalpay",
                "source_channel": "discount",
                "user_telegram_id": db_user.telegram_id,
                "expires_at": expires_at.isoformat()
            }).execute()
        )
        
        order = order_result.data[0]
        order_id = order["id"]
        
        # Create order item
        await asyncio.to_thread(
            lambda: db.client.table("order_items").insert({
                "order_id": order_id,
                "product_id": product["id"],
                "quantity": 1,
                "price": discount_price,
                "insurance_id": insurance_id
            }).execute()
        )
        
        # Determine user currency
        user_currency = "USD"  # Default
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service
            
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            # Get user's preferred currency or determine from language
            preferred_currency = getattr(db_user, 'preferred_currency', None)
            user_lang = getattr(db_user, 'language_code', 'en') or 'en'
            
            user_currency = currency_service.get_user_currency(user_lang, preferred_currency)
            
            # CrystalPay supports: USD, RUB, EUR, UAH, TRY, INR, AED
            supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
            if user_currency not in supported_currencies:
                logger.warning(f"User currency {user_currency} not supported by CrystalPay, using USD")
                user_currency = "USD"
        except Exception as e:
            logger.warning(f"Failed to determine user currency: {e}, using USD")
        
        # Create payment
        description = f"Order {order_id[:8]} - {product.get('name', 'Product')}"
        if insurance:
            description += f" + {insurance.get('duration_days', 7)}d insurance"
        
        payment_url = await create_crystalpay_payment(
            amount_usd=total_price,
            currency=user_currency,
            order_id=order_id,
            description=description
        )
        
        if not payment_url:
            await callback.answer(
                get_text("discount.order.paymentError", lang),
                show_alert=True
            )
            return
        
        # Update order with payment URL
        await asyncio.to_thread(
            lambda: db.client.table("orders").update({
                "payment_url": payment_url
            }).eq("id", order_id).execute()
        )
        
        # Format price in user's currency for display
        display_amount = total_price
        display_discount_price = discount_price
        display_insurance_price = insurance_price
        display_currency_symbol = "$"
        exchange_rate = 1.0
        
        if user_currency != "USD":
            try:
                from core.db import get_redis
                from core.services.currency import get_currency_service
                redis = get_redis()
                currency_service = get_currency_service(redis)
                exchange_rate = await currency_service.get_exchange_rate(user_currency)
                display_amount = total_price * exchange_rate
                display_discount_price = discount_price * exchange_rate
                display_insurance_price = insurance_price * exchange_rate
                
                # Currency symbols
                currency_symbols = {
                    "RUB": "₽",
                    "EUR": "€",
                    "UAH": "₴",
                    "TRY": "₺",
                    "INR": "₹",
                    "AED": "د.إ"
                }
                display_currency_symbol = currency_symbols.get(user_currency, user_currency)
            except Exception as e:
                logger.warning(f"Failed to convert price for display: {e}")
        
        # Send payment message
        text = get_text("discount.order.header", lang, order_id=order_id[:8])
        text += get_text("discount.order.product", lang, name=product.get('name', 'Product')) + "\n"
        text += get_text("discount.order.price", lang, amount=f"{display_currency_symbol}{display_discount_price:.0f}") + "\n"
        
        if insurance:
            text += get_text(
                "discount.order.insurance", 
                lang, 
                amount=f"{display_currency_symbol}{display_insurance_price:.0f}",
                days=insurance.get('duration_days', 7)
            ) + "\n"
        
        text += f"\n<b>{get_text('discount.order.total', lang, amount=f'{display_currency_symbol}{display_amount:.0f}')}</b>\n\n"
        text += get_text("discount.order.linkExpires", lang) + "\n"
        text += get_text("discount.order.deliveryTime", lang)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(payment_url, lang),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        await callback.answer(
            get_text("discount.order.creationError", lang),
            show_alert=True
        )


@router.message(F.text.in_(["📦 Мои заказы", "📦 My Orders"]))
async def msg_orders(message: Message, db_user: User):
    """Show user orders."""
    lang = db_user.language_code
    db = get_database()
    
    try:
        # Get user UUID
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("id").eq(
                "telegram_id", db_user.telegram_id
            ).single().execute()
        )
        user_uuid = user_result.data["id"]
        
        # Get orders from discount channel
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select("*").eq(
                "user_id", user_uuid
            ).eq("source_channel", "discount").order(
                "created_at", desc=True
            ).limit(10).execute()
        )
        
        orders = orders_result.data or []
        
        if not orders:
            text = (
                "📦 <b>Мои заказы</b>\n\n"
                "У вас пока нет заказов."
            ) if lang == "ru" else (
                "📦 <b>My Orders</b>\n\n"
                "You don't have any orders yet."
            )
            await message.answer(text, parse_mode=ParseMode.HTML)
            return
        
        text = (
            "📦 <b>Мои заказы</b>\n\n"
            "Выберите заказ для подробностей:"
        ) if lang == "ru" else (
            "📦 <b>My Orders</b>\n\n"
            "Select an order for details:"
        )
        
        await message.answer(
            text,
            reply_markup=get_orders_keyboard(orders, lang),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Orders fetch error: {e}")
        await message.answer("Ошибка загрузки заказов" if lang == "ru" else "Error loading orders")


@router.callback_query(F.data == "discount:orders")
async def cb_orders(callback: CallbackQuery, db_user: User):
    """Show user orders from callback."""
    lang = db_user.language_code
    db = get_database()
    
    try:
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("id").eq(
                "telegram_id", db_user.telegram_id
            ).single().execute()
        )
        user_uuid = user_result.data["id"]
        
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select("*").eq(
                "user_id", user_uuid
            ).eq("source_channel", "discount").order(
                "created_at", desc=True
            ).limit(10).execute()
        )
        
        orders = orders_result.data or []
        
        text = (
            "📦 <b>Мои заказы</b>\n\n"
        ) if lang == "ru" else (
            "📦 <b>My Orders</b>\n\n"
        )
        
        if not orders:
            text += "У вас пока нет заказов." if lang == "ru" else "You don't have any orders yet."
        else:
            text += "Выберите заказ:" if lang == "ru" else "Select an order:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_orders_keyboard(orders, lang) if orders else None,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Orders fetch error: {e}")
        await callback.answer("Ошибка" if lang == "ru" else "Error", show_alert=True)


@router.callback_query(F.data.startswith("discount:order:"))
async def cb_order_detail(callback: CallbackQuery, db_user: User):
    """Show order details."""
    lang = db_user.language_code
    db = get_database()
    
    order_short_id = callback.data.split(":")[2]
    
    try:
        # Get order
        order_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select("*").ilike(
                "id", f"{order_short_id}%"
            ).limit(1).execute()
        )
        
        if not order_result.data:
            await callback.answer("Заказ не найден" if lang == "ru" else "Order not found", show_alert=True)
            return
        
        order = order_result.data[0]
        
        # Get order items
        items_result = await asyncio.to_thread(
            lambda: db.client.table("order_items").select(
                "*, products(name)"
            ).eq("order_id", order["id"]).execute()
        )
        
        items = items_result.data or []
        
        # Check if has insurance
        has_insurance = any(item.get("insurance_id") for item in items)
        order["has_insurance"] = has_insurance
        
        status_text = {
            "pending": "⏳ Ожидает оплаты" if lang == "ru" else "⏳ Pending payment",
            "paid": "💳 Оплачен" if lang == "ru" else "💳 Paid",
            "processing": "⚙️ Обработка" if lang == "ru" else "⚙️ Processing",
            "delivered": "✅ Доставлен" if lang == "ru" else "✅ Delivered",
            "refunded": "↩️ Возврат" if lang == "ru" else "↩️ Refunded",
            "expired": "❌ Просрочен" if lang == "ru" else "❌ Expired"
        }.get(order["status"], order["status"])
        
        text = (
            f"📦 <b>Заказ #{order['id'][:8]}</b>\n\n"
            f"Статус: {status_text}\n"
            f"Сумма: ${order['amount']:.0f}\n"
            f"Создан: {order['created_at'][:10]}\n\n"
        )
        
        for item in items:
            product_name = item.get("products", {}).get("name", "Product") if isinstance(item.get("products"), dict) else "Product"
            text += f"• {product_name}\n"
            if item.get("insurance_id"):
                text += "  🛡 Со страховкой\n" if lang == "ru" else "  🛡 With insurance\n"
        
        if order["status"] == "paid":
            # Show scheduled delivery
            scheduled = order.get("scheduled_delivery_at")
            if scheduled:
                text += f"\n📦 Доставка ожидается: {scheduled[:16].replace('T', ' ')}\n" if lang == "ru" else f"\n📦 Expected delivery: {scheduled[:16].replace('T', ' ')}\n"
            else:
                text += "\n📦 Доставка в течение 1-4 часов\n" if lang == "ru" else "\n📦 Delivery in 1-4 hours\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_order_detail_keyboard(order, lang),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Order detail error: {e}")
        await callback.answer("Ошибка" if lang == "ru" else "Error", show_alert=True)


@router.callback_query(F.data.startswith("discount:status:"))
async def cb_order_status(callback: CallbackQuery, db_user: User):
    """Check order status (redirects to order detail)."""
    order_short_id = callback.data.split(":")[2]
    
    # Simulate redirect by updating callback data
    callback.data = f"discount:order:{order_short_id}"
    await cb_order_detail(callback, db_user)
