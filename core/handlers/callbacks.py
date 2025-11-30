"""
Callback Handlers - Inline Button Callbacks

Handles:
- Payment buttons
- Cart management
- Waitlist join
- Ticket creation
- Review submission
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.cart import CartManager
from core.queue import publish_to_worker, WorkerEndpoints


router = Router(name="callbacks")


# ============================================================
# FSM States
# ============================================================

class TicketStates(StatesGroup):
    """States for ticket creation flow."""
    waiting_for_order_id = State()
    waiting_for_description = State()


class ReviewStates(StatesGroup):
    """States for review submission."""
    waiting_for_rating = State()
    waiting_for_text = State()


# ============================================================
# Cart Callbacks
# ============================================================

@router.callback_query(F.data.startswith("add_cart:"))
async def add_to_cart_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    supabase,
    cart_manager: CartManager,
    **kwargs
):
    """Add product to cart from inline button."""
    product_id = callback.data.split(":")[1]
    
    # Get product info
    product = await supabase.table("products").select("*").eq(
        "id", product_id
    ).single().execute()
    
    if not product.data:
        await callback.answer("❌ Product not found", show_alert=True)
        return
    
    # Get available stock
    stock = await supabase.table("available_stock_with_discounts").select(
        "*"
    ).eq("product_id", product_id).execute()
    
    available = len(stock.data) if stock.data else 0
    discount = stock.data[0].get("discount_percent", 0) if stock.data else 0
    
    # Add to cart
    cart = await cart_manager.add_item(
        user_telegram_id=user_telegram_id,
        product_id=product_id,
        product_name=product.data["name"],
        quantity=1,
        available_stock=available,
        unit_price=product.data["price"],
        discount_percent=discount
    )
    
    await callback.answer(
        f"✅ Added {product.data['name']} to cart!\n"
        f"Cart total: {cart.total:.0f}₽",
        show_alert=True
    )


@router.callback_query(F.data == "cart_clear")
async def clear_cart_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    cart_manager: CartManager,
    **kwargs
):
    """Clear user's cart."""
    await cart_manager.clear_cart(user_telegram_id)
    await callback.answer("🗑 Cart cleared!")
    
    # Edit the original message
    await callback.message.edit_text(
        "🛒 Your cart is empty.\n\n"
        "Just tell me what you need and I'll help you find it!"
    )


@router.callback_query(F.data.startswith("cart_remove:"))
async def remove_from_cart_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    cart_manager: CartManager,
    **kwargs
):
    """Remove item from cart."""
    product_id = callback.data.split(":")[1]
    
    await cart_manager.remove_item(user_telegram_id, product_id)
    await callback.answer("✅ Item removed from cart")


# ============================================================
# Waitlist Callbacks
# ============================================================

@router.callback_query(F.data.startswith("waitlist:"))
async def join_waitlist_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    supabase,
    **kwargs
):
    """Add user to product waitlist."""
    product_id = callback.data.split(":")[1]
    
    # Get user and product
    user = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    product = await supabase.table("products").select("name").eq(
        "id", product_id
    ).single().execute()
    
    if not user.data or not product.data:
        await callback.answer("❌ Error joining waitlist", show_alert=True)
        return
    
    # Check if already on waitlist
    existing = await supabase.table("waitlist").select("id").eq(
        "user_id", user.data["id"]
    ).eq("product_id", product_id).execute()
    
    if existing.data:
        await callback.answer(
            f"You're already on the waitlist for {product.data['name']}!",
            show_alert=True
        )
        return
    
    # Add to waitlist
    await supabase.table("waitlist").insert({
        "user_id": user.data["id"],
        "product_id": product_id,
        "product_name": product.data["name"]
    }).execute()
    
    await callback.answer(
        f"✅ You're on the waitlist for {product.data['name']}!\n"
        "We'll notify you when it's available.",
        show_alert=True
    )


# ============================================================
# Support Ticket Callbacks
# ============================================================

@router.callback_query(F.data == "create_ticket")
async def create_ticket_start(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
):
    """Start ticket creation flow."""
    await state.set_state(TicketStates.waiting_for_order_id)
    
    await callback.message.answer(
        "🎫 <b>Create Support Ticket</b>\n\n"
        "Please provide your order ID (you can find it in /my_orders).\n"
        "Or type 'skip' if this isn't about a specific order."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_order:"))
async def create_ticket_with_order(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
):
    """Start ticket with pre-filled order ID."""
    order_id = callback.data.split(":")[1]
    
    await state.update_data(order_id=order_id)
    await state.set_state(TicketStates.waiting_for_description)
    
    await callback.message.answer(
        f"📝 Order ID: {order_id[:8]}...\n\n"
        "Please describe your issue in detail:"
    )
    await callback.answer()


# ============================================================
# Review Callbacks
# ============================================================

@router.callback_query(F.data.startswith("review:"))
async def start_review_callback(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
):
    """Start review submission flow."""
    order_id = callback.data.split(":")[1]
    
    await state.update_data(order_id=order_id)
    await state.set_state(ReviewStates.waiting_for_rating)
    
    # Rating buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rating:1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rating:2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating:3"),
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating:4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating:5"),
        ]
    ])
    
    await callback.message.answer(
        "⭐ <b>Leave a Review</b>\n\n"
        "How would you rate your purchase?\n"
        "💡 Get 5% cashback for your honest review!",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rating:"))
async def rating_callback(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
):
    """Handle rating selection."""
    rating = int(callback.data.split(":")[1])
    
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_for_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Skip text review", callback_data="review_skip_text")]
    ])
    
    await callback.message.edit_text(
        f"⭐ Rating: {'⭐' * rating}\n\n"
        "Would you like to add a text review? (optional)\n"
        "Just type your feedback or click Skip.",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "review_skip_text")
