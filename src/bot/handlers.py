"""Telegram Bot Handlers"""
import os
import asyncio
import hashlib
import traceback
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext

from src.services.database import User, get_database
from src.i18n import get_text
from src.bot.keyboards import (
    get_shop_keyboard,
    get_product_keyboard,
    get_checkout_keyboard
)
from src.bot.states import TicketStates, ReviewStates

router = Router()

# Get webapp URL from environment
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


# ==================== HELPERS ====================

def get_share_keyboard(product_name: str = "") -> InlineKeyboardMarkup:
    """
    Get keyboard with share button using switchInlineQuery.
    
    Args:
        product_name: Product name to pre-fill in query
    
    Returns:
        Keyboard with share button
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Поделиться с друзьями",
            switch_inline_query=product_name
        )]
    ])


def get_share_current_chat_keyboard(product_name: str) -> InlineKeyboardMarkup:
    """
    Get keyboard for sharing in current chat.
    Uses switch_inline_query_current_chat.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Поделиться здесь",
            switch_inline_query_current_chat=product_name
        )]
    ])


async def safe_answer(message: Message, text: str, **kwargs):
    """
    Safely send message, handling Telegram API errors gracefully.
    Returns True if sent successfully, False otherwise.
    """
    try:
        # Validate text before sending
        if not text or not text.strip():
            print(f"ERROR: Attempted to send empty message to chat {message.chat.id}")
            return False
        
        # Log before sending (for debugging)
        print(f"DEBUG: safe_answer - chat_id: {message.chat.id}, text_length: {len(text)}, has_markup: {kwargs.get('reply_markup') is not None}")
        
        await message.answer(text, **kwargs)
        print(f"DEBUG: Message sent successfully to chat {message.chat.id}")
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        error_msg = str(e).lower()
        print(f"ERROR: Telegram API error in safe_answer: {e}")
        print(f"ERROR: Error message (lower): {error_msg}")
        if "chat not found" in error_msg or "chat_id" in error_msg:
            print(f"WARNING: Cannot send message to chat {message.chat.id}: chat not found")
        elif "bot was blocked" in error_msg or "forbidden" in error_msg:
            print(f"WARNING: Bot blocked by user {message.chat.id}")
        else:
            print(f"ERROR: Telegram API error details: {e}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error in safe_answer: {type(e).__name__}: {e}")
        print("ERROR: Full traceback:")
        traceback.print_exc()
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, bot: Bot):
    """Handle /start command with optional referral and onboarding"""
    db = get_database()
    
    # Check if this is a returning user
    history = await db.get_chat_history(db_user.id, limit=1)
    is_new_user = not history
    
    # Parse referral from start parameter
    referral_id = None
    if message.text and "start" in message.text.lower():
        parts = message.text.split()
        for part in parts:
            if part.startswith("ref_"):
                try:
                    referral_id = int(part.replace("ref_", ""))
                    # Get referrer user
                    referrer = await db.get_user_by_telegram_id(referral_id)
                    if referrer and referrer.id != db_user.id:
                        # Link referral - run in thread pool to avoid blocking event loop
                        await asyncio.to_thread(
                            lambda: db.client.table("users").update({
                                "referrer_id": referrer.id
                            }).eq("id", db_user.id).execute()
                        )
                except Exception:
                    pass
    
    if is_new_user:
        onboarding_text = get_text("welcome", db_user.language_code)
    else:
        onboarding_text = get_text("welcome_back", db_user.language_code)
    
    # Save bot's welcome message
    await db.save_chat_message(db_user.id, "assistant", onboarding_text)
    
    await safe_answer(
        message,
        onboarding_text,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: User):
    """Handle /help command"""
    text = get_text("help", db_user.language_code)
    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("my_orders"))
async def cmd_my_orders(message: Message, db_user: User):
    """Handle /my_orders command - show purchase history"""
    db = get_database()
    orders = await db.get_user_orders(db_user.id, limit=10)
    
    if not orders:
        await message.answer(get_text("no_orders", db_user.language_code))
        return
    
    # Format orders list
    order_lines = []
    for order in orders:
        product = await db.get_product_by_id(order.product_id)
        product_name = product.name if product else "Unknown"
        
        status_map = {
            "pending": "⏳",
            "paid": "💳",
            "completed": "✅",
            "failed": "❌",
            "refunded": "↩️"
        }
        status_icon = status_map.get(order.status, "❓")
        
        order_lines.append(
            f"{status_icon} {product_name} - {order.amount}₽"
        )
    
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


