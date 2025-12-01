"""
PVNDORA AI Marketplace - Main FastAPI Application

Single entry point for all webhooks and API routes.
Optimized for Vercel Hobby plan (max 12 serverless functions).
"""
import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Add src to path for imports
# Try multiple paths for Vercel compatibility
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path))
# Also try absolute path
if str(_base_path) not in sys.path:
    sys.path.insert(0, str(_base_path.resolve()))

try:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    # Import bot components
    from src.bot.handlers import router as bot_router
    from src.bot.middlewares import (
        AuthMiddleware,
        LanguageMiddleware,
        ActivityMiddleware,
        AnalyticsMiddleware
    )
    from src.services.database import get_database
    from src.utils.validators import (
        validate_telegram_init_data, extract_user_from_init_data
    )
except ImportError as e:
    import traceback
    print(f"ERROR: Failed to import modules: {e}")
    print(f"ERROR: sys.path = {sys.path}")
    print(f"ERROR: Traceback: {traceback.format_exc()}")
    raise


# ==================== BOT INITIALIZATION ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora.app")

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


def get_bot() -> Bot:
    """Get or create bot instance"""
    global bot
    if bot is None and TELEGRAM_TOKEN:
        bot = Bot(
            token=TELEGRAM_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return bot


def get_dispatcher() -> Dispatcher:
    """Get or create dispatcher instance"""
    global dp
    if dp is None:
        dp = Dispatcher()

        # Register middlewares (order matters!)
        dp.message.middleware(AuthMiddleware())
        dp.message.middleware(LanguageMiddleware())
        dp.message.middleware(ActivityMiddleware())
        dp.message.middleware(AnalyticsMiddleware())

        dp.callback_query.middleware(AuthMiddleware())
        dp.callback_query.middleware(LanguageMiddleware())
        dp.callback_query.middleware(ActivityMiddleware())

        # Register router
        dp.include_router(bot_router)

    return dp


# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    yield
    # Shutdown
    if bot:
        await bot.session.close()


app = FastAPI(
    title="PVNDORA AI Marketplace",
    description="AI-powered digital goods marketplace API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini Apps require this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "pvndora"}


@app.get("/api/webhook/test")
async def test_webhook():
    """Test webhook endpoint - verify bot is configured"""
    bot_instance = get_bot()
    dispatcher = get_dispatcher()

    return {
        "bot_configured": bot_instance is not None,
        "dispatcher_configured": dispatcher is not None,
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "webhook_url": f"{WEBAPP_URL}/webhook/telegram"
    }


# ==================== TELEGRAM WEBHOOK ====================

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Telegram webhook updates"""
    import traceback

    # IMPORTANT: Return 200 immediately to avoid 307 redirects
    # Process update in background to avoid timeout
    try:
        # Get bot and dispatcher
        bot_instance = get_bot()
        dispatcher = get_dispatcher()

        if not bot_instance:
            print("ERROR: Bot instance is None - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=200,  # Return 200 even on error to prevent Telegram retries
                content={"ok": False, "error": "Bot not configured"}
            )

        # Parse update
        try:
            data = await request.json()
            update_id = data.get('update_id', 'unknown')
            print(f"DEBUG: Received update: {update_id}")
        except Exception as e:
            print(f"ERROR: Failed to parse JSON: {e}")
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid JSON: {str(e)}"}
            )

        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
            event_type = getattr(update, 'event_type', 'unknown')
            print(f"DEBUG: Update validated, type: {event_type}")
        except Exception as e:
            print(f"ERROR: Failed to validate update: {e}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=200,  # Return 200 to prevent retries
                content={"ok": False, "error": f"Invalid update: {str(e)}"}
            )

        # Process update in background - FastAPI BackgroundTasks are guaranteed to run
        # Return 200 immediately to Telegram
        background_tasks.add_task(
            _process_update_async,
            bot_instance,
            dispatcher,
            update
        )

        print(f"DEBUG: Update {update_id} queued for background processing")

        # Return 200 OK immediately
        return JSONResponse(content={"ok": True})

    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Webhook exception: {error_msg}")
        print(f"ERROR: Traceback: {error_trace}")
        # Always return 200 to prevent Telegram from retrying
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": error_msg}
        )


async def _process_update_async(
    bot_instance: Bot, dispatcher: Dispatcher, update: Update
):
    """Process update asynchronously"""
    import traceback
    update_id = update.update_id if hasattr(update, 'update_id') else 'unknown'
    print(f"DEBUG: Starting background processing of update {update_id}")
    try:
        await dispatcher.feed_update(bot_instance, update)
        print(f"DEBUG: Update {update_id} processed successfully")
    except Exception as e:
        print(f"ERROR: Failed to process update {update_id}: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")


# ==================== AUTHENTICATION ====================

async def verify_telegram_auth(
    authorization: str = Header(None, alias="Authorization"),
    x_init_data: str = Header(None, alias="X-Init-Data")
):
    """
    Verify Telegram Mini App authentication.
    Accepts either:
    - Authorization: tma <initData>
    - X-Init-Data: <initData>
    """
    init_data = None

    # Try X-Init-Data header first (frontend sends this)
    if x_init_data:
        init_data = x_init_data
    # Fallback to Authorization header
    elif authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "tma":
            init_data = parts[1]
        else:
            init_data = authorization  # Try raw value

    if not init_data:
        raise HTTPException(status_code=401, detail="No authorization header")

    # For development/testing - allow bypass with special token
    if init_data == "dev_bypass" and os.environ.get("DEBUG") == "true":
        return {"id": 339469894, "first_name": "Test", "language_code": "ru"}

    if not validate_telegram_init_data(init_data, TELEGRAM_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user = extract_user_from_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Could not extract user")

    return user


# ==================== PRODUCTS API ====================

class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    type: str
    status: str
    stock_count: int
    warranty_hours: int
    rating: float = 0
    reviews_count: int = 0


@app.get("/api/products")
async def get_products():
    """Get all available products"""
    db = get_database()
    products = await db.get_products(status="active")

    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)
        result.append(ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            type=p.type,
            status=p.status,
            stock_count=p.stock_count,
            warranty_hours=p.warranty_hours,
            rating=rating_info["average"],
            reviews_count=rating_info["count"]
        ))

    return result


@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID"""
    db = get_database()
    product = await db.get_product_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rating_info = await db.get_product_rating(product_id)
    reviews = await db.get_product_reviews(product_id, limit=5)

    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "type": product.type,
        "status": product.status,
        "stock_count": product.stock_count,
        "warranty_hours": product.warranty_hours,
        "instructions": product.instructions,
        "terms": product.terms,
        "rating": rating_info["average"],
        "reviews_count": rating_info["count"],
        "reviews": reviews
    }


# ==================== WEBAPP API (Mini App) ====================

@app.get("/api/webapp/products/{product_id}")
async def get_webapp_product(product_id: str):
    """
    Get product with discount and social proof for Mini App.
    Public endpoint - product info is not sensitive.
    """
    db = get_database()
    product = await db.get_product_by_id(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get available stock with discounts
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("available_stock_with_discounts").select(
            "*"
        ).eq("product_id", product_id).limit(1).execute()
    )

    discount_percent = 0
    if stock_result.data:
        discount_percent = stock_result.data[0].get("discount_percent", 0)

    # Get social proof
    rating_info = await db.get_product_rating(product_id)

    # Calculate final price
    original_price = float(product.price)
    final_price = original_price * (1 - discount_percent / 100)

    # Get fulfillment info for on-demand products
    fulfillment_time_hours = getattr(product, 'fulfillment_time_hours', 48)
    can_fulfill_on_demand = product.status == 'active'

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "original_price": original_price,
            "price": original_price,  # For backward compatibility
            "discount_percent": discount_percent,
            "final_price": round(final_price, 2),
            "warranty_days": getattr(product, 'warranty_hours', 24) // 24,
            "duration_days": getattr(product, 'duration_days', None),
            "available_count": product.stock_count,
            "available": product.stock_count > 0,
            "can_fulfill_on_demand": can_fulfill_on_demand,
            "fulfillment_time_hours": fulfillment_time_hours if can_fulfill_on_demand else None,
            "type": product.type,
            "instructions": product.instructions,
            "rating": rating_info["average"],
            "reviews_count": rating_info["count"]
        }
    }


