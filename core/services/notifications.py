"""Notification Service - Order Fulfillment and Telegram Notifications"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from core.services.database import get_database
from core.i18n import get_text
from core.logging import get_logger

logger = get_logger(__name__)


async def get_user_language(telegram_id: int) -> str:
    """Get user's preferred language from database."""
    try:
        db = get_database()
        result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("interface_language, language_code")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute()
        )
        if result.data:
            # Prefer interface_language, fallback to language_code
            lang = result.data[0].get("interface_language") or result.data[0].get("language_code") or "en"
            # Normalize to supported languages (en/ru)
            return "ru" if lang.lower().startswith("ru") else "en"
    except Exception as e:
        logger.warning(f"Failed to get user language for {telegram_id}: {e}")
    return "en"


def _msg(lang: str, ru: str, en: str) -> str:
    """Return message in user's language."""
    return ru if lang == "ru" else en


async def get_referral_settings() -> dict:
    """Get referral program settings from database."""
    try:
        db = get_database()
        result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        if result.data:
            s = result.data[0]
            return {
                "level1_percent": int(s.get("level1_commission_percent", 10) or 10),
                "level2_percent": int(s.get("level2_commission_percent", 7) or 7),
                "level3_percent": int(s.get("level3_commission_percent", 3) or 3),
                "level2_threshold": int(s.get("level2_threshold_usd", 250) or 250),
                "level3_threshold": int(s.get("level3_threshold_usd", 1000) or 1000),
            }
    except Exception as e:
        logger.warning(f"Failed to get referral settings: {e}")
    # Default values
    return {
        "level1_percent": 10,
        "level2_percent": 7,
        "level3_percent": 3,
        "level2_threshold": 250,
        "level3_threshold": 1000,
    }


