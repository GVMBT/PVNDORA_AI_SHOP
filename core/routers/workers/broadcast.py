"""
Broadcast Worker

QStash worker for sending broadcast messages to users.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import asyncio
import os
from datetime import UTC, datetime

import httpx
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from fastapi import APIRouter, Request

from core.logging import get_logger
from core.routers.deps import verify_qstash
from core.services.database import get_database

logger = get_logger(__name__)

broadcast_router = APIRouter()


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _download_media_from_admin_bot(media_file_id: str, broadcast_id: str) -> bytes | None:
    """Download media file from admin bot for re-upload."""
    admin_token = os.environ.get("ADMIN_BOT_TOKEN", "")
    if not admin_token:
        return None

    try:
        admin_bot = Bot(token=admin_token)
        file = await admin_bot.get_file(media_file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{admin_token}/{file_path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(file_url)
            if response.status_code == 200:
                logger.info(f"Broadcast {broadcast_id}: Downloaded media file, size={len(response.content)} bytes")
                await admin_bot.session.close()
                return response.content
            logger.error(f"Broadcast {broadcast_id}: Failed to download media, status={response.status_code}")

        await admin_bot.session.close()
    except Exception:
        logger.exception(f"Broadcast {broadcast_id}: Failed to download media from admin bot")

    return None


def _get_localized_message(content: dict, lang: str) -> dict:
    """Get localized message content with fallbacks."""
    return content.get(lang) or content.get("en") or (next(iter(content.values())) if content else {})


def _build_keyboard_rows(buttons: list, lang: str) -> list[list[InlineKeyboardButton]]:
    """Build keyboard rows from button definitions."""
    rows = []
    for btn in buttons:
        text_dict = btn.get("text", {})
        btn_text = text_dict.get(lang) or text_dict.get("en") or (next(iter(text_dict.values())) if text_dict else "Button")

        if "url" in btn:
            rows.append([InlineKeyboardButton(text=btn_text, url=btn["url"])])
        elif "web_app" in btn:
            rows.append([InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=btn["web_app"]["url"]))])
        elif "callback_data" in btn:
            rows.append([InlineKeyboardButton(text=btn_text, callback_data=btn["callback_data"])])

    return rows


async def _send_media_message(
    bot: Bot, telegram_id: int, media_bytes: bytes | None, media_file_id: str | None,
    media_type: str | None, text: str, parse_mode_str: str, keyboard: InlineKeyboardMarkup | None
) -> bool:
    """Send message with media (photo, video, animation) or text. Returns True on success, False if nothing to send."""
    # Photo with bytes
    if media_bytes and media_type == "photo":
        await bot.send_photo(
            chat_id=telegram_id,
            photo=BufferedInputFile(media_bytes, filename="broadcast.jpg"),
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    # Video with bytes
    if media_bytes and media_type == "video":
        await bot.send_video(
            chat_id=telegram_id,
            video=BufferedInputFile(media_bytes, filename="broadcast.mp4"),
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    # Animation with bytes
    if media_bytes and media_type == "animation":
        await bot.send_animation(
            chat_id=telegram_id,
            animation=BufferedInputFile(media_bytes, filename="broadcast.gif"),
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    # Fallback to file_id (may fail if from different bot)
    if media_file_id and media_type == "photo":
        await bot.send_photo(
            chat_id=telegram_id, photo=media_file_id,
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    if media_file_id and media_type == "video":
        await bot.send_video(
            chat_id=telegram_id, video=media_file_id,
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    if media_file_id and media_type == "animation":
        await bot.send_animation(
            chat_id=telegram_id, animation=media_file_id,
            caption=text, parse_mode=parse_mode_str, reply_markup=keyboard,
        )
        return True

    # Text-only message - only send if we have text content
    if text:
        from core.services.telegram_messaging import send_telegram_message_with_keyboard
        token = os.environ.get("TELEGRAM_TOKEN", "")
        await send_telegram_message_with_keyboard(
            chat_id=telegram_id, text=text,
            keyboard=keyboard if keyboard else None,
            parse_mode=parse_mode_str, bot_token=token,
        )
        return True

    # No content to send
    return False


async def _handle_send_failure(db, user_id: str, telegram_id: int, broadcast_id: str, error_msg: str) -> None:
    """Handle message send failure - update user and recipient status."""
    blocked_phrases = [
        "bot was blocked by the user",
        "chat not found",
        "user is deactivated",
        "forbidden: bot can't initiate",
    ]
    is_blocked = any(phrase in error_msg.lower() for phrase in blocked_phrases)

    if is_blocked:
        await (
            db.client.table("users")
            .update({"bot_blocked_at": datetime.now(UTC).isoformat()})
            .eq("id", user_id)
            .execute()
        )
        logger.info(f"Marked user {user_id} as blocked (telegram_id={telegram_id})")

    await (
        db.client.table("broadcast_recipients")
        .update({"status": "failed", "error_message": error_msg[:500]})
        .eq("broadcast_id", broadcast_id)
        .eq("user_id", user_id)
        .execute()
    )


async def _send_to_user(
    db, bot: Bot, user_id: str, broadcast: dict, content: dict, buttons: list,
    media_bytes: bytes | None, broadcast_id: str
) -> bool:
    """Send broadcast message to a single user. Returns True if sent successfully."""
    media_file_id = broadcast.get("media_file_id")
    media_type = broadcast.get("media_type")

    # Get user data
    user_result = (
        await db.client.table("users")
        .select("telegram_id, language_code, first_name")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not user_result.data:
        return False

    user = user_result.data
    lang = user.get("language_code", "en")
    telegram_id = user.get("telegram_id")
    first_name = user.get("first_name", "")

    if not telegram_id:
        return False

    # Get localized message
    msg_data = _get_localized_message(content, lang)
    text = msg_data.get("text", "").replace("{name}", first_name or "")
    parse_mode_str = msg_data.get("parse_mode", "HTML")

    # Build keyboard
    keyboard = None
    if buttons:
        rows = _build_keyboard_rows(buttons, lang)
        if rows:
            keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    try:
        await _send_media_message(
            bot, telegram_id, media_bytes, media_file_id, media_type,
            text, parse_mode_str, keyboard
        )

        # Update recipient status
        await (
            db.client.table("broadcast_recipients")
            .update({"status": "sent", "sent_at": datetime.now(UTC).isoformat()})
            .eq("broadcast_id", broadcast_id)
            .eq("user_id", user_id)
            .execute()
        )
        return True

    except Exception as e:
        error_type = type(e).__name__
        from core.logging import sanitize_id_for_logging

        logger.warning(
            "Broadcast to user failed: broadcast_id=%s, error_type=%s",
            sanitize_id_for_logging(broadcast_id),
            error_type,
        )
        error_msg = str(e)
        await _handle_send_failure(db, user_id, telegram_id, broadcast_id, error_msg)
        return False


async def _check_broadcast_complete(db, broadcast_id: str, broadcast: dict, sent: int, failed: int) -> None:
    """Check if broadcast is complete and update status."""
    # Update broadcast stats
    new_sent_count = broadcast.get("sent_count", 0) + sent
    new_failed_count = broadcast.get("failed_count", 0) + failed

    await (
        db.client.table("broadcast_messages")
        .update({"sent_count": new_sent_count, "failed_count": new_failed_count})
        .eq("id", broadcast_id)
        .execute()
    )

    # Query actual counts from DB
    total_recipients_result = (
        await db.client.table("broadcast_recipients")
        .select("id", count="exact")
        .eq("broadcast_id", broadcast_id)
        .execute()
    )
    total_sent_result = (
        await db.client.table("broadcast_recipients")
        .select("id", count="exact")
        .eq("broadcast_id", broadcast_id)
        .eq("status", "sent")
        .execute()
    )
    total_failed_result = (
        await db.client.table("broadcast_recipients")
        .select("id", count="exact")
        .eq("broadcast_id", broadcast_id)
        .eq("status", "failed")
        .execute()
    )

    total_recipients = total_recipients_result.count or 0
    total_sent_in_db = total_sent_result.count or 0
    total_failed_in_db = total_failed_result.count or 0
    total_processed = total_sent_in_db + total_failed_in_db

    logger.info(
        f"Broadcast {broadcast_id}: DB counts - total={total_recipients}, "
        f"sent={total_sent_in_db}, failed={total_failed_in_db}, processed={total_processed}"
    )

    if total_processed >= total_recipients > 0:
        await (
            db.client.table("broadcast_messages")
            .update({"status": "sent", "completed_at": datetime.now(UTC).isoformat()})
            .eq("id", broadcast_id)
            .execute()
        )
        logger.info(f"Broadcast {broadcast_id} completed: {total_sent_in_db} sent, {total_failed_in_db} failed")


# =============================================================================
# Main Worker Endpoint
# =============================================================================


@broadcast_router.post("/send-broadcast")
async def worker_send_broadcast(request: Request):
    """
    QStash Worker: Send broadcast message to batch of users.

    Accepts:
    - broadcast_id: ID рассылки
    - user_ids: Batch пользователей (50-100 за раз)
    - target_bot: 'pvndora' or 'discount'
    """
    logger.info("Worker send-broadcast called")
    try:
        data = await verify_qstash(request)
        logger.info(f"QStash verified, data keys: {list(data.keys())}")
    except Exception as e:
        error_type = type(e).__name__
        logger.exception("QStash verification failed")
        return {"error": f"QStash verification failed: {error_type}"}

    broadcast_id = data.get("broadcast_id")
    user_ids = data.get("user_ids", [])
    target_bot = data.get("target_bot", "pvndora")

    logger.info(f"Broadcast worker: broadcast_id={broadcast_id}, user_ids_count={len(user_ids)}, target_bot={target_bot}")

    if not broadcast_id or not user_ids:
        logger.error("Broadcast worker: missing required fields")
        return {"error": "broadcast_id and user_ids required"}

    db = get_database()

    # Get broadcast template
    logger.info(f"Fetching broadcast {broadcast_id} from database")
    broadcast_result = (
        await db.client.table("broadcast_messages")
        .select("*")
        .eq("id", broadcast_id)
        .single()
        .execute()
    )

    if not broadcast_result.data:
        logger.error(f"Broadcast {broadcast_id} not found in database")
        return {"error": "Broadcast not found"}

    logger.info(f"Broadcast {broadcast_id} found: status={broadcast_result.data.get('status')}")

    broadcast = broadcast_result.data
    content = broadcast.get("content", {})
    buttons = broadcast.get("buttons", [])
    media_file_id = broadcast.get("media_file_id")
    media_type = broadcast.get("media_type")

    # Get appropriate bot token
    token = os.environ.get("DISCOUNT_BOT_TOKEN", "") if target_bot == "discount" else os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        return {"error": f"Bot token not configured for {target_bot}"}

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Download media if needed
    media_bytes = None
    if media_file_id and media_type:
        media_bytes = await _download_media_from_admin_bot(media_file_id, broadcast_id)

    sent = 0
    failed = 0

    try:
        for user_id in user_ids:
            success = await _send_to_user(
                db, bot, user_id, broadcast, content, buttons, media_bytes, broadcast_id
            )
            if success:
                sent += 1
            else:
                failed += 1

            # Rate limiting - 30 messages per second max
            await asyncio.sleep(0.035)

        await _check_broadcast_complete(db, broadcast_id, broadcast, sent, failed)

    finally:
        await bot.session.close()

    logger.info(f"Broadcast {broadcast_id}: sent={sent}, failed={failed}")
    return {"sent": sent, "failed": failed}
