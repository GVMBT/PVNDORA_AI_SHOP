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
        
        message = _msg(lang,
            f"✅ <b>Замена аккаунта выполнена</b>\n\n"
            f"Товар: {product_name}\n"
            f"ID товара: {item_id}\n\n"
            f"Ваш аккаунт заменён. Новые данные доступа доступны в разделе <b>«Мои заказы»</b>:\n"
            f"1. Откройте раздел «Мои заказы»\n"
            f"2. Найдите соответствующий заказ\n"
            f"3. Раскройте ключ доступа для просмотра новых данных",
            f"✅ <b>Account Replacement Completed</b>\n\n"
            f"Product: {product_name}\n"
            f"Item ID: {item_id}\n\n"
            f"Your account has been replaced. New access credentials are available in <b>«My Orders»</b>:\n"
            f"1. Open «My Orders» section\n"
            f"2. Find the corresponding order\n"
            f"3. Reveal the access key to view new credentials"
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
        
        lang = await get_user_language(telegram_id)
        
        if issue_type == "replacement":
            message = _msg(lang,
                f"✅ <b>Тикет #{ticket_id} одобрен</b>\n\n"
                f"Ваш запрос на замену одобрен.\n"
                f"Новый аккаунт будет доставлен в ближайшее время.",
                f"✅ <b>Ticket #{ticket_id} Approved</b>\n\n"
                f"Your replacement request has been approved.\n"
                f"A new account will be delivered to you shortly."
            )
        elif issue_type == "refund":
            message = _msg(lang,
                f"✅ <b>Тикет #{ticket_id} одобрен</b>\n\n"
                f"Ваш запрос на возврат одобрен.\n"
                f"Сумма будет зачислена на ваш баланс.",
                f"✅ <b>Ticket #{ticket_id} Approved</b>\n\n"
                f"Your refund request has been approved.\n"
                f"The amount will be credited to your balance."
            )
        else:
            message = _msg(lang,
                f"✅ <b>Тикет #{ticket_id} одобрен</b>\n\n"
                f"Ваш запрос одобрен и обрабатывается.",
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
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            "🎉 <b>Реферальная программа активирована!</b>\n\n"
            "Теперь вы можете приглашать друзей и получать бонусы с их покупок:\n\n"
            "💰 <b>10%</b> с покупок ваших рефералов\n\n"
            "📈 <b>Повышайте уровень</b> для открытия дополнительных линий:\n"
            "• Уровень 2 ($250+): +7% со 2-й линии\n"
            "• Уровень 3 ($1000+): +3% с 3-й линии\n\n"
            "🔗 Ваша реферальная ссылка доступна в профиле!",
            "🎉 <b>Referral Program Activated!</b>\n\n"
            "You can now invite friends and earn bonuses from their purchases:\n\n"
            "💰 <b>10%</b> from your referrals' purchases\n\n"
            "📈 <b>Level up</b> to unlock additional tiers:\n"
            "• Level 2 ($250+): +7% from tier 2\n"
            "• Level 3 ($1000+): +3% from tier 3\n\n"
            "🔗 Your referral link is available in your profile!"
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
        
        if new_level == 2:
            message = _msg(lang,
                "🚀 <b>Уровень реферальной программы повышен!</b>\n\n"
                "Вы достигли <b>Уровня 2</b>!\n\n"
                "Теперь вы получаете:\n"
                "• 10% с покупок рефералов 1-й линии\n"
                "• <b>+7% с покупок рефералов 2-й линии</b>\n\n"
                "До Уровня 3 осталось набрать $1000 оборота.",
                "🚀 <b>Referral Level Up!</b>\n\n"
                "You've reached <b>Level 2</b>!\n\n"
                "You now earn:\n"
                "• 10% from tier 1 referrals\n"
                "• <b>+7% from tier 2 referrals</b>\n\n"
                "$1000 turnover remaining to Level 3."
            )
        elif new_level == 3:
            message = _msg(lang,
                "🏆 <b>Максимальный уровень достигнут!</b>\n\n"
                "Поздравляем с <b>Уровнем 3</b>!\n\n"
                "Теперь вы получаете максимальные бонусы:\n"
                "• 10% с покупок рефералов 1-й линии\n"
                "• 7% с покупок рефералов 2-й линии\n"
                "• <b>+3% с покупок рефералов 3-й линии</b>\n\n"
                "🎉 Вы — VIP партнёр PVNDORA!",
                "🏆 <b>Maximum Level Reached!</b>\n\n"
                "Congratulations on reaching <b>Level 3</b>!\n\n"
                "You now earn maximum bonuses:\n"
                "• 10% from tier 1 referrals\n"
                "• 7% from tier 2 referrals\n"
                "• <b>+3% from tier 3 referrals</b>\n\n"
                "🎉 You're a PVNDORA VIP Partner!"
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
        
        lang = await get_user_language(telegram_id)
        
        message = _msg(lang,
            f"📦 <b>Ваш заказ доставлен!</b>\n\n"
            f"Товар: {product_name}\n\n"
            f"<code>{content}</code>\n\n"
            f"Спасибо за покупку! Оставьте отзыв и получите 5% кэшбэк.",
            f"📦 <b>Your order has been delivered!</b>\n\n"
            f"Product: {product_name}\n\n"
            f"<code>{content}</code>\n\n"
            f"Thank you for your purchase! Leave a review and get 5% cashback."
        )
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
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
                f"💰 <b>Кэшбек начислен!</b>\n\n"
                f"За ваш отзыв вам начислено <b>${cashback_amount:.2f}</b>.\n"
                f"Новый баланс: <b>${new_balance:.2f}</b>\n\n"
                f"Спасибо за обратную связь! 🙏",
                f"💰 <b>Cashback credited!</b>\n\n"
                f"You received <b>${cashback_amount:.2f}</b> for your review.\n"
                f"New balance: <b>${new_balance:.2f}</b>\n\n"
                f"Thank you for your feedback! 🙏"
            )
        else:
            message = _msg(lang,
                f"💰 <b>Кэшбек начислен!</b>\n\n"
                f"Вам начислено <b>${cashback_amount:.2f}</b>.\n"
                f"Новый баланс: <b>${new_balance:.2f}</b>",
                f"💰 <b>Cashback credited!</b>\n\n"
                f"You received <b>${cashback_amount:.2f}</b>.\n"
                f"New balance: <b>${new_balance:.2f}</b>"
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
            f"✅ <b>Заявка на вывод одобрена</b>\n\n"
            f"Сумма: <b>${amount:.2f}</b>\n"
            f"Метод: {method}\n\n"
            f"Средства будут отправлены в ближайшее время.",
            f"✅ <b>Withdrawal Request Approved</b>\n\n"
            f"Amount: <b>${amount:.2f}</b>\n"
            f"Method: {method}\n\n"
            f"Funds will be sent shortly."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
            f"❌ <b>Заявка на вывод отклонена</b>\n\n"
            f"Сумма: <b>${amount:.2f}</b>\n\n"
            f"<i>Причина: {reason}</i>\n\n"
            f"Средства возвращены на ваш баланс.",
            f"❌ <b>Withdrawal Request Rejected</b>\n\n"
            f"Amount: <b>${amount:.2f}</b>\n\n"
            f"<i>Reason: {reason}</i>\n\n"
            f"Funds have been returned to your balance."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
            f"💸 <b>Вывод выполнен!</b>\n\n"
            f"Сумма: <b>${amount:.2f}</b>\n"
            f"Метод: {method}\n\n"
            f"Средства отправлены. Спасибо за использование PVNDORA!",
            f"💸 <b>Withdrawal Completed!</b>\n\n"
            f"Amount: <b>${amount:.2f}</b>\n"
            f"Method: {method}\n\n"
            f"Funds have been sent. Thank you for using PVNDORA!"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
            f"💰 <b>Баланс пополнен!</b>\n\n"
            f"Сумма: <b>{amount:.2f} {currency}</b>\n"
            f"Новый баланс: <b>${new_balance:.2f}</b>\n\n"
            f"Спасибо! Теперь вы можете совершать покупки.",
            f"💰 <b>Balance Topped Up!</b>\n\n"
            f"Amount: <b>{amount:.2f} {currency}</b>\n"
            f"New balance: <b>${new_balance:.2f}</b>\n\n"
            f"Thank you! You can now make purchases."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
            "🎉 <b>Поздравляем! Вы стали VIP-партнёром PVNDORA!</b>\n\n"
            "Ваша заявка одобрена.\n\n"
            "Теперь вам доступны:\n"
            "• Повышенные комиссии с рефералов\n"
            "• Персональный менеджер\n"
            "• Приоритетная поддержка\n\n"
            "Добро пожаловать в команду! 🚀",
            "🎉 <b>Congratulations! You are now a PVNDORA VIP Partner!</b>\n\n"
            "Your application has been approved.\n\n"
            "You now have access to:\n"
            "• Increased referral commissions\n"
            "• Personal manager\n"
            "• Priority support\n\n"
            "Welcome to the team! 🚀"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
        
        reason_text_ru = reason or "Ваша заявка не соответствует требованиям партнёрской программы."
        reason_text_en = reason or "Your application does not meet the partner program requirements."
        
        message = _msg(lang,
            f"❌ <b>Заявка на VIP-партнёрство отклонена</b>\n\n"
            f"<i>{reason_text_ru}</i>\n\n"
            f"Вы можете подать новую заявку позже или связаться с поддержкой для уточнения деталей.",
            f"❌ <b>VIP Partnership Application Rejected</b>\n\n"
            f"<i>{reason_text_en}</i>\n\n"
            f"You can submit a new application later or contact support for details."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
        
        line_text_ru = f"({line}-й линии) " if line > 1 else ""
        line_text_en = f"(tier {line}) " if line > 1 else ""
        
        message = _msg(lang,
            f"💸 <b>Реферальный бонус!</b>\n\n"
            f"Ваш реферал {line_text_ru}{referral_name} совершил покупку на ${purchase_amount:.2f}\n\n"
            f"Ваш бонус: <b>+${bonus_amount:.2f}</b>\n\n"
            f"Бонус зачислен на ваш баланс.",
            f"💸 <b>Referral Bonus!</b>\n\n"
            f"Your referral {line_text_en}{referral_name} made a purchase of ${purchase_amount:.2f}\n\n"
            f"Your bonus: <b>+${bonus_amount:.2f}</b>\n\n"
            f"Bonus credited to your balance."
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
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
        
        line_text_ru = f" ({line}-й линии)" if line > 1 else ""
        line_text_en = f" (tier {line})" if line > 1 else ""
        
        message = _msg(lang,
            f"👤 <b>Новый реферал!</b>\n\n"
            f"{referral_name} присоединился{line_text_ru} по вашей ссылке.\n\n"
            f"Вы будете получать бонусы с его покупок!",
            f"👤 <b>New Referral!</b>\n\n"
            f"{referral_name} joined{line_text_en} via your link.\n\n"
            f"You'll earn bonuses from their purchases!"
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Sent new referral notification to {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send new referral notification to {telegram_id}: {e}")