@app.get("/api/webapp/products")
async def get_webapp_products():
    """
    Get all products for Mini App catalog.
    Public endpoint - products are not sensitive data.
    """
    db = get_database()
    products = await db.get_products(status="active")

    result = []
    for p in products:
        rating_info = await db.get_product_rating(p.id)

        # Get fulfillment info
        fulfillment_time_hours = getattr(p, 'fulfillment_time_hours', 48)

        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "type": p.type,
            "status": p.status,
            "stock_count": p.stock_count,
            "available": p.stock_count > 0,
            "can_fulfill_on_demand": p.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours,
            "warranty_days": p.warranty_hours // 24 if hasattr(p, 'warranty_hours') and p.warranty_hours else 1,
            "duration_days": getattr(p, 'duration_days', None),
            "rating": rating_info["average"],
            "reviews_count": rating_info["count"]
        })

    return {"products": result, "count": len(result)}


@app.get("/api/webapp/orders")
async def get_webapp_orders(user = Depends(verify_telegram_auth)):
    """
    Get user's order history for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()

    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    orders = await db.get_user_orders(db_user.id, limit=50)

    result = []
    for o in orders:
        product = await db.get_product_by_id(o.product_id)
        product_name = product.name if product else "Unknown Product"

        result.append({
            "id": o.id,
            "product_id": o.product_id,
            "product_name": product_name,
            "amount": o.amount,
            "original_price": o.original_price,
            "discount_percent": o.discount_percent,
            "status": o.status,
            "order_type": getattr(o, 'order_type', 'instant'),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivered_at": o.delivered_at.isoformat() if hasattr(o, 'delivered_at') and o.delivered_at else None,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "warranty_until": o.warranty_until.isoformat() if hasattr(o, 'warranty_until') and o.warranty_until else None
        })

    return {"orders": result, "count": len(result)}


@app.get("/api/webapp/leaderboard")
async def get_webapp_leaderboard(user = Depends(verify_telegram_auth)):
    """
    Get savings leaderboard for Mini App.
    Shows top users by total_saved amount.
    """
    db = get_database()

    # Get top 50 users by total_saved
    result = await asyncio.to_thread(
        lambda: db.client.table("users").select(
            "telegram_id,username,first_name,total_saved"
        ).gt("total_saved", 0).order(
            "total_saved", desc=True
        ).limit(50).execute()
    )

    # Get current user's stats
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank = None
    user_saved = 0

    if db_user:
        user_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0

        # Calculate user's rank
        if user_saved > 0:
            rank_result = await asyncio.to_thread(
                lambda: db.client.table("users").select(
                    "id", count="exact"
                ).gt("total_saved", user_saved).execute()
            )
            user_rank = (rank_result.count or 0) + 1

    leaderboard = []
    for i, entry in enumerate(result.data):
        display_name = entry.get("username") or entry.get("first_name") or f"User{entry['telegram_id']}"
        # Mask name for privacy (show first 3 chars + ***)
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"

        leaderboard.append({
            "rank": i + 1,
            "name": display_name,
            "total_saved": float(entry.get("total_saved", 0)),
            "is_current_user": entry["telegram_id"] == user.id
        })

    return {
        "leaderboard": leaderboard,
        "user_rank": user_rank,
        "user_saved": user_saved
    }


@app.get("/api/webapp/faq")
async def get_webapp_faq(language_code: str = "en", user = Depends(verify_telegram_auth)):
    """
    Get FAQ entries for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()
    faq_entries = await db.get_faq(language_code)

    # Group by category
    categories = {}
    for entry in faq_entries:
        category = entry.get("category", "general")
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "question": entry["question"],
            "answer": entry["answer"]
        })

    return {
        "categories": categories,
        "total": len(faq_entries)
    }


@app.get("/api/webapp/cart")
async def get_webapp_cart(user = Depends(verify_telegram_auth)):
    """
    Get user's shopping cart for Mini App.
    Requires Telegram initData authentication.
    """
    from core.cart import get_cart_manager

    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)

        if not cart:
            return {
                "cart": None,
                "items": [],
                "total": 0.0,
                "subtotal": 0.0,
                "instant_total": 0.0,
                "prepaid_total": 0.0,
                "promo_code": None,
                "promo_discount_percent": 0.0
            }

        # Get product details for each item
        db = get_database()
        items_with_details = []
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            items_with_details.append({
                "product_id": item.product_id,
                "product_name": product.name if product else "Unknown Product",
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "unit_price": item.unit_price,
                "final_price": item.final_price,
                "total_price": item.total_price,
                "discount_percent": item.discount_percent
            })

        return {
            "cart": {
                "user_telegram_id": cart.user_telegram_id,
                "created_at": cart.created_at,
                "updated_at": cart.updated_at
            },
            "items": items_with_details,
            "total": cart.total,
            "subtotal": cart.subtotal,
            "instant_total": cart.instant_total,
            "prepaid_total": cart.prepaid_total,
            "promo_code": cart.promo_code,
            "promo_discount_percent": cart.promo_discount_percent
        }
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")


class PromoCheckRequest(BaseModel):
    code: str


@app.post("/api/webapp/promo/check")
async def check_webapp_promo(request: PromoCheckRequest, user = Depends(verify_telegram_auth)):
    """
    Check if promo code is valid for Mini App.
    Requires Telegram initData authentication.
    """
    db = get_database()

    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)

    if promo:
        return {
            "valid": True,
            "code": code,
            "discount_percent": promo["discount_percent"],
            "expires_at": promo.get("expires_at"),
            "usage_remaining": (promo.get("usage_limit") or 999) - (promo.get("usage_count") or 0)
        }

    return {
        "valid": False,
        "code": code,
        "message": "Invalid or expired promo code"
    }


class WebAppReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: Optional[str] = None


