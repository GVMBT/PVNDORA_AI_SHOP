"""
Cron: Deliver Overdue Discount Orders

Fallback for QStash - if scheduled_delivery_at has passed
but order is still 'paid', deliver it.

Runs every 5 minutes.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

# Add project root to path for imports BEFORE any core.* imports
_base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_base_path))
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger
from core.services.database import get_database_async

logger = get_logger(__name__)

CRON_SECRET = os.environ.get("CRON_SECRET", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

_referral_settings_cache: dict[str, int] | None = None


async def get_referral_percentages() -> dict[str, int]:
    """Get referral percentages from database (cached)."""
    global _referral_settings_cache
    if _referral_settings_cache:
        return _referral_settings_cache

    try:
        db = await get_database_async()
        result = await db.client.table("referral_settings").select("*").limit(1).execute()
        if result.data and isinstance(result.data[0], dict):
            s = cast(dict[str, Any], result.data[0])
            _referral_settings_cache = {
                "l1": int(s.get("level1_commission_percent", 10) or 10),
                "l2": int(s.get("level2_commission_percent", 7) or 7),
                "l3": int(s.get("level3_commission_percent", 3) or 3),
            }
            return _referral_settings_cache
    except Exception as e:
        logger.warning(f"Failed to get referral settings: {e}")

    return {"l1": 10, "l2": 7, "l3": 3}


app = FastAPI()


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    from core.services.telegram_messaging import send_telegram_message as _send_msg

    bot_token = DISCOUNT_BOT_TOKEN or TELEGRAM_TOKEN
    return await _send_msg(chat_id=chat_id, text=text, parse_mode="HTML", bot_token=bot_token)


async def _find_or_assign_stock(db: Any, product_id: str, stock_item_id: str | None) -> str | None:
    """Find or use existing stock item. Returns stock_item_id or None."""
    if stock_item_id:
        return stock_item_id

    stock_result = (
        await db.client.table("stock_items")
        .select("id")
        .eq("product_id", product_id)
        .in_("status", ["available", "reserved"])
        .limit(1)
        .execute()
    )

    if not stock_result.data:
        return None
    return str(stock_result.data[0]["id"])


async def _get_stock_content(db: Any, stock_item_id: str) -> tuple[str, str]:
    """Get stock content and product name. Returns (content, product_name)."""
    stock_item = (
        await db.client.table("stock_items")
        .select("content, products(name)")
        .eq("id", stock_item_id)
        .single()
        .execute()
    )

    if not stock_item.data:
        return "", "Product"

    content = stock_item.data.get("content", "")
    products = stock_item.data.get("products")
    product_name = products.get("name", "Product") if isinstance(products, dict) else "Product"
    return content, product_name


async def _mark_stock_as_sold(db: Any, stock_item_id: str) -> None:
    """Mark stock item as sold."""
    await (
        db.client.table("stock_items")
        .update({"status": "sold", "sold_at": datetime.now(UTC).isoformat()})
        .eq("id", stock_item_id)
        .execute()
    )


async def _update_order_item_delivered(
    db: Any, order_item_id: str, stock_item_id: str, content: str
) -> None:
    """Update order item with delivery content and status."""
    await (
        db.client.table("order_items")
        .update(
            {
                "stock_item_id": stock_item_id,
                "delivery_content": content,
                "status": "delivered",
                "delivered_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("id", order_item_id)
        .execute()
    )


async def _get_user_language(db: Any, telegram_id: int) -> str:
    """Get user's language code."""
    user_result = (
        await db.client.table("users")
        .select("language_code")
        .eq("telegram_id", telegram_id)
        .single()
        .execute()
    )
    return user_result.data.get("language_code", "en") if user_result.data else "en"


