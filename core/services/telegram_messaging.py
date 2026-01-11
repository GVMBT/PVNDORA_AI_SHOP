"""
Consolidated Telegram Message Sending Service

Single source of truth for all Telegram message sending across the project.
Replaces 8+ duplicate implementations with unified retry logic, error handling, and logging.
"""
import os
import asyncio
from typing import Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    bot_token: Optional[str] = None,
    retries: int = 2,
    timeout: float = 10.0,
) -> bool:
    """
    Send a Telegram message with retry logic and error handling.
    
    This is the single source of truth for all Telegram message sending.
    Use this instead of direct bot.send_message() or httpx calls.
    
    Args:
        chat_id: Telegram chat ID (user or group)
        text: Message text (HTML or Markdown supported)
        parse_mode: "HTML", "Markdown", or None
        bot_token: Optional bot token. If not provided, uses TELEGRAM_TOKEN
        retries: Number of retry attempts (default 2)
        timeout: Request timeout in seconds (default 10)
        
    Returns:
        True if sent successfully, False otherwise
        
    Example:
        >>> await send_telegram_message(123456789, "Hello, <b>World</b>!")
        True
        
        >>> await send_telegram_message(
        ...     chat_id=123456789,
        ...     text="Custom bot message",
        ...     bot_token=os.environ.get("DISCOUNT_BOT_TOKEN")
        ... )
        True
    """
    token = bot_token or TELEGRAM_TOKEN
    if not token:
        logger.warning(f"No bot token configured for sending message to {chat_id}")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=timeout)
                
                if response.status_code == 200:
                    logger.debug(f"Message sent successfully to {chat_id}")
                    return True
                
                # Log API error
                error_text = response.text[:200] if response.text else "No response body"
                logger.warning(
                    f"Telegram API error for {chat_id}: "
                    f"status={response.status_code}, response={error_text}"
                )
                
                # Check for permanent errors (no retry needed)
                if response.status_code in [400, 403, 404]:
                    # 400 - Bad request (invalid chat_id, message too long, etc.)
                    # 403 - Forbidden (bot blocked by user, user not found)
                    # 404 - Chat not found
                    return False
                
                # For other errors (429 rate limit, 5xx server errors), retry
                last_error = f"HTTP {response.status_code}"
                
        except httpx.TimeoutException:
            last_error = "Timeout"
            logger.warning(f"Timeout sending message to {chat_id} (attempt {attempt + 1}/{retries + 1})")
        except httpx.ConnectError as e:
            last_error = f"Connection error: {e}"
            logger.warning(f"Connection error sending to {chat_id}: {e}")
        except Exception as e:
            last_error = str(e)
            logger.error(f"Unexpected error sending message to {chat_id}: {e}")
        
        # Exponential backoff before retry
        if attempt < retries:
            delay = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s...
            await asyncio.sleep(delay)
    
    logger.error(f"Failed to send message to {chat_id} after {retries + 1} attempts: {last_error}")
    return False


async def send_telegram_message_with_keyboard(
    chat_id: int,
    text: str,
    keyboard,
    parse_mode: str = "HTML",
    bot_token: Optional[str] = None,
    retries: int = 2,
    timeout: float = 10.0,
) -> bool:
    """
    Send a Telegram message with inline keyboard.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text
        keyboard: InlineKeyboardMarkup (aiogram object) or dict (reply_markup payload)
        parse_mode: Parse mode
        bot_token: Optional bot token
        retries: Number of retry attempts
        timeout: Request timeout
        
    Returns:
        True if sent successfully, False otherwise
    """
    token = bot_token or TELEGRAM_TOKEN
    if not token:
        logger.warning(f"No bot token configured for sending message to {chat_id}")
        return False
    
    # Convert aiogram keyboard to dict if needed
    keyboard_dict = keyboard
    if isinstance(keyboard, dict):
        # Already a dict, use as-is
        keyboard_dict = keyboard
    elif hasattr(keyboard, 'model_dump'):
        # aiogram 3.x InlineKeyboardMarkup - use model_dump with exclude_none=True
        # This excludes None values which Telegram API doesn't accept
        try:
            keyboard_dict = keyboard.model_dump(exclude_none=True)
        except Exception as e:
            logger.error(f"Failed to convert keyboard using model_dump: {e}")
            return False
    elif hasattr(keyboard, 'dict'):
        # aiogram 2.x InlineKeyboardMarkup
        try:
            # Try exclude_none=True first (Pydantic v2 compatible)
            keyboard_dict = keyboard.dict(exclude_none=True)
        except Exception:
            try:
                keyboard_dict = keyboard.dict()
            except Exception as e:
                logger.error(f"Failed to convert keyboard using dict: {e}")
                return False
    else:
        logger.error(f"Unknown keyboard type: {type(keyboard)}, cannot convert to dict. Use InlineKeyboardMarkup from aiogram.")
        return False
    
    # Check message length (Telegram limit: 4096 characters)
    if len(text) > 4096:
        logger.error(f"Message too long for {chat_id}: {len(text)} characters (max 4096)")
        # Truncate message
        text = text[:4090] + "..."
        logger.warning(f"Truncated message to {len(text)} characters")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard_dict,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=timeout)
                
                if response.status_code == 200:
                    return True
                
                # Log API error with full response body
                try:
                    error_data = response.json() if response.text else {}
                    error_description = error_data.get("description", "") or response.text[:500] if response.text else "No response body"
                    logger.error(
                        f"Telegram API error for {chat_id} (keyboard): "
                        f"status={response.status_code}, description={error_description}"
                    )
                except Exception:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error(
                        f"Telegram API error for {chat_id} (keyboard): "
                        f"status={response.status_code}, response={error_text}"
                    )
                
                if response.status_code in [400, 403, 404]:
                    return False
                
                last_error = f"HTTP {response.status_code}"
                
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Error sending keyboard message to {chat_id}: {e}")
        
        if attempt < retries:
            await asyncio.sleep(0.5 * (2 ** attempt))
    
    logger.error(f"Failed to send keyboard message to {chat_id}: {last_error}")
    return False


# Convenience functions for specific bots

async def send_via_main_bot(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send message via main PVNDORA bot."""
    return await send_telegram_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        bot_token=TELEGRAM_TOKEN
    )


async def send_via_discount_bot(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send message via discount bot (for migration offers)."""
    return await send_telegram_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        bot_token=DISCOUNT_BOT_TOKEN or TELEGRAM_TOKEN
    )
