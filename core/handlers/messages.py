"""
Message Handlers - Text Message Processing

Handles:
- /start with referral parsing
- /my_orders, /wishlist, /cart commands
- General messages routed to AI
"""

import re
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from core.models import AIResponse, ActionType
from core.ai import AIConsultant, register_ai_functions
from core.cart import CartManager


router = Router(name="messages")


# ============================================================
# Command Handlers
# ============================================================

@router.message(CommandStart(deep_link=True))
async def cmd_start_with_ref(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    supabase,
    ai_consultant: AIConsultant,
    **kwargs
):
    """Handle /start with referral or deep link."""
    # Extract deep link parameter
    args = message.text.split(maxsplit=1)
    param = args[1] if len(args) > 1 else ""
    
    # Check for referral
    ref_match = re.match(r"ref_(\d+)", param)
    referrer_id = int(ref_match.group(1)) if ref_match else None
    
    # Create or update user
    user_data = {
        "telegram_id": user_telegram_id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "language_code": language_code
    }
    
    if referrer_id and referrer_id != user_telegram_id:
        # Check if referrer exists
        ref_check = await supabase.table("users").select("id").eq(
            "telegram_id", referrer_id
        ).single().execute()
        
        if ref_check.data:
            user_data["referrer_telegram_id"] = referrer_id
    
    # Upsert user
    await supabase.table("users").upsert(
        user_data,
        on_conflict="telegram_id"
    ).execute()
    
    # Generate welcome message via AI
    welcome_prompt = "User just started the bot. Send a friendly welcome message with examples of what they can ask."
    
    response = await ai_consultant.consult(
        user_message=welcome_prompt,
        user_telegram_id=user_telegram_id,
        language_code=language_code
    )
    
    # Send welcome with catalog button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Browse Catalog",
            web_app={"url": f"https://t.me/{(await message.bot.me()).username}/app"}
        )],
        [InlineKeyboardButton(
            text="💬 Ask me anything",
            callback_data="ask_prompt"
        )]
    ])
    
    await message.answer(
        response.reply_text,
        reply_markup=keyboard
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    supabase,
    ai_consultant: AIConsultant,
    **kwargs
):
    """Handle plain /start command."""
    # Create or update user
    await supabase.table("users").upsert({
        "telegram_id": user_telegram_id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "language_code": language_code
    }, on_conflict="telegram_id").execute()
    
    # Welcome message
    response = await ai_consultant.consult(
        user_message="User started the bot. Welcome them and explain what you can help with.",
        user_telegram_id=user_telegram_id,
        language_code=language_code
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Browse Catalog",
            web_app={"url": f"https://t.me/{(await message.bot.me()).username}/app"}
        )]
    ])
    
    await message.answer(response.reply_text, reply_markup=keyboard)


@router.message(Command("my_orders"))
async def cmd_my_orders(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    supabase,
    **kwargs
):
    """Show user's order history."""
    # Fetch orders
    result = await supabase.table("orders").select(
        "id, amount, status, created_at, expires_at, products(name)"
    ).eq("user_telegram_id", user_telegram_id).order(
        "created_at", desc=True
    ).limit(10).execute()
    
    orders = result.data or []
    
    if not orders:
        await message.answer(
            "📦 You don't have any orders yet.\n\n"
            "Ask me about any AI subscription and I'll help you find the best option!"
        )
        return
    
    # Format orders
    lines = ["📦 <b>Your Recent Orders:</b>\n"]
    
    for order in orders:
        status_emoji = {
            "delivered": "✅",
            "pending": "⏳",
            "prepaid": "💳",
            "fulfilling": "🔄",
            "ready": "📬",
            "refunded": "↩️",
            "cancelled": "❌",
            "failed": "⚠️"
        }.get(order["status"], "❓")
        
        product_name = order.get("products", {}).get("name", "Unknown")
        lines.append(
            f"{status_emoji} <b>{product_name}</b>\n"
            f"   Amount: {order['amount']}₽ | Status: {order['status']}"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📜 Full History",
            web_app={"url": f"https://t.me/{(await message.bot.me()).username}/app?startapp=orders"}
        )]
    ])
    
    await message.answer("\n".join(lines), reply_markup=keyboard)


