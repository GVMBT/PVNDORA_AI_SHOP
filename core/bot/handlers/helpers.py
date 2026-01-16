"""Bot handler helpers - keyboards and utilities."""

import os
import traceback
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from core.logging import get_logger

logger = get_logger(__name__)

# Get webapp URL from environment
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


def get_share_keyboard(product_name: str = "") -> InlineKeyboardMarkup:
    """Get keyboard with share button using switchInlineQuery."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Поделиться с друзьями",
                    switch_inline_query=product_name,
                ),
            ],
        ],
    )


def get_share_current_chat_keyboard(product_name: str) -> InlineKeyboardMarkup:
    """Get keyboard for sharing in current chat."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Поделиться здесь",
                    switch_inline_query_current_chat=product_name,
                ),
            ],
        ],
    )


async def safe_answer(message: Message, text: str, **kwargs: Any) -> bool:
    """Safely send message, handling Telegram API errors gracefully.
    Returns True if sent successfully, False otherwise.
    """
    try:
        if not text or not text.strip():
            # Don't log chat.id (user-controlled data) - just log error type
            logger.error("Attempted to send empty message")
            return False

        logger.debug("safe_answer - text_length: %d", len(text))
        await message.answer(text, **kwargs)
        logger.debug("Message sent successfully")
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        error_msg = str(e).lower()
        logger.exception("Telegram API error in safe_answer")
        if "chat not found" in error_msg:
            # Don't log chat.id (user-controlled data)
            logger.warning("Cannot send message: chat not found")
        elif "bot was blocked" in error_msg or "forbidden" in error_msg:
            # Don't log chat.id (user-controlled data)
            logger.warning("Bot blocked by user")
        else:
            logger.exception("Traceback: %s", traceback.format_exc())
        return False
    except Exception as e:
        logger.error("Unexpected error in safe_answer: %s", type(e).__name__, exc_info=True)
        return False