@app.post("/api/webapp/reviews")
async def submit_webapp_review(request: WebAppReviewRequest, user = Depends(verify_telegram_auth)):
    """
    Submit a product review from Mini App.
    Awards 5% cashback for first review on an order.
    """
    db = get_database()

    # Validate rating
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Get user
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get order and verify ownership
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check if order belongs to user
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")

    # Check if order is completed
    if order.status not in ["completed", "delivered"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")

    # Check if already reviewed
    existing_review = await asyncio.to_thread(
        lambda: db.client.table("reviews").select("id").eq(
            "order_id", request.order_id
        ).execute()
    )

    if existing_review.data:
        raise HTTPException(status_code=400, detail="Order already reviewed")

    # Create review
    review_data = {
        "user_id": db_user.id,
        "order_id": request.order_id,
        "product_id": order.product_id,
        "rating": request.rating,
        "text": request.text,
        "cashback_given": False
    }

    result = await asyncio.to_thread(
        lambda: db.client.table("reviews").insert(review_data).execute()
    )

    # Calculate and award 5% cashback
    cashback_amount = float(order.amount) * 0.05

    await asyncio.to_thread(
        lambda: db.client.table("users").update({
            "balance": db_user.balance + cashback_amount
        }).eq("id", db_user.id).execute()
    )

    # Mark cashback as given
    await asyncio.to_thread(
        lambda: db.client.table("reviews").update({
            "cashback_given": True
        }).eq("id", result.data[0]["id"]).execute()
    )

    return {
        "success": True,
        "review_id": result.data[0]["id"],
        "cashback_awarded": round(cashback_amount, 2),
        "new_balance": round(float(db_user.balance) + cashback_amount, 2)
    }


# ==================== ORDERS API ====================

class CreateOrderRequest(BaseModel):
    product_id: Optional[str] = None
    quantity: Optional[int] = 1
    promo_code: Optional[str] = None
    # For cart-based orders
    use_cart: Optional[bool] = False


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


@app.post("/api/webapp/orders")
async def create_webapp_order(
    request: CreateOrderRequest,
    user = Depends(verify_telegram_auth)
):
    """
    Create new order from Mini App.
    Supports both single product and cart-based orders.
    """
    db = get_database()

    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine payment method based on language
    # Priority: cardlink (if configured) > aaio > stripe
    cardlink_configured = bool(os.environ.get("CARDLINK_API_TOKEN") and os.environ.get("CARDLINK_SHOP_ID"))
    if cardlink_configured and db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "cardlink"
    elif db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "aaio"
    else:
        payment_method = "stripe"

    from src.services.payments import PaymentService
    payment_service = PaymentService()

    # Cart-based order
    if request.use_cart or (not request.product_id):
        from core.cart import get_cart_manager

        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)

        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Validate all products in cart
        total_amount = 0.0
        total_original = 0.0
        order_items = []

        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            # Check stock for instant items
            if item.instant_quantity > 0:
                available_stock = await db.get_available_stock_count(item.product_id)
                if available_stock < item.instant_quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock for {product.name}. Available: {available_stock}, Requested: {item.instant_quantity}"
                    )

            # Calculate price with discount
            original_price = product.price * item.quantity
            discount_percent = item.discount_percent

            # Apply promo code if present
            if cart.promo_code and cart.promo_discount_percent > 0:
                discount_percent = max(discount_percent, cart.promo_discount_percent)

            final_price = original_price * (1 - discount_percent / 100)

            total_amount += final_price
            total_original += original_price

            order_items.append({
                "product_id": item.product_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "amount": final_price,
                "original_price": original_price,
                "discount_percent": discount_percent
            })

        # Create order for first item (or create a combined order)
        # For now, create order for first item and include others in metadata
        first_item = order_items[0]

        order = await db.create_order(
            user_id=db_user.id,
            product_id=first_item["product_id"],
            amount=total_amount,
            original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_method=payment_method
        )

        # Store additional items in order metadata (if supported)
        # For now, we'll create separate orders for each item
        # TODO: Implement multi-item order support in database

        # Generate payment URL with total amount
        product_names = ", ".join([item["product_name"] for item in order_items[:3]])
        if len(order_items) > 3:
            product_names += f" и еще {len(order_items) - 3}"

        payment_url = await payment_service.create_payment(
            order_id=order.id,
            amount=total_amount,
            product_name=product_names,
            method=payment_method,
            user_email=f"{user.id}@telegram.user"
        )

        # Use promo code if valid
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)

        # Clear cart after successful order creation
        await cart_manager.clear_cart(user.id)

        return OrderResponse(
            order_id=order.id,
            amount=total_amount,
            original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_url=payment_url,
            payment_method=payment_method
        )

    # Single product order
    else:
        if not request.product_id:
            raise HTTPException(status_code=400, detail="product_id is required for single product orders")

        # Get product
        product = await db.get_product_by_id(request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        quantity = request.quantity or 1

        # Check stock
        available_stock = await db.get_available_stock_count(request.product_id)
        if available_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock. Available: {available_stock}, Requested: {quantity}"
            )

        # Calculate price with potential discount
        original_price = product.price * quantity
        discount_percent = 0

        # Check for stock item discount (age-based)
        stock_item = await db.get_available_stock_item(request.product_id)
        if stock_item:
            discount_percent = await db.calculate_discount(stock_item, product)

        # Check promo code
        if request.promo_code:
            promo = await db.validate_promo_code(request.promo_code)
            if promo:
                # Use higher discount
                discount_percent = max(discount_percent, promo["discount_percent"])

        # Calculate final price
        final_price = original_price * (1 - discount_percent / 100)

        # Create order
        order = await db.create_order(
            user_id=db_user.id,
            product_id=request.product_id,
            amount=final_price,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_method=payment_method
        )

        # Generate payment URL
        payment_url = await payment_service.create_payment(
            order_id=order.id,
            amount=final_price,
            product_name=product.name,
            method=payment_method,
            user_email=f"{user.id}@telegram.user"  # Placeholder
        )

        # Use promo code if valid
        if request.promo_code:
            await db.use_promo_code(request.promo_code)

        return OrderResponse(
            order_id=order.id,
            amount=final_price,
            original_price=original_price,
            discount_percent=discount_percent,
            payment_url=payment_url,
            payment_method=payment_method
        )


@app.post("/api/orders")
async def create_order(
    request: CreateOrderRequest,
    user = Depends(verify_telegram_auth)
):
    """Create new order and get payment URL (legacy endpoint, redirects to webapp)"""
    return await create_webapp_order(request, user)


@app.get("/api/orders")
async def get_user_orders(user = Depends(verify_telegram_auth)):
    """Get user's orders"""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    orders = await db.get_user_orders(db_user.id)
    return orders


# ==================== PAYMENT WEBHOOKS ====================

@app.post("/webhook/aaio")
async def aaio_webhook(request: Request):
    """Handle AAIO payment callback"""
    from src.services.payments import PaymentService
    from core.queue import publish_to_worker, WorkerEndpoints

    try:
        data = await request.form()

        payment_service = PaymentService()
        result = await payment_service.verify_aaio_callback(dict(data))

        if result["success"]:
            order_id = result["order_id"]

            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=5,
                deduplication_id=f"deliver-{order_id}"
            )

            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=3,
                deduplication_id=f"referral-{order_id}"
            )

            return JSONResponse({"ok": True})

        return JSONResponse({"ok": False, "error": result.get("error")}, status_code=400)

    except Exception as e:
        print(f"AAIO webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/webhook/cardlink")
