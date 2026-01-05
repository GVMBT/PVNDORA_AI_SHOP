"""
Checkout & Payment Tools for Shop Agent.

Order creation, payment processing, balance payments.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta

from langchain_core.tools import tool

from core.logging import get_logger
from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def checkout_cart(payment_method: str = "card") -> dict:
    """
    Create order from cart and get payment link.
    Use when user confirms they want to buy/purchase/order.
    
    CRITICAL: Call this when user says:
    - "купи", "оформи", "заказать", "оплатить"
    - "buy", "checkout", "order", "purchase"
    - "да" (after adding to cart)
    
    Args:
        payment_method: "card" (external payment) or "balance" (pay from internal balance)
        
    Returns:
        Order info with payment URL or confirmation
    """
    try:
        from core.cart import get_cart_manager
        from core.db import get_redis
        from core.services.currency import get_currency_service
        
        ctx = get_user_context()
        db = get_db()
        cart_manager = get_cart_manager()
        
        cart = await cart_manager.get_cart(ctx.telegram_id)
        if not cart or not cart.items:
            return {
                "success": False,
                "error": "Корзина пуста. Сначала добавь товары.",
                "action": "show_catalog"
            }
        
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("id, balance, preferred_currency, language_code")
            .eq("telegram_id", ctx.telegram_id)
            .single()
            .execute()
        )
        
        if not user_result.data:
            return {"success": False, "error": "User not found"}
        
        db_user = user_result.data
        user_id = db_user["id"]
        balance_usd = float(db_user.get("balance", 0) or 0)
        
        cart_total_usd = float(cart.total)
        
        if payment_method == "balance":
            if balance_usd < cart_total_usd:
                redis = get_redis()
                currency_service = get_currency_service(redis)
                
                if ctx.currency != "USD":
                    balance_display = await currency_service.convert_price(balance_usd, ctx.currency)
                    cart_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
                else:
                    balance_display = balance_usd
                    cart_display = cart_total_usd
                
                return {
                    "success": False,
                    "error": "Недостаточно средств на балансе",
                    "balance": balance_display,
                    "cart_total": cart_display,
                    "shortage": cart_display - balance_display,
                    "message": f"Баланс: {currency_service.format_price(balance_display, ctx.currency)}, нужно: {currency_service.format_price(cart_display, ctx.currency)}. Используй оплату картой.",
                    "action": "suggest_card_payment"
                }
        
        payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        payment_gateway = os.environ.get("DEFAULT_PAYMENT_GATEWAY", "crystalpay")
        
        order_result = await asyncio.to_thread(
            lambda: db.client.table("orders").insert({
                "user_id": user_id,
                "amount": cart_total_usd,
                "original_price": float(cart.subtotal),
                "discount_percent": 0,
                "status": "pending",
                "payment_method": payment_method,
                "payment_gateway": payment_gateway if payment_method != "balance" else None,
                "user_telegram_id": ctx.telegram_id,
                "expires_at": payment_expires_at.isoformat(),
                "source_channel": "premium"
            }).execute()
        )
        
        if not order_result.data:
            return {"success": False, "error": "Failed to create order"}
        
        order = order_result.data[0]
        order_id = order["id"]
        
        order_items = []
        for item in cart.items:
            stock_result = await asyncio.to_thread(
                lambda pid=item.product_id: db.client.table("stock_items")
                .select("id")
                .eq("product_id", pid)
                .eq("status", "available")
                .limit(1)
                .execute()
            )
            
            stock_item_id = stock_result.data[0]["id"] if stock_result.data else None
            
            order_items.append({
                "order_id": order_id,
                "product_id": item.product_id,
                "stock_item_id": stock_item_id,
                "quantity": item.quantity,
                "price": float(item.unit_price),
                "discount_percent": int(item.discount_percent),
                "fulfillment_type": "instant" if item.instant_quantity > 0 else "preorder",
                "status": "pending"
            })
        
        await asyncio.to_thread(
            lambda: db.client.table("order_items").insert(order_items).execute()
        )
        
        if payment_method == "balance":
            new_balance = balance_usd - cart_total_usd
            await asyncio.to_thread(
                lambda: db.client.table("users")
                .update({"balance": new_balance})
                .eq("id", user_id)
                .execute()
            )
            
            await asyncio.to_thread(
                lambda: db.client.table("balance_transactions").insert({
                    "user_id": user_id,
                    "type": "purchase",
                    "amount": -cart_total_usd,
                    "currency": "USD",
                    "balance_before": balance_usd,
                    "balance_after": new_balance,
                    "reference_type": "order",
                    "reference_id": order_id,
                    "status": "completed",
                    "description": f"Оплата заказа {order_id[:8]}"
                }).execute()
            )
            
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"status": "paid"})
                .eq("id", order_id)
                .execute()
            )
            
            await cart_manager.clear_cart(ctx.telegram_id)
            
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            if ctx.currency != "USD":
                amount_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
                new_balance_display = await currency_service.convert_price(new_balance, ctx.currency)
            else:
                amount_display = cart_total_usd
                new_balance_display = new_balance
            
            items_text = ", ".join([f"{item.product_name}" for item in cart.items])
            
            return {
                "success": True,
                "order_id": order_id[:8],
                "status": "paid",
                "payment_method": "balance",
                "amount": amount_display,
                "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
                "new_balance": new_balance_display,
                "new_balance_formatted": currency_service.format_price(new_balance_display, ctx.currency),
                "items": items_text,
                "message": f"Заказ #{order_id[:8]} оплачен! Товар будет доставлен в течение нескольких минут.",
                "action": "order_paid"
            }
        
        from core.routers.deps import get_payment_service
        payment_service = get_payment_service()
        
        try:
            payment_result = await payment_service.create_invoice(
                amount=cart_total_usd,
                order_id=order_id,
                description=f"PVNDORA Order #{order_id[:8]}",
                user_telegram_id=ctx.telegram_id
            )
            
            payment_url = payment_result.get("url") or payment_result.get("payment_url")
            payment_id = payment_result.get("id") or payment_result.get("payment_id")
            
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({
                    "payment_id": str(payment_id) if payment_id else None,
                    "payment_url": payment_url
                })
                .eq("id", order_id)
                .execute()
            )
            
            await cart_manager.clear_cart(ctx.telegram_id)
            
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            if ctx.currency != "USD":
                amount_display = await currency_service.convert_price(cart_total_usd, ctx.currency)
            else:
                amount_display = cart_total_usd
            
            items_text = ", ".join([f"{item.product_name}" for item in cart.items])
            
            return {
                "success": True,
                "order_id": order_id[:8],
                "status": "pending",
                "payment_method": "card",
                "amount": amount_display,
                "amount_formatted": currency_service.format_price(amount_display, ctx.currency),
                "payment_url": payment_url,
                "items": items_text,
                "expires_in_minutes": 15,
                "message": f"Заказ #{order_id[:8]} создан! Оплати по ссылке в течение 15 минут.",
                "action": "show_payment_link"
            }
            
        except Exception as e:
            logger.error(f"Payment service error: {e}")
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"status": "cancelled"})
                .eq("id", order_id)
                .execute()
            )
            return {
                "success": False,
                "error": f"Ошибка платежного шлюза: {str(e)}",
                "action": "retry_payment"
            }
            
    except Exception as e:
        logger.error(f"checkout_cart error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def pay_cart_from_balance() -> dict:
    """
    Pay for cart items using internal balance.
    Use when user says "оплати с баланса", "спиши с баланса", "pay from balance".
    Uses telegram_id and user_id from context.
        
    Returns:
        Instructions or confirmation
    """
    try:
        from core.cart import get_cart_manager
        
        ctx = get_user_context()
        db = get_db()
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(ctx.telegram_id)
        
        if not cart or not cart.items:
            return {"success": False, "error": "Корзина пуста. Сначала добавь товары."}
        
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users").select("balance, language_code, preferred_currency").eq("id", ctx.user_id).single().execute()
        )
        balance_usd = float(user_result.data.get("balance", 0) or 0) if user_result.data else 0
        
        user_currency = ctx.currency
        
        try:
            from core.db import get_redis
            from core.services.currency import get_currency_service
            redis = get_redis()
            currency_service = get_currency_service(redis)
            
            if user_currency != "USD":
                try:
                    balance = await currency_service.convert_price(balance_usd, user_currency)
                    cart_total = await currency_service.convert_price(cart.total, user_currency)
                except Exception:
                    balance = balance_usd
                    cart_total = cart.total
            else:
                balance = balance_usd
                cart_total = cart.total
        except Exception:
            balance = balance_usd
            cart_total = cart.total
            user_currency = "USD"
            currency_service = None
        
        if balance < cart_total:
            if currency_service:
                try:
                    balance_formatted = currency_service.format_price(balance, user_currency)
                    cart_total_formatted = currency_service.format_price(cart_total, user_currency)
                    message = f"Баланс: {balance_formatted}, нужно: {cart_total_formatted}. Пополни баланс или оплати картой."
                except Exception:
                    message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            else:
                message = f"Баланс: {balance:.0f}, нужно: {cart_total:.0f}. Пополни баланс или оплати картой."
            
            return {
                "success": False,
                "error": "Недостаточно средств на балансе",
                "balance": balance,
                "cart_total": cart_total,
                "shortage": cart_total - balance,
                "message": message
            }
        
        items_text = ", ".join([f"{item.product_name} x{item.quantity}" for item in cart.items])
        
        return {
            "success": True,
            "can_pay": True,
            "balance": balance,
            "cart_total": cart.total,
            "remaining_after": balance - cart.total,
            "items": items_text,
            "message": "Можно оплатить с баланса! Нажми Магазин → Корзина → выбери 'С баланса' и подтверди.",
            "instructions": "В корзине выбери способ оплаты 'С баланса' и нажми 'Оплатить'"
        }
        
    except Exception as e:
        logger.error(f"pay_cart_from_balance error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