async def skip_review_text(
    callback: CallbackQuery,
    state: FSMContext,
    user_telegram_id: int,
    supabase,
    **kwargs
):
    """Submit review without text."""
    data = await state.get_data()
    order_id = data.get("order_id")
    rating = data.get("rating", 5)
    
    await submit_review(
        callback, order_id, rating, None, user_telegram_id, supabase
    )
    await state.clear()


async def submit_review(
    callback: CallbackQuery,
    order_id: str,
    rating: int,
    text: str | None,
    user_telegram_id: int,
    supabase
):
    """Submit the review and trigger cashback."""
    # Get order and user info
    order = await supabase.table("orders").select(
        "id, amount, product_id"
    ).eq("id", order_id).single().execute()
    
    user = await supabase.table("users").select("id").eq(
        "telegram_id", user_telegram_id
    ).single().execute()
    
    if not order.data or not user.data:
        await callback.message.edit_text("❌ Error submitting review")
        return
    
    # Insert review
    review = await supabase.table("reviews").insert({
        "user_id": user.data["id"],
        "order_id": order_id,
        "product_id": order.data["product_id"],
        "rating": rating,
        "text": text
    }).execute()
    
    # Trigger cashback worker
    await publish_to_worker(
        endpoint=WorkerEndpoints.PROCESS_REVIEW_CASHBACK,
        body={
            "user_telegram_id": user_telegram_id,
            "order_id": order_id,
            "order_amount": order.data["amount"],
            "review_id": review.data[0]["id"] if review.data else None
        }
    )
    
    await callback.message.edit_text(
        f"✅ Thank you for your review! {'⭐' * rating}\n\n"
        "Your 5% cashback will be credited to your balance shortly."
    )


# ============================================================
# Quick Action Callbacks
# ============================================================

@router.callback_query(F.data == "ask_prompt")
async def ask_prompt_callback(callback: CallbackQuery, **kwargs):
    """Prompt user to ask a question."""
    await callback.message.answer(
        "💬 What would you like to know?\n\n"
        "Try asking:\n"
        "• What's the best option for ChatGPT?\n"
        "• I need Midjourney for my work\n"
        "• Show me deals under 500₽"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_again:"))
async def buy_again_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    supabase,
    cart_manager: CartManager,
    **kwargs
):
    """Quick reorder from order history."""
    order_id = callback.data.split(":")[1]
    
    # Get order details
    order = await supabase.table("orders").select(
        "product_id, products(name, price)"
    ).eq("id", order_id).single().execute()
    
    if not order.data:
        await callback.answer("❌ Order not found", show_alert=True)
        return
    
    product_id = order.data["product_id"]
    product = order.data.get("products", {})
    
    # Get current stock/price
    stock = await supabase.table("available_stock_with_discounts").select(
        "*"
    ).eq("product_id", product_id).execute()
    
    available = len(stock.data) if stock.data else 0
    discount = stock.data[0].get("discount_percent", 0) if stock.data else 0
    
    # Add to cart
    await cart_manager.add_item(
        user_telegram_id=user_telegram_id,
        product_id=product_id,
        product_name=product.get("name", "Product"),
        quantity=1,
        available_stock=available,
        unit_price=product.get("price", 0),
        discount_percent=discount
    )
    
    await callback.answer(
        f"✅ Added {product.get('name', 'Product')} to cart!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("apply_promo:"))
async def apply_promo_callback(
    callback: CallbackQuery,
    user_telegram_id: int,
    cart_manager: CartManager,
    supabase,
    **kwargs
):
    """Apply promo code to cart."""
    code = callback.data.split(":")[1]
    
    # Validate promo code
    promo = await supabase.table("promo_codes").select("*").eq(
        "code", code.upper()
    ).single().execute()
    
    if not promo.data:
        await callback.answer("❌ Invalid promo code", show_alert=True)
        return
    
    # Check expiration and usage
    from datetime import datetime
    promo_data = promo.data
    
    if promo_data.get("expires_at"):
        expires = datetime.fromisoformat(promo_data["expires_at"].replace("Z", "+00:00"))
        if expires < datetime.now(expires.tzinfo):
            await callback.answer("❌ Promo code expired", show_alert=True)
            return
    
    if promo_data.get("usage_limit"):
        if promo_data.get("usage_count", 0) >= promo_data["usage_limit"]:
            await callback.answer("❌ Promo code limit reached", show_alert=True)
            return
    
    # Apply to cart
    await cart_manager.apply_promo_code(
        user_telegram_id,
        code.upper(),
        promo_data.get("discount_percent", 0)
    )
    
    await callback.answer(
        f"✅ Promo code applied! -{promo_data.get('discount_percent', 0)}%",
        show_alert=True
    )



