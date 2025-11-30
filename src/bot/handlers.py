"""Telegram Bot Handlers"""
import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from src.services.database import Database, User, get_database
from src.i18n import get_text
from src.bot.keyboards import (
    get_shop_keyboard,
    get_product_keyboard,
    get_order_keyboard,
    get_cancel_keyboard
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
                        # #region agent log
                        import json, time
                        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "handlers.py:43", "message": "Before referral update execute (async)", "data": {"user_id": db_user.id, "referrer_id": referrer.id}, "timestamp": int(time.time() * 1000)}) + "\n")
                        # #endregion
                        
                        # Link referral - run in thread pool to avoid blocking event loop
                        exec_start = time.time()
                        await asyncio.to_thread(
                            lambda: db.client.table("users").update({
                                "referrer_id": referrer.id
                            }).eq("id", db_user.id).execute()
                        )
                        
                        # #region agent log
                        exec_duration = (time.time() - exec_start) * 1000
                        with open(r"d:\pvndora\.cursor\debug.log", "a", encoding="utf-8") as f:
                            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "handlers.py:52", "message": "After referral update execute", "data": {"exec_duration_ms": exec_duration}, "timestamp": int(time.time() * 1000)}) + "\n")
                        # #endregion
                except:
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
    order_id = callback.data.split(":")[1]
    
    # TODO: Create support ticket
    await callback.answer(
        get_text("support_ticket", db_user.language_code),
        show_alert=True
    )


@router.callback_query(F.data.startswith("review:"))
async def callback_review(callback: CallbackQuery, db_user: User):
    """Handle review button click"""
    order_id = callback.data.split(":")[1]
    
    await callback.message.answer(
        get_text("review_request", db_user.language_code)
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
            except:
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
        
        # Save assistant response
        await db.save_chat_message(db_user.id, "assistant", response.text)
        
        # Send response to user
        reply_markup = None
        if response.show_shop:
            reply_markup = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
        elif response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                reply_markup = get_product_keyboard(
                    db_user.language_code,
                    response.product_id,
                    WEBAPP_URL,
                    in_stock=product.stock_count > 0
                )
        
        await message.answer(
            response.text,
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
    
    # Send response with appropriate keyboard if action suggested
    keyboard = None
    if response.product_id:
        product = await db.get_product_by_id(response.product_id)
        if product:
            keyboard = get_product_keyboard(
                db_user.language_code,
                response.product_id,
                WEBAPP_URL,
                in_stock=product.stock_count > 0
            )
    elif response.show_shop:
        keyboard = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
    
    await message.answer(
        response.text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


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
    if response.transcription:
        await db.save_chat_message(db_user.id, "user", f"🎤 {response.transcription}")
    await db.save_chat_message(db_user.id, "assistant", response.text)
    
    # Send response
    keyboard = None
    if response.product_id:
        product = await db.get_product_by_id(response.product_id)
        if product:
            keyboard = get_product_keyboard(
                db_user.language_code,
                response.product_id,
                WEBAPP_URL,
                in_stock=product.stock_count > 0
            )
    elif response.show_shop:
        keyboard = get_shop_keyboard(db_user.language_code, WEBAPP_URL)
    
    await message.answer(
        response.text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

