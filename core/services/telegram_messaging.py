"""
Consolidated Telegram Message Sending Service

Single source of truth for all Telegram message sending across the project.
Replaces 8+ duplicate implementations with unified retry logic, error handling, and logging.
"""

import asyncio
import os

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

# Constants
NO_RESPONSE_BODY = "No response body"
PERMANENT_ERROR_CODES = {400, 403, 404}

# Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DISCOUNT_BOT_TOKEN = os.environ.get("DISCOUNT_BOT_TOKEN", "")


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def _is_permanent_error(status_code: int) -> bool:
    """Check if error is permanent (no retry needed)."""
    return status_code in PERMANENT_ERROR_CODES


def _calculate_backoff_delay(attempt: int) -> float:
    """Calculate exponential backoff delay."""
    return float(0.5 * (2 ** attempt))


async def _make_telegram_request(
    client: httpx.AsyncClient, url: str, payload: dict, timeout: float
) -> tuple[bool, int, str]:
    """Make HTTP request to Telegram API. Returns (success, status_code, error_text)."""
    response = await client.post(url, json=payload, timeout=timeout)

    if response.status_code == 200:
        return True, 200, ""

    error_text = response.text[:200] if response.text else NO_RESPONSE_BODY
    return False, response.status_code, error_text


def _try_model_dump(keyboard) -> dict | None:
    """Try to convert keyboard using model_dump (aiogram 3.x)."""
    try:
        result = keyboard.model_dump(exclude_none=True)
        return dict(result) if result else None
    except Exception:
        logger.exception("Failed to convert keyboard using model_dump")
        return None


def _try_dict_method(keyboard) -> dict | None:
    """Try to convert keyboard using dict method (aiogram 2.x)."""
    try:
        result = keyboard.dict(exclude_none=True)
        return dict(result) if result else None
    except Exception:
        pass

    try:
        result = keyboard.dict()
        return dict(result) if result else None
    except Exception:
        logger.exception("Failed to convert keyboard using dict")
        return None


def _convert_keyboard_to_dict(keyboard) -> dict | None:
    """Convert aiogram keyboard to dict format."""
    if isinstance(keyboard, dict):
        return dict(keyboard)

    if hasattr(keyboard, "model_dump"):
        return _try_model_dump(keyboard)

    if hasattr(keyboard, "dict"):
        return _try_dict_method(keyboard)

    logger.error(f"Unknown keyboard type: {type(keyboard)}")
    return None


def _truncate_message(text: str, max_length: int = 4096) -> str:
    """Truncate message to Telegram's limit."""
    if len(text) <= max_length:
        return text

    logger.warning(f"Truncating message from {len(text)} to {max_length - 3} characters")
    return text[:max_length - 3] + "..."


async def _send_with_retry(
    url: str, payload: dict, retries: int, timeout: float, chat_id: int
) -> bool:
    """Send request with retry logic."""
    last_error = None

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                success, status_code, error_text = await _make_telegram_request(
                    client, url, payload, timeout
                )

                if success:
                    logger.debug(f"Message sent successfully to {chat_id}")
                    return True

                logger.warning(f"Telegram API error for {chat_id}: status={status_code}, response={error_text}")

                if _is_permanent_error(status_code):
                    return False

                last_error = f"HTTP {status_code}"

        except httpx.TimeoutException:
            last_error = "Timeout"
            logger.warning(f"Timeout sending message to {chat_id} (attempt {attempt + 1}/{retries + 1})")
        except httpx.ConnectError as e:
            last_error = f"Connection error: {e}"
            logger.warning(f"Connection error sending to {chat_id}: {e}")
        except Exception as e:
            last_error = str(e)
            logger.exception(f"Unexpected error sending message to {chat_id}")

        if attempt < retries:
            delay = _calculate_backoff_delay(attempt)
            await asyncio.sleep(delay)

    logger.error(f"Failed to send message to {chat_id} after {retries + 1} attempts: {last_error}")
    return False


def _parse_error_response(response: httpx.Response) -> str:
    """Parse error response from Telegram API."""
    try:
        error_data = response.json() if response.text else {}
        return error_data.get("description", "") or response.text[:500] if response.text else NO_RESPONSE_BODY
    except Exception:
        return response.text[:500] if response.text else NO_RESPONSE_BODY


# =============================================================================
# Public API
# =============================================================================


async def send_telegram_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = "HTML",
    bot_token: str | None = None,
    retries: int = 2,
    timeout: float = 10.0,
) -> bool:
    """
    Send a Telegram message with retry logic and error handling.

    Args:
        chat_id: Telegram chat ID (user or group)
        text: Message text (HTML or Markdown supported)
        parse_mode: "HTML", "Markdown", or None
        bot_token: Optional bot token. If not provided, uses TELEGRAM_TOKEN
        retries: Number of retry attempts (default 2)
        timeout: Request timeout in seconds (default 10)

    Returns:
        True if sent successfully, False otherwise
    """
    token = bot_token or TELEGRAM_TOKEN
    if not token:
        logger.warning(f"No bot token configured for sending message to {chat_id}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    return await _send_with_retry(url, payload, retries, timeout, chat_id)


async def send_telegram_message_with_keyboard(
    chat_id: int,
    text: str,
    keyboard,
    parse_mode: str | None = "HTML",
    bot_token: str | None = None,
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

    keyboard_dict = _convert_keyboard_to_dict(keyboard)
    if keyboard_dict is None:
        return False

    text = _truncate_message(text)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "reply_markup": keyboard_dict}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    last_error = None

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=timeout)

                if response.status_code == 200:
                    return True

                error_description = _parse_error_response(response)
                logger.error(f"Telegram API error for {chat_id} (keyboard): status={response.status_code}, description={error_description}")

                if _is_permanent_error(response.status_code):
                    return False

                last_error = f"HTTP {response.status_code}"

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Error sending keyboard message to {chat_id}: {e}")

        if attempt < retries:
            await asyncio.sleep(_calculate_backoff_delay(attempt))

    logger.error(f"Failed to send keyboard message to {chat_id}: {last_error}")
    return False


# =============================================================================
# Convenience functions for specific bots
# =============================================================================


async def send_via_main_bot(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send message via main PVNDORA bot."""
    return await send_telegram_message(
        chat_id=chat_id, text=text, parse_mode=parse_mode, bot_token=TELEGRAM_TOKEN
    )


async def send_via_discount_bot(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send message via discount bot (for migration offers)."""
    return await send_telegram_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        bot_token=DISCOUNT_BOT_TOKEN or TELEGRAM_TOKEN,
    )
