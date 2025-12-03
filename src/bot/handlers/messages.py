"""Text and voice message handlers - AI conversation entry points."""
import asyncio
import sys
import traceback

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ParseMode

from src.services.database import User, get_database
from src.i18n import get_text
from src.bot.keyboards import get_shop_keyboard, get_product_keyboard, get_checkout_keyboard
from src.bot.handlers.helpers import safe_answer, WEBAPP_URL

router = Router()


async def _get_keyboard_for_response(response, db_user: User, db):
    """Get keyboard based on AI response action."""
    from core.models import ActionType
    
    if response.action == ActionType.SHOW_CATALOG:
        return get_shop_keyboard(db_user.language_code, WEBAPP_URL)
    
    elif response.action == ActionType.OFFER_PAYMENT:
        if response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                return get_product_keyboard(
                    db_user.language_code, response.product_id, WEBAPP_URL,
                    in_stock=product.stock_count > 0, quantity=response.quantity or 1
                )
        elif response.cart_items and len(response.cart_items) > 0:
            return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
        else:
            return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
    
    elif response.action == ActionType.ADD_TO_CART:
        if response.product_id:
            product = await db.get_product_by_id(response.product_id)
            if product:
                return get_product_keyboard(
                    db_user.language_code, response.product_id, WEBAPP_URL,
                    in_stock=product.stock_count > 0, quantity=response.quantity or 1
                )
        else:
            return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)
    
    elif response.product_id:
        product = await db.get_product_by_id(response.product_id)
        if product:
            return get_product_keyboard(
                db_user.language_code, response.product_id, WEBAPP_URL,
                in_stock=product.stock_count > 0, quantity=response.quantity or 1
            )
    
    return None


# Tool display names (human-readable) for progress updates
TOOL_LABELS = {
    "search_products": {"ru": "Ищу товары", "en": "Searching products"},
    "get_product_details": {"ru": "Загружаю детали", "en": "Loading details"},
    "check_availability": {"ru": "Проверяю наличие", "en": "Checking stock"},
    "get_cart": {"ru": "Загружаю корзину", "en": "Loading cart"},
    "add_to_cart": {"ru": "Добавляю в корзину", "en": "Adding to cart"},
    "get_order_history": {"ru": "Загружаю заказы", "en": "Loading orders"},
    "get_user_profile": {"ru": "Загружаю профиль", "en": "Loading profile"},
    "get_faq": {"ru": "Ищу в FAQ", "en": "Searching FAQ"},
    "get_wishlist": {"ru": "Загружаю избранное", "en": "Loading wishlist"},
    "create_support_ticket": {"ru": "Создаю тикет", "en": "Creating ticket"},
}


@router.message(F.text)
async def handle_text_message(message: Message, db_user: User, bot: Bot):
    """Handle regular text messages - route to AI consultant."""
    from src.ai.consultant import AIConsultant
    from core.models import ActionType
    
    db = get_database()
    await db.save_chat_message(db_user.id, "user", message.text)
    
    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    
    # Send initial progress message
    progress_msg = await message.answer("." if lang == "ru" else ".")
    dots_state = {"count": 1, "task": None, "active": True, "base_text": ""}
    
    async def animate_dots():
        """Animate dots: . → .. → ... → . (loop)"""
        while dots_state["active"]:
            await asyncio.sleep(0.4)
            if not dots_state["active"]:
                break
            dots_state["count"] = (dots_state["count"] % 3) + 1
            dots = "." * dots_state["count"]
            try:
                text = f"{dots_state['base_text']}{dots}" if dots_state["base_text"] else dots
                await progress_msg.edit_text(text)
            except Exception:
                pass
    
    async def update_progress(stage: str, details: str):
        """Update progress message based on stage."""
        try:
            if stage == "analyzing":
                dots_state["base_text"] = "Анализирую" if lang == "ru" else "Analyzing"
            elif stage == "tool":
                # Get first tool label if multiple tools
                first_tool = details.split()[0] if details else ""
                tool_info = TOOL_LABELS.get(first_tool, {})
                dots_state["base_text"] = tool_info.get(lang, "Обрабатываю" if lang == "ru" else "Processing")
            elif stage == "generating":
                dots_state["base_text"] = "Формирую ответ" if lang == "ru" else "Generating"
            else:
                return
            
            # Start animation task if not running
            if dots_state["task"] is None:
                dots_state["task"] = asyncio.create_task(animate_dots())
            
            # Immediate update
            dots = "." * dots_state["count"]
            await progress_msg.edit_text(f"{dots_state['base_text']}{dots}")
        except Exception:
            pass
    
    try:
        consultant = AIConsultant()
        response = await consultant.get_response(
            user_id=db_user.id,
            user_message=message.text,
            language=db_user.language_code,
            progress_callback=update_progress
        )
        
        await db.save_chat_message(db_user.id, "assistant", response.reply_text)
        
        # Auto-detect payment intent
        if response.action == ActionType.NONE:
            reply_text_lower = response.reply_text.lower() if response.reply_text else ""
            payment_keywords = ["оплатить", "к оплате", "итого", "общая сумма", "предзаказ"]
            has_payment_intent = any(kw in reply_text_lower for kw in payment_keywords)
            has_price = "₽" in response.reply_text or "руб" in reply_text_lower
            if has_payment_intent and has_price:
                print("DEBUG: Auto-detected payment intent")
                response.action = ActionType.OFFER_PAYMENT
        
        keyboard = await _get_keyboard_for_response(response, db_user, db)
        
        print(f"DEBUG: Action: {response.action}, Product: {response.product_id}")
        
        # Stop animation
        dots_state["active"] = False
        if dots_state["task"]:
            dots_state["task"].cancel()
        
        # Edit progress message with final response
        try:
            await progress_msg.edit_text(response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception:
            # If edit fails (e.g., same text), send new message
            await progress_msg.delete()
            await safe_answer(message, response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        print(f"ERROR: AI error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Stop animation
        dots_state["active"] = False
        if dots_state["task"]:
            dots_state["task"].cancel()
        
        error_text = get_text("error_generic", db_user.language_code)
        try:
            await progress_msg.edit_text(error_text)
        except Exception:
            await safe_answer(message, error_text)
        await db.save_chat_message(db_user.id, "assistant", error_text)


@router.message(F.voice)
async def handle_voice_message(message: Message, db_user: User, bot: Bot):
    """Handle voice messages - transcribe with Gemini and process."""
    from src.ai.consultant import AIConsultant
    
    db = get_database()
    await db.save_chat_message(db_user.id, "user", "[🎤 Голосовое сообщение]")
    
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
        voice = message.voice
        print(f"DEBUG: Voice - duration: {voice.duration}s, size: {voice.file_size}")
        
        file = await bot.get_file(voice.file_id)
        voice_data = await bot.download_file(file.file_path)
        
        consultant = AIConsultant()
        response = await consultant.get_response_from_voice(
            user_id=db_user.id,
            voice_data=voice_data.read(),
            language=db_user.language_code
        )
        
        await db.save_chat_message(db_user.id, "assistant", response.reply_text)
        keyboard = await _get_keyboard_for_response(response, db_user, db)
        
        await message.answer(response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        print(f"ERROR: Voice error: {e}")
        traceback.print_exc()
        
        error_text = get_text("error_generic", db_user.language_code)
        await safe_answer(message, error_text)
        await db.save_chat_message(db_user.id, "assistant", error_text)
    finally:
        typing_active = False
        typing_task.cancel()


