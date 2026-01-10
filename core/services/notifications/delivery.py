"""
Delivery Notifications

Notifications for order delivery and credentials.
"""
import os
from datetime import datetime
from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from core.i18n import get_text
from core.logging import get_logger
from .base import NotificationServiceBase, get_user_language, _msg

logger = get_logger(__name__)


class DeliveryNotificationsMixin(NotificationServiceBase):
    """Mixin for delivery-related notifications."""
    
    async def _send_credentials(
        self,
        telegram_id: int,
        product_name: str,
        credentials: str,
        instructions: Optional[str],
        expires_at: Optional[datetime],
        order_id: str,
        language: str
    ) -> None:
        """Send credentials to user via Telegram"""
        # Format expiration
        expires_str = "N/A"
        if expires_at:
            expires_str = expires_at.strftime("%d.%m.%Y %H:%M UTC")
        
        # Build message
        message = get_text(
            "order_success",
            language,
            credentials=f"<code>{credentials}</code>",
            instructions=instructions or get_text("no_instructions", language) if hasattr(get_text, "no_instructions") else "See product documentation",
            expires=expires_str
        )
        
        # Add order keyboard
        from core.bot.keyboards import get_order_keyboard
        keyboard = get_order_keyboard(language, order_id)
        
        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard
            await send_telegram_message_with_keyboard(
                chat_id=telegram_id,
                text=message,
                keyboard=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send credentials to {telegram_id}: {e}")
    
    async def send_replacement_notification(
        self,
        telegram_id: int,
        product_name: str,
        item_id: str
    ) -> None:
        """Send notification about account replacement"""
        lang = await get_user_language(telegram_id)
        short_id = item_id[:8] if len(item_id) > 8 else item_id
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     🔄 <b>ЗАМЕНА ВЫПОЛНЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Товар:</b> {product_name}\n"
            f"◈ <b>ID:</b> <code>{short_id}</code>\n\n"
            f"Новые данные доступа готовы.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Посмотреть → «Мои заказы»</i>",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     🔄 <b>REPLACEMENT DONE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Product:</b> {product_name}\n"
            f"◈ <b>ID:</b> <code>{short_id}</code>\n\n"
            f"New access credentials are ready.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>View → «My Orders»</i>"
        )
        
        # Add WebApp button
        webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📦 Мои заказы" if lang == "ru" else "📦 My Orders",
                web_app=WebAppInfo(url=f"{webapp_url}/orders")
            )
        ]])
        
        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard
            await send_telegram_message_with_keyboard(
                chat_id=telegram_id,
                text=message,
                keyboard=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Sent replacement notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send replacement notification to {telegram_id}: {e}")
    
    async def send_delivery(
        self, 
        telegram_id: int, 
        product_name: str, 
        content: str,
        expires_at: Optional[datetime] = None,
        order_id: Optional[str] = None
    ) -> None:
        """Send delivery notification with product credentials."""
        lang = await get_user_language(telegram_id)
        
        # Format expiration if available
        expires_info = ""
        if expires_at:
            expires_str = expires_at.strftime("%d.%m.%Y")
            expires_info = _msg(lang,
                f"\n◈ <b>Активен до:</b> {expires_str}",
                f"\n◈ <b>Valid until:</b> {expires_str}"
            )
        
        # Order reference
        order_ref = ""
        if order_id:
            short_id = order_id[:8]
            order_ref = _msg(lang,
                f"<i>#{short_id}</i>\n",
                f"<i>#{short_id}</i>\n"
            )
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      💎 <b>ДОСТАВКА ЗАВЕРШЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"{order_ref}"
            f"◈ <b>Товар:</b> {product_name}\n"
            f"◈ <b>Статус:</b> Активирован ✓{expires_info}\n\n"
            f"🔐 <b>ДАННЫЕ ДОСТУПА</b>\n"
            f"<code>{content}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Инструкции и детали — в разделе «Мои заказы»</i>\n\n"
            f"⭐ Оставьте отзыв → получите <b>5% кэшбэк</b>",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      💎 <b>DELIVERY COMPLETE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"{order_ref}"
            f"◈ <b>Product:</b> {product_name}\n"
            f"◈ <b>Status:</b> Activated ✓{expires_info}\n\n"
            f"🔐 <b>ACCESS CREDENTIALS</b>\n"
            f"<code>{content}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Instructions & details — in «My Orders»</i>\n\n"
            f"⭐ Leave a review → get <b>5% cashback</b>"
        )
        
        # Add WebApp button for viewing order
        keyboard = None
        if order_id:
            webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📦 Мои заказы" if lang == "ru" else "📦 My Orders",
                    web_app=WebAppInfo(url=f"{webapp_url}/orders")
                )
            ]])
        
        try:
            from core.services.telegram_messaging import send_telegram_message_with_keyboard
            if keyboard:
                await send_telegram_message_with_keyboard(
                    chat_id=telegram_id,
                    text=message,
                    keyboard=keyboard,
                    parse_mode="HTML"
                )
            else:
                from core.services.telegram_messaging import send_telegram_message
                await send_telegram_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Failed to send delivery notification: {e}")
