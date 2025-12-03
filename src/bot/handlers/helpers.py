"""Bot handler helpers - keyboards and utilities."""
import os
import traceback

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# Get webapp URL from environment
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")


def get_share_keyboard(product_name: str = "") -> InlineKeyboardMarkup:
    """Get keyboard with share button using switchInlineQuery."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Поделиться с друзьями",
            switch_inline_query=product_name
        )]
    ])


def get_share_current_chat_keyboard(product_name: str) -> InlineKeyboardMarkup:
    """Get keyboard for sharing in current chat."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Поделиться здесь",
            switch_inline_query_current_chat=product_name
        )]
    ])


async def safe_answer(message: Message, text: str, **kwargs) -> bool:
    """
    Safely send message, handling Telegram API errors gracefully.
    Returns True if sent successfully, False otherwise.
    """
    try:
        if not text or not text.strip():
            print(f"ERROR: Attempted to send empty message to chat {message.chat.id}")
            return False
        
        print(f"DEBUG: safe_answer - chat_id: {message.chat.id}, text_length: {len(text)}")
        await message.answer(text, **kwargs)
        print(f"DEBUG: Message sent successfully to chat {message.chat.id}")
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        error_msg = str(e).lower()
        print(f"ERROR: Telegram API error in safe_answer: {e}")
        if "chat not found" in error_msg:
            print(f"WARNING: Cannot send message to chat {message.chat.id}: chat not found")
        elif "bot was blocked" in error_msg or "forbidden" in error_msg:
            print(f"WARNING: Bot blocked by user {message.chat.id}")
        else:
            print(f"ERROR: Traceback: {traceback.format_exc()}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error in safe_answer: {type(e).__name__}: {e}")
        print("ERROR: Full traceback:")
        traceback.print_exc()
        return False


