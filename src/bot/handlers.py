"""Telegram Bot Handlers"""
import os
import asyncio
import traceback
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.services.database import User, get_database
from src.i18n import get_text
from src.bot.keyboards import (
    get_shop_keyboard,
    get_product_keyboard,
    get_checkout_keyboard
)

router = Router()

# Get webapp URL from environment
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


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


# ==================== INLINE QUERY HANDLER ====================

@router.inline_query(F.query.startswith("invite"))
async def handle_inline_invite(query: InlineQuery, db_user: User, bot: Bot):
    """Handle inline query for invites (fallback for shareMessage)"""
    # Validate db_user exists before accessing attributes
    if db_user is None:
        await query.answer([], cache_time=0)
        return

    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{db_user.id}"

    # Calculate savings
    total_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0

    results = [
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
    ]

    await query.answer(results, cache_time=0, is_personal=True)


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
                    import traceback
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