async def cardlink_webhook(request: Request):
    """Handle CardLink payment webhook"""
    from src.services.payments import PaymentService
    from core.queue import publish_to_worker, WorkerEndpoints

    try:
        data = await request.json()

        payment_service = PaymentService()
        result = await payment_service.verify_cardlink_webhook(data)

        if result["success"]:
            order_id = result["order_id"]

            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=5,
                deduplication_id=f"deliver-{order_id}"
            )

            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=3,
                deduplication_id=f"referral-{order_id}"
            )

            return JSONResponse({"ok": True})

        return JSONResponse({"ok": False, "error": result.get("error")}, status_code=400)

    except Exception as e:
        print(f"CardLink webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/webhook/cardlink/refund")
async def cardlink_refund_webhook(request: Request):
    """Handle CardLink refund webhook"""
    try:
        data = await request.json()
        # Process refund notification
        print(f"CardLink refund webhook: {data}")
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"CardLink refund webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/webhook/cardlink/chargeback")
async def cardlink_chargeback_webhook(request: Request):
    """Handle CardLink chargeback webhook"""
    try:
        data = await request.json()
        # Process chargeback notification
        print(f"CardLink chargeback webhook: {data}")
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"CardLink chargeback webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        print(f"AAIO webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe payment webhook"""
    from src.services.payments import PaymentService
    from core.queue import publish_to_worker, WorkerEndpoints

    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        payment_service = PaymentService()
        result = await payment_service.verify_stripe_webhook(payload, sig_header)

        if result["success"]:
            order_id = result["order_id"]

            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=5,
                deduplication_id=f"deliver-{order_id}"
            )

            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=3,
                deduplication_id=f"referral-{order_id}"
            )

        return JSONResponse(content={"received": True})

    except Exception as e:
        print(f"Stripe webhook error: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


# ==================== USER API ====================

@app.get("/api/user/profile")
async def get_user_profile(user = Depends(verify_telegram_auth)):
    """Get user profile"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": db_user.id,
        "telegram_id": db_user.telegram_id,
        "username": db_user.username,
        "first_name": db_user.first_name,
        "balance": db_user.balance,
        "language_code": db_user.language_code,
        "referral_percent": db_user.personal_ref_percent,
        "is_admin": db_user.is_admin or False
    }


@app.get("/api/user/referral")
async def get_referral_info(user = Depends(verify_telegram_auth)):
    """Get referral link and stats"""
    bot_instance = get_bot()

    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")

    bot_info = await bot_instance.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    return {
        "link": referral_link,
        "percent": db_user.personal_ref_percent if db_user else 20,
        "balance": db_user.balance if db_user else 0
    }


@app.post("/api/webapp/referral/share-link")
async def create_referral_share_link(user = Depends(verify_telegram_auth)):
    """
    Create a prepared inline message for sharing.
    Returns prepared_message_id to be used with Telegram.WebApp.shareMessage()
    """
    from aiogram.types import InlineQueryResultPhoto, InlineKeyboardMarkup, InlineKeyboardButton
    import traceback

    bot_instance = get_bot()
    if not bot_instance:
        raise HTTPException(status_code=500, detail="Bot not configured")

    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate savings or get from DB
    total_saved = int(float(db_user.total_saved)) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
    display_name = db_user.first_name or db_user.username or "User"

    # Calculate leaderboard rank
    user_rank = None
    if total_saved > 0:
        rank_result = await asyncio.to_thread(
            lambda: db.client.table("users").select(
                "id", count="exact"
            ).gt("total_saved", total_saved).execute()
        )
        user_rank = (rank_result.count or 0) + 1

    # Referral link
    bot_info = await bot_instance.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    # Dynamic Image URL powered by Vercel OG
    import urllib.parse
    from datetime import timezone
    timestamp = int(datetime.now(timezone.utc).timestamp())
    avatar_url = getattr(user, "photo_url", None)
    if not avatar_url:
        initials_seed = urllib.parse.quote(display_name)
        avatar_url = f"https://api.dicebear.com/7.x/initials/png?seed={initials_seed}&backgroundColor=1f1f2e,4c1d95&fontWeight=700"

    query_params = {
        "name": display_name,
        "saved": total_saved,
        "lang": db_user.language_code or "ru",
        "avatar": avatar_url,
        "t": timestamp,
        "handle": f"@{bot_info.username}"
    }
    if user_rank:
        query_params["rank"] = user_rank

    query_string = urllib.parse.urlencode(query_params, doseq=False)
    photo_url = f"{WEBAPP_URL}/og/referral?{query_string}"

    result_id = f"share_{user.id}_{timestamp}"

    # Лаконичный caption от первого лица
    if db_user.language_code == "ru":
        caption_text = "Оплачиваю тарифы нейросетей за 20% от их стоимости"
        button_text = "🎁 Попробовать"
    else:
        caption_text = "Paying for AI subscriptions at 20% of their cost"
        button_text = "🎁 Try it"

    # Using InlineQueryResultPhoto for "Major-style" large image
    photo = InlineQueryResultPhoto(
        id=result_id,
        photo_url=photo_url,
        thumbnail_url=photo_url,  # Use same URL for thumb
        title="🎁 PVNDORA AI",
        description=caption_text,
        caption=caption_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=button_text, url=ref_link)
            ]]
        )
    )

    try:
        print(f"DEBUG: Attempting to save prepared message for user {user.id}")
        prepared_message = await bot_instance.save_prepared_inline_message(
            user_id=user.id,
            result=photo,
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True
        )
        print(f"DEBUG: Prepared message saved successfully, ID: {prepared_message.id}")
        return {"prepared_message_id": prepared_message.id}
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Failed to save prepared message: {error_msg}")
        print(f"ERROR: Traceback: {error_trace}")

        if "object has no attribute 'save_prepared_inline_message'" in error_msg:
             raise HTTPException(status_code=501, detail="Feature not supported by bot backend version")

        # Check if it's a Telegram API error
        if "Bad Request" in error_msg or "400" in error_msg:
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_msg}")

        raise HTTPException(status_code=500, detail=f"Failed to save prepared message: {error_msg}")


# ==================== FAQ API ====================

@app.get("/api/faq")
async def get_faq(language_code: str = "en"):
    """Get FAQ entries"""
    db = get_database()
    faq = await db.get_faq(language_code)
    return {"faq": faq}


# ==================== WISHLIST API ====================

@app.get("/api/wishlist")
async def get_wishlist(user = Depends(verify_telegram_auth)):
    """Get user's wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    products = await db.get_wishlist(db_user.id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock_count": p.stock_count
        }
        for p in products
    ]


@app.post("/api/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user = Depends(verify_telegram_auth)):
    """Add product to wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.add_to_wishlist(db_user.id, product_id)
    return {"success": True}