def _format_delivery_message(lang: str, product_name: str, order_id: str, content: str) -> str:
    """Format delivery message."""
    truncated = content[:500]
    suffix = "...(обрезано)" if len(content) > 500 else ""
    suffix_en = "...(truncated)" if len(content) > 500 else ""

    if lang == "ru":
        return (
            f"╔══════════════════════════════╗\n"
            f"     ✅ <b>ЗАКАЗ ДОСТАВЛЕН</b>\n"
            f"╚══════════════════════════════╝\n\n"
            f"📦 <b>Товар:</b> {product_name}\n"
            f"🔖 <b>Заказ:</b> <code>#{order_id[:8]}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 <b>ДАННЫЕ ДОСТУПА:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{truncated}</code>{suffix}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>СОХРАНИТЕ ЭТИ ДАННЫЕ!</b>\n\n"
            f"💬 Проблема? → /orders → выберите заказ"
        )
    return (
        f"╔══════════════════════════════╗\n"
        f"      ✅ <b>ORDER DELIVERED</b>\n"
        f"╚══════════════════════════════╝\n\n"
        f"📦 <b>Product:</b> {product_name}\n"
        f"🔖 <b>Order:</b> <code>#{order_id[:8]}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔐 <b>ACCESS CREDENTIALS:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<code>{truncated}</code>{suffix_en}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>SAVE THIS DATA!</b>\n\n"
        f"💬 Problem? → /orders → select order"
    )


async def _format_offer_message(lang: str, product_name: str, purchase_count: int) -> str:
    """Format PVNDORA offer message."""
    ref = await get_referral_percentages()

    if lang == "ru":
        if purchase_count == 1:
            progress = (
                f"🎯 <b>Это твоя первая покупка!</b>\n"
                f"   В PVNDORA ты сразу получишь партнёрку\n"
                f"   и сможешь зарабатывать {ref['l1']}% с друзей\n"
            )
        elif purchase_count < 3:
            remaining = 3 - purchase_count
            progress = (
                f"🎯 <b>Уже {purchase_count} покупок!</b>\n"
                f"   Ещё {remaining} — и персональная скидка 50%\n"
            )
        else:
            progress = "🎯 <b>Ты наш постоянный клиент!</b>\n   Смотри ниже — там подарок!\n"

        return (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>ПОНРАВИЛСЯ {product_name.upper()}?</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{progress}\n"
            f"В <b>PVNDORA</b> такие товары:\n\n"
            f"⚡️ <b>Доставляются мгновенно</b>\n   Не ждёшь 1-4 часа в очереди\n\n"
            f"🛡 <b>С полной гарантией</b>\n   Проблема? Бесплатная замена\n\n"
            f"💰 <b>+ Партнёрка {ref['l1']}/{ref['l2']}/{ref['l3']}%</b>\n"
            f"   Пригласи друга — получи {ref['l1']}% с его покупок\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 <b>@pvndora_ai_bot</b>"
        )

    if purchase_count == 1:
        progress = (
            f"🎯 <b>This is your first purchase!</b>\n"
            f"   In PVNDORA you instantly get affiliate\n"
            f"   and can earn {ref['l1']}% from friends' orders\n"
        )
    elif purchase_count < 3:
        remaining = 3 - purchase_count
        progress = (
            f"🎯 <b>Already {purchase_count} purchases!</b>\n"
            f"   {remaining} more — and personal 50% discount\n"
        )
    else:
        progress = "🎯 <b>You're a loyal customer!</b>\n   Check below — there's a gift!\n"

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>LIKED {product_name.upper()}?</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{progress}\n"
        f"In <b>PVNDORA</b> such products:\n\n"
        f"⚡️ <b>Delivered instantly</b>\n   No 1-4 hour queue wait\n\n"
        f"🛡 <b>With full warranty</b>\n   Problem? Free replacement\n\n"
        f"💰 <b>+ Affiliate {ref['l1']}/{ref['l2']}/{ref['l3']}%</b>\n"
        f"   Invite a friend — get {ref['l1']}% of their purchases\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 <b>@pvndora_ai_bot</b>"
    )