class NotificationService:
    """Service for sending notifications and fulfilling orders"""
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_TOKEN", "")
        self._bot: Optional[Bot] = None
    
    def _get_bot(self) -> Bot:
        """Get or create bot instance"""
        if self._bot is None and self.bot_token:
            self._bot = Bot(
                token=self.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        return self._bot
    
    async def fulfill_order(self, order_id: str) -> bool:
        """
        Process order fulfillment after successful payment.
        
        DEPRECATED: Use workers._deliver_items_for_order instead.
        This is legacy code kept for backwards compatibility.
        
        1. Get available stock item
        2. Reserve the stock item (atomic)
        3. Send credentials to user
        4. Update order status
        5. Notify supplier
        6. Process referral bonus
        
        Args:
            order_id: Order ID to fulfill
            
        Returns:
            True if successful, False otherwise
        """
        db = get_database()
        
        # Get order details
        order = await db.get_order_by_id(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        if order.status == "delivered":
            logger.info(f"Order already completed: {order_id}")
            return True
        
        # Get user
        user_result = db.client.table("users").select("*").eq("id", order.user_id).execute()
        if not user_result.data:
            logger.warning(f"User not found for order: {order_id}")
            return False
        
        user = user_result.data[0]
        language = user.get("language_code", "en")
        
        # Get product_id from order_items (source of truth)
        order_items = await db.get_order_items_by_order(order_id)
        if not order_items:
            logger.warning(f"No order items found for order: {order_id}")
            await self._refund_to_balance(order, user, language, "No order items")
            return False
        
        product_id = order_items[0].get("product_id")
        
        # Get product
        product = await db.get_product_by_id(product_id)
        if not product:
            logger.warning(f"Product not found for order: {order_id}")
            await self._refund_to_balance(order, user, language, "Product not found")
            return False
        
        # Get available stock item
        stock_item = await db.get_available_stock_item(product_id)
        if not stock_item:
            logger.warning(f"No stock available for order: {order_id}")
            await self._refund_to_balance(order, user, language, "Out of stock")
            return False
        
        # Reserve stock item (atomic operation)
        reserved = await db.reserve_stock_item(stock_item.id)
        if not reserved:
            # Race condition - item was sold to someone else
            logger.info(f"Stock item already sold, trying next: {order_id}")
            
            # Try one more time with a different item
            stock_item = await db.get_available_stock_item(product_id)
            if stock_item:
                reserved = await db.reserve_stock_item(stock_item.id)
            
            if not reserved:
                await self._refund_to_balance(order, user, language, "Stock race condition")
                return False
        
        # Calculate expiration
        expires_at = None
        if stock_item.expires_at:
            expires_at = stock_item.expires_at
        elif product.warranty_hours:
            # For items without preset expiry, calculate from purchase
            # Assuming warranty_hours represents subscription duration in hours
            # This is simplified - adjust based on your business logic
            expires_at = datetime.utcnow() + timedelta(hours=product.warranty_hours)
        
        # Update order with expiration
        # Note: stock_item_id removed - stock items are linked via order_items table
        await db.update_order_status(
            order_id=order_id,
            status="delivered",
            expires_at=expires_at
        )
        
        # Send credentials to user
        await self._send_credentials(
            telegram_id=user["telegram_id"],
            product_name=product.name,
            credentials=stock_item.content,
            instructions=product.instructions,
            expires_at=expires_at,
            order_id=order_id,
            language=language
        )
        
        # Notify supplier if configured
        if stock_item.supplier_id:
            await self._notify_supplier(stock_item.supplier_id, product.name, order.amount)
        
        # Process referral bonus
        await db.process_referral_bonus(order)
        
        # Log analytics event
        await db.log_event(
            user_id=order.user_id,
            event_type="purchase_completed",
            metadata={
                "order_id": order_id,
                "product_id": product.id,
                "amount": order.amount
            }
        )
        
        return True
    
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
        bot = self._get_bot()
        if not bot:
            logger.warning("Bot not configured for notifications")
            return
        
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
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Failed to send credentials to {telegram_id}: {e}")
    
    async def _refund_to_balance(
        self,
        order,
        user: dict,
        language: str,
        reason: str
    ) -> None:
        """Refund order amount to user balance"""
        db = get_database()
        
        # Credit to balance
        await db.update_user_balance(order.user_id, order.amount)
        
        # Update order status
        await db.update_order_status(order.id, "refunded")
        
        # Notify user
        bot = self._get_bot()
        if bot:
            message = get_text("error_payment", language)
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to send refund notification: {e}")
        
        logger.info(f"Refunded order {order.id} to balance: {reason}")
    
    async def send_replacement_notification(
        self,
        telegram_id: int,
        product_name: str,
        item_id: str
    ) -> None:
        """Send notification about account replacement"""
        bot = self._get_bot()
        if not bot:
            return
        
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
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            logger.info(f"Sent replacement notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send replacement notification to {telegram_id}: {e}")
    
    async def send_ticket_approved_notification(
        self,
        telegram_id: int,
        ticket_id: str,
        issue_type: str,
        language: str = "en"
    ) -> None:
        """Send notification when ticket is approved"""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        short_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id
        
        if issue_type == "replacement":
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Решение:</b> Замена\n"
                f"◈ <b>Статус:</b> В обработке\n\n"
                f"<i>Новый аккаунт придёт в течение 24ч</i>",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Resolution:</b> Replacement\n"
                f"◈ <b>Status:</b> Processing\n\n"
                f"<i>New account will arrive within 24h</i>"
            )
        elif issue_type == "refund":
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Решение:</b> Возврат средств\n"
                f"◈ <b>Статус:</b> Зачислено на баланс ✓",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"◈ <b>Resolution:</b> Refund\n"
                f"◈ <b>Status:</b> Credited to balance ✓"
            )
        else:
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>ТИКЕТ ОДОБРЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"Ваш запрос принят в обработку.",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"     ✓ <b>TICKET APPROVED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"<i>#{short_id}</i>\n\n"
                f"Your request is being processed."
            )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent approval notification to {telegram_id} for ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Failed to send approval notification to {telegram_id}: {e}")
    
    async def send_ticket_rejected_notification(
        self,
        telegram_id: int,
        ticket_id: str,
        reason: str,
        language: str = "en"
    ) -> None:
        """Send notification when ticket is rejected"""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        short_id = ticket_id[:8] if len(ticket_id) > 8 else ticket_id
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      ✗ <b>ТИКЕТ ОТКЛОНЁН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<i>#{short_id}</i>\n\n"
            f"К сожалению, запрос не может быть выполнен.\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Есть вопросы? Напишите в поддержку.",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"      ✗ <b>TICKET REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<i>#{short_id}</i>\n\n"
            f"Unfortunately, your request cannot be fulfilled.\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Questions? Contact support."
        )
        
        button_text = "🆘 Поддержка" if lang == "ru" else "🆘 Support"
        
        # Create keyboard with support button
        webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.com")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=button_text,
                web_app=WebAppInfo(url=f"{webapp_url}/support")
            )]
        ])
        
        try:
            await bot.send_message(
                chat_id=telegram_id, 
                text=message, 
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            logger.info(f"Sent rejection notification to {telegram_id} for ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Failed to send rejection notification to {telegram_id}: {e}")
    
    async def _notify_supplier(
        self,
        supplier_id: str,
        product_name: str,
        amount: float
    ) -> None:
        """Notify supplier about sale"""
        db = get_database()
        bot = self._get_bot()
        
        if not bot:
            return
        
        # Get supplier
        supplier_result = db.client.table("suppliers").select("telegram_id,name").eq("id", supplier_id).execute()
        if not supplier_result.data:
            return
        
        supplier = supplier_result.data[0]
        telegram_id = supplier.get("telegram_id")
        
        if not telegram_id:
            return
        
        message = (
            f"💰 <b>Продажа!</b>\n\n"
            f"Товар: {product_name}\n"
            f"Сумма: {amount}₽"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.error(f"Failed to notify supplier {supplier_id}: {e}")
    
    # ==================== SCHEDULED NOTIFICATIONS ====================
    
    async def send_review_request(self, order_id: str) -> None:
        """Send review request 1 hour after purchase"""
        db = get_database()
        bot = self._get_bot()
        
        if not bot:
            return
        
        order = await db.get_order_by_id(order_id)
        if not order or order.status != "delivered":
            return
        
        # Get user
        user_result = db.client.table("users").select("telegram_id,language_code").eq("id", order.user_id).execute()
        if not user_result.data:
            return
        
        user = user_result.data[0]
        language = user.get("language_code", "en")
        
        message = get_text("review_request", language)
        
        from core.bot.keyboards import get_order_keyboard
        keyboard = get_order_keyboard(language, order_id)
        
        try:
            await bot.send_message(
                chat_id=user["telegram_id"],
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Failed to send review request: {e}")
    
    async def send_expiration_reminder(
        self,
        telegram_id: int,
        product_name: str,
        days_left: int,
        language: str
    ) -> None:
        """Send subscription expiration reminder"""
        bot = self._get_bot()
        if not bot:
            return
        
        message = get_text(
            "subscription_expiring",
            language,
            product=product_name,
            days=days_left
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send expiration reminder: {e}")
    
    async def send_waitlist_notification(
        self,
        telegram_id: int,
        product_name: str,
        language: str,
        product_id: Optional[str] = None,
        in_stock: bool = False
    ) -> None:
        """
        Notify user that waitlisted product is available again.
        
        Args:
            telegram_id: User's Telegram ID
            product_name: Name of the product
            language: User's language code
            product_id: Product ID (optional, for creating order link)
            in_stock: Whether product is currently in stock
        """
        bot = self._get_bot()
        if not bot:
            return
        
        # Build message based on stock status
        if in_stock:
            # Product is available immediately
            message = get_text(
                "waitlist_notify_in_stock",
                language,
                product=product_name
            )
        else:
            # Product is active but out of stock - can order prepaid
            message = get_text(
                "waitlist_notify_prepaid",
                language,
                product=product_name
            )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send waitlist notification: {e}")
    
    async def send_referral_unlock_notification(self, telegram_id: int) -> None:
        """
        Send notification when referral program is unlocked after first purchase.
        """
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        settings = await get_referral_settings()
        l1 = settings["level1_percent"]
        l2 = settings["level2_percent"]
        l3 = settings["level3_percent"]
        t2 = settings["level2_threshold"]
        t3 = settings["level3_threshold"]
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   🔗 <b>ПАРТНЁРКА АКТИВИРОВАНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Добро пожаловать в сеть PVNDORA.\n"
            f"Теперь вы получаете бонусы с покупок друзей.\n\n"
            f"<b>▸ УРОВЕНЬ 1</b> — активен\n"
            f"   └ <b>{l1}%</b> с покупок рефералов\n\n"
            f"<b>▸ УРОВЕНЬ 2</b> — оборот ${t2}+\n"
            f"   └ +{l2}% со 2-й линии\n\n"
            f"<b>▸ УРОВЕНЬ 3</b> — оборот ${t3}+\n"
            f"   └ +{l3}% с 3-й линии\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Ссылка и статистика — в профиле</i>",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"   🔗 <b>AFFILIATE ACTIVATED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Welcome to the PVNDORA network.\n"
            f"You now earn bonuses from friends' purchases.\n\n"
            f"<b>▸ LEVEL 1</b> — active\n"
            f"   └ <b>{l1}%</b> from referrals\n\n"
            f"<b>▸ LEVEL 2</b> — turnover ${t2}+\n"
            f"   └ +{l2}% from tier 2\n\n"
            f"<b>▸ LEVEL 3</b> — turnover ${t3}+\n"
            f"   └ +{l3}% from tier 3\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <i>Link & stats — in your profile</i>"
        )
        
        try:
            await bot.send_message(
                chat_id=telegram_id, 
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send referral unlock notification: {e}")
    
    async def send_referral_level_up_notification(self, telegram_id: int, new_level: int) -> None:
        """
        Send notification when user's referral level increases.
        """
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        settings = await get_referral_settings()
        l1 = settings["level1_percent"]
        l2 = settings["level2_percent"]
        l3 = settings["level3_percent"]
        t3 = settings["level3_threshold"]
        
        if new_level == 2:
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    📈 <b>УРОВЕНЬ ПОВЫШЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Вы достигли <b>Уровня 2</b>.\n"
                f"Теперь активна 2-я линия рефералов.\n\n"
                f"<b>▸ ЛИНИЯ 1:</b> {l1}%\n"
                f"<b>▸ ЛИНИЯ 2:</b> +{l2}% ← новое\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"До Уровня 3: оборот ${t3}",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    📈 <b>LEVEL UP</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"You've reached <b>Level 2</b>.\n"
                f"Tier 2 referrals now active.\n\n"
                f"<b>▸ TIER 1:</b> {l1}%\n"
                f"<b>▸ TIER 2:</b> +{l2}% ← new\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"To Level 3: ${t3} turnover"
            )
        elif new_level == 3:
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    🏆 <b>МАКСИМУМ ДОСТИГНУТ</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Поздравляем! <b>Уровень 3</b> — это вершина.\n"
                f"Все три линии активны.\n\n"
                f"<b>▸ ЛИНИЯ 1:</b> {l1}%\n"
                f"<b>▸ ЛИНИЯ 2:</b> {l2}%\n"
                f"<b>▸ ЛИНИЯ 3:</b> +{l3}% ← новое\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <i>Вы — VIP партнёр PVNDORA</i>",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"    🏆 <b>MAXIMUM REACHED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Congratulations! <b>Level 3</b> — the top.\n"
                f"All three tiers active.\n\n"
                f"<b>▸ TIER 1:</b> {l1}%\n"
                f"<b>▸ TIER 2:</b> {l2}%\n"
                f"<b>▸ TIER 3:</b> +{l3}% ← new\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <i>You're a PVNDORA VIP Partner</i>"
            )
        else:
            return
        
        try:
            await bot.send_message(
                chat_id=telegram_id, 
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send referral level up notification: {e}")
    
    async def send_delivery(
        self, 
        telegram_id: int, 
        product_name: str, 
        content: str,
        expires_at: Optional[datetime] = None,
        order_id: Optional[str] = None
    ) -> None:
        """Send delivery notification with product credentials."""
        bot = self._get_bot()
        if not bot:
            return
        
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
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Failed to send delivery notification: {e}")
    
    async def send_cashback_notification(
        self,
        telegram_id: int,
        cashback_amount: float,
        new_balance: float,
        reason: str = "review"
    ) -> None:
        """Send notification about cashback credit."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        if reason == "review":
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>КЭШБЕК ЗАЧИСЛЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Спасибо за ваш отзыв!\n\n"
                f"◈ <b>Начислено:</b> +${cashback_amount:.2f}\n"
                f"◈ <b>Баланс:</b> ${new_balance:.2f}\n\n"
                f"<i>Ваше мнение помогает другим оперативникам</i> ✓",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>CASHBACK CREDITED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"Thank you for your review!\n\n"
                f"◈ <b>Credited:</b> +${cashback_amount:.2f}\n"
                f"◈ <b>Balance:</b> ${new_balance:.2f}\n\n"
                f"<i>Your feedback helps other operatives</i> ✓"
            )
        else:
            message = _msg(lang,
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>КЭШБЕК ЗАЧИСЛЕН</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"◈ <b>Начислено:</b> +${cashback_amount:.2f}\n"
                f"◈ <b>Баланс:</b> ${new_balance:.2f}",
                
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
                f"      💰 <b>CASHBACK CREDITED</b>\n"
                f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
                f"◈ <b>Credited:</b> +${cashback_amount:.2f}\n"
                f"◈ <b>Balance:</b> ${new_balance:.2f}"
            )
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Sent cashback notification to {telegram_id}: ${cashback_amount:.2f}")
        except Exception as e:
            logger.error(f"Failed to send cashback notification: {e}")
    
    async def send_broadcast(
        self,
        message: str,
        exclude_dnd: bool = True
    ) -> int:
        """
        Send broadcast message to all users.
        
        Args:
            message: Message text
            exclude_dnd: Exclude users with do_not_disturb=True
            
        Returns:
            Number of successfully sent messages
        """
        db = get_database()
        bot = self._get_bot()
        
        if not bot:
            return 0
        
        # Get users
        query = db.client.table("users").select("telegram_id").eq("is_banned", False)
        if exclude_dnd:
            query = query.eq("do_not_disturb", False)
        
        result = query.execute()
        
        sent_count = 0
        for user in result.data:
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=message
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['telegram_id']}: {e}")
        
        return sent_count
    
    # ==================== WITHDRAWAL NOTIFICATIONS ====================
    
    async def send_withdrawal_approved_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        method: str
    ) -> None:
        """Notify user that their withdrawal request was approved."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✓ <b>ВЫВОД ОДОБРЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> ${amount:.2f}\n"
            f"◈ <b>Метод:</b> {method}\n"
            f"◈ <b>Статус:</b> Ожидает отправки\n\n"
            f"<i>Средства поступят в течение 24ч</i>",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✓ <b>WITHDRAWAL APPROVED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> ${amount:.2f}\n"
            f"◈ <b>Method:</b> {method}\n"
            f"◈ <b>Status:</b> Pending send\n\n"
            f"<i>Funds will arrive within 24h</i>"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal approved notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send withdrawal approved notification to {telegram_id}: {e}")
    
    async def send_withdrawal_rejected_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        reason: str
    ) -> None:
        """Notify user that their withdrawal request was rejected."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>ВЫВОД ОТКЛОНЁН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> ${amount:.2f}\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Средства возвращены на баланс ✓",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>WITHDRAWAL REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> ${amount:.2f}\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Funds returned to balance ✓"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal rejected notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send withdrawal rejected notification to {telegram_id}: {e}")
    
    async def send_withdrawal_completed_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        method: str
    ) -> None:
        """Notify user that their withdrawal has been completed."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>ВЫВОД ВЫПОЛНЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Сумма:</b> ${amount:.2f}\n"
            f"◈ <b>Метод:</b> {method}\n"
            f"◈ <b>Статус:</b> Отправлено ✓\n\n"
            f"<i>Спасибо за использование PVNDORA</i>",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>WITHDRAWAL COMPLETE</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Amount:</b> ${amount:.2f}\n"
            f"◈ <b>Method:</b> {method}\n"
            f"◈ <b>Status:</b> Sent ✓\n\n"
            f"<i>Thank you for using PVNDORA</i>"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent withdrawal completed notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send withdrawal completed notification to {telegram_id}: {e}")
    
    # ==================== TOPUP NOTIFICATIONS ====================
    
    async def send_topup_success_notification(
        self,
        telegram_id: int,
        amount: float,
        currency: str,
        new_balance: float
    ) -> None:
        """Notify user that their balance was topped up."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💰 <b>БАЛАНС ПОПОЛНЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Зачислено:</b> +{amount:.2f} {currency}\n"
            f"◈ <b>Баланс:</b> ${new_balance:.2f}\n\n"
            f"<i>Средства доступны для покупок</i> ✓",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💰 <b>BALANCE TOPPED UP</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Credited:</b> +{amount:.2f} {currency}\n"
            f"◈ <b>Balance:</b> ${new_balance:.2f}\n\n"
            f"<i>Funds available for purchases</i> ✓"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent topup success notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send topup success notification to {telegram_id}: {e}")
    
    # ==================== PARTNER APPLICATION NOTIFICATIONS ====================
    
    async def send_partner_application_approved_notification(
        self,
        telegram_id: int
    ) -> None:
        """Notify user that their partner application was approved."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "    🏆 <b>VIP-ПАРТНЁР PVNDORA</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Поздравляем! Ваша заявка одобрена.\n\n"
            "<b>Теперь вам доступны:</b>\n"
            "▸ Повышенные комиссии\n"
            "▸ Персональный менеджер\n"
            "▸ Приоритетная поддержка\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Добро пожаловать в команду</i> 💎",
            
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            "    🏆 <b>PVNDORA VIP PARTNER</b>\n"
            "◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            "Congratulations! Your application was approved.\n\n"
            "<b>You now have access to:</b>\n"
            "▸ Increased commissions\n"
            "▸ Personal manager\n"
            "▸ Priority support\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Welcome to the team</i> 💎"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent partner approved notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send partner approved notification to {telegram_id}: {e}")
    
    async def send_partner_application_rejected_notification(
        self,
        telegram_id: int,
        reason: Optional[str] = None
    ) -> None:
        """Notify user that their partner application was rejected."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        reason_text_ru = reason or "Заявка не соответствует требованиям программы."
        reason_text_en = reason or "Application does not meet program requirements."
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Причина:</b>\n"
            f"<i>{reason_text_ru}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Подайте повторно позже или\n"
            f"напишите в поддержку.",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     ✗ <b>APPLICATION REJECTED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"◈ <b>Reason:</b>\n"
            f"<i>{reason_text_en}</i>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Reapply later or contact\n"
            f"support for details."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent partner rejected notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send partner rejected notification to {telegram_id}: {e}")
    
    # ==================== REFERRAL NOTIFICATIONS ====================
    
    async def send_referral_bonus_notification(
        self,
        telegram_id: int,
        bonus_amount: float,
        referral_name: str,
        purchase_amount: float,
        line: int = 1
    ) -> None:
        """Notify referrer about bonus from referral purchase."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        line_info_ru = f" • линия {line}" if line > 1 else ""
        line_info_en = f" • tier {line}" if line > 1 else ""
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>БОНУС ПОЛУЧЕН</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Ваш реферал <b>{referral_name}</b>{line_info_ru}\n"
            f"совершил покупку.\n\n"
            f"◈ <b>Сумма покупки:</b> ${purchase_amount:.2f}\n"
            f"◈ <b>Ваш бонус:</b> +${bonus_amount:.2f}\n\n"
            f"<i>Зачислено на баланс</i> ✓",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     💸 <b>BONUS RECEIVED</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"Your referral <b>{referral_name}</b>{line_info_en}\n"
            f"made a purchase.\n\n"
            f"◈ <b>Purchase:</b> ${purchase_amount:.2f}\n"
            f"◈ <b>Your bonus:</b> +${bonus_amount:.2f}\n\n"
            f"<i>Credited to balance</i> ✓"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent referral bonus notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send referral bonus notification to {telegram_id}: {e}")
    
    async def send_new_referral_notification(
        self,
        telegram_id: int,
        referral_name: str,
        line: int = 1
    ) -> None:
        """Notify referrer about new referral joining."""
        bot = self._get_bot()
        if not bot:
            return
        
        lang = await get_user_language(telegram_id)
        
        line_info_ru = f" • линия {line}" if line > 1 else ""
        line_info_en = f" • tier {line}" if line > 1 else ""
        
        message = _msg(lang,
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     👤 <b>НОВЫЙ РЕФЕРАЛ</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<b>{referral_name}</b>{line_info_ru}\n"
            f"присоединился к вашей сети.\n\n"
            f"<i>Бонусы с его покупок — автоматически</i> ✓",
            
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n"
            f"     👤 <b>NEW REFERRAL</b>\n"
            f"◈━━━━━━━━━━━━━━━━━━━━━◈\n\n"
            f"<b>{referral_name}</b>{line_info_en}\n"
            f"joined your network.\n\n"
            f"<i>Bonuses from their purchases — automatic</i> ✓"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
            logger.info(f"Sent new referral notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send new referral notification to {telegram_id}: {e}")

