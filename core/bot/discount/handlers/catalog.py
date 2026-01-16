"""Discount bot catalog handlers."""

from typing import TYPE_CHECKING, Any, cast

from aiogram import F, Router

if TYPE_CHECKING:
    from core.services.database import Database
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message

from core.bot.discount.keyboards import get_product_card_keyboard, get_products_keyboard
from core.logging import get_logger
from core.services.database import User, get_database
from core.services.domains import InsuranceService

logger = get_logger(__name__)

router = Router(name="discount_catalog")

# Cache for pagination
_products_cache: dict[str, Any] = {}


async def get_user_currency_info(db_user: User) -> tuple[str, float]:
    """Get user currency and exchange rate."""
    currency = "USD"
    exchange_rate = 1.0

    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        redis = get_redis()
        currency_service = get_currency_service(redis)

        preferred_currency = getattr(db_user, "preferred_currency", None)
        user_lang = getattr(db_user, "language_code", "en") or "en"

        currency = currency_service.get_user_currency(user_lang, preferred_currency)

        # CrystalPay supports: USD, RUB, EUR, UAH, TRY, INR, AED
        supported_currencies = ["USD", "RUB", "EUR", "UAH", "TRY", "INR", "AED"]
        if currency not in supported_currencies:
            currency = "USD"

        if currency != "USD":
            exchange_rate = currency_service.get_exchange_rate(currency)
    except Exception as e:
        logger.warning("Failed to get user currency: %s", type(e).__name__)

    return currency, exchange_rate


async def get_unique_categories(db: "Database") -> list[str]:
    """Extract unique categories from products with discount_price.

    Uses products_with_stock_summary VIEW for consistency with other queries.
    """
    try:
        result = (
            await db.client.table("products_with_stock_summary")
            .select("categories")
            .eq("status", "active")
            .not_.is_("discount_price", "null")
            .execute()
        )

        # Extract unique categories from all products
        all_categories = set()
        for product in result.data or []:
            cats = product.get("categories") or []
            for cat in cats:
                if cat:
                    all_categories.add(cat)

        # Sort and return as list of dicts for compatibility
        sorted_categories: list[str] = sorted([str(cat) for cat in all_categories if cat])
        return [{"id": cat, "name": cat} for cat in sorted_categories]
    except Exception:
        logger.exception("Failed to get categories")
        return []


async def get_all_discount_products(db: "Database") -> list[dict[str, Any]]:
    """Get all products with discount_price.

    Uses products_with_stock_summary VIEW to eliminate N+1 queries.
    Single query returns products with aggregated stock counts.
    """
    try:
        # Use VIEW for aggregated stock data (no N+1!)
        result = (
            await db.client.table("products_with_stock_summary")
            .select("id, name, description, discount_price, categories, status, stock_count")
            .eq("status", "active")
            .not_.is_("discount_price", "null")
            .execute()
        )

        products = result.data or []

        # Map stock_count to available_count for compatibility
        result_list: list[dict[str, Any]] = []
        for p in products:
            if isinstance(p, dict):
                p["available_count"] = p.get("stock_count", 0) or 0
                result_list.append(p)

        return result_list
    except Exception:
        logger.exception("Failed to get products")
        return []


async def get_products_by_category(db, category_name: str | None = None) -> list:
    """Get products with discount_price, optionally filtered by category."""
    products = await get_all_discount_products(db)

    if category_name and category_name != "all":
        # Filter by category (categories is an array field)
        products = [p for p in products if category_name in (p.get("categories") or [])]

    return products


async def get_product_by_id(db: "Database", product_id: str) -> dict[str, Any] | None:
    """Get single product by short ID (first 8 chars of UUID)."""
    try:
        # Get all discount products and filter by prefix
        # Note: .ilike() doesn't work with UUID fields in Supabase PostgREST
        all_products = await get_all_discount_products(db)

        # Filter by UUID prefix (first 8 chars)
        product = None
        for p in all_products:
            if str(p["id"]).startswith(product_id.lower()) or str(p["id"]).startswith(
                product_id.upper(),
            ):
                product = cast(dict[str, Any], p)
                break

        return product
    except Exception:
        logger.exception("Failed to get product")
        return None


@router.message(F.text.in_(["🛒 Каталог", "🛒 Catalog"]))
async def msg_catalog(message: Message, db_user: User) -> None:
    """Show catalog - all discount products directly."""
    lang = db_user.language_code
    db = get_database()

    # Get user currency and exchange rate
    currency, exchange_rate = await get_user_currency_info(db_user)

    # Get all discount products directly (no separate categories table)
    products = await get_all_discount_products(db)

    if not products:
        text = "Товары не найдены." if lang == "ru" else "No products found."
        await message.answer(text)
        return

    # Cache for pagination
    cache_key = f"{db_user.telegram_id}:all"
    _products_cache[cache_key] = products

    text = (
        ("🛒 <b>Каталог товаров:</b>\n\n🟢 — в наличии\n🟡 — предзаказ")
        if lang == "ru"
        else ("🛒 <b>Product Catalog:</b>\n\n🟢 — in stock\n🟡 — pre-order")
    )

    await message.answer(
        text,
        reply_markup=get_products_keyboard(
            products,
            lang,
            "all",
            page=0,
            exchange_rate=exchange_rate,
            currency=currency,
        ),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "discount:catalog")