# ==================== CALLBACK HANDLERS ====================

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
    callback.data.split(":")[1]  # Extract order_id (not used yet)
    
    # TODO: Create support ticket
    await callback.answer(
        get_text("support_ticket", db_user.language_code),
        show_alert=True
    )


@router.callback_query(F.data.startswith("review:"))
async def callback_review(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Handle review button click - start review flow"""
    order_id = callback.data.split(":")[1]
    
    # Store order_id and start review flow
    await state.update_data(order_id=order_id)
    await state.set_state(ReviewStates.waiting_for_rating)
    
    # Rating buttons
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
    order_id = data.get("order_id")
    rating = data.get("rating", 5)
    
    await _submit_review(callback, order_id, rating, None, db_user)
    await state.clear()


@router.message(ReviewStates.waiting_for_text)
async def handle_review_text(message: Message, db_user: User, state: FSMContext):
    """Handle text input for review"""
    data = await state.get_data()
    order_id = data.get("order_id")
    rating = data.get("rating", 5)
    
    await _submit_review_from_message(message, order_id, rating, message.text, db_user)
    await state.clear()


async def _submit_review(
    callback: CallbackQuery,
    order_id: str,
    rating: int,
    text: str | None,
    db_user: User
):
    """Submit the review and trigger cashback."""
    db = get_database()
    
    # Get order info
    order = await db.get_order_by_id(order_id)
    if not order:
        await callback.message.edit_text("❌ Заказ не найден")
        return
    
    # Create review
    await db.create_review(
        user_id=db_user.id,
        order_id=order_id,
        product_id=order.product_id,
        rating=rating,
        text=text
    )
    
    # Trigger cashback worker via QStash (if available)
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(
            endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
            body={
                "user_telegram_id": db_user.telegram_id,
                "order_id": order_id,
                "order_amount": float(order.amount),
            }
        )
    except Exception as e:
        print(f"WARNING: Failed to trigger cashback worker: {e}")
    
    await callback.message.edit_text(
        f"✅ Спасибо за отзыв! {'⭐' * rating}\n\n"
        "Ваш 5% кэшбэк скоро будет начислен на баланс."
    )


async def _submit_review_from_message(
    message: Message,
    order_id: str,
    rating: int,
    text: str | None,
    db_user: User
):
    """Submit the review from message context."""
    db = get_database()
    
    # Get order info
    order = await db.get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Заказ не найден")
        return
    
    # Create review
    await db.create_review(
        user_id=db_user.id,
        order_id=order_id,
        product_id=order.product_id,
        rating=rating,
        text=text
    )
    
    # Trigger cashback worker
    try:
        from core.queue import publish_to_worker, WorkerEndpoints
        await publish_to_worker(
            endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
            body={
                "user_telegram_id": db_user.telegram_id,
                "order_id": order_id,
                "order_amount": float(order.amount),
            }
        )
    except Exception as e:
        print(f"WARNING: Failed to trigger cashback worker: {e}")
    
    await message.answer(
        f"✅ Спасибо за отзыв! {'⭐' * rating}\n\n"
        "Ваш 5% кэшбэк скоро будет начислен на баланс."
    )


# ==================== TICKET CREATION FLOW ====================

@router.callback_query(F.data == "create_ticket")
async def callback_create_ticket_start(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Start support ticket creation flow"""
    await state.set_state(TicketStates.waiting_for_order_id)
    
    await callback.message.answer(
        "🎫 <b>Создать обращение</b>\n\n"
        "Укажите номер заказа (можно найти в /my_orders).\n"
        "Или напишите 'skip' если это не связано с конкретным заказом.",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_order:"))
async def callback_create_ticket_with_order(callback: CallbackQuery, db_user: User, state: FSMContext):
    """Start ticket with pre-filled order ID"""
    order_id = callback.data.split(":")[1]
    
    await state.update_data(order_id=order_id)
    await state.set_state(TicketStates.waiting_for_description)
    
    await callback.message.answer(
        f"📝 Заказ: {order_id[:8]}...\n\n"
        "Опишите вашу проблему подробно:",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.message(TicketStates.waiting_for_order_id)
async def handle_ticket_order_id(message: Message, db_user: User, state: FSMContext):
    """Handle order ID input for ticket"""
    order_id = message.text.strip()
    
    if order_id.lower() == 'skip':
        await state.update_data(order_id=None)
    else:
        await state.update_data(order_id=order_id)
    
    await state.set_state(TicketStates.waiting_for_description)
    await message.answer("📝 Опишите вашу проблему подробно:")


@router.message(TicketStates.waiting_for_description)
async def handle_ticket_description(message: Message, db_user: User, state: FSMContext):
    """Handle ticket description and create ticket"""
    data = await state.get_data()
    order_id = data.get("order_id")
    description = message.text.strip()
    
    db = get_database()
    
    # Create support ticket in database
    try:
        # Use direct supabase client for ticket creation
        import asyncio
        result = await asyncio.to_thread(
            lambda: db.client.table("support_tickets").insert({
                "user_id": db_user.id,
                "order_id": order_id,
                "type": "general",
                "description": description,
                "status": "open"
            }).execute()
        )
        
        ticket_id = result.data[0]["id"] if result.data else None
        
        await message.answer(
            f"✅ Обращение создано!\n\n"
            f"🎫 Номер: {ticket_id[:8] if ticket_id else 'N/A'}...\n"
            f"Мы ответим в ближайшее время."
        )
    except Exception as e:
        print(f"ERROR: Failed to create ticket: {e}")
        await message.answer(
            "❌ Не удалось создать обращение. Попробуйте позже или напишите @support."
        )
    
    await state.clear()


# ==================== QUICK REORDER ====================

@router.callback_query(F.data.startswith("buy_again:"))
async def callback_buy_again(callback: CallbackQuery, db_user: User, bot: Bot):
    """Quick reorder from order history"""
    order_id = callback.data.split(":")[1]
    
    db = get_database()
    order = await db.get_order_by_id(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    product = await db.get_product_by_id(order.product_id)
    if not product:
        await callback.answer("❌ Товар больше не доступен", show_alert=True)
        return
    
    # Show product with buy button
    await callback.message.answer(
        f"🔄 <b>Повторный заказ</b>\n\n"
        f"📦 {product.name}\n"
        f"💰 {product.price}₽\n",
        reply_markup=get_product_keyboard(
            db_user.language_code,
            product.id,
            WEBAPP_URL,
            in_stock=product.stock_count > 0
        ),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("preorder:"))
async def callback_preorder(callback: CallbackQuery, db_user: User, bot: Bot):
    """Handle pre-order button click - open checkout in Mini App"""
    product_id = callback.data.split(":")[1]
    
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Product not found", show_alert=True)
        return
    
    # WebApp URL must be direct HTTPS URL, not t.me deep link
    checkout_url = f"{WEBAPP_URL}?startapp=pay_{product_id}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 {get_text('btn_pay', db_user.language_code)} {product.price}₽",
            web_app=WebAppInfo(url=checkout_url)
        )]
    ])
    
    fulfillment_hours = getattr(product, 'fulfillment_time_hours', 48)
    
    await callback.message.answer(
        f"📦 Предзаказ: **{product.name}**\n"
        f"💰 Цена: {product.price}₽\n"
        f"⏱ Изготовление: {fulfillment_hours} часов\n\n"
        f"Нажмите кнопку ниже для оплаты:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, db_user: User):
    """Handle cancel button click"""
    await callback.message.delete()
    await callback.answer()


# ==================== INLINE QUERY HANDLERS ====================

@router.inline_query()
async def handle_inline_query(query: InlineQuery, db_user: User, bot: Bot):
    """
    Handle inline queries for product sharing and search.
    
    - Empty query: show default sharing options
    - "invite" query: show referral sharing
    - Other queries: search products to share
    """
    # Validate db_user exists before accessing attributes
    if db_user is None:
        await query.answer([], cache_time=0)
        return
    
    query_text = query.query.strip()
    bot_info = await bot.get_me()
    user_telegram_id = query.from_user.id
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_telegram_id}"
    
    results = []
    
    if not query_text or query_text.lower() == "invite":
        # Default: show sharing options
        total_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        
        results.append(
            InlineQueryResultArticle(
                id=f"invite_{db_user.id}",
                title="🎁 Пригласить друга (скидка 20%)",
                description=f"Я сэкономил {int(total_saved)}₽. Поделись ссылкой!",
                thumbnail_url=f"{WEBAPP_URL}/assets/share-preview.png",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🚀 <b>Я уже сэкономил {int(total_saved)}₽ на AI-подписках с PVNDORA!</b>\n\n"
                        f"Залетай и получи скидку 20% на первый заказ 👇"
                    ),
                    parse_mode=ParseMode.HTML
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🛍 Перейти в магазин", url=referral_link)
                    ]]
                )
            )
        )
        
        results.append(
            InlineQueryResultArticle(
                id="share_catalog",
                title="🛍 Поделиться каталогом",
                description="Отправить ссылку на каталог друзьям",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "🛍 <b>PVNDORA Каталог</b>\n\n"
                        "Премиум AI-подписки:\n"
                        "✅ Лучшие цены\n"
                        "✅ Мгновенная доставка\n"
                        "✅ Гарантия включена\n\n"
                        "Смотри! 👇"
                    ),
                    parse_mode=ParseMode.HTML
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🛍 Открыть каталог",
                        url=referral_link
                    )]
                ])
            )
        )
    
    else:
        # Search products to share
        try:
            db = get_database()
            products = await db.search_products(query_text, limit=10)
            
            for product in products:
                product_id = product.id
                name = product.name
                description = (product.description or "")[:100]
                price = product.price
                
                # Create unique result ID
                result_id = hashlib.md5(f"{product_id}:{user_telegram_id}".encode()).hexdigest()
                
                # Deep link with product ID and referral
                product_link = f"https://t.me/{bot_info.username}?start=product_{product_id}_ref_{user_telegram_id}"
                
                results.append(
                    InlineQueryResultArticle(
                        id=result_id,
                        title=f"📦 {name}",
                        description=f"{description}... • {price:.0f}₽",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"📦 <b>{name}</b>\n\n"
                                f"{description}\n\n"
                                f"💰 Цена: <b>{price:.0f}₽</b>\n\n"
                                f"🛒 Купить здесь:"
                            ),
                            parse_mode=ParseMode.HTML
                        ),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Купить {name}",
                                url=product_link
                            )]
                        ])
                    )
                )
        
        except Exception as e:
            print(f"ERROR: Inline product search failed: {e}")
            # Fallback: show generic search result
            results.append(
                InlineQueryResultArticle(
                    id="search_fallback",
                    title=f"🔍 Найти: {query_text}",
                    description="Поиск в PVNDORA",
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"🔍 Ищете <b>{query_text}</b>?\n\n"
                            f"Найдите лучшие AI-подписки в PVNDORA!"
                        ),
                        parse_mode=ParseMode.HTML
                    ),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🔍 Искать в PVNDORA",
                            url=referral_link
                        )]
                    ])
                )
            )
    
    # Answer with results (personal for referral links)
    await query.answer(results, cache_time=300, is_personal=True)


