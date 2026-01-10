"""
Broadcast Worker

QStash worker for sending broadcast messages to users.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Request

import httpx
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BufferedInputFile

from core.services.database import get_database
from core.routers.deps import verify_qstash
from core.logging import get_logger

logger = get_logger(__name__)

broadcast_router = APIRouter()


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
        logger.error(f"QStash verification failed: {e}")
        return {"error": f"QStash verification failed: {str(e)}"}
    
    broadcast_id = data.get("broadcast_id")
    user_ids = data.get("user_ids", [])
    target_bot = data.get("target_bot", "pvndora")
    
    logger.info(f"Broadcast worker: broadcast_id={broadcast_id}, user_ids_count={len(user_ids)}, target_bot={target_bot}")
    
    if not broadcast_id or not user_ids:
        logger.error(f"Broadcast worker: missing required fields - broadcast_id={broadcast_id}, user_ids_count={len(user_ids) if user_ids else 0}")
        return {"error": "broadcast_id and user_ids required"}
    
    db = get_database()
    
    # Get broadcast template
    logger.info(f"Fetching broadcast {broadcast_id} from database")
    broadcast_result = await db.client.table("broadcast_messages").select("*").eq(
        "id", broadcast_id
    ).single().execute()
    
    if not broadcast_result.data:
        logger.error(f"Broadcast {broadcast_id} not found in database")
        return {"error": "Broadcast not found"}
    
    logger.info(f"Broadcast {broadcast_id} found: status={broadcast_result.data.get('status')}, recipients={broadcast_result.data.get('total_recipients')}")
    
    broadcast = broadcast_result.data
    content = broadcast.get("content", {})
    buttons = broadcast.get("buttons", [])
    media_file_id = broadcast.get("media_file_id")
    media_type = broadcast.get("media_type")
    
    # Get appropriate bot
    if target_bot == "discount":
        token = os.environ.get("DISCOUNT_BOT_TOKEN", "")
    else:
        token = os.environ.get("TELEGRAM_TOKEN", "")
    
    if not token:
        return {"error": f"Bot token not configured for {target_bot}"}
    
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # CRITICAL: file_id from Admin Bot doesn't work with other bots!
    # We need to download the file and re-upload it
    media_bytes = None
    if media_file_id and media_type:
        admin_token = os.environ.get("ADMIN_BOT_TOKEN", "")
        if admin_token:
            try:
                admin_bot = Bot(token=admin_token)
                file = await admin_bot.get_file(media_file_id)
                file_path = file.file_path
                # Download file from Telegram servers
                file_url = f"https://api.telegram.org/file/bot{admin_token}/{file_path}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_url)
                    if response.status_code == 200:
                        media_bytes = response.content
                        logger.info(f"Broadcast {broadcast_id}: Downloaded media file, size={len(media_bytes)} bytes")
                    else:
                        logger.error(f"Broadcast {broadcast_id}: Failed to download media, status={response.status_code}")
                await admin_bot.session.close()
            except Exception as e:
                logger.error(f"Broadcast {broadcast_id}: Failed to download media from admin bot: {e}")
    
    sent = 0
    failed = 0
    
    try:
        for user_id in user_ids:
            # Get user data
            user_result = await db.client.table("users").select(
                "telegram_id, language_code, first_name"
            ).eq("id", user_id).single().execute()
            
            if not user_result.data:
                failed += 1
                continue
            
            user = user_result.data
            lang = user.get("language_code", "en")
            telegram_id = user.get("telegram_id")
            first_name = user.get("first_name", "")
            
            if not telegram_id:
                failed += 1
                continue
            
            # Get localized message (fallback to English, then first available)
            msg_data = content.get(lang) or content.get("en") or (list(content.values())[0] if content else {})
            text = msg_data.get("text", "")
            parse_mode_str = msg_data.get("parse_mode", "HTML")
            
            # Personalize message
            text = text.replace("{name}", first_name or "")
            
            # Build keyboard
            keyboard = None
            if buttons:
                rows = []
                for btn in buttons:
                    text_dict = btn.get("text", {})
                    btn_text = text_dict.get(lang) or text_dict.get("en") or (list(text_dict.values())[0] if text_dict else "Button")
                    
                    if "url" in btn:
                        rows.append([InlineKeyboardButton(text=btn_text, url=btn["url"])])
                    elif "web_app" in btn:
                        rows.append([InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=btn["web_app"]["url"]))])
                    elif "callback_data" in btn:
                        rows.append([InlineKeyboardButton(text=btn_text, callback_data=btn["callback_data"])])
                
                if rows:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
            
            try:
                # Use downloaded media bytes if available, otherwise try file_id
                if media_bytes and media_type == "photo":
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=BufferedInputFile(media_bytes, filename="broadcast.jpg"),
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                elif media_bytes and media_type == "video":
                    await bot.send_video(
                        chat_id=telegram_id,
                        video=BufferedInputFile(media_bytes, filename="broadcast.mp4"),
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                elif media_file_id and media_type == "photo":
                    # Fallback to file_id (may fail if from different bot)
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=media_file_id,
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                elif media_file_id and media_type == "video":
                    await bot.send_video(
                        chat_id=telegram_id,
                        video=media_file_id,
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                elif media_bytes and media_type == "animation":
                    await bot.send_animation(
                        chat_id=telegram_id,
                        animation=BufferedInputFile(media_bytes, filename="broadcast.gif"),
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                elif media_file_id and media_type == "animation":
                    # Fallback to file_id
                    await bot.send_animation(
                        chat_id=telegram_id,
                        animation=media_file_id,
                        caption=text,
                        parse_mode=parse_mode_str,
                        reply_markup=keyboard
                    )
                else:
                    # Use consolidated telegram messaging for text messages
                    from core.services.telegram_messaging import send_telegram_message_with_keyboard
                    await send_telegram_message_with_keyboard(
                        chat_id=telegram_id,
                        text=text,
                        keyboard=keyboard if keyboard else None,
                        parse_mode=parse_mode_str,
                        bot_token=token
                    )
                sent += 1
                
                # Update recipient status
                await db.client.table("broadcast_recipients").update({
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat()
                }).eq("broadcast_id", broadcast_id).eq("user_id", user_id).execute()
                
            except Exception as e:
                failed += 1
                error_msg = str(e)
                logger.warning(f"Broadcast to {telegram_id} failed: {error_msg}")
                
                # Check if user is permanently unreachable
                is_blocked = any(phrase in error_msg.lower() for phrase in [
                    "bot was blocked by the user",
                    "chat not found",
                    "user is deactivated",
                    "forbidden: bot can't initiate"
                ])
                
                if is_blocked:
                    # Mark user as unreachable for future broadcasts
                    await db.client.table("users").update({
                        "bot_blocked_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", user_id).execute()
                    logger.info(f"Marked user {user_id} as blocked (telegram_id={telegram_id})")
                
                # Update recipient status with error
                await db.client.table("broadcast_recipients").update({
                    "status": "failed",
                    "error_message": error_msg[:500]
                }).eq("broadcast_id", broadcast_id).eq("user_id", user_id).execute()
            
            # Rate limiting - 30 messages per second max for bots
            import asyncio
            await asyncio.sleep(0.035)
        
        # Update broadcast stats
        new_sent_count = broadcast.get("sent_count", 0) + sent
        new_failed_count = broadcast.get("failed_count", 0) + failed
        
        await db.client.table("broadcast_messages").update({
            "sent_count": new_sent_count,
            "failed_count": new_failed_count
        }).eq("id", broadcast_id).execute()
        
        # Check if broadcast is complete (all recipients processed)
        # Query actual counts from DB instead of relying on broadcast data
        total_recipients_result = await db.client.table("broadcast_recipients").select(
            "id", count="exact"
        ).eq("broadcast_id", broadcast_id).execute()
        total_sent_result = await db.client.table("broadcast_recipients").select(
            "id", count="exact"
        ).eq("broadcast_id", broadcast_id).eq("status", "sent").execute()
        total_failed_result = await db.client.table("broadcast_recipients").select(
            "id", count="exact"
        ).eq("broadcast_id", broadcast_id).eq("status", "failed").execute()
        
        total_recipients = total_recipients_result.count or 0
        total_sent_in_db = total_sent_result.count or 0
        total_failed_in_db = total_failed_result.count or 0
        total_processed = total_sent_in_db + total_failed_in_db
        
        logger.info(f"Broadcast {broadcast_id}: DB counts - total={total_recipients}, sent={total_sent_in_db}, failed={total_failed_in_db}, processed={total_processed}")
        
        if total_processed >= total_recipients and total_recipients > 0:
            # All recipients processed - mark as completed
            await db.client.table("broadcast_messages").update({
                "status": "sent",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", broadcast_id).execute()
            logger.info(f"Broadcast {broadcast_id} completed: {total_sent_in_db} sent, {total_failed_in_db} failed")
        
    finally:
        await bot.session.close()
    
    logger.info(f"Broadcast {broadcast_id}: sent={sent}, failed={failed}")
    return {"sent": sent, "failed": failed}
