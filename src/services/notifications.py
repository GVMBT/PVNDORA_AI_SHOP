"""Notification Service - Order Fulfillment and Telegram Notifications"""
import os
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.services.database import get_database
from src.i18n import get_text


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
            print(f"Order not found: {order_id}")
            return False
        
        if order.status == "completed":
            print(f"Order already completed: {order_id}")
            return True
        
        # Get user
        user_result = db.client.table("users").select("*").eq("id", order.user_id).execute()
        if not user_result.data:
            print(f"User not found for order: {order_id}")
            return False
        
        user = user_result.data[0]
        language = user.get("language_code", "en")
        
        # Get product
        product = await db.get_product_by_id(order.product_id)
        if not product:
            print(f"Product not found for order: {order_id}")
            await self._refund_to_balance(order, user, language, "Product not found")
            return False
        
        # Get available stock item
        stock_item = await db.get_available_stock_item(order.product_id)
        if not stock_item:
            print(f"No stock available for order: {order_id}")
            await self._refund_to_balance(order, user, language, "Out of stock")
            return False
        
        # Reserve stock item (atomic operation)
        reserved = await db.reserve_stock_item(stock_item.id)
        if not reserved:
            # Race condition - item was sold to someone else
            print(f"Stock item already sold, trying next: {order_id}")
            
            # Try one more time with a different item
            stock_item = await db.get_available_stock_item(order.product_id)
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
        
        # Update order with stock item and expiration
        await db.update_order_status(
            order_id=order_id,
            status="completed",
            stock_item_id=stock_item.id,
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
            print("Bot not configured for notifications")
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
        from src.bot.keyboards import get_order_keyboard
        keyboard = get_order_keyboard(language, order_id)
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Failed to send credentials to {telegram_id}: {e}")
    
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
                print(f"Failed to send refund notification: {e}")
        
        print(f"Refunded order {order.id} to balance: {reason}")
    
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
            print(f"Failed to notify supplier {supplier_id}: {e}")
    
    # ==================== SCHEDULED NOTIFICATIONS ====================
    
    async def send_review_request(self, order_id: str) -> None:
        """Send review request 1 hour after purchase"""
        db = get_database()
        bot = self._get_bot()
        
        if not bot:
            return
        
        order = await db.get_order_by_id(order_id)
        if not order or order.status != "completed":
            return
        
        # Get user
        user_result = db.client.table("users").select("telegram_id,language_code").eq("id", order.user_id).execute()
        if not user_result.data:
            return
        
        user = user_result.data[0]
        language = user.get("language_code", "en")
        
        message = get_text("review_request", language)
        
        from src.bot.keyboards import get_order_keyboard
        keyboard = get_order_keyboard(language, order_id)
        
        try:
            await bot.send_message(
                chat_id=user["telegram_id"],
                text=message,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Failed to send review request: {e}")
    
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
            print(f"Failed to send expiration reminder: {e}")
    
    async def send_waitlist_notification(
        self,
        telegram_id: int,
        product_name: str,
        language: str
    ) -> None:
        """Notify user that waitlisted product is available"""
        bot = self._get_bot()
        if not bot:
            return
        
        message = get_text(
            "waitlist_notify",
            language,
            product=product_name
        )
        
        try:
            await bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            print(f"Failed to send waitlist notification: {e}")
    
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
                print(f"Failed to send broadcast to {user['telegram_id']}: {e}")
        
        return sent_count

