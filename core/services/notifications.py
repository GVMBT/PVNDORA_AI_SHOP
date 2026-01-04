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
        
        # Get user language
        db = get_database()
        user_res = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("language_code")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute()
        )
        language = "en"
        if user_res.data:
            language = user_res.data[0].get("language_code", "en") or "en"
        
        # Build replacement message
        message = (
            f"✅ <b>Account Replacement Completed</b>\n\n"
            f"Product: {product_name}\n"
            f"Item ID: {item_id}\n\n"
            f"Your account has been replaced. Please check your orders for new credentials."
        )
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message
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
        
        if issue_type == "replacement":
            message = (
                f"✅ <b>Ticket #{ticket_id} Approved</b>\n\n"
                f"Your replacement request has been approved.\n"
                f"A new account will be delivered to you shortly."
            )
        elif issue_type == "refund":
            message = (
                f"✅ <b>Ticket #{ticket_id} Approved</b>\n\n"
                f"Your refund request has been approved.\n"
                f"The amount will be credited to your balance."
            )
        else:
            message = (
                f"✅ <b>Ticket #{ticket_id} Approved</b>\n\n"
                f"Your request has been approved and is being processed."
            )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
        
        # Get localized messages
        title = get_text("ticket_rejected_title", language, default=f"❌ Ticket #{ticket_id} Rejected").format(ticket_id=ticket_id)
        message_text = get_text("ticket_rejected_message", language, default="Unfortunately, your request could not be approved.")
        reason_text = get_text("ticket_rejected_reason", language, default="Reason: {reason}").format(reason=reason)
        contact_text = get_text("ticket_rejected_contact", language, default="If you have questions, please contact support.")
        button_text = get_text("btn_contact_support", language, default="🆘 Contact Support")
        
        message = (
            f"{title}\n\n"
            f"{message_text}\n\n"
            f"<i>{reason_text}</i>\n\n"
            f"{contact_text}"
        )
        
        # Create keyboard with support button
        webapp_url = os.environ.get("WEBAPP_URL", "https://pvndora.app")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=button_text,
                web_app=WebAppInfo(url=f"{webapp_url}?startapp=contacts")
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
        
        message = (
            "🎉 <b>Реферальная программа активирована!</b>\n\n"
            "Теперь вы можете приглашать друзей и получать бонусы с их покупок:\n\n"
            "💰 <b>5%</b> с покупок ваших рефералов\n\n"
            "📈 <b>Повышайте уровень</b> для открытия дополнительных линий:\n"
            "• Уровень 2 (от 5,000₽): +2% со 2-й линии\n"
            "• Уровень 3 (от 15,000₽): +1% с 3-й линии\n\n"
            "🔗 Ваша реферальная ссылка доступна в профиле!"
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
        
        if new_level == 2:
            message = (
                "🚀 <b>Уровень реферальной программы повышен!</b>\n\n"
                "Вы достигли <b>Уровня 2</b>!\n\n"
                "Теперь вы получаете:\n"
                "• 5% с покупок рефералов 1-й линии\n"
                "• <b>+2% с покупок рефералов 2-й линии</b>\n\n"
                "До Уровня 3 осталось набрать 15,000₽ покупок."
            )
        elif new_level == 3:
            message = (
                "🏆 <b>Максимальный уровень достигнут!</b>\n\n"
                "Поздравляем с <b>Уровнем 3</b>!\n\n"
                "Теперь вы получаете максимальные бонусы:\n"
                "• 5% с покупок рефералов 1-й линии\n"
                "• 2% с покупок рефералов 2-й линии\n"
                "• <b>+1% с покупок рефералов 3-й линии</b>\n\n"
                "🎉 Вы — VIP партнёр PVNDORA!"
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
    
    async def send_delivery(self, telegram_id: int, product_name: str, content: str) -> None:
        """Send delivery notification with product credentials."""
        bot = self._get_bot()
        if not bot:
            return
        
        message = (
            f"📦 <b>Ваш заказ доставлен!</b>\n\n"
            f"Товар: {product_name}\n\n"
            f"<code>{content}</code>\n\n"
            f"Спасибо за покупку! Оставьте отзыв и получите 5% кэшбэк."
        )
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send delivery notification: {e}")
    
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

