"""Command handlers: /start, /help, /my_orders, /wishlist, /referral, /faq, /terms, /support"""
import asyncio

from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from core.services.database import User, get_database
from core.i18n import get_text
from core.bot.keyboards import get_product_keyboard
from core.bot.handlers.helpers import safe_answer, WEBAPP_URL
from core.logging import get_logger

logger = get_logger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, bot: Bot):
    """Handle /start command with optional referral and onboarding"""
    db = get_database()
    
    # Check if this is a returning user
    history = await db.get_chat_history(db_user.id, limit=1)
    is_new_user = not history
    
    # Parse referral from start parameter
    if message.text and "start" in message.text.lower():
        parts = message.text.split()
        for part in parts:
            if part.startswith("ref_"):
                try:
                    referral_id = int(part.replace("ref_", ""))
                    referrer = await db.get_user_by_telegram_id(referral_id)
                    if referrer and referrer.id != db_user.id:
                        # Track referral click (increment referrer's click count)
                        await asyncio.to_thread(
                            lambda: db.client.rpc("increment_referral_click", {
                                "referrer_user_id": referrer.id
                            }).execute()
                        )
                        
                        # Set referrer for new user if not already set
                        if not db_user.referrer_id:
                            await asyncio.to_thread(
                                lambda: db.client.table("users").update({
                                    "referrer_id": referrer.id
                                }).eq("id", db_user.id).execute()
                            )
                except Exception as e:
                    logger.warning(f"Failed to process referral: {e}", exc_info=True)
    
    onboarding_text = get_text(
        "welcome" if is_new_user else "welcome_back",
        db_user.language_code
    )
    
    await db.save_chat_message(db_user.id, "assistant", onboarding_text)
    await safe_answer(message, onboarding_text, parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User):
    """Handle /help command with quick access buttons"""
    text = get_text("help", db_user.language_code)
    
    # Get localized button texts
    faq_text = get_text("faq.title", db_user.language_code, default="FAQ")
    terms_text = get_text("terms.title", db_user.language_code, default="Условия")
    support_text = get_text("contacts.support", db_user.language_code, default="Поддержка")
    
    # Add keyboard with quick access buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"❓ {faq_text}",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=faq")
            ),
            InlineKeyboardButton(
                text=f"📄 {terms_text}",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=terms")
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🆘 {support_text}",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=contacts")
            )
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(Command("faq"))
async def cmd_faq(message: Message, db_user: User):
    """Handle /faq command - open FAQ page"""
    title = get_text("faq.title", db_user.language_code, default="FAQ")
    subtitle = get_text("faq.subtitle", db_user.language_code, default="Часто задаваемые вопросы")
    text = f"<b>{title}</b>\n\n{subtitle}"
    btn_text = get_text("btn_open_faq", db_user.language_code, default="📖 Открыть FAQ")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=btn_text,
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=faq")
        )
    ]])
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(Command("terms"))
async def cmd_terms(message: Message, db_user: User):
    """Handle /terms command - open Terms of Service page"""
    title = get_text("terms.title", db_user.language_code, default="Пользовательское соглашение")
    subtitle = get_text("terms.subtitle", db_user.language_code, default="Условия использования сервиса")
    text = f"<b>{title}</b>\n\n{subtitle}"
    btn_text = get_text("btn_open_terms", db_user.language_code, default="📄 Открыть условия")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=btn_text,
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=terms")
        )
    ]])
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(Command("support"))
async def cmd_support(message: Message, db_user: User):
    """Handle /support command - open support/contacts page"""
    title = get_text("contacts.title", db_user.language_code, default="Поддержка")
    subtitle = get_text("contacts.supportDescription", db_user.language_code, default="Свяжитесь с нами для получения помощи")
    text = f"<b>{title}</b>\n\n{subtitle}"
    btn_text = get_text("btn_open_support", db_user.language_code, default="🆘 Открыть поддержку")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=btn_text,
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=contacts")
        )
    ]])
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(Command("my_orders"))
async def cmd_my_orders(message: Message, db_user: User):
    """Handle /my_orders command - show purchase history"""
    db = get_database()
    orders = await db.get_user_orders(db_user.id, limit=10)
    
    if not orders:
        await message.answer(get_text("no_orders", db_user.language_code))
        return
    
    order_lines = []
    for order in orders:
        # Get product name from order_items (source of truth)
        order_items = await db.get_order_items_by_order(order.id)
        if order_items:
            product_id = order_items[0].get("product_id")
            product = await db.get_product_by_id(product_id) if product_id else None
            product_name = product.name if product else "Unknown"
        else:
            product_name = "Unknown"
        
        status_map = {
            "pending": "⏳", "paid": "💳", "prepaid": "💳",
            "partial": "📦", "cancelled": "❌", "refunded": "↩️", "delivered": "✅"
        }
        status_icon = status_map.get(order.status, "❓")
        order_lines.append(f"{status_icon} {product_name} - {order.amount}₽")
    
    text = get_text(
        "order_history",
        db_user.language_code,
        orders="\n".join(order_lines),
        count=len(orders)
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("wishlist"))
async def cmd_wishlist(message: Message, db_user: User):
    """Handle /wishlist command - show saved products"""
    db = get_database()
    products = await db.get_wishlist(db_user.id)
    
    if not products:
        await message.answer(get_text("wishlist_empty", db_user.language_code))
        return
    
    for product in products:
        stock_status = (
            get_text("stock_available", db_user.language_code)
            if product.stock_count > 0
            else get_text("stock_empty", db_user.language_code)
        )
        
        text = get_text(
            "product_card",
            db_user.language_code,
            name=product.name,
            price=product.price,
            rating="4.8",
            reviews="0",
            stock_status=stock_status,
            description=product.description or ""
        )
        
        await message.answer(
            text,
            reply_markup=get_product_keyboard(
                db_user.language_code,
                product.id,
                WEBAPP_URL,
                in_stock=product.stock_count > 0
            ),
            parse_mode=ParseMode.HTML
        )


@router.message(Command("referral"))
async def cmd_referral(message: Message, db_user: User, bot: Bot):
    """Handle /referral command - show referral link"""
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    
    text = get_text(
        "referral_link",
        db_user.language_code,
        link=referral_link,
        percent=db_user.personal_ref_percent
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


