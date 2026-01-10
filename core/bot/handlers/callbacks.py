"""Callback query handlers for inline keyboard buttons.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from core.services.database import User, get_database
from core.services.money import to_float
from core.i18n import get_text
from core.bot.keyboards import get_product_keyboard
from core.bot.states import TicketStates, ReviewStates
from core.bot.handlers.helpers import WEBAPP_URL
from core.logging import get_logger

logger = get_logger(__name__)

router = Router()


# ==================== CHANNEL SUBSCRIPTION ====================

@router.callback_query(F.data == "pvndora:check_sub")
async def callback_check_subscription(callback: CallbackQuery, db_user: User, bot: Bot):
    """Re-check channel subscription."""
    from core.bot.middlewares import REQUIRED_CHANNEL
    
    lang = db_user.language_code
    
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=db_user.telegram_id)
        
        if member.status in ("left", "kicked"):
            await callback.answer(
                "Вы ещё не подписались на канал!" if lang == "ru" else "You haven't subscribed yet!",
                show_alert=True
            )
            return
        
        # Subscribed - confirm and suggest /start
        await callback.message.delete()
        
        text = (
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     ✅ <b>ПОДПИСКА ПОДТВЕРЖДЕНА</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Добро пожаловать в PVNDORA!\n"
            "Нажмите /start для начала."
        ) if lang == "ru" else (
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "     ✅ <b>SUBSCRIPTION CONFIRMED</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Welcome to PVNDORA!\n"
            "Press /start to begin."
        )
        
        # Send directly to user (not via deleted message context)
        await bot.send_message(chat_id=callback.from_user.id, text=text, parse_mode=ParseMode.HTML)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Failed to check subscription: {e}")
        await callback.answer(
            "Ошибка проверки" if lang == "ru" else "Check error", 
            show_alert=True
        )


# ==================== SIMPLE CALLBACKS ====================

@router.callback_query(F.data.startswith("waitlist:"))
async def callback_waitlist(callback: CallbackQuery, db_user: User):
    """Handle waitlist button click"""
    product_id = callback.data.split(":")[1]
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if product:
        await db.add_to_waitlist(db_user.id, product.name)
        await callback.answer(
            get_text("waitlist_added", db_user.language_code, product=product.name),
            show_alert=True
        )
    else:
        await callback.answer("Product not found", show_alert=True)


@router.callback_query(F.data.startswith("wishlist:"))
async def callback_wishlist(callback: CallbackQuery, db_user: User):
    """Handle add to wishlist button click"""
    product_id = callback.data.split(":")[1]
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if product:
        await db.add_to_wishlist(db_user.id, product_id)
        await callback.answer(
            get_text("wishlist_added", db_user.language_code, product=product.name),
            show_alert=True
        )
    else:
        await callback.answer("Product not found", show_alert=True)


@router.callback_query(F.data.startswith("support:"))
async def callback_support(callback: CallbackQuery, db_user: User):
    """Handle support button click"""
    await callback.answer(
        get_text("support_ticket", db_user.language_code),
        show_alert=True
    )


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, db_user: User):
    """Handle cancel button click"""
    await callback.message.delete()
    await callback.answer()


# ==================== REVIEW FLOW ====================

@router.callback_query(F.data.startswith("review:"))
async def callback_review(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Handle review button click - start review flow"""
    order_id = callback.data.split(":")[1]
    
    await state.update_data(order_id=order_id)
    await state.set_state(ReviewStates.waiting_for_rating)
    
    rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rating:1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rating:2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating:3"),
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating:4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating:5"),
        ]
    ])
    
    await callback.message.answer(
        "⭐ <b>Оставить отзыв</b>\n\n"
        "Как бы вы оценили покупку?\n"
        "💡 Получите 5% кэшбэка за честный отзыв!",
        reply_markup=rating_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rating:"))
async def callback_rating(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Handle rating selection in review flow"""
    rating = int(callback.data.split(":")[1])
    
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_for_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить текст", callback_data="review_skip_text")]
    ])
    
    await callback.message.edit_text(
        f"⭐ Оценка: {'⭐' * rating}\n\n"
        "Хотите добавить текстовый отзыв? (опционально)\n"
        "Просто напишите или нажмите Пропустить.",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "review_skip_text")
async def callback_review_skip_text(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Submit review without text"""
    data = await state.get_data()
    await _submit_review(callback, data.get("order_id"), data.get("rating", 5), None, db_user)
    await state.clear()


@router.message(ReviewStates.waiting_for_text)
async def handle_review_text(message: Message, db_user: User, state: FSMContext):
    """Handle text input for review"""
    data = await state.get_data()
    await _submit_review_from_message(message, data.get("order_id"), data.get("rating", 5), message.text, db_user)
    await state.clear()


async def _submit_review(callback: CallbackQuery, order_id: str, rating: int, text: str | None, db_user: User):
    """Submit the review and trigger cashback."""
    db = get_database()
    order = await db.get_order_by_id(order_id)
    if not order:
        await callback.message.edit_text("❌ Заказ не найден")
        return
    
    # Get product_id from order_items (source of truth)
    order_items = await db.get_order_items_by_order(order_id)
    product_id = order_items[0].get("product_id") if order_items else None
    
    await db.create_review(user_id=db_user.id, order_id=order_id, product_id=product_id, rating=rating, text=text)
    
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK, body={
            "user_telegram_id": db_user.telegram_id, "order_id": order_id, "order_amount": to_float(order.amount)
        })
    except Exception as e:
        logger.warning(f"Failed to trigger cashback worker: {e}", exc_info=True)
    
    await callback.message.edit_text(f"✅ Спасибо за отзыв! {'⭐' * rating}\n\nВаш 5% кэшбэк скоро будет начислен.")


async def _submit_review_from_message(message: Message, order_id: str, rating: int, text: str | None, db_user: User):
    """Submit the review from message context."""
    db = get_database()
    order = await db.get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Заказ не найден")
        return
    
    # Get product_id from order_items (source of truth)
    order_items = await db.get_order_items_by_order(order_id)
    product_id = order_items[0].get("product_id") if order_items else None
    
    await db.create_review(user_id=db_user.id, order_id=order_id, product_id=product_id, rating=rating, text=text)
    
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK, body={
            "user_telegram_id": db_user.telegram_id, "order_id": order_id, "order_amount": to_float(order.amount)
        })
    except Exception as e:
        logger.warning(f"Failed to trigger cashback worker: {e}", exc_info=True)
    
    await message.answer(f"✅ Спасибо за отзыв! {'⭐' * rating}\n\nВаш 5% кэшбэк скоро будет начислен.")