@router.chosen_inline_result()
async def handle_chosen_inline_result(chosen_result, db_user: User):
    """
    Track when user sends an inline result.
    Used for analytics on viral sharing.
    """
    result_id = chosen_result.result_id
    query_text = chosen_result.query
    
    try:
        db = get_database()
        await db.log_event(
            user_id=db_user.id if db_user else None,
            event_type="share",
            metadata={
                "result_id": result_id,
                "query": query_text
            }
        )
    except Exception:
        pass  # Non-critical, don't fail


# ==================== TEXT MESSAGE HANDLER ====================
# This handler should be registered LAST as it catches all text messages

@router.message(F.text)
async def handle_text_message(message: Message, db_user: User, bot: Bot):
    """
    Handle regular text messages - route to AI consultant.
    This is the main entry point for AI conversation.
    """
    import asyncio
    import traceback
    from src.ai.consultant import AIConsultant
    
    db = get_database()
    
    # Save user message
    await db.save_chat_message(db_user.id, "user", message.text)
    
    # Typing indicator task - keeps sending "typing" every 4 seconds
    typing_active = True
    async def keep_typing():
        while typing_active:
            try:
                await bot.send_chat_action(message.chat.id, "typing")
                await asyncio.sleep(4)
            except Exception:
                break
    
    typing_task = asyncio.create_task(keep_typing())
    
    try:
        # Get AI response
        consultant = AIConsultant()
        response = await consultant.get_response(
            user_id=db_user.id,
            user_message=message.text,
            language=db_user.language_code
        )
        
        # Save assistant response (use reply_text from structured response)
        await db.save_chat_message(db_user.id, "assistant", response.reply_text)
        
        # Auto-detect payment intent if AI mentions order/payment but didn't set action
        from core.models import ActionType
        if response.action == ActionType.NONE:
            reply_text_lower = response.reply_text.lower() if response.reply_text else ""
            # Check if response mentions payment/order keywords
            payment_keywords = [
                "как будем оплачивать", "готов оплатить", "готов(а) оплатить",
                "общая сумма", "итого", "к оплате", "оплатить",
                "предзаказ", "под заказ", "заказ"
            ]
            # Check if response contains order summary (mentions products and price)
            has_order_summary = any(keyword in reply_text_lower for keyword in payment_keywords)
            has_price = "₽" in response.reply_text or "руб" in reply_text_lower or "рубл" in reply_text_lower
            
            if has_order_summary and has_price:
                print("DEBUG: Auto-detected payment intent from reply text, setting action=OFFER_PAYMENT")
                response.action = ActionType.OFFER_PAYMENT
        
        # Send response to user based on structured action
        reply_markup = None
        
        # Handle actions from structured response
        if response.action == ActionType.SHOW_CATALOG:
            reply_markup = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
        elif response.action == ActionType.OFFER_PAYMENT:
            if response.product_id:
                # Single product - show product keyboard with quantity
                product = await db.get_product_by_id(response.product_id)
                if product:
                    reply_markup = get_product_keyboard(
                        db_user.language_code,
                        response.product_id,
                        WEBAPP_URL,
                        in_stock=product.stock_count > 0,
                        quantity=response.quantity or 1
                    )
            elif response.cart_items and len(response.cart_items) > 0:
                # Multiple products in cart - create checkout URL with cart data
                # For now, use first product as primary (cart checkout page will handle multiple items)
                try:
                    first_item = response.cart_items[0]
                    # Check if first_item is a dict or object with product_id
                    if isinstance(first_item, dict):
                        product_id = first_item.get('product_id')
                    elif hasattr(first_item, 'product_id'):
                        product_id = first_item.product_id
                    else:
                        print(f"WARNING: cart_items[0] has no product_id attribute: {first_item}")
                        product_id = None
                    
                    if product_id:
                        product = await db.get_product_by_id(product_id)
                        if product:
                            # Use checkout with cart parameter
                            reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
                        else:
                            # Product not found, use generic checkout
                            reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
                    else:
                        # No product_id, use generic checkout
                        reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
                except (IndexError, AttributeError, TypeError, KeyError) as e:
                    print(f"ERROR: Failed to process cart_items: {e}")
                    print(f"ERROR: cart_items type: {type(response.cart_items)}, value: {response.cart_items}")
                    traceback.print_exc()
                    # Fallback to generic checkout
                    reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
            else:
                # Multiple products or no specific product - show checkout button instead of shop
                # This handles cases where AI offers payment for multiple items
                reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
        elif response.action == ActionType.ADD_TO_CART:
            # After adding to cart, show payment button with correct quantity
            if response.product_id:
                # Single product added to cart - show payment button
                product = await db.get_product_by_id(response.product_id)
                if product:
                    reply_markup = get_product_keyboard(
                        db_user.language_code,
                        response.product_id,
                        WEBAPP_URL,
                        in_stock=product.stock_count > 0,
                        quantity=response.quantity or 1
                    )
            else:
                # Multiple products in cart - use cart checkout
                reply_markup = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
        elif response.product_id:
            # Fallback: if product_id set but no specific action
            product = await db.get_product_by_id(response.product_id)
            if product:
                reply_markup = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0,
                    quantity=response.quantity or 1
                )
        
        # Debug logging before sending
        print(f"DEBUG: Sending message to user {db_user.id} (telegram_id: {db_user.telegram_id})")
        print(f"DEBUG: Action: {response.action}, Product ID: {response.product_id}")
        print(f"DEBUG: Cart items: {response.cart_items}")
        print(f"DEBUG: Reply markup: {reply_markup}")
        print(f"DEBUG: Reply text length: {len(response.reply_text) if response.reply_text else 0}")
        
        # Send message
        success = await safe_answer(
            message,
            response.reply_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        if not success:
            print(f"ERROR: Failed to send message to user {db_user.id}")
        
    except Exception as e:
        # Log error for debugging with full traceback
        error_msg = f"AI error in handle_text_message: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        import sys
        print(f"ERROR: Exception type: {type(e).__name__}", file=sys.stderr)
        print("ERROR: Full traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Send user-friendly error message
        error_text = get_text("error_generic", db_user.language_code)
        try:
            await safe_answer(message, error_text)
        except Exception as send_error:
            print(f"ERROR: Failed to send error message: {send_error}")
        
        # Save error as assistant message for context (don't fail if this fails)
        try:
            await db.save_chat_message(db_user.id, "assistant", error_text)
        except Exception as save_error:
            print(f"ERROR: Failed to save error message: {save_error}")
        
    finally:
        typing_active = False
        typing_task.cancel()


# ==================== VOICE MESSAGE HANDLER ====================

@router.message(F.voice)
async def handle_voice_message(message: Message, db_user: User, bot: Bot):
    """
    Handle voice messages - transcribe with Gemini and process.
    """
    import asyncio
    import traceback
    from src.ai.consultant import AIConsultant
    
    db = get_database()
    
    # Save user's voice message marker in history (for context continuity)
    await db.save_chat_message(db_user.id, "user", "[🎤 Голосовое сообщение]")
    
    # Typing indicator task - keeps sending "typing" every 4 seconds
    typing_active = True
    async def keep_typing():
        while typing_active:
            try:
                await bot.send_chat_action(message.chat.id, "typing")
                await asyncio.sleep(4)
            except Exception:
                break
    
    typing_task = asyncio.create_task(keep_typing())
    
    try:
        # Download voice file
        voice = message.voice
        print(f"DEBUG: Voice message - duration: {voice.duration}s, file_size: {voice.file_size}")
        
        file = await bot.get_file(voice.file_id)
        voice_data = await bot.download_file(file.file_path)
        
        # Get AI response with voice
        consultant = AIConsultant()
        response = await consultant.get_response_from_voice(
            user_id=db_user.id,
            voice_data=voice_data.read(),
            language=db_user.language_code
        )
        
    except Exception as e:
        typing_active = False
        typing_task.cancel()
        
        error_msg = f"Voice processing error: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        
        # Send user-friendly error message
        error_text = get_text("error_generic", db_user.language_code)
        await safe_answer(message, error_text)
        await db.save_chat_message(db_user.id, "assistant", error_text)
        return
    finally:
        typing_active = False
        typing_task.cancel()
    
    # Save transcription and response
    # Note: transcription is now in reply_text if AI includes it
    await db.save_chat_message(db_user.id, "assistant", response.reply_text)
    
    # Send response based on structured action
    from core.models import ActionType
    keyboard = None
    
    if response.action == ActionType.SHOW_CATALOG:
        keyboard = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
    elif response.action == ActionType.OFFER_PAYMENT:
        if response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                keyboard = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0,
                    quantity=response.quantity or 1
                )
        elif response.cart_items and len(response.cart_items) > 0:
            # Multiple products in cart - use checkout
            keyboard = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
        else:
            # Multiple products or no specific product - show checkout button instead of shop
            keyboard = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
    elif response.action == ActionType.ADD_TO_CART:
        # After adding to cart, show payment button with correct quantity
        if response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                keyboard = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0,
                    quantity=response.quantity or 1
                )
        else:
            # Multiple products in cart - use cart checkout
            keyboard = get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
    elif response.product_id:
        # Fallback: if product_id set but no specific action
        product = await db.get_product_by_id(response.product_id)
        if product:
            keyboard = get_product_keyboard(
                db_user.language_code,
                response.product_id,
                WEBAPP_URL,
                in_stock=product.stock_count > 0,
            )
    
    await message.answer(
        response.reply_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

