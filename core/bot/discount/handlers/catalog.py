"""Discount bot catalog handlers."""
import asyncio
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from core.services.database import User, get_database
from core.services.domains import InsuranceService
from core.logging import get_logger
from ..keyboards import (
    get_categories_keyboard,
    get_products_keyboard,
    get_product_card_keyboard,
)

logger = get_logger(__name__)

router = Router(name="discount_catalog")

# Cache for pagination
_products_cache: dict = {}


async def get_categories(db) -> list:
    """Get product categories."""
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("categories").select("*").eq(
                "is_active", True
            ).order("sort_order").execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return []


async def get_products_by_category(db, category_id: Optional[str] = None) -> list:
    """Get products with discount_price and stock count."""
    try:
        query = db.client.table("products").select(
            "id, name, description, discount_price, category_id, status"
        ).eq("status", "active").not_.is_("discount_price", "null")
        
        if category_id:
            # Find full UUID from short ID
            cat_result = await asyncio.to_thread(
                lambda: db.client.table("categories").select("id").ilike(
                    "id", f"{category_id}%"
                ).limit(1).execute()
            )
            if cat_result.data:
                full_cat_id = cat_result.data[0]["id"]
                query = query.eq("category_id", full_cat_id)
        
        result = await asyncio.to_thread(lambda: query.execute())
        products = result.data or []
        
        # Get stock counts for each product
        for p in products:
            stock_result = await asyncio.to_thread(
                lambda pid=p["id"]: db.client.table("stock_items").select(
                    "id", count="exact"
                ).eq("product_id", pid).eq("status", "available").is_(
                    "sold_at", "null"
                ).execute()
            )
            p["available_count"] = stock_result.count if stock_result.count else 0
        
        return products
    except Exception as e:
        logger.error(f"Failed to get products: {e}")
        return []


async def get_product_by_id(db, product_id: str) -> Optional[dict]:
    """Get single product by short ID."""
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("products").select("*").ilike(
                "id", f"{product_id}%"
            ).limit(1).execute()
        )
        
        if not result.data:
            return None
        
        product = result.data[0]
        
        # Get stock count
        stock_result = await asyncio.to_thread(
            lambda: db.client.table("stock_items").select(
                "id", count="exact"
            ).eq("product_id", product["id"]).eq("status", "available").is_(
                "sold_at", "null"
            ).execute()
        )
        product["available_count"] = stock_result.count if stock_result.count else 0
        
        return product
    except Exception as e:
        logger.error(f"Failed to get product: {e}")
        return None


@router.message(F.text.in_(["🛒 Каталог", "🛒 Catalog"]))
async def msg_catalog(message: Message, db_user: User):
    """Show catalog categories."""
    lang = db_user.language_code
    db = get_database()
    
    categories = await get_categories(db)
    
    if not categories:
        text = "Категории не найдены." if lang == "ru" else "No categories found."
        await message.answer(text)
        return
    
    text = (
        "📁 <b>Выберите категорию:</b>"
    ) if lang == "ru" else (
        "📁 <b>Select a category:</b>"
    )
    
    await message.answer(
        text,
        reply_markup=get_categories_keyboard(categories, lang),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "discount:categories")
async def cb_categories(callback: CallbackQuery, db_user: User):
    """Show catalog categories."""
    lang = db_user.language_code
    db = get_database()
    
    categories = await get_categories(db)
    
    text = (
        "📁 <b>Выберите категорию:</b>"
    ) if lang == "ru" else (
        "📁 <b>Select a category:</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_categories_keyboard(categories, lang),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("discount:cat:"))
async def cb_category_selected(callback: CallbackQuery, db_user: User):
    """Show products in category."""
    lang = db_user.language_code
    db = get_database()
    
    category_id = callback.data.split(":")[2]
    
    products = await get_products_by_category(db, category_id)
    
    # Cache for pagination
    cache_key = f"{db_user.telegram_id}:{category_id}"
    _products_cache[cache_key] = products
    
    if not products:
        text = (
            "В этой категории пока нет товаров."
        ) if lang == "ru" else (
            "No products in this category yet."
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_categories_keyboard(await get_categories(db), lang),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    text = (
        "🛒 <b>Товары:</b>\n\n"
        "🟢 — в наличии\n"
        "🟡 — предзаказ"
    ) if lang == "ru" else (
        "🛒 <b>Products:</b>\n\n"
        "🟢 — in stock\n"
        "🟡 — pre-order"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_products_keyboard(products, lang, category_id, page=0),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("discount:page:"))
async def cb_products_page(callback: CallbackQuery, db_user: User):
    """Handle products pagination."""
    lang = db_user.language_code
    
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
        "🛒 <b>Товары:</b>\n\n"
        "🟢 — в наличии\n"
        "🟡 — предзаказ"
    ) if lang == "ru" else (
        "🛒 <b>Products:</b>\n\n"
        "🟢 — in stock\n"
        "🟡 — pre-order"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_products_keyboard(products, lang, category_id, page=page),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("discount:prod:"))
async def cb_product_selected(callback: CallbackQuery, db_user: User):
    """Show product card."""
    lang = db_user.language_code
    db = get_database()
    
    product_id = callback.data.split(":")[2]
    
    product = await get_product_by_id(db, product_id)
    
    if not product:
        await callback.answer(
            "Товар не найден" if lang == "ru" else "Product not found",
            show_alert=True
        )
        return
    
    # Get insurance options
    insurance_service = InsuranceService(db.client)
    insurance_options = await insurance_service.get_options_for_product(product["id"])
    
    name = product.get("name", "Product")
    description = product.get("description", "")
    discount_price = product.get("discount_price", 0)
    available = product.get("available_count", 0)
    
    stock_status = "✅ В наличии" if available > 0 else "🟡 Предзаказ"
    if lang != "ru":
        stock_status = "✅ In stock" if available > 0 else "🟡 Pre-order"
    
    text = (
        f"<b>{name}</b>\n\n"
        f"{description[:200]}{'...' if len(description) > 200 else ''}\n\n"
        f"💰 <b>Цена:</b> ${discount_price:.0f}\n"
        f"📦 <b>Статус:</b> {stock_status}\n\n"
    ) if lang == "ru" else (
        f"<b>{name}</b>\n\n"
        f"{description[:200]}{'...' if len(description) > 200 else ''}\n\n"
        f"💰 <b>Price:</b> ${discount_price:.0f}\n"
        f"📦 <b>Status:</b> {stock_status}\n\n"
    )
    
    if insurance_options:
        text += "🛡 <b>Страховка</b> — замена при проблеме\n" if lang == "ru" else "🛡 <b>Insurance</b> — replacement if issue\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_product_card_keyboard(
            product["id"],
            discount_price,
            [{"id": io.id, "duration_days": io.duration_days, "price_percent": io.price_percent} for io in insurance_options],
            lang,
            in_stock=available > 0
        ),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    """No-op callback for decorative buttons."""
    await callback.answer()