# ==================== TICKET FLOW ====================

@router.callback_query(F.data == "create_ticket")
async def callback_create_ticket_start(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Start support ticket creation flow"""
    await state.set_state(TicketStates.waiting_for_order_id)
    await callback.message.answer(
        "🎫 <b>Создать обращение</b>\n\nУкажите номер заказа или 'skip'.",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_order:"))
async def callback_create_ticket_with_order(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Start ticket with pre-filled order ID"""
    order_id = callback.data.split(":")[1]
    await state.update_data(order_id=order_id)
    await state.set_state(TicketStates.waiting_for_description)
    await callback.message.answer(f"📝 Заказ: {order_id[:8]}...\n\nОпишите проблему:")
    await callback.answer()


@router.message(TicketStates.waiting_for_order_id)
async def handle_ticket_order_id(message: Message, db_user: User, state: FSMContext):
    """Handle order ID input for ticket"""
    order_id = message.text.strip()
    await state.update_data(order_id=None if order_id.lower() == 'skip' else order_id)
    await state.set_state(TicketStates.waiting_for_description)
    await message.answer("📝 Опишите вашу проблему подробно:")


@router.message(TicketStates.waiting_for_description)
async def handle_ticket_description(message: Message, db_user: User, state: FSMContext):
    """Handle ticket description and create ticket"""
    data = await state.get_data()
    db = get_database()
    
    try:
        result = await db.client.table("support_tickets").insert({
            "user_id": db_user.id,
            "order_id": data.get("order_id"),
            "type": "general",
            "description": message.text.strip(),
            "status": "open"
        }).execute()
        ticket_id = result.data[0]["id"] if result.data else None
        await message.answer(f"✅ Обращение создано!\n🎫 Номер: {ticket_id[:8] if ticket_id else 'N/A'}...")
    except Exception as e:
        logger.error(f"Failed to create ticket: {e}", exc_info=True)
        await message.answer("❌ Не удалось создать обращение.")
    
    await state.clear()


# ==================== QUICK ACTIONS ====================

@router.callback_query(F.data.startswith("buy_again:"))
async def callback_buy_again(callback: CallbackQuery, db_user: User, bot: Bot):
    """Quick reorder from order history"""
    order_id = callback.data.split(":")[1]
    db = get_database()
    order = await db.get_order_by_id(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Get product from order_items (source of truth)
    order_items = await db.get_order_items_by_order(order_id)
    product_id = order_items[0].get("product_id") if order_items else None
    
    product = await db.get_product_by_id(product_id) if product_id else None
    if not product:
        await callback.answer("❌ Товар больше не доступен", show_alert=True)
        return
    
    await callback.message.answer(
        f"🔄 <b>Повторный заказ</b>\n\n📦 {product.name}\n💰 {product.price}₽\n",
        reply_markup=get_product_keyboard(db_user.language_code, product.id, WEBAPP_URL, in_stock=product.stock_count > 0),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("preorder:"))
async def callback_preorder(callback: CallbackQuery, db_user: User, bot: Bot):
    """Handle pre-order button click"""
    product_id = callback.data.split(":")[1]
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Product not found", show_alert=True)
        return
    
    checkout_url = f"{WEBAPP_URL}?startapp=pay_{product_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 {get_text('btn_pay', db_user.language_code)} {product.price}₽",
            web_app=WebAppInfo(url=checkout_url)
        )]
    ])
    
    fulfillment_hours = getattr(product, 'fulfillment_time_hours', 48)
    await callback.message.answer(
        f"📦 Предзаказ: **{product.name}**\n💰 {product.price}₽\n⏱ {fulfillment_hours} часов",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()