@app.delete("/api/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user = Depends(verify_telegram_auth)):
    """Remove product from wishlist"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.remove_from_wishlist(db_user.id, product_id)
    return {"success": True}


# ==================== ADMIN API ====================

async def verify_admin(user = Depends(verify_telegram_auth)):
    """Verify that user is an admin"""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return db_user


class AddStockRequest(BaseModel):
    product_id: str
    content: str  # Login:Pass or invite link
    expires_at: Optional[str] = None  # ISO datetime
    supplier_id: Optional[str] = None


class BroadcastRequest(BaseModel):
    message: str
    exclude_dnd: bool = True


class BanUserRequest(BaseModel):
    telegram_id: int
    ban: bool = True
    reason: Optional[str] = None


class CreateProductRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    type: str = "shared"  # student, trial, shared, key
    fulfillment_time_hours: int = 48
    warranty_hours: int = 24
    instructions: Optional[str] = None
    msrp: Optional[float] = None
    duration_days: Optional[int] = None


class CreateFAQRequest(BaseModel):
    question: str
    answer: str
    language_code: str = "ru"
    category: str = "general"


@app.post("/api/admin/products")
async def admin_create_product(request: CreateProductRequest, admin = Depends(verify_admin)):
    """Create a new product"""
    db = get_database()

    result = await asyncio.to_thread(
        lambda: db.client.table("products").insert({
            "name": request.name,
            "description": request.description,
            "price": request.price,
            "type": request.type,
            "fulfillment_time_hours": request.fulfillment_time_hours,
            "warranty_hours": request.warranty_hours,
            "instructions": request.instructions,
            "msrp": request.msrp,
            "duration_days": request.duration_days,
            "status": "active"
        }).execute()
    )

    if result.data:
        return {"success": True, "product": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create product")


@app.get("/api/admin/products")
async def admin_get_products(admin = Depends(verify_admin)):
    """Get all products for admin (including inactive)"""
    db = get_database()

    # Get all products without status filter
    result = await asyncio.to_thread(
        lambda: db.client.table("products").select("*").order("created_at", desc=True).execute()
    )

    if not result.data:
        return {"products": []}

    products = []
    for p in result.data:
        product_id = p["id"]
        # Count available stock - create query inside lambda
        stock_result = await asyncio.to_thread(
            lambda pid=product_id: db.client.table("stock_items").select("id", count="exact")
                .eq("product_id", pid).eq("is_sold", False).execute()
        )
        p["stock_count"] = getattr(stock_result, 'count', 0) or 0
        products.append(p)

    return {"products": products}


@app.put("/api/admin/products/{product_id}")
async def admin_update_product(product_id: str, request: CreateProductRequest, admin = Depends(verify_admin)):
    """Update a product"""
    db = get_database()

    result = await asyncio.to_thread(
        lambda: db.client.table("products").update({
            "name": request.name,
            "description": request.description,
            "price": request.price,
            "type": request.type,
            "fulfillment_time_hours": request.fulfillment_time_hours,
            "warranty_hours": request.warranty_hours,
            "instructions": request.instructions,
            "msrp": request.msrp,
            "duration_days": request.duration_days
        }).eq("id", product_id).execute()
    )

    return {"success": True, "updated": len(result.data) > 0}


@app.post("/api/admin/faq")
async def admin_create_faq(request: CreateFAQRequest, admin = Depends(verify_admin)):
    """Create a FAQ entry"""
    db = get_database()

    result = await asyncio.to_thread(
        lambda: db.client.table("faq").insert({
            "question": request.question,
            "answer": request.answer,
            "language_code": request.language_code,
            "category": request.category,
            "is_active": True
        }).execute()
    )

    if result.data:
        return {"success": True, "faq": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create FAQ")


@app.get("/api/admin/faq")
async def admin_get_faq(admin = Depends(verify_admin)):
    """Get all FAQ entries for admin"""
    db = get_database()

    result = await asyncio.to_thread(
        lambda: db.client.table("faq").select("*").order("language_code").order("category").execute()
    )

    return {"faq": result.data}


@app.get("/api/admin/orders")
async def admin_get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin = Depends(verify_admin)
):
    """Get all orders with optional filtering"""
    db = get_database()

    # Create query inside lambda to avoid context issues
    def execute_query():
        query = db.client.table("orders").select(
            "*, users(telegram_id, username, first_name), products(name)"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)

        if status:
            query = query.eq("status", status)

        return query.execute()

    result = await asyncio.to_thread(execute_query)
    return {"orders": result.data if result.data else []}


@app.get("/api/admin/users")
async def admin_get_users(
    limit: int = 50,
    offset: int = 0,
    admin = Depends(verify_admin)
):
    """Get all users"""
    db = get_database()

    result = db.client.table("users").select("*").order(
        "created_at", desc=True
    ).range(offset, offset + limit - 1).execute()

    return result.data


@app.get("/api/admin/users/{telegram_id}")
async def admin_get_user(telegram_id: int, admin = Depends(verify_admin)):
    """Get specific user details"""
    db = get_database()
    user = await db.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's orders
    orders = await db.get_user_orders(user.id, limit=20)

    return {
        "user": user,
        "orders": orders
    }


@app.post("/api/admin/users/ban")
async def admin_ban_user(request: BanUserRequest, admin = Depends(verify_admin)):
    """Ban or unban a user"""
    db = get_database()
    await db.ban_user(request.telegram_id, request.ban)

    return {"success": True, "banned": request.ban}


@app.post("/api/admin/users/{telegram_id}/warning")
async def admin_add_warning(telegram_id: int, admin = Depends(verify_admin)):
    """Add warning to user (auto-ban after 3)"""
    db = get_database()
    new_count = await db.add_warning(telegram_id)

    return {
        "success": True,
        "warnings_count": new_count,
        "auto_banned": new_count >= 3
    }


@app.post("/api/admin/stock")
async def admin_add_stock(request: AddStockRequest, admin = Depends(verify_admin)):
    """Add single stock item for a product"""
    db = get_database()

    # Verify product exists
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create stock item
    data = {
        "product_id": request.product_id,
        "content": request.content,
        "is_sold": False
    }

    if request.expires_at:
        data["expires_at"] = request.expires_at
    if request.supplier_id:
        data["supplier_id"] = request.supplier_id

    result = db.client.table("stock_items").insert(data).execute()

    # Notify waitlist users
    await _notify_waitlist_for_product(product.name)

    return {"success": True, "stock_item": result.data[0]}


class BulkStockRequest(BaseModel):
    product_id: str
    items: List[str]  # List of credentials (login:pass or invite links)
    expires_at: Optional[str] = None
    supplier_id: Optional[str] = None


@app.post("/api/admin/stock/bulk")
async def admin_add_stock_bulk(request: BulkStockRequest, admin = Depends(verify_admin)):
    """Bulk add stock items for a product (for supplier uploads)"""
    db = get_database()

    # Verify product exists
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create stock items
    items_data = []
    for content in request.items:
        content = content.strip()
        if not content:
            continue

        item = {
            "product_id": request.product_id,
            "content": content,
            "is_sold": False
        }
        if request.expires_at:
            item["expires_at"] = request.expires_at
        if request.supplier_id:
            item["supplier_id"] = request.supplier_id

        items_data.append(item)

    if not items_data:
        raise HTTPException(status_code=400, detail="No valid items provided")

    result = db.client.table("stock_items").insert(items_data).execute()

    # Notify waitlist users
    await _notify_waitlist_for_product(product.name)

    return {
        "success": True,
        "added_count": len(result.data),
        "product_name": product.name
    }


async def _notify_waitlist_for_product(product_name: str, product_id: Optional[str] = None):
    """
    Notify users on waitlist when product becomes available again.
    
    When a discontinued product becomes 'active' again, notify waitlist users
    that they can order prepaid or get instantly if in stock.
    """
    db = get_database()

    # Get waitlist users for this product
    waitlist = db.client.table("waitlist").select(
        "id,user_id,users(telegram_id,language_code)"
    ).ilike("product_name", f"%{product_name}%").execute()

    if not waitlist.data:
        return

    # Check if product is in stock
    in_stock = False
    if product_id:
        product = await db.get_product_by_id(product_id)
        if product:
            in_stock = product.stock_count > 0

    from src.services.notifications import NotificationService
    notification_service = NotificationService()

    for item in waitlist.data:
        user = item.get("users")
        if user:
            await notification_service.send_waitlist_notification(
                telegram_id=user["telegram_id"],
                product_name=product_name,
                language=user.get("language_code", "en"),
                product_id=product_id,
                in_stock=in_stock
            )

            # Remove from waitlist
            db.client.table("waitlist").delete().eq("id", item["id"]).execute()


@app.get("/api/admin/stock")
async def admin_get_stock(
    product_id: Optional[str] = None,
    available_only: bool = True,
    admin = Depends(verify_admin)
):
    """Get stock items"""
    db = get_database()

    # Create query inside lambda to avoid context issues
    def execute_query():
        query = db.client.table("stock_items").select(
            "*, products(name)"
        ).order("created_at", desc=True)

        if product_id:
            query = query.eq("product_id", product_id)
        if available_only:
            query = query.eq("is_sold", False)

        return query.execute()

    result = await asyncio.to_thread(execute_query)
    return {"stock": result.data if result.data else []}


@app.post("/api/admin/broadcast")
async def admin_broadcast(request: BroadcastRequest, admin = Depends(verify_admin)):
    """Send broadcast message to all users"""
    from src.services.notifications import NotificationService

    notification_service = NotificationService()
    sent_count = await notification_service.send_broadcast(
        message=request.message,
        exclude_dnd=request.exclude_dnd
    )

    return {"success": True, "sent_count": sent_count}


@app.get("/api/admin/analytics")
async def admin_get_analytics(
    days: int = 7,
    admin = Depends(verify_admin)
):
    """Get sales analytics"""
    from datetime import datetime, timedelta

    db = get_database()

    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    start_iso = start_date.isoformat()

    # Get orders in period - create query inside lambda
    def get_orders():
        return db.client.table("orders").select(
            "amount, status, created_at, products(name)"
        ).gte("created_at", start_iso).execute()

    orders_result = await asyncio.to_thread(get_orders)

    # Calculate metrics
    orders_data = orders_result.data if orders_result.data else []
    total_orders = len(orders_data)
    completed_orders = [o for o in orders_data if o.get("status") in ["delivered", "completed"]]
    total_revenue = sum(o.get("amount", 0) for o in completed_orders)
    avg_order_value = total_revenue / len(completed_orders) if completed_orders else 0

    # Get top products
    product_counts = {}
    for o in orders_data:
        if o.get("products") and isinstance(o["products"], dict):
            product_name = o["products"].get("name", "Unknown")
            product_counts[product_name] = product_counts.get(product_name, 0) + 1

    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "period_days": days,
        "total_orders": total_orders,
        "completed_orders": len(completed_orders),
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "conversion_rate": len(completed_orders) / total_orders * 100 if total_orders > 0 else 0,
        "top_products": [{"name": name, "count": count} for name, count in top_products]
    }


@app.get("/api/admin/tickets")
async def admin_get_tickets(
    status: str = "open",
    admin = Depends(verify_admin)
):
    """Get support tickets"""
    db = get_database()

    def execute_query():
        return db.client.table("tickets").select(
            "*, users(telegram_id, username), orders(id, product_id)"
        ).eq("status", status).order("created_at", desc=True).execute()

    result = await asyncio.to_thread(execute_query)
    return {"tickets": result.data if result.data else []}


@app.post("/api/admin/tickets/{ticket_id}/resolve")
async def admin_resolve_ticket(
    ticket_id: str,
    approve: bool = True,
    admin = Depends(verify_admin)
):
    """Resolve a support ticket"""
    db = get_database()

    # Update ticket status
    status = "approved" if approve else "rejected"
    db.client.table("tickets").update({
        "status": status,
        "resolved_at": datetime.utcnow().isoformat()
    }).eq("id", ticket_id).execute()

    # If approved replacement, handle it
    if approve:
        # Get ticket details
        ticket = db.client.table("tickets").select("*").eq("id", ticket_id).execute()
        if ticket.data:
            # TODO: Implement replacement logic
            pass

    return {"success": True, "status": status}


# ==================== REVIEWS API ====================

class SubmitReviewRequest(BaseModel):
    order_id: str
    rating: int  # 1-5
    text: Optional[str] = None


@app.post("/api/reviews")
async def submit_review(
    request: SubmitReviewRequest,
    user = Depends(verify_telegram_auth)
):
    """Submit product review with 5% cashback"""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get order
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status != "completed":
        raise HTTPException(status_code=400, detail="Order not completed")

    # Check if review already exists
    existing = db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Review already submitted")

    # Create review
    await db.create_review(
        user_id=db_user.id,
        order_id=request.order_id,
        product_id=order.product_id,
        rating=request.rating,
        text=request.text
    )

    # Calculate 5% cashback
    cashback = order.amount * 0.05
    await db.update_user_balance(db_user.id, cashback)

    # Mark cashback as given
    db.client.table("reviews").update({
        "cashback_given": True
    }).eq("order_id", request.order_id).execute()

    return {
        "success": True,
        "cashback": cashback,
        "new_balance": db_user.balance + cashback
    }


# ==================== CRON JOBS (Vercel Cron) ====================

@app.get("/api/cron/review-requests")
async def cron_review_requests(authorization: str = Header(None)):
    """
    Send review requests for orders completed 1 hour ago.
    Called by Vercel Cron every 15 minutes.
    """
    # Verify cron secret
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    db = get_database()

    # Get orders completed ~1 hour ago (between 45-75 minutes)
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=75)
    end_time = now - timedelta(minutes=45)

    orders = db.client.table("orders").select("id").eq(
        "status", "completed"
    ).gte("delivered_at", start_time.isoformat()).lte(
        "delivered_at", end_time.isoformat()
    ).execute()

    from src.services.notifications import NotificationService
    notification_service = NotificationService()

    sent_count = 0
    for order in orders.data:
        # Check if review already exists
        existing = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
        if not existing.data:
            await notification_service.send_review_request(order["id"])
            sent_count += 1

    return {"sent": sent_count}


@app.get("/api/cron/expiration-reminders")
async def cron_expiration_reminders(authorization: str = Header(None)):
    """
    Send reminders for subscriptions expiring in 3 days.
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    db = get_database()

    # Get orders expiring in 3 days
    orders = await db.get_expiring_orders(days_before=3)

    from src.services.notifications import NotificationService
    notification_service = NotificationService()

    sent_count = 0
    for order in orders:
        # Get user and product info
        user_result = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("id", order.user_id).execute()

        product = await db.get_product_by_id(order.product_id)

        if user_result.data and product:
            user = user_result.data[0]
            days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0

            await notification_service.send_expiration_reminder(
                telegram_id=user["telegram_id"],
                product_name=product.name,
                days_left=days_left,
                language=user.get("language_code", "en")
            )
            sent_count += 1

    return {"sent": sent_count}


@app.get("/api/cron/wishlist-reminders")
async def cron_wishlist_reminders(authorization: str = Header(None)):
    """
    Send reminders for items in wishlist for 3+ days.
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    db = get_database()

    # Get wishlist items older than 3 days that haven't been reminded
    cutoff = datetime.utcnow() - timedelta(days=3)

    items = db.client.table("wishlist").select(
        "id,user_id,product_id,products(name,stock_count:stock_items(count))"
    ).eq("reminded", False).lt("created_at", cutoff.isoformat()).execute()

    from src.services.notifications import NotificationService
    notification_service = NotificationService()

    sent_count = 0
    for item in items.data:
        # Get user
        user_result = db.client.table("users").select(
            "telegram_id,language_code,do_not_disturb"
        ).eq("id", item["user_id"]).execute()

        if not user_result.data:
            continue

        user = user_result.data[0]
        if user.get("do_not_disturb"):
            continue

        product_name = item.get("products", {}).get("name", "Product")

        from src.i18n import get_text
        message = get_text(
            "wishlist_reminder",
            user.get("language_code", "en"),
            product=product_name
        )

        bot = notification_service._get_bot()
        if bot:
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=message)

                # Mark as reminded
                db.client.table("wishlist").update({
                    "reminded": True
                }).eq("id", item["id"]).execute()

                sent_count += 1
            except Exception as e:
                print(f"Failed to send wishlist reminder: {e}")

    return {"sent": sent_count}


@app.get("/api/cron/re-engagement")
async def cron_re_engagement(authorization: str = Header(None)):
    """
    Send re-engagement messages to inactive users (7+ days).
    Called by Vercel Cron daily.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    db = get_database()

    # Get users inactive for 7+ days
    cutoff = datetime.utcnow() - timedelta(days=7)

    users = db.client.table("users").select(
        "telegram_id,language_code"
    ).eq("is_banned", False).eq("do_not_disturb", False).lt(
        "last_activity_at", cutoff.isoformat()
    ).limit(50).execute()

    from src.services.notifications import NotificationService
    notification_service = NotificationService()
    bot = notification_service._get_bot()

    if not bot:
        return {"sent": 0}

    sent_count = 0
    for user in users.data:
        lang = user.get("language_code", "en")

        # Personalized re-engagement message
        message = {
            "ru": "👋 Давно не виделись! У нас появились новые предложения. Может, поможем найти что-то интересное?",
            "en": "👋 Long time no see! We have new offers. Can we help you find something interesting?",
        }.get(lang, "👋 Long time no see! We have new offers. Can we help you find something interesting?")

        try:
            await bot.send_message(chat_id=user["telegram_id"], text=message)
            sent_count += 1
        except Exception:
            pass  # User may have blocked the bot

    return {"sent": sent_count}


@app.get("/api/cron/daily-tasks")
async def cron_daily_tasks(authorization: str = Header(None)):
    """
    Combined daily cron job for Hobby plan (max 2 crons, once per day).
    Runs ALL scheduled tasks:
    - Review requests (orders completed yesterday)
    - Expiration reminders (subscriptions expiring in 3 days)
    - Wishlist reminders (items saved 3+ days ago)
    - Re-engagement (users inactive 7+ days)
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    results = {
        "review_requests": 0,
        "expiration_reminders": 0,
        "wishlist_reminders": 0,
        "re_engagement": 0,
        "rag_indexed": 0
    }

    from src.services.notifications import NotificationService
    notification_service = NotificationService()
    db = get_database()
    bot = notification_service._get_bot()

    # -1. Index products for RAG (semantic search)
    try:
        from core.rag import get_product_search
        search = get_product_search()
        if search.is_available:
            indexed = await search.index_all_products()
            results["rag_indexed"] = indexed
    except Exception as e:
        print(f"RAG indexing error: {e}")

    if not bot:
        return {"error": "Bot not configured", "results": results}

    # 0. Review requests (orders completed yesterday)
    try:
        yesterday_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)

        orders = db.client.table("orders").select("id").eq(
            "status", "completed"
        ).gte("delivered_at", yesterday_start.isoformat()).lt(
            "delivered_at", yesterday_end.isoformat()
        ).is_("review_requested_at", "null").execute()

        for order in orders.data:
            existing_review = db.client.table("reviews").select("id").eq("order_id", order["id"]).execute()
            if not existing_review.data:
                await notification_service.send_review_request(order["id"])
                db.client.table("orders").update(
                    {"review_requested_at": datetime.utcnow().isoformat()}
                ).eq("id", order["id"]).execute()
                results["review_requests"] += 1
    except Exception as e:
        print(f"Review requests error: {e}")

    # 1. Expiration reminders (subscriptions expiring in 3 days)
    try:
        orders = await db.get_expiring_orders(days_before=3)
        for order in orders:
            user_result = db.client.table("users").select(
                "telegram_id,language_code"
            ).eq("id", order.user_id).execute()
            product = await db.get_product_by_id(order.product_id)

            if user_result.data and product:
                user = user_result.data[0]
                days_left = (order.expires_at - datetime.utcnow()).days if order.expires_at else 0
                await notification_service.send_expiration_reminder(
                    telegram_id=user["telegram_id"],
                    product_name=product.name,
                    days_left=days_left,
                    language=user.get("language_code", "en")
                )
                results["expiration_reminders"] += 1
    except Exception as e:
        print(f"Expiration reminders error: {e}")

    # 2. Wishlist reminders (items saved 3+ days ago)
    try:
        from src.i18n import get_text
        cutoff = datetime.utcnow() - timedelta(days=3)
        items = db.client.table("wishlist").select(
            "id,user_id,products(name)"
        ).eq("reminded", False).lt("created_at", cutoff.isoformat()).limit(20).execute()

        for item in items.data:
            user_result = db.client.table("users").select(
                "telegram_id,language_code,do_not_disturb"
            ).eq("id", item["user_id"]).execute()

            if user_result.data and not user_result.data[0].get("do_not_disturb"):
                user = user_result.data[0]
                try:
                    msg = get_text("wishlist_reminder", user.get("language_code", "en"),
                                  product=item.get("products", {}).get("name", "Product"))
                    await bot.send_message(chat_id=user["telegram_id"], text=msg)
                    db.client.table("wishlist").update({"reminded": True}).eq("id", item["id"]).execute()
                    results["wishlist_reminders"] += 1
                except Exception:
                    pass
    except Exception as e:
        print(f"Wishlist reminders error: {e}")

    # 3. Re-engagement (users inactive 7+ days)
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        users = db.client.table("users").select(
            "telegram_id,language_code"
        ).eq("is_banned", False).eq("do_not_disturb", False).lt(
            "last_activity_at", cutoff.isoformat()
        ).limit(30).execute()

        for user in users.data:
            lang = user.get("language_code", "en")
            msg = {
                "ru": "👋 Давно не виделись! У нас появились новые предложения.",
                "en": "👋 Long time no see! We have new offers."
            }.get(lang, "👋 Long time no see! We have new offers.")
            try:
                await bot.send_message(chat_id=user["telegram_id"], text=msg)
                results["re_engagement"] += 1
            except Exception:
                pass
    except Exception as e:
        print(f"Re-engagement error: {e}")

    return results


# ==================== QSTASH WORKERS ====================

@app.post("/api/workers/deliver-goods")
async def worker_deliver_goods(request: Request):
    """
    QStash Worker: Deliver digital goods after payment.
    Called by QStash with guaranteed delivery.
    """
    from core.queue import verify_qstash_request
    from src.services.notifications import NotificationService

    data = await verify_qstash_request(request)
    order_id = data.get("order_id")

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()
    notification_service = NotificationService()

    # Complete purchase via RPC
    result = db.client.rpc("complete_purchase", {"p_order_id": order_id}).execute()

    if result.data and result.data[0].get("success"):
        content = result.data[0].get("content")

        # Get order details
        order = db.client.table("orders").select(
            "user_telegram_id, products(name)"
        ).eq("id", order_id).single().execute()

        if order.data:
            await notification_service.send_delivery(
                telegram_id=order.data["user_telegram_id"],
                product_name=order.data.get("products", {}).get("name", "Product"),
                content=content
            )

        return {"success": True, "order_id": order_id}

    return {"error": "Failed to complete purchase", "order_id": order_id}


@app.post("/api/workers/calculate-referral")
async def worker_calculate_referral(request: Request):
    """
    QStash Worker: Calculate and apply referral bonuses.
    """
    from core.queue import verify_qstash_request

    data = await verify_qstash_request(request)
    order_id = data.get("order_id")

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()

    # Get order with user referral info
    order = db.client.table("orders").select(
        "amount, user_id, users(referrer_id)"
    ).eq("id", order_id).single().execute()

    if not order.data:
        return {"error": "Order not found"}

    referrer_id = order.data.get("users", {}).get("referrer_id")
    if not referrer_id:
        return {"skipped": True, "reason": "No referrer"}

    # Calculate 5% bonus
    bonus = float(order.data["amount"]) * 0.05

    # Add to referrer balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": referrer_id,
        "p_amount": bonus,
        "p_reason": f"Referral bonus from order {order_id}"
    }).execute()

    return {"success": True, "referrer_id": referrer_id, "bonus": bonus}


@app.post("/api/workers/notify-supplier")
async def worker_notify_supplier(request: Request):
    """
    QStash Worker: Notify supplier about low stock.
    """
    from core.queue import verify_qstash_request

    data = await verify_qstash_request(request)
    product_id = data.get("product_id")
    threshold = data.get("threshold", 3)

    if not product_id:
        return {"error": "product_id required"}

    db = get_database()

    # Check current stock
    stock = db.client.table("stock_items").select("id").eq(
        "product_id", product_id
    ).eq("status", "available").execute()

    if len(stock.data) <= threshold:
        # Log low stock alert (in production, send to admin)
        print(f"LOW STOCK ALERT: Product {product_id} has only {len(stock.data)} items")
        return {"alerted": True, "stock_count": len(stock.data)}

    return {"skipped": True, "stock_count": len(stock.data)}


@app.post("/api/workers/process-refund")
async def worker_process_refund(request: Request):
    """
    QStash Worker: Process refund for prepaid orders.
    """
    from core.queue import verify_qstash_request
    from src.services.notifications import NotificationService

    data = await verify_qstash_request(request)
    order_id = data.get("order_id")
    reason = data.get("reason", "Fulfillment deadline exceeded")

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()
    notification_service = NotificationService()

    # Get order
    order = db.client.table("orders").select(
        "id, amount, user_id, user_telegram_id, status, products(name)"
    ).eq("id", order_id).single().execute()

    if not order.data:
        return {"error": "Order not found"}

    if order.data["status"] != "prepaid":
        return {"skipped": True, "reason": f"Order status is {order.data['status']}"}

    # Refund to balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": order.data["user_id"],
        "p_amount": float(order.data["amount"]),
        "p_reason": f"Refund for order {order_id}: {reason}"
    }).execute()

    # Update order
    db.client.table("orders").update({
        "status": "refunded",
        "refund_reason": reason,
        "refund_processed_at": datetime.utcnow().isoformat()
    }).eq("id", order_id).execute()

    # Notify user
    await notification_service.send_refund_notification(
        telegram_id=order.data["user_telegram_id"],
        product_name=order.data.get("products", {}).get("name", "Product"),
        amount=order.data["amount"],
        reason=reason
    )

    return {"success": True, "refunded_amount": order.data["amount"]}


@app.post("/api/workers/process-review-cashback")
async def worker_process_review_cashback(request: Request):
    """
    QStash Worker: Process 5% cashback for review.
    """
    from core.queue import verify_qstash_request

    data = await verify_qstash_request(request)
    review_id = data.get("review_id")

    if not review_id:
        return {"error": "review_id required"}

    db = get_database()

    # Get review with order info
    review = db.client.table("reviews").select(
        "id, order_id, cashback_processed, orders(amount, user_id)"
    ).eq("id", review_id).single().execute()

    if not review.data:
        return {"error": "Review not found"}

    if review.data.get("cashback_processed"):
        return {"skipped": True, "reason": "Cashback already processed"}

    order = review.data.get("orders", {})
    if not order:
        return {"error": "Order not found"}

    # Calculate 5% cashback
    cashback = float(order["amount"]) * 0.05

    # Add to user balance
    db.client.rpc("add_to_user_balance", {
        "p_user_id": order["user_id"],
        "p_amount": cashback,
        "p_reason": "Review cashback for order"
    }).execute()

    # Mark as processed
    db.client.table("reviews").update({
        "cashback_processed": True
    }).eq("id", review_id).execute()

    return {"success": True, "cashback": cashback}


# ==================== ADMIN ENDPOINTS ====================

@app.post("/api/admin/index-products")
async def admin_index_products(authorization: str = Header(None)):
    """
    Admin endpoint: Index all products for RAG (semantic search).
    Requires CRON_SECRET for authentication.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from core.rag import get_product_search
        search = get_product_search()

        if not search.is_available:
            return {"success": False, "error": "RAG not available"}

        indexed = await search.index_all_products()
        return {"success": True, "indexed_products": indexed}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app when 'app' variable is present
# No need to export handler - FastAPI is auto-detected