async def _get_user_purchase_count(db: Any, telegram_id: int) -> int:
    """Get user's delivered discount purchase count."""
    result = (
        await db.client.table("orders")
        .select("id", count="exact")
        .eq("user_telegram_id", telegram_id)
        .eq("source_channel", "discount")
        .eq("status", "delivered")
        .execute()
    )
    return result.count if result.count else 1


async def _send_loyal_promo_if_eligible(
    user_id: str, telegram_id: int, lang: str, purchase_count: int
) -> bool:
    """Send loyal customer promo code after 3rd purchase."""
    from core.services.domains.promo import PromoCodeService, PromoTriggers

    db = await get_database_async()
    promo_service = PromoCodeService(db.client)

    try:
        existing = await promo_service.get_promo_by_trigger(
            user_id, PromoTriggers.LOYAL_3_PURCHASES
        )
        if existing:
            return False

        promo_code = await promo_service.generate_personal_promo(
            user_id=user_id,
            telegram_id=telegram_id,
            trigger=PromoTriggers.LOYAL_3_PURCHASES,
            discount_percent=50,
        )

        if not promo_code:
            return False

        ref = await get_referral_percentages()

        if lang == "ru":
            text = (
                f"🎉 <b>Спасибо за доверие!</b>\n\n"
                f"Вы совершили {purchase_count} покупок — это круто!\n\n"
                f"В благодарность дарим вам <b>-50% на первую покупку</b> в PVNDORA:\n\n"
                f"🎁 <b>Промокод: {promo_code}</b>\n\n"
                f"В PVNDORA вас ждут:\n"
                f"• 🚀 Мгновенная доставка\n"
                f"• 🛡 Гарантии на все товары\n"
                f"• 💰 Партнерка {ref['l1']}/{ref['l2']}/{ref['l3']}%\n"
                f"• 🎧 Круглосуточная поддержка\n\n"
                f"👉 @pvndora_ai_bot"
            )
        else:
            text = (
                f"🎉 <b>Thank you for your loyalty!</b>\n\n"
                f"You've made {purchase_count} purchases — awesome!\n\n"
                f"As a thank you, we're giving you <b>-50% off your first purchase</b> in PVNDORA:\n\n"
                f"🎁 <b>Promo code: {promo_code}</b>\n\n"
                f"In PVNDORA you get:\n"
                f"• 🚀 Instant delivery\n"
                f"• 🛡 Warranty on all products\n"
                f"• 💰 Affiliate {ref['l1']}/{ref['l2']}/{ref['l3']}%\n"
                f"• 🎧 24/7 support\n\n"
                f"👉 @pvndora_ai_bot"
            )

        from core.services.telegram_messaging import send_telegram_message as _send_msg

        return await _send_msg(
            chat_id=telegram_id, text=text, parse_mode="HTML", bot_token=TELEGRAM_TOKEN
        )

    except Exception as e:
        logger.warning(f"Failed to send loyal promo to {telegram_id}: {e}")
        return False


async def _deliver_order_item(
    db: Any, order_id: str, item: dict[str, Any], telegram_id: int
) -> bool:
    """Deliver a single order item. Returns True on success."""
    order_item_id = item["id"]
    product_id = item["product_id"]
    stock_item_id = item.get("stock_item_id")

    # Find or assign stock
    stock_item_id = await _find_or_assign_stock(db, product_id, stock_item_id)
    if not stock_item_id:
        logger.warning(f"No stock available for order {order_id}, product {product_id}")
        return False

    # Get content
    content, product_name = await _get_stock_content(db, stock_item_id)
    if not content:
        logger.warning(f"Stock item {stock_item_id} not found")
        return False

    # Mark as sold and update order item
    await _mark_stock_as_sold(db, stock_item_id)
    await _update_order_item_delivered(db, order_item_id, stock_item_id, content)

    # Send delivery message
    lang = await _get_user_language(db, telegram_id)
    delivery_text = _format_delivery_message(lang, product_name, order_id, content)
    await send_telegram_message(telegram_id, delivery_text)

    # Get purchase count and send offer
    purchase_count = await _get_user_purchase_count(db, telegram_id)
    await asyncio.sleep(10)

    offer_text = await _format_offer_message(lang, product_name, purchase_count)
    await send_telegram_message(telegram_id, offer_text)

    # Send loyal promo if eligible
    if purchase_count >= 3:
        user_lookup = (
            await db.client.table("users")
            .select("id")
            .eq("telegram_id", telegram_id)
            .single()
            .execute()
        )
        if user_lookup.data:
            await _send_loyal_promo_if_eligible(
                user_lookup.data.get("id"), telegram_id, lang, purchase_count
            )

    return True


