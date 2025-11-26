"""
PVNDORA AI Marketplace - Main FastAPI Application

Single entry point for all webhooks and API routes.
Optimized for Vercel Hobby plan (max 12 serverless functions).
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
from src.utils.validators import validate_telegram_init_data, extract_user_from_init_data


# ==================== BOT INITIALIZATION ====================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://pvndora-ai-shop.vercel.app")

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
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    import traceback
    
    try:
        # Get bot and dispatcher
        bot_instance = get_bot()
        dispatcher = get_dispatcher()
        
        if not bot_instance:
            print("ERROR: Bot instance is None - TELEGRAM_TOKEN may be missing")
            return JSONResponse(
                status_code=500,
                content={"error": "Bot not configured"}
            )
        
        # Parse update
        try:
            data = await request.json()
            print(f"DEBUG: Received update: {data.get('update_id', 'unknown')}")
        except Exception as e:
            print(f"ERROR: Failed to parse JSON: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid JSON: {str(e)}"}
            )
        
        # Validate update
        try:
            update = Update.model_validate(data, context={"bot": bot_instance})
            print(f"DEBUG: Update validated, type: {update.event_type if hasattr(update, 'event_type') else 'unknown'}")
        except Exception as e:
            print(f"ERROR: Failed to validate update: {e}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid update: {str(e)}"}
            )
        
        # Process update - use process_update for better error handling
        try:
            await dispatcher.feed_update(bot_instance, update)
            print(f"DEBUG: Update processed successfully")
        except Exception as e:
            print(f"ERROR: Failed to process update: {e}")
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            # Still return 200 to Telegram to avoid retries
            return JSONResponse(content={"ok": True, "error": str(e)})
        
        return JSONResponse(content={"ok": True})
    
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Webhook exception: {error_msg}")
        print(f"ERROR: Traceback: {error_trace}")
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )


# ==================== AUTHENTICATION ====================

async def verify_telegram_auth(authorization: str = Header(None)):
    """Verify Telegram Mini App authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    
    # Parse "tma <initData>"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "tma":
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    init_data = parts[1]
    
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


# ==================== ORDERS API ====================

class CreateOrderRequest(BaseModel):
    product_id: str
    promo_code: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


@app.post("/api/orders")
async def create_order(
    request: CreateOrderRequest,
    user = Depends(verify_telegram_auth)
):
    """Create new order and get payment URL"""
    db = get_database()
    
    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get product
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.stock_count == 0:
        raise HTTPException(status_code=400, detail="Product out of stock")
    
    # Calculate price with potential discount
    original_price = product.price
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
    
    # Determine payment method based on language
    payment_method = "aaio" if db_user.language_code in ["ru", "uk", "be", "kk"] else "stripe"
    
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
    from src.services.payments import PaymentService
    payment_service = PaymentService()
    
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
    from src.services.notifications import NotificationService
    
    try:
        data = await request.form()
        
        payment_service = PaymentService()
        result = await payment_service.verify_aaio_callback(dict(data))
        
        if result["success"]:
            order_id = result["order_id"]
            
            # Process fulfillment
            notification_service = NotificationService()
            await notification_service.fulfill_order(order_id)
        
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
    from src.services.notifications import NotificationService
    
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        payment_service = PaymentService()
        result = await payment_service.verify_stripe_webhook(payload, sig_header)
        
        if result["success"]:
            order_id = result["order_id"]
            
            # Process fulfillment
            notification_service = NotificationService()
            await notification_service.fulfill_order(order_id)
        
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
        "referral_percent": db_user.personal_ref_percent
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


# ==================== FAQ API ====================

@app.get("/api/faq")
async def get_faq(lang: str = "en"):
    """Get FAQ entries"""
    db = get_database()
    faq = await db.get_faq(lang)
    return faq


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


@app.get("/api/admin/orders")
async def admin_get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin = Depends(verify_admin)
):
    """Get all orders with optional filtering"""
    db = get_database()
    
    query = db.client.table("orders").select(
        "*, users(telegram_id, username, first_name), products(name)"
    ).order("created_at", desc=True).range(offset, offset + limit - 1)
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    return result.data


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


async def _notify_waitlist_for_product(product_name: str):
    """Notify users on waitlist when product becomes available"""
    db = get_database()
    
    # Get waitlist users for this product
    waitlist = db.client.table("waitlist").select(
        "id,user_id,users(telegram_id,language_code)"
    ).ilike("product_name", f"%{product_name}%").execute()
    
    if not waitlist.data:
        return
    
    from src.services.notifications import NotificationService
    notification_service = NotificationService()
    
    for item in waitlist.data:
        user = item.get("users")
        if user:
            await notification_service.send_waitlist_notification(
                telegram_id=user["telegram_id"],
                product_name=product_name,
                language=user.get("language_code", "en")
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
    
    query = db.client.table("stock_items").select(
        "*, products(name)"
    ).order("created_at", desc=True)
    
    if product_id:
        query = query.eq("product_id", product_id)
    if available_only:
        query = query.eq("is_sold", False)
    
    result = query.execute()
    return result.data


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
    
    # Get orders in period
    orders_result = db.client.table("orders").select(
        "amount, status, created_at"
    ).gte("created_at", start_date.isoformat()).execute()
    
    # Calculate metrics
    total_orders = len(orders_result.data)
    completed_orders = [o for o in orders_result.data if o["status"] == "completed"]
    total_revenue = sum(o["amount"] for o in completed_orders)
    
    # Get event counts
    events_result = db.client.table("analytics_events").select(
        "event_type", count="exact"
    ).gte("timestamp", start_date.isoformat()).execute()
    
    # Get new users
    users_result = db.client.table("users").select(
        "id", count="exact"
    ).gte("created_at", start_date.isoformat()).execute()
    
    return {
        "period_days": days,
        "total_orders": total_orders,
        "completed_orders": len(completed_orders),
        "total_revenue": total_revenue,
        "conversion_rate": len(completed_orders) / total_orders * 100 if total_orders > 0 else 0,
        "new_users": users_result.count or 0,
        "events": events_result.count or 0
    }


@app.get("/api/admin/tickets")
async def admin_get_tickets(
    status: str = "open",
    admin = Depends(verify_admin)
):
    """Get support tickets"""
    db = get_database()
    
    result = db.client.table("tickets").select(
        "*, users(telegram_id, username), orders(id, product_id)"
    ).eq("status", status).order("created_at", desc=True).execute()
    
    return result.data


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
    
    from src.i18n import get_text
    
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
    Combined daily cron job for Hobby plan (max 2 crons).
    Runs: expiration reminders, wishlist reminders, re-engagement.
    """
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    
    results = {
        "expiration_reminders": 0,
        "wishlist_reminders": 0,
        "re_engagement": 0
    }
    
    from src.services.notifications import NotificationService
    notification_service = NotificationService()
    db = get_database()
    bot = notification_service._get_bot()
    
    if not bot:
        return {"error": "Bot not configured", "results": results}
    
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
                except:
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
            except:
                pass
    except Exception as e:
        print(f"Re-engagement error: {e}")
    
    return results


# ==================== VERCEL EXPORT ====================
# Vercel automatically detects FastAPI app, but we can also export explicitly
handler = app