async def cb_catalog(callback: CallbackQuery, db_user: User) -> None:
    """Show catalog - all discount products."""
    lang = db_user.language_code
    db = get_database()

    # Get user currency and exchange rate
    currency, exchange_rate = await get_user_currency_info(db_user)

    products = await get_all_discount_products(db)

    # Cache for pagination
    cache_key = f"{db_user.telegram_id}:all"
    _products_cache[cache_key] = products

    text = (
        ("🛒 <b>Каталог товаров:</b>\n\n🟢 — в наличии\n🟡 — предзаказ")
        if lang == "ru"
        else ("🛒 <b>Product Catalog:</b>\n\n🟢 — in stock\n🟡 — pre-order")
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_products_keyboard(
            products,
            lang,
            "all",
            page=0,
            exchange_rate=exchange_rate,
            currency=currency,
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("discount:page:"))
async def cb_products_page(callback: CallbackQuery, db_user: User) -> None:
    """Handle products pagination."""
    lang = db_user.language_code

    # Get user currency and exchange rate
    currency, exchange_rate = await get_user_currency_info(db_user)

    parts = callback.data.split(":")
    page = int(parts[2])
    category_id = parts[3] if len(parts) > 3 else None

    # Get from cache
    cache_key = f"{db_user.telegram_id}:{category_id}"
    products = _products_cache.get(cache_key, [])

    if not products:
        # Reload
        db = get_database()
        products = await get_products_by_category(db, category_id if category_id != "all" else None)
        _products_cache[cache_key] = products

    text = (
        ("🛒 <b>Товары:</b>\n\n🟢 — в наличии\n🟡 — предзаказ")
        if lang == "ru"
        else ("🛒 <b>Products:</b>\n\n🟢 — in stock\n🟡 — pre-order")
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_products_keyboard(
            products,
            lang,
            category_id,
            page=page,
            exchange_rate=exchange_rate,
            currency=currency,
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# Helper to format product description (reduces cognitive complexity)
def _format_product_description(desc: str) -> str:
    """Format product description with length limit."""
    if len(desc) > 200:
        return f"{desc[:200]}..."
    return desc


# Helper to get stock status text (reduces cognitive complexity)
def _get_stock_status_text(is_ru: bool, is_available: bool) -> str:
    """Get stock status text based on language and availability."""
    if is_ru:
        return "✅ В наличии" if is_available else "🟡 Предзаказ"
    return "✅ In stock" if is_available else "🟡 Pre-order"


# Helper to format product card text (reduces cognitive complexity)
def _format_product_card_text(
    name: str,
    description: str,
    price_label: str,
    status_label: str,
    stock_status: str,
    currency_symbol: str,
    discount_price_display: float,
) -> str:
    """Format product card text."""
    return (
        f"<b>{name}</b>\n\n"
        f"{_format_product_description(description)}\n\n"
        f"💰 <b>{price_label}:</b> {currency_symbol}{discount_price_display:.0f}\n"
        f"📦 <b>{status_label}:</b> {stock_status}\n\n"
    )


@router.callback_query(F.data.startswith("discount:prod:"))
async def cb_product_selected(callback: CallbackQuery, db_user: User) -> None:
    """Show product card."""
    lang = db_user.language_code
    db = get_database()

    currency, exchange_rate = await get_user_currency_info(db_user)
    product_id = callback.data.split(":")[2]

    product = await get_product_by_id(db, product_id)

    if not product:
        await callback.answer(
            "Товар не найден" if lang == "ru" else "Product not found",
            show_alert=True,
        )
        return

    insurance_service = InsuranceService(db.client)
    insurance_options = await insurance_service.get_options_for_product(product["id"])

    name = product.get("name", "Product")
    description = product.get("description", "")
    discount_price_usd = float(product.get("discount_price", 0) or 0)
    available = product.get("available_count", 0)

    discount_price_display = discount_price_usd * exchange_rate

    from core.services.currency import CURRENCY_SYMBOLS

    currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)

    price_label = "Цена" if lang == "ru" else "Price"
    status_label = "Статус" if lang == "ru" else "Status"
    stock_status = _get_stock_status_text(lang == "ru", available > 0)

    text = _format_product_card_text(
        name,
        description,
        price_label,
        status_label,
        stock_status,
        currency_symbol,
        discount_price_display,
    )

    if insurance_options:
        text += (
            "🛡 <b>Страховка</b> — замена при проблеме\n"
            if lang == "ru"
            else "🛡 <b>Insurance</b> — replacement if issue\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=get_product_card_keyboard(
            product["id"],
            discount_price_usd,
            [
                {"id": io.id, "duration_days": io.duration_days, "price_percent": io.price_percent}
                for io in insurance_options
            ],
            lang,
            in_stock=available > 0,
            exchange_rate=exchange_rate,
            currency=currency,
        ),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """No-op callback for decorative buttons."""
    await callback.answer()