async def deliver_discount_order(db: Any, order_id: str, order_data: dict[str, Any]) -> bool:
    """Deliver a discount order."""
    try:
        telegram_id = order_data.get("user_telegram_id")

        order_items_result = (
            await db.client.table("order_items")
            .select("id, product_id, stock_item_id")
            .eq("order_id", order_id)
            .execute()
        )

        if not order_items_result.data:
            logger.warning(f"No order items for order {order_id}")
            return False

        # Track delivery success for each item
        all_delivered = True
        failed_items: list[dict[str, str]] = []

        for item_raw in order_items_result.data:
            if not isinstance(item_raw, dict):
                logger.warning(f"Invalid item format in order {order_id}: {item_raw}")
                all_delivered = False
                continue

            item = cast(dict[str, Any], item_raw)
            success = await _deliver_order_item(db, order_id, item, telegram_id)
            if not success:
                all_delivered = False
                item_id = item.get("id", "unknown")
                product_id = item.get("product_id", "unknown")
                failed_items.append({"item_id": item_id, "product_id": product_id})
                logger.warning(
                    f"Failed to deliver item {item_id} (product {product_id}) for order {order_id}"
                )

        # Only mark order as delivered if ALL items were successfully delivered
        if all_delivered:
            await (
                db.client.table("orders")
                .update({"status": "delivered", "delivered_at": datetime.now(UTC).isoformat()})
                .eq("id", order_id)
                .execute()
            )
            logger.info(f"Discount order {order_id} delivered successfully via cron fallback")
            return True

        total_items = len(order_items_result.data) if order_items_result.data else 0
        failed_count = len(failed_items)
        logger.error(
            f"Discount order {order_id} partially failed: {failed_count}/{total_items} items failed. "
            f"Failed items: {failed_items}. Order status remains 'paid'."
        )
        return False

    except Exception:
        logger.exception(f"Failed to deliver discount order {order_id}")
        return False


@app.get("/api/cron/deliver_overdue_discount")
async def deliver_overdue_discount(request: Request):
    """Find and deliver overdue discount orders."""
    auth_header = request.headers.get("Authorization", "")
    if CRON_SECRET and auth_header != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        db = await get_database_async()
        now = datetime.now(UTC).isoformat()

        result = (
            await db.client.table("orders")
            .select("id, user_telegram_id, source_channel, scheduled_delivery_at")
            .eq("status", "paid")
            .eq("source_channel", "discount")
            .lte("scheduled_delivery_at", now)
            .limit(10)
            .execute()
        )

        overdue_orders = result.data or []

        if not overdue_orders:
            logger.info("No overdue discount orders to deliver")
            return JSONResponse({"ok": True, "delivered": 0})

        logger.info(f"Found {len(overdue_orders)} overdue discount orders to deliver")

        delivered_count = 0
        for order_raw in overdue_orders:
            if not isinstance(order_raw, dict):
                continue
            order = cast(dict[str, Any], order_raw)
            if order.get("id") and await deliver_discount_order(db, order["id"], order):
                delivered_count += 1

        return JSONResponse(
            {"ok": True, "checked": len(overdue_orders), "delivered": delivered_count}
        )

    except Exception as e:
        logger.exception("deliver_overdue_discount error")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
