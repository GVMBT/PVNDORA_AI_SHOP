"""Telegram Bot Handlers"""
import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from src.services.database import User, get_database
from src.i18n import get_text
from src.bot.keyboards import (
    get_shop_keyboard,
    get_product_keyboard
)

router = Router()

# Get webapp URL from environment
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora-ai-shop.vercel.app")


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
        # Enhanced onboarding for new users
        onboarding_text = get_text("welcome", db_user.language_code)
        
        # Add quick examples based on language
        examples = {
            "ru": "\n\n💡 Попробуйте:\n• \"Нужен ChatGPT для работы\"\n• \"Покажи что есть\"\n• \"Хочу Midjourney\"",
            "en": "\n\n💡 Try:\n• \"I need ChatGPT for work\"\n• \"Show me what you have\"\n• \"I want Midjourney\"",
        }
        onboarding_text += examples.get(db_user.language_code, examples["en"])
    else:
        onboarding_text = get_text("welcome_back", db_user.language_code)
    
    # Save bot's welcome message
    await db.save_chat_message(db_user.id, "assistant", onboarding_text)
    
    await message.answer(
        onboarding_text,
        reply_markup=get_shop_keyboard(db_user.language_code, WEBAPP_URL),
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
async def callback_review(callback: CallbackQuery, db_user: User):
    """Handle review button click"""
    callback.data.split(":")[1]  # Extract order_id (not used yet)
    
    await callback.message.answer(
        get_text("review_request", db_user.language_code)
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
        
        # Send response to user based on structured action
        reply_markup = None
        
        # Handle actions from structured response
        from core.models import ActionType
        if response.action == ActionType.SHOW_CATALOG:
            reply_markup = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
        elif response.action == ActionType.OFFER_PAYMENT and response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                reply_markup = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0,
                )
        elif response.product_id:
            # Fallback: if product_id set but no specific action
            product = await db.get_product_by_id(response.product_id)
            if product:
                reply_markup = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0,
                )
        
        await message.answer(
            response.reply_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        # Log error for debugging
        error_msg = f"AI error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        # Send user-friendly error message
        error_text = get_text("error_generic", db_user.language_code)
        await message.answer(error_text)
        
        # Save error as assistant message for context
        await db.save_chat_message(db_user.id, "assistant", error_text)
        
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
    from src.ai.consultant import AIConsultant
    
    db = get_database()
    
    # Typing indicator task - keeps sending "typing" every 4 seconds
    typing_active = True
    async def keep_typing():
        while typing_active:
            await bot.send_chat_action(message.chat.id, "typing")
            await asyncio.sleep(4)
    
    typing_task = asyncio.create_task(keep_typing())
    
    try:
        # Download voice file
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        voice_data = await bot.download_file(file.file_path)
        
        # Get AI response with voice
        consultant = AIConsultant()
        response = await consultant.get_response_from_voice(
            user_id=db_user.id,
            voice_data=voice_data.read(),
            language=db_user.language_code
        )
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
    elif response.action == ActionType.OFFER_PAYMENT and response.product_id:
        product = await db.get_product_by_id(response.product_id)
        if product:
            keyboard = get_product_keyboard(
                db_user.language_code,
                response.product_id,
                WEBAPP_URL,
                in_stock=product.stock_count > 0,
            )
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

