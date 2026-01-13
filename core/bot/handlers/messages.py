"""Text and voice message handlers - AI conversation entry points."""

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message

from core.bot.handlers.helpers import WEBAPP_URL, safe_answer
from core.bot.keyboards import get_checkout_keyboard, get_product_keyboard, get_shop_keyboard
from core.i18n import get_text
from core.logging import get_logger
from core.services.database import User, get_database

logger = get_logger(__name__)

router = Router()


async def _get_product_keyboard_for_response(
    response, db_user: User, db
) -> InlineKeyboardMarkup | None:
    """Get product keyboard for response (reduces cognitive complexity)."""
    if not response.product_id:
        return None

    product = await db.get_product_by_id(response.product_id)
    if not product:
        return None

    return get_product_keyboard(
        db_user.language_code,
        response.product_id,
        WEBAPP_URL,
        in_stock=product.stock_count > 0,
        quantity=response.quantity or 1,
    )


async def _get_keyboard_for_payment_action(
    response, db_user: User, db
) -> InlineKeyboardMarkup | None:
    """Get keyboard for payment action (reduces cognitive complexity)."""
    product_keyboard = await _get_product_keyboard_for_response(response, db_user, db)
    if product_keyboard:
        return product_keyboard

    if response.cart_items and len(response.cart_items) > 0:
        return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)

    return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)


async def _get_keyboard_for_response(response, db_user: User, db):
    """Get keyboard based on AI response action."""
    from core.models import ActionType

    if response.action == ActionType.SHOW_CATALOG:
        return get_shop_keyboard(db_user.language_code, WEBAPP_URL)

    if response.action == ActionType.OFFER_PAYMENT:
        return await _get_keyboard_for_payment_action(response, db_user, db)

    if response.action == ActionType.ADD_TO_CART:
        product_keyboard = await _get_product_keyboard_for_response(response, db_user, db)
        if product_keyboard:
            return product_keyboard
        return get_checkout_keyboard(db_user.language_code, WEBAPP_URL)

    if response.product_id:
        return await _get_product_keyboard_for_response(response, db_user, db)

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


# Helper to detect payment intent (reduces cognitive complexity)
def _detect_payment_intent(reply_text: str) -> bool:
    """Detect if message contains payment intent."""
    if not reply_text:
        return False
    reply_text_lower = reply_text.lower()
    payment_keywords = ["оплатить", "к оплате", "итого", "общая сумма", "предзаказ"]
    has_payment_intent = any(kw in reply_text_lower for kw in payment_keywords)
    has_price = "₽" in reply_text or "руб" in reply_text_lower
    return has_payment_intent and has_price


# Helper to create mock response (reduces cognitive complexity)
def _create_mock_response(reply_text: str, action_str: str, product_id: str | None):
    """Create mock response object for keyboard detection."""
    from core.models import ActionType

    class MockResponse:
        def __init__(self, text, action_str, product_id):
            self.reply_text = text
            self.product_id = product_id
            self.quantity = 1
            self.cart_items = []
            action_map = {
                "add_to_cart": ActionType.ADD_TO_CART,
                "offer_payment": ActionType.OFFER_PAYMENT,
                "create_ticket": ActionType.CREATE_TICKET,
                "show_catalog": ActionType.SHOW_CATALOG,
            }
            self.action = action_map.get(action_str, ActionType.NONE)

    return MockResponse(reply_text, action_str, product_id)


# Helper to send final response (reduces cognitive complexity)
async def _send_final_response(progress_msg, message, reply_text, keyboard):
    """Send final response, handling edit/delete fallback."""
    try:
        await progress_msg.edit_text(reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await progress_msg.delete()
        except Exception:
            pass
        await safe_answer(message, reply_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(F.text)
async def handle_text_message(message: Message, db_user: User, bot: Bot):
    """Handle regular text messages - route to AI agent."""
    from core.agent import get_shop_agent
    from core.models import ActionType

    db = get_database()
    message_text = message.text or ""
    await db.save_chat_message(db_user.id, "user", message_text)

    lang = db_user.language_code if db_user.language_code in ("ru", "en") else "en"
    initial_text = "Думаю" if lang == "ru" else "Thinking"

    progress_msg = await message.answer(f"{initial_text}...")

    try:
        agent = get_shop_agent(db)
        telegram_id = message.from_user.id if message.from_user else db_user.telegram_id
        response = await agent.chat(
            message=message_text,
            user_id=db_user.id,
            language=db_user.language_code,
            telegram_id=telegram_id,
        )

        reply_text = response.content
        await db.save_chat_message(db_user.id, "assistant", reply_text)

        mock_response = _create_mock_response(reply_text, response.action, response.product_id)

        if mock_response.action == ActionType.NONE and _detect_payment_intent(reply_text):
            logger.debug("Auto-detected payment intent")
            mock_response.action = ActionType.OFFER_PAYMENT

        keyboard = await _get_keyboard_for_response(mock_response, db_user, db)
        logger.debug("Action: %s, Product: %s", mock_response.action, response.product_id)

        await _send_final_response(progress_msg, message, reply_text, keyboard)

    except Exception as e:
        logger.error("AI error: %s", e, exc_info=True)

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

    # Voice support disabled - requires Whisper API integration (planned for future release)
    error_text = (
        "Голосовые сообщения временно недоступны. Пожалуйста, напишите текстом."
        if lang == "ru"
        else "Voice messages temporarily unavailable. Please type your message."
    )

    await safe_answer(message, error_text)