@router.message(Command("wishlist"))
async def cmd_wishlist(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    supabase,
    **kwargs
):
    """Show user's wishlist."""
    # Get user ID first
    user_result = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if not user_result.data:
        await message.answer("❤️ Your wishlist is empty.")
        return
    
    user_id = user_result.data["id"]
    
    # Fetch wishlist
    result = await supabase.table("wishlist").select(
        "id, product_name, created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()
    
    items = result.data or []
    
    if not items:
        await message.answer(
            "❤️ Your wishlist is empty.\n\n"
            "Say \"Add to wishlist\" when viewing a product to save it!"
        )
        return
    
    lines = ["❤️ <b>Your Wishlist:</b>\n"]
    for item in items:
        lines.append(f"• {item['product_name']}")
    
    await message.answer("\n".join(lines))


@router.message(Command("cart"))
async def cmd_cart(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    cart_manager: CartManager,
    **kwargs
):
    """Show cart contents."""
    cart = await cart_manager.get_cart(user_telegram_id)
    
    if not cart or not cart.items:
        await message.answer(
            "🛒 Your cart is empty.\n\n"
            "Just tell me what you need and I'll help you find it!"
        )
        return
    
    lines = ["🛒 <b>Your Cart:</b>\n"]
    
    for item in cart.items:
        instant_note = f" ({item.instant_quantity} now" if item.instant_quantity else ""
        prepaid_note = f", {item.prepaid_quantity} ordered)" if item.prepaid_quantity else ")"
        if instant_note:
            instant_note += prepaid_note if item.prepaid_quantity else ")"
        
        lines.append(
            f"• <b>{item.product_name}</b> x{item.quantity}{instant_note}\n"
            f"  {item.final_price:.0f}₽ each = {item.total_price:.0f}₽"
        )
    
    lines.append(f"\n<b>Total: {cart.total:.0f}₽</b>")
    
    if cart.promo_code:
        lines.append(f"🏷 Promo: {cart.promo_code} (-{cart.promo_discount_percent}%)")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Checkout",
            web_app={"url": f"https://t.me/{(await message.bot.me()).username}/app?startapp=checkout"}
        )],
        [InlineKeyboardButton(text="🗑 Clear Cart", callback_data="cart_clear")]
    ])
    
    await message.answer("\n".join(lines), reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(
    message: Message,
    language_code: str,
    ai_consultant: AIConsultant,
    user_telegram_id: int,
    **kwargs
):
    """Show help message."""
    response = await ai_consultant.consult(
        user_message="User needs help. Explain what you can do and give examples.",
        user_telegram_id=user_telegram_id,
        language_code=language_code
    )
    await message.answer(response.reply_text)


# ============================================================
# General Message Handler (AI Consultation)
# ============================================================

@router.message(F.text)
async def handle_message(
    message: Message,
    language_code: str,
    user_telegram_id: int,
    supabase,
    ai_consultant: AIConsultant,
    cart_manager: CartManager,
    **kwargs
):
    """
    Handle all text messages via AI consultation.
    
    This is the main AI sales flow.
    """
    user_message = message.text
    
    # Get chat history for context
    history_result = await supabase.table("chat_history").select(
        "role, message"
    ).eq("user_telegram_id", user_telegram_id).order(
        "timestamp", desc=True
    ).limit(10).execute()
    
    chat_history = list(reversed(history_result.data or []))
    
    # Save user message to history
    user_result = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if user_result.data:
        await supabase.table("chat_history").insert({
            "user_id": user_result.data["id"],
            "role": "user",
            "message": user_message
        }).execute()
    
    # Register function handlers for this request
    async def check_availability(product_id: str):
        result = await supabase.table("available_stock_with_discounts").select(
            "*"
        ).eq("product_id", product_id).limit(1).execute()
        
        if result.data:
            item = result.data[0]
            return {
                "product_id": product_id,
                "available": True,
                "stock_count": 1,
                "price": item.get("original_price", 0),
                "discount_percent": item.get("discount_percent", 0),
                "final_price": item.get("final_price", 0)
            }
        
        # Check if product exists but out of stock
        product = await supabase.table("products").select(
            "id, name, price, fulfillment_time_hours"
        ).eq("id", product_id).single().execute()
        
        if product.data:
            return {
                "product_id": product_id,
                "available": False,
                "stock_count": 0,
                "can_fulfill_on_demand": True,
                "fulfillment_time_hours": product.data.get("fulfillment_time_hours", 48),
                "price": product.data.get("price", 0)
            }
        
        return {"error": "Product not found"}
    
    async def get_user_cart():
        return await cart_manager.get_cart_summary(user_telegram_id)
    
    async def add_to_cart(product_id: str, quantity: int = 1):
        # Get product info
        product = await supabase.table("products").select("*").eq(
            "id", product_id
        ).single().execute()
        
        if not product.data:
            return {"error": "Product not found"}
        
        # Get available stock
        stock = await supabase.table("available_stock_with_discounts").select(
            "count"
        ).eq("product_id", product_id).execute()
        
        available = len(stock.data) if stock.data else 0
        
        cart = await cart_manager.add_item(
            user_telegram_id=user_telegram_id,
            product_id=product_id,
            product_name=product.data["name"],
            quantity=quantity,
            available_stock=available,
            unit_price=product.data["price"],
            discount_percent=stock.data[0].get("discount_percent", 0) if stock.data else 0
        )
        
        return await cart_manager.get_cart_summary(user_telegram_id)
    
    async def update_cart(operation: str, product_id: str = None, quantity: int = None):
        if operation == "clear":
            await cart_manager.clear_cart(user_telegram_id)
            return {"success": True, "message": "Cart cleared"}
        elif operation == "remove_item" and product_id:
            await cart_manager.remove_item(user_telegram_id, product_id)
            return await cart_manager.get_cart_summary(user_telegram_id)
        elif operation == "update_quantity" and product_id and quantity is not None:
            # Get available stock
            stock = await supabase.table("available_stock_with_discounts").select(
                "count"
            ).eq("product_id", product_id).execute()
            available = len(stock.data) if stock.data else 0
            
            await cart_manager.update_item_quantity(
                user_telegram_id, product_id, quantity, available
            )
            return await cart_manager.get_cart_summary(user_telegram_id)
        
        return {"error": "Invalid operation"}
    
    # Register handlers
    ai_consultant.register_function("check_product_availability", check_availability)
    ai_consultant.register_function("get_user_cart", get_user_cart)
    ai_consultant.register_function("add_to_cart", add_to_cart)
    ai_consultant.register_function("update_cart", update_cart)
    
    # Get AI response
    response = await ai_consultant.consult(
        user_message=user_message,
        user_telegram_id=user_telegram_id,
        language_code=language_code,
        chat_history=chat_history
    )
    
    # Save assistant response to history
    if user_result.data:
        await supabase.table("chat_history").insert({
            "user_id": user_result.data["id"],
            "role": "assistant",
            "message": response.reply_text
        }).execute()
    
    # Log analytics event
    await supabase.table("analytics_events").insert({
        "user_id": user_result.data["id"] if user_result.data else None,
        "event_type": "view" if response.action == ActionType.NONE else "checkout",
        "metadata": {
            "action": response.action.value if response.action else None,
            "product_id": response.product_id
        }
    }).execute()
    
    # Build response with appropriate buttons
    keyboard = None
    
    if response.action == ActionType.OFFER_PAYMENT and response.product_id:
        # Payment button
        bot_username = (await message.bot.me()).username
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Pay Now",
                web_app={"url": f"https://t.me/{bot_username}/app?startapp=pay_{response.product_id}"}
            )],
            [InlineKeyboardButton(
                text="🛒 Add to Cart",
                callback_data=f"add_cart:{response.product_id}"
            )]
        ])
    
    elif response.action == ActionType.SHOW_CATALOG:
        bot_username = (await message.bot.me()).username
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🛍 Open Catalog",
                web_app={"url": f"https://t.me/{bot_username}/app?startapp=catalog"}
            )]
        ])
    
    elif response.action == ActionType.ADD_TO_WAITLIST and response.product_id:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Join Waitlist",
                callback_data=f"waitlist:{response.product_id}"
            )]
        ])
    
    elif response.action == ActionType.CREATE_TICKET:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎫 Create Support Ticket",
                callback_data="create_ticket"
            )]
        ])
    
    await message.answer(response.reply_text, reply_markup=keyboard)

