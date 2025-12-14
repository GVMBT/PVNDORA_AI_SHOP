"""Text and voice message handlers - AI conversation entry points."""
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ParseMode

from core.services.database import User, get_database
from core.i18n import get_text
from core.bot.keyboards import get_shop_keyboard, get_product_keyboard, get_checkout_keyboard
from core.bot.handlers.helpers import safe_answer, WEBAPP_URL
from core.logging import get_logger

logger = get_logger(__name__)

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
    from core.ai.consultant import AIConsultant
    from core.models import ActionType
    
    db = get_database()
    await db.save_chat_message(db_user.id, "user", message.text)
    
    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    initial_text = "Думаю" if lang == "ru" else "Thinking"
    
    # Send initial progress message with text immediately
    progress_msg = await message.answer(f"{initial_text}.")
    dots_state = {"count": 1, "active": True, "base_text": initial_text, "last_text": ""}
    
    async def animate_dots():
        """Animate dots: . → .. → ... → . (loop) with 1s interval to respect Telegram limits"""
        while dots_state["active"]:
            await asyncio.sleep(1.0)  # Telegram limit: ~20 edits/min = 1 edit per 3s safe, 1s aggressive
            if not dots_state["active"]:
                break
            dots_state["count"] = (dots_state["count"] % 3) + 1
            dots = "." * dots_state["count"]
            new_text = f"{dots_state['base_text']}{dots}"
            # Only edit if text changed
            if new_text != dots_state["last_text"]:
                try:
                    await progress_msg.edit_text(new_text)
                    dots_state["last_text"] = new_text
                except Exception:
                    pass
    
    # Start animation immediately
    animation_task = asyncio.create_task(animate_dots())
    
    async def update_progress(stage: str, details: str):
        """Update progress message based on stage."""
        try:
            if stage == "analyzing":
                dots_state["base_text"] = "Анализирую" if lang == "ru" else "Analyzing"
            elif stage == "tool":
                first_tool = details.split()[0] if details else ""
                tool_info = TOOL_LABELS.get(first_tool, {})
                dots_state["base_text"] = tool_info.get(lang, "Обрабатываю" if lang == "ru" else "Processing")
            elif stage == "generating":
                dots_state["base_text"] = "Формирую ответ" if lang == "ru" else "Generating"
            else:
                return
            
            # Immediate update on stage change
            dots = "." * dots_state["count"]
            new_text = f"{dots_state['base_text']}{dots}"
            if new_text != dots_state["last_text"]:
                await progress_msg.edit_text(new_text)
                dots_state["last_text"] = new_text
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
                logger.debug("Auto-detected payment intent")
                response.action = ActionType.OFFER_PAYMENT
        
        keyboard = await _get_keyboard_for_response(response, db_user, db)
        
        logger.debug(f"Action: {response.action}, Product: {response.product_id}")
        
        # Stop animation
        dots_state["active"] = False
        animation_task.cancel()
        
        # Edit progress message with final response
        try:
            await progress_msg.edit_text(response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception:
            # If edit fails (e.g., same text), send new message
            try:
                await progress_msg.delete()
            except Exception:
                pass
            await safe_answer(message, response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        
        # Stop animation
        dots_state["active"] = False
        animation_task.cancel()
        
        error_text = get_text("error_generic", db_user.language_code)
        try:
            await progress_msg.edit_text(error_text)
        except Exception:
            await safe_answer(message, error_text)
        await db.save_chat_message(db_user.id, "assistant", error_text)


@router.message(F.voice)
async def handle_voice_message(message: Message, db_user: User, bot: Bot):
    """Handle voice messages - transcribe with Gemini and process."""
    from core.ai.consultant import AIConsultant
    
    db = get_database()
    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    
    # Send progress message immediately
    progress_text = "Слушаю" if lang == "ru" else "Listening"
    progress_msg = await message.answer(f"{progress_text}...")
    
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
        logger.debug(f"Voice - duration: {voice.duration}s, size: {voice.file_size}")
        
        # Validate voice duration (Gemini has limits)
        if voice.duration > 60:
            error_text = "Голосовое слишком длинное (макс. 60 сек)" if lang == "ru" else "Voice too long (max 60 sec)"
            await progress_msg.edit_text(error_text)
            return
        
        # Download voice file
        try:
            file = await bot.get_file(voice.file_id)
            voice_data = await bot.download_file(file.file_path)
            audio_bytes = voice_data.read()
            logger.debug(f"Downloaded voice file, size: {len(audio_bytes)} bytes")
        except Exception as download_error:
            logger.error(f"Failed to download voice: {download_error}", exc_info=True)
            error_text = "Не удалось загрузить голосовое" if lang == "ru" else "Failed to download voice"
            await progress_msg.edit_text(error_text)
            return
        
        # Update progress
        try:
            await progress_msg.edit_text("Распознаю..." if lang == "ru" else "Transcribing...")
        except Exception:
            pass
        
        # Process with AI (with retry)
        consultant = AIConsultant()
        last_error = None
        for attempt in range(2):  # 2 attempts
            try:
                response = await consultant.get_response_from_voice(
                    user_id=db_user.id,
                    voice_data=audio_bytes,
                    language=db_user.language_code
                )
                break
            except Exception as ai_error:
                last_error = ai_error
                logger.error(f"Voice AI attempt {attempt + 1} failed: {ai_error}", exc_info=True)
                if attempt == 0:
                    await asyncio.sleep(1)  # Wait before retry
        else:
            # All attempts failed
            raise last_error
        
        await db.save_chat_message(db_user.id, "assistant", response.reply_text)
        keyboard = await _get_keyboard_for_response(response, db_user, db)
        
        # Edit progress message with response
        try:
            await progress_msg.edit_text(response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception:
            try:
                await progress_msg.delete()
            except Exception:
                pass
            await message.answer(response.reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"Voice error: {error_str}", exc_info=True)
        
        # More specific error messages
        if "timeout" in error_str.lower() or "timed out" in error_str.lower():
            error_text = "Превышено время ожидания. Попробуйте ещё раз." if lang == "ru" else "Request timed out. Please try again."
        elif "quota" in error_str.lower() or "rate" in error_str.lower():
            error_text = "Слишком много запросов. Подождите минуту." if lang == "ru" else "Too many requests. Wait a minute."
        elif "audio" in error_str.lower() or "format" in error_str.lower():
            error_text = "Не удалось распознать аудио. Попробуйте записать заново." if lang == "ru" else "Could not process audio. Try recording again."
        else:
            error_text = get_text("error_generic", db_user.language_code)
        
        try:
            await progress_msg.edit_text(f"❌ {error_text}")
        except Exception:
            await safe_answer(message, f"❌ {error_text}")
        await db.save_chat_message(db_user.id, "assistant", error_text)
    finally:
        typing_active = False
        typing_task.cancel()


