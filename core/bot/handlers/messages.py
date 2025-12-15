"""Text and voice message handlers - AI conversation entry points."""
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
    """Handle regular text messages - route to AI agent."""
    from core.agent import get_shop_agent
    from core.models import ActionType
    
    db = get_database()
    await db.save_chat_message(db_user.id, "user", message.text)
    
    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    initial_text = "Думаю" if lang == "ru" else "Thinking"
    
    # Send initial progress message
    progress_msg = await message.answer(f"{initial_text}...")
    
    try:
        # Get AI response via LangGraph agent
        agent = get_shop_agent(db)
        response = await agent.chat(
            message=message.text,
            user_id=db_user.id,
            language=db_user.language_code,
            thread_id=f"bot_{db_user.id}",
            telegram_id=message.from_user.id,
        )
        
        reply_text = response.content
        await db.save_chat_message(db_user.id, "assistant", reply_text)
        
        # Build mock response object for keyboard detection
        class MockResponse:
            def __init__(self, text, action_str, product_id):
                self.reply_text = text
                self.product_id = product_id
                self.quantity = 1
                self.cart_items = []
                # Map action string to ActionType
                action_map = {
                    "add_to_cart": ActionType.ADD_TO_CART,
                    "offer_payment": ActionType.OFFER_PAYMENT,
                    "create_ticket": ActionType.CREATE_TICKET,
                    "show_catalog": ActionType.SHOW_CATALOG,
                }
                self.action = action_map.get(action_str, ActionType.NONE)
        
        mock_response = MockResponse(reply_text, response.action, response.product_id)
        
        # Auto-detect payment intent
        if mock_response.action == ActionType.NONE and reply_text:
            reply_text_lower = reply_text.lower()
            payment_keywords = ["оплатить", "к оплате", "итого", "общая сумма", "предзаказ"]
            has_payment_intent = any(kw in reply_text_lower for kw in payment_keywords)
            has_price = "₽" in reply_text or "руб" in reply_text_lower
            if has_payment_intent and has_price:
                logger.debug("Auto-detected payment intent")
                mock_response.action = ActionType.OFFER_PAYMENT
        
        keyboard = await _get_keyboard_for_response(mock_response, db_user, db)
        
        logger.debug(f"Action: {mock_response.action}, Product: {response.product_id}")
        
        # Edit progress message with final response
        try:
            await progress_msg.edit_text(reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception:
            try:
                await progress_msg.delete()
            except Exception:
                pass
            await safe_answer(message, reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        
        error_text = get_text("error_generic", db_user.language_code)
        try:
            await progress_msg.edit_text(error_text)
        except Exception:
            await safe_answer(message, error_text)
        await db.save_chat_message(db_user.id, "assistant", error_text)


@router.message(F.voice)
async def handle_voice_message(message: Message, db_user: User, bot: Bot):
    """Handle voice messages - temporarily unsupported after agent migration."""
    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    
    # Voice support temporarily disabled during agent migration
    # TODO: Add voice transcription to new LangGraph agent
    error_text = (
        "Голосовые сообщения временно недоступны. Пожалуйста, напишите текстом."
        if lang == "ru" else
        "Voice messages temporarily unavailable. Please type your message."
    )
    
    await safe_answer(message, error_text)


