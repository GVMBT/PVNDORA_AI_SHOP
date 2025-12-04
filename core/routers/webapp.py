"""
WebApp API Router

Mini App endpoints for Telegram WebApp frontend.
Requires Telegram initData authentication for user-specific endpoints.
"""
import os
import hmac
import hashlib
import asyncio
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.services.database import get_database
from core.auth import verify_telegram_auth
from core.routers.deps import get_payment_service

router = APIRouter(prefix="/api/webapp", tags=["webapp"])

# Session tokens for web login (in-memory for simplicity, use Redis in production)
_web_sessions = {}


# ==================== PYDANTIC MODELS ====================

class TelegramLoginData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class WithdrawalRequest(BaseModel):
    amount: float
    method: str  # card, phone, crypto
    details: str


class PromoCheckRequest(BaseModel):
    code: str


class WebAppReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: str | None = None


class CreateOrderRequest(BaseModel):
    product_id: str | None = None
    quantity: int | None = 1
    promo_code: str | None = None
    use_cart: bool = False


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


# ==================== WEB AUTH (Telegram Login Widget) ====================

def verify_telegram_login_hash(data: dict, bot_token: str) -> bool:
    """Verify Telegram Login Widget data using HMAC-SHA256."""
    check_hash = data.pop('hash', None)
    if not check_hash:
        return False
    
    # Create data-check-string
    data_items = sorted(data.items())
    data_check_string = '\n'.join(f"{k}={v}" for k, v in data_items if v is not None)
    
    # Create secret key (SHA256 of bot token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, check_hash)


@router.post("/auth/telegram-login")
async def telegram_login_widget_auth(data: TelegramLoginData):
    """
    Authenticate user via Telegram Login Widget (for desktop/web access).
    
    Verifies the hash using bot token and creates a session.
    Only admins can access the web panel.
    """
    bot_token = os.environ.get("TELEGRAM_TOKEN", "")
    
    # Convert to dict for verification
    auth_data = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
        "hash": data.hash
    }
    if data.last_name:
        auth_data["last_name"] = data.last_name
    if data.username:
        auth_data["username"] = data.username
    if data.photo_url:
        auth_data["photo_url"] = data.photo_url
    
    # Verify hash
    if not verify_telegram_login_hash(auth_data.copy(), bot_token):
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    
    # Check auth_date (not older than 1 hour)
    auth_time = datetime.fromtimestamp(data.auth_date, tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_time > timedelta(hours=1):
        raise HTTPException(status_code=401, detail="Authentication data expired")
    
    # Get or create user
    db = get_database()
    db_user = await db.get_user_by_telegram_id(data.id)
    
    if not db_user:
        # Create new user
        db_user = await db.create_user(
            telegram_id=data.id,
            username=data.username,
            first_name=data.first_name,
            language_code="en"
        )
    
    # Check if admin (required for web access)
    if not db_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Web access is only available for administrators. Please use the Telegram Mini App."
        )
    
    # Create session token
    session_token = secrets.token_urlsafe(32)
    _web_sessions[session_token] = {
        "user_id": str(db_user.id),
        "telegram_id": data.id,
        "username": data.username,
        "is_admin": db_user.is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }
    
    return {
        "session_token": session_token,
        "user": {
            "id": data.id,
            "username": data.username,
            "first_name": data.first_name,
            "is_admin": db_user.is_admin
        }
    }


class SessionTokenRequest(BaseModel):
    session_token: str


@router.post("/auth/verify-session")
async def verify_web_session(data: SessionTokenRequest):
    """Verify a web session token."""
    session = _web_sessions.get(data.session_token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _web_sessions[data.session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {
        "valid": True,
        "user": {
            "telegram_id": session["telegram_id"],
            "username": session["username"],
            "is_admin": session["is_admin"]
        }
    }


# ==================== PUBLIC ENDPOINTS ====================

@router.get("/products/{product_id}")
async def get_webapp_product(product_id: str):
    """Get product with discount and social proof for Mini App."""
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("available_stock_with_discounts").select("*").eq("product_id", product_id).limit(1).execute()
    )
    
    discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
    rating_info = await db.get_product_rating(product_id)
    
    original_price = float(product.price)
    final_price = original_price * (1 - discount_percent / 100)
    fulfillment_time_hours = getattr(product, 'fulfillment_time_hours', 48)
    
    return {
        "product": {
            "id": product.id, "name": product.name, "description": product.description,
            "original_price": original_price, "price": original_price,
            "discount_percent": discount_percent, "final_price": round(final_price, 2),
            "warranty_days": product.warranty_hours // 24 if hasattr(product, 'warranty_hours') else 1,
            "duration_days": getattr(product, 'duration_days', None),
            "available_count": product.stock_count, "available": product.stock_count > 0,
            "can_fulfill_on_demand": product.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours if product.status == 'active' else None,
            "type": product.type, "instructions": product.instructions,
            "rating": rating_info["average"], "reviews_count": rating_info["count"]
        }
    }


@router.get("/products")
async def get_webapp_products():
    """Get all active products for Mini App catalog."""
    db = get_database()
    products = await db.get_products(status="active")
    
    result = []
    for p in products:
        stock_result = await asyncio.to_thread(
            lambda pid=p.id: db.client.table("available_stock_with_discounts").select("*").eq("product_id", pid).limit(1).execute()
        )
        discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
        rating_info = await db.get_product_rating(p.id)
        
        original_price = float(p.price)
        final_price = original_price * (1 - discount_percent / 100)
        
        result.append({
            "id": p.id, "name": p.name, "description": p.description,
            "original_price": original_price, "price": original_price,
            "discount_percent": discount_percent, "final_price": round(final_price, 2),
            "available_count": p.stock_count, "available": p.stock_count > 0,
            "can_fulfill_on_demand": p.status == 'active',
            "type": p.type, "rating": rating_info["average"], "reviews_count": rating_info["count"]
        })
    
    return {"products": result, "count": len(result)}


# ==================== AUTH REQUIRED ENDPOINTS ====================

@router.get("/orders")
async def get_webapp_orders(user=Depends(verify_telegram_auth)):
    """Get user's order history."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.get_user_orders(db_user.id, limit=50)
    
    result = []
    for o in orders:
        product = await db.get_product_by_id(o.product_id)
        result.append({
            "id": o.id, "product_id": o.product_id,
            "product_name": product.name if product else "Unknown Product",
            "amount": o.amount, "original_price": o.original_price,
            "discount_percent": o.discount_percent, "status": o.status,
            "order_type": getattr(o, 'order_type', 'instant'),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivered_at": o.delivered_at.isoformat() if hasattr(o, 'delivered_at') and o.delivered_at else None,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "warranty_until": o.warranty_until.isoformat() if hasattr(o, 'warranty_until') and o.warranty_until else None
        })
    
    return {"orders": result, "count": len(result)}


@router.get("/faq")
async def get_webapp_faq(language_code: str = "en", user=Depends(verify_telegram_auth)):
    """Get FAQ entries grouped by category."""
    db = get_database()
    faq_entries = await db.get_faq(language_code)
    
    categories = {}
    for entry in faq_entries:
        category = entry.get("category", "general")
        if category not in categories:
            categories[category] = []
        categories[category].append({"question": entry["question"], "answer": entry["answer"]})
    
    return {"categories": categories, "total": len(faq_entries)}


@router.get("/profile")
async def get_webapp_profile(user=Depends(verify_telegram_auth)):
    """Get user profile with referral stats, balance, and history."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Загружаем динамические настройки из БД
    try:
        settings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        settings = settings_result.data[0] if settings_result.data and len(settings_result.data) > 0 else {}
    except Exception as e:
        print(f"ERROR: Failed to load referral_settings: {e}")
        settings = {}
    
    # Пороги разблокировки уровней в USD (из настроек)
    # Level 1 is instant (threshold = 0), so we don't need THRESHOLD_LEVEL1
    THRESHOLD_LEVEL2 = float(settings.get("level2_threshold_usd", 250) or 250)
    THRESHOLD_LEVEL3 = float(settings.get("level3_threshold_usd", 1000) or 1000)
    
    # Комиссии
    COMMISSION_LEVEL1 = float(settings.get("level1_commission_percent", 20) or 20)
    COMMISSION_LEVEL2 = float(settings.get("level2_commission_percent", 10) or 10)
    COMMISSION_LEVEL3 = float(settings.get("level3_commission_percent", 5) or 5)
    
    # Get extended referral stats from view
    try:
        extended_stats_result = await asyncio.to_thread(
            lambda: db.client.table("referral_stats_extended").select("*").eq("user_id", db_user.id).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query referral_stats_extended: {e}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        extended_stats_result = type('obj', (object,), {'data': []})()
    
    # Initialize with default values
    referral_stats = {
        "level1_count": 0, "level2_count": 0, "level3_count": 0,
        "level1_earnings": 0, "level2_earnings": 0, "level3_earnings": 0,
        "active_referrals": 0
    }
    referral_program = {
        "unlocked": False,
        "status": "locked",
        "is_partner": False,
        "effective_level": 0,
        "level1_unlocked": False,
        "level2_unlocked": False,
        "level3_unlocked": False,
        "turnover_usd": 0,
        "amount_to_level2_usd": THRESHOLD_LEVEL2,
        "amount_to_level3_usd": THRESHOLD_LEVEL3,
        "amount_to_next_level_usd": THRESHOLD_LEVEL2,
        "next_threshold_usd": THRESHOLD_LEVEL2,
        "thresholds_usd": {
            "level2": THRESHOLD_LEVEL2,
            "level3": THRESHOLD_LEVEL3
        },
        "commissions_percent": {
            "level1": COMMISSION_LEVEL1,
            "level2": COMMISSION_LEVEL2,
            "level3": COMMISSION_LEVEL3
        },
        "level1_unlocked_at": None,
        "level2_unlocked_at": None,
        "level3_unlocked_at": None,
    }
    
    if extended_stats_result.data and len(extended_stats_result.data) > 0:
        s = extended_stats_result.data[0]
        
        # Referral network counts (always counted, even if level locked)
        referral_stats = {
            "level1_count": s.get("level1_count", 0),
            "level2_count": s.get("level2_count", 0),
            "level3_count": s.get("level3_count", 0),
            "level1_earnings": float(s.get("level1_earnings") or 0) if s.get("level1_earnings") is not None else 0,
            "level2_earnings": float(s.get("level2_earnings") or 0) if s.get("level2_earnings") is not None else 0,
            "level3_earnings": float(s.get("level3_earnings") or 0) if s.get("level3_earnings") is not None else 0,
            "active_referrals": s.get("active_referrals_count", 0),
        }
        
        # Core program data from view
        unlocked = s.get("referral_program_unlocked", False)
        is_partner = s.get("is_partner", False)
        partner_override = s.get("partner_level_override")
        turnover_usd = float(s.get("turnover_usd") or 0) if s.get("turnover_usd") is not None else 0
        
        # Эффективный уровень (Level 1 = мгновенно после покупки!)
        if is_partner and partner_override is not None:
            effective_level = partner_override
        elif not unlocked:
            effective_level = 0
        elif turnover_usd >= THRESHOLD_LEVEL3:
            effective_level = 3
        elif turnover_usd >= THRESHOLD_LEVEL2:
            effective_level = 2
        elif unlocked:  # Level 1 даётся СРАЗУ при активации
            effective_level = 1
        else:
            effective_level = 0
        
        # Статус (упрощённый: locked или active)
        status = "locked" if not unlocked else "active"
        
        # Calculate level thresholds
        level1_unlocked = effective_level >= 1
        level2_unlocked = effective_level >= 2
        level3_unlocked = effective_level >= 3
        
        # Amount to each threshold (Level 1 = 0, так как мгновенный)
        amount_to_level2 = max(0, THRESHOLD_LEVEL2 - turnover_usd) if not level2_unlocked else 0
        amount_to_level3 = max(0, THRESHOLD_LEVEL3 - turnover_usd) if not level3_unlocked else 0
        
        # Next threshold to reach (теперь стартуем с Level 2!)
        if not level2_unlocked:
            next_threshold = THRESHOLD_LEVEL2
            amount_to_next = amount_to_level2
        elif not level3_unlocked:
            next_threshold = THRESHOLD_LEVEL3
            amount_to_next = amount_to_level3
        else:
            next_threshold = None
            amount_to_next = 0
        
        referral_program = {
            # Basic status
            "unlocked": unlocked,  # Program activated (first purchase made)
            "status": status,  # "locked" | "active" (pre_level removed!)
            "is_partner": is_partner,
            
            # Levels unlock state (Level 1 = instant!)
            "effective_level": effective_level,
            "level1_unlocked": level1_unlocked,
            "level2_unlocked": level2_unlocked,
            "level3_unlocked": level3_unlocked,
            
            # Turnover & progress (in USD)
            "turnover_usd": turnover_usd,
            "amount_to_level2_usd": amount_to_level2,
            "amount_to_level3_usd": amount_to_level3,
            "amount_to_next_level_usd": amount_to_next,
            "next_threshold_usd": next_threshold,
            
            # Thresholds and commissions (dynamic from settings)
            "thresholds_usd": {
                "level2": THRESHOLD_LEVEL2,
                "level3": THRESHOLD_LEVEL3
            },
            "commissions_percent": {
                "level1": COMMISSION_LEVEL1,
                "level2": COMMISSION_LEVEL2,
                "level3": COMMISSION_LEVEL3
            },
            
            # Unlock timestamps
            "level1_unlocked_at": s.get("level1_unlocked_at"),
            "level2_unlocked_at": s.get("level2_unlocked_at"),
            "level3_unlocked_at": s.get("level3_unlocked_at"),
        }
    else:
        # Fallback for users not in view
        referral_stats = {
            "level1_count": 0, "level2_count": 0, "level3_count": 0,
            "level1_earnings": 0, "level2_earnings": 0, "level3_earnings": 0,
            "active_referrals": 0
        }
        referral_program = {
            "unlocked": False,
            "status": "locked",
            "is_partner": False,
            "effective_level": 0,
            "level1_unlocked": False,
            "level2_unlocked": False,
            "level3_unlocked": False,
            "turnover_usd": 0,
            "amount_to_level2_usd": THRESHOLD_LEVEL2,
            "amount_to_level3_usd": THRESHOLD_LEVEL3,
            "amount_to_next_level_usd": THRESHOLD_LEVEL2,  # Level 1 instant, so next is Level 2
            "next_threshold_usd": THRESHOLD_LEVEL2,
            "thresholds_usd": {
                "level2": THRESHOLD_LEVEL2,
                "level3": THRESHOLD_LEVEL3
            },
            "commissions_percent": {
                "level1": COMMISSION_LEVEL1,
                "level2": COMMISSION_LEVEL2,
                "level3": COMMISSION_LEVEL3
            },
            "level1_unlocked_at": None,
            "level2_unlocked_at": None,
            "level3_unlocked_at": None,
        }
    
    try:
        bonus_result = await asyncio.to_thread(
            lambda: db.client.table("referral_bonuses").select("*").eq("user_id", db_user.id).eq("eligible", True).order("created_at", desc=True).limit(10).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query referral_bonuses: {e}")
        bonus_result = type('obj', (object,), {'data': []})()
    
    try:
        withdrawal_result = await asyncio.to_thread(
            lambda: db.client.table("withdrawal_requests").select("*").eq("user_id", db_user.id).order("created_at", desc=True).limit(10).execute()
        )
    except Exception as e:
        print(f"ERROR: Failed to query withdrawal_requests: {e}")
        withdrawal_result = type('obj', (object,), {'data': []})()
    
    return {
        "profile": {
            "balance": float(db_user.balance) if db_user.balance else 0,
            "total_referral_earnings": float(db_user.total_referral_earnings) if hasattr(db_user, 'total_referral_earnings') and db_user.total_referral_earnings else 0,
            "total_saved": float(db_user.total_saved) if db_user.total_saved else 0,
            "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "is_admin": db_user.is_admin or False,
            "is_partner": referral_program.get("is_partner", False)  # VIP partner flag
        },
        "referral_program": referral_program,
        "referral_stats": referral_stats,
        "bonus_history": bonus_result.data or [],
        "withdrawals": withdrawal_result.data or []
    }


@router.get("/partner/dashboard")
async def get_partner_dashboard(user=Depends(verify_telegram_auth)):
    """
    Partner Dashboard - extended analytics for VIP partners (is_partner=true).
    
    Returns:
    - summary: key metrics (balance, total earned, conversion %, referral count)
    - referrals: detailed list of direct referrals with purchase history
    - earnings_history: daily/weekly earnings breakdown
    - top_products: most purchased products by referrals
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is a partner
    is_partner = getattr(db_user, 'is_partner', False)
    if not is_partner:
        raise HTTPException(status_code=403, detail="Partner access required")
    
    # Get partner analytics from view
    try:
        analytics_result = await asyncio.to_thread(
            lambda: db.client.table("partner_analytics").select("*").eq("user_id", db_user.id).execute()
        )
        analytics = analytics_result.data[0] if analytics_result.data else {}
    except Exception as e:
        print(f"ERROR: Failed to query partner_analytics: {e}")
        analytics = {}
    
    # Get direct referrals with their purchase info
    try:
        referrals_result = await asyncio.to_thread(
            lambda: db.client.from_("users").select(
                "id, telegram_id, username, first_name, created_at"
            ).eq("referrer_id", db_user.id).order("created_at", desc=True).limit(50).execute()
        )
        
        # Enrich with purchase data
        referrals = []
        for ref in (referrals_result.data or []):
            # Get orders for this referral
            orders_result = await asyncio.to_thread(
                lambda rid=ref["id"]: db.client.table("orders").select(
                    "amount, status, created_at"
                ).eq("user_id", rid).eq("status", "completed").execute()
            )
            orders = orders_result.data or []
            total_spent = sum(float(o.get("amount", 0)) for o in orders)
            
            referrals.append({
                "telegram_id": ref.get("telegram_id"),
                "username": ref.get("username"),
                "first_name": ref.get("first_name"),
                "joined_at": ref.get("created_at"),
                "orders_count": len(orders),
                "total_spent": total_spent,
                "is_paying": len(orders) > 0
            })
    except Exception as e:
        print(f"ERROR: Failed to query referrals: {e}")
        referrals = []
    
    # Get earnings history (last 7 days)
    try:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        earnings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_bonuses").select(
                "amount, level, created_at"
            ).eq("user_id", db_user.id).eq("eligible", True).gte(
                "created_at", seven_days_ago
            ).order("created_at", desc=True).execute()
        )
        
        # Group by day
        from collections import defaultdict
        daily_earnings = defaultdict(float)
        for bonus in (earnings_result.data or []):
            day = bonus.get("created_at", "")[:10]  # YYYY-MM-DD
            daily_earnings[day] += float(bonus.get("amount", 0))
        
        earnings_history = [
            {"date": day, "amount": amount} 
            for day, amount in sorted(daily_earnings.items(), reverse=True)
        ]
    except Exception as e:
        print(f"ERROR: Failed to query earnings history: {e}")
        earnings_history = []
    
    # Get top purchased products by referrals
    try:
        top_products_result = await asyncio.to_thread(
            lambda: db.client.rpc("get_partner_top_products", {
                "p_partner_id": str(db_user.id),
                "p_limit": 5
            }).execute()
        )
        top_products = top_products_result.data or []
    except Exception as e:
        # Fallback - RPC might not exist yet
        print(f"WARNING: get_partner_top_products RPC not available: {e}")
        top_products = []
    
    # Calculate summary
    total_referrals = len(referrals)
    paying_referrals = sum(1 for r in referrals if r.get("is_paying"))
    conversion_rate = (paying_referrals / total_referrals * 100) if total_referrals > 0 else 0
    
    return {
        "summary": {
            "balance": float(db_user.balance) if db_user.balance else 0,
            "total_earned": float(db_user.total_referral_earnings) if hasattr(db_user, 'total_referral_earnings') and db_user.total_referral_earnings else 0,
            "total_referrals": total_referrals,
            "paying_referrals": paying_referrals,
            "conversion_rate": round(conversion_rate, 1),
            "effective_level": analytics.get("effective_level", 3),
            "referral_revenue": float(analytics.get("referral_revenue", 0) or 0)
        },
        "referrals": referrals,
        "earnings_history": earnings_history,
        "top_products": top_products,
        "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}"
    }


# ==================== PARTNER APPLICATION ====================

class PartnerApplicationRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    source: str  # instagram, youtube, telegram_channel, website, other
    audience_size: str  # 1k-10k, 10k-50k, 50k-100k, 100k+
    description: str  # Why they want partnership
    expected_volume: str | None = None  # Expected monthly volume
    social_links: dict | None = None  # {instagram: url, youtube: url, ...}


@router.post("/partner/apply")
async def submit_partner_application(request: PartnerApplicationRequest, user=Depends(verify_telegram_auth)):
    """
    Submit application to become a VIP partner.
    
    Required fields:
    - source: Where your audience is (instagram, youtube, telegram_channel, website, other)
    - audience_size: Size of your audience (1k-10k, 10k-50k, 50k-100k, 100k+)
    - description: Why you want to become a partner
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a partner
    if getattr(db_user, 'is_partner', False):
        raise HTTPException(status_code=400, detail="You are already a partner")
    
    # Check for existing pending application
    existing = await asyncio.to_thread(
        lambda: db.client.table("partner_applications").select("id, status").eq(
            "user_id", db_user.id
        ).eq("status", "pending").execute()
    )
    
    if existing.data:
        raise HTTPException(status_code=400, detail="You already have a pending application")
    
    # Insert application
    result = await asyncio.to_thread(
        lambda: db.client.table("partner_applications").insert({
            "user_id": str(db_user.id),
            "telegram_id": user.id,
            "username": getattr(user, 'username', None),
            "email": request.email,
            "phone": request.phone,
            "source": request.source,
            "audience_size": request.audience_size,
            "description": request.description,
            "expected_volume": request.expected_volume,
            "social_links": request.social_links or {},
            "status": "pending"
        }).execute()
    )
    
    # Verify insert succeeded
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create application")
    
    return {
        "success": True,
        "message": "Application submitted successfully",
        "application_id": result.data[0]["id"]
    }


@router.get("/partner/application-status")
async def get_partner_application_status(user=Depends(verify_telegram_auth)):
    """Get status of user's partner application."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already partner
    is_partner = getattr(db_user, 'is_partner', False)
    if is_partner:
        return {
            "is_partner": True,
            "application": None,
            "message": "You are already a partner"
        }
    
    # Get latest application
    result = await asyncio.to_thread(
        lambda: db.client.table("partner_applications").select(
            "id, status, created_at, admin_comment, reviewed_at"
        ).eq("user_id", db_user.id).order("created_at", desc=True).limit(1).execute()
    )
    
    application = result.data[0] if result.data else None
    
    return {
        "is_partner": False,
        "application": application,
        "can_apply": application is None or application.get("status") in ["rejected"]
    }


@router.post("/profile/withdraw")
async def request_withdrawal(request: WithdrawalRequest, user=Depends(verify_telegram_auth)):
    """Request balance withdrawal."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    MIN_WITHDRAWAL = 500
    balance = float(db_user.balance) if db_user.balance else 0
    
    if request.amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is {MIN_WITHDRAWAL}₽")
    if request.amount > balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    if request.method not in ['card', 'phone', 'crypto']:
        raise HTTPException(status_code=400, detail="Invalid payment method")
    
    await asyncio.to_thread(
        lambda: db.client.table("withdrawal_requests").insert({
            "user_id": db_user.id, "amount": request.amount,
            "payment_method": request.method, "payment_details": {"details": request.details}
        }).execute()
    )
    
    await asyncio.to_thread(
        lambda: db.client.table("users").update({"balance": balance - request.amount}).eq("id", db_user.id).execute()
    )
    
    return {"success": True, "message": "Withdrawal request submitted"}


@router.get("/cart")
async def get_webapp_cart(user=Depends(verify_telegram_auth)):
    """Get user's shopping cart."""
    from core.cart import get_cart_manager
    
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        if not cart:
            return {"cart": None, "items": [], "total": 0.0, "subtotal": 0.0,
                    "instant_total": 0.0, "prepaid_total": 0.0, "promo_code": None, "promo_discount_percent": 0.0}
        
        db = get_database()
        items_with_details = []
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            items_with_details.append({
                "product_id": item.product_id, "product_name": product.name if product else "Unknown",
                "quantity": item.quantity, "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity, "unit_price": item.unit_price,
                "final_price": item.final_price, "total_price": item.total_price, "discount_percent": item.discount_percent
            })
        
        return {
            "cart": {"user_telegram_id": cart.user_telegram_id, "created_at": cart.created_at, "updated_at": cart.updated_at},
            "items": items_with_details, "total": cart.total, "subtotal": cart.subtotal,
            "instant_total": cart.instant_total, "prepaid_total": cart.prepaid_total,
            "promo_code": cart.promo_code, "promo_discount_percent": cart.promo_discount_percent
        }
    except Exception as e:
        print(f"ERROR: Failed to get cart: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {str(e)}")


@router.post("/promo/check")
async def check_webapp_promo(request: PromoCheckRequest, user=Depends(verify_telegram_auth)):
    """Check if promo code is valid."""
    db = get_database()
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)
    
    if promo:
        return {
            "valid": True, "code": code, "discount_percent": promo["discount_percent"],
            "expires_at": promo.get("expires_at"),
            "usage_remaining": (promo.get("usage_limit") or 999) - (promo.get("usage_count") or 0)
        }
    return {"valid": False, "code": code, "message": "Invalid or expired promo code"}


@router.post("/reviews")
async def submit_webapp_review(request: WebAppReviewRequest, user=Depends(verify_telegram_auth)):
    """Submit a product review. Awards 5% cashback."""
    db = get_database()
    
    if not 1 <= request.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    order = await db.get_order_by_id(request.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != db_user.id:
        raise HTTPException(status_code=403, detail="Order does not belong to user")
    if order.status not in ["completed", "delivered"]:
        raise HTTPException(status_code=400, detail="Can only review completed orders")
    
    existing = await asyncio.to_thread(
        lambda: db.client.table("reviews").select("id").eq("order_id", request.order_id).execute()
    )
    if existing.data:
        raise HTTPException(status_code=400, detail="Order already reviewed")
    
    result = await asyncio.to_thread(
        lambda: db.client.table("reviews").insert({
            "user_id": db_user.id, "order_id": request.order_id, "product_id": order.product_id,
            "rating": request.rating, "text": request.text, "cashback_given": False
        }).execute()
    )
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create review")
    
    review_id = result.data[0]["id"]
    cashback_amount = float(order.amount) * 0.05
    await asyncio.to_thread(
        lambda: db.client.table("users").update({"balance": db_user.balance + cashback_amount}).eq("id", db_user.id).execute()
    )
    await asyncio.to_thread(
        lambda: db.client.table("reviews").update({"cashback_given": True}).eq("id", review_id).execute()
    )
    
    return {"success": True, "review_id": review_id, "cashback_awarded": round(cashback_amount, 2),
            "new_balance": round(float(db_user.balance) + cashback_amount, 2)}


@router.get("/leaderboard")
async def get_webapp_leaderboard(period: str = "all", user=Depends(verify_telegram_auth)):
    """Get savings leaderboard. Supports period: all, month, week"""
    db = get_database()
    LEADERBOARD_SIZE = 25
    now = datetime.now(timezone.utc)
    
    date_filter = None
    if period == "week":
        date_filter = (now - timedelta(days=7)).isoformat()
    elif period == "month":
        date_filter = (now - timedelta(days=30)).isoformat()
    
    if date_filter:
        orders_result = await asyncio.to_thread(
            lambda: db.client.table("orders").select(
                "user_id,amount,original_price,users(telegram_id,username,first_name)"
            ).eq("status", "completed").gte("created_at", date_filter).execute()
        )
        
        user_savings = {}
        for order in (orders_result.data or []):
            uid = order.get("user_id")
            if not uid:
                continue
            orig = float(order.get("original_price") or order.get("amount") or 0)
            paid = float(order.get("amount") or 0)
            saved = max(0, orig - paid)
            
            if uid not in user_savings:
                user_data = order.get("users", {})
                user_savings[uid] = {
                    "telegram_id": user_data.get("telegram_id"),
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "total_saved": 0
                }
            user_savings[uid]["total_saved"] += saved
        
        result_data = sorted(user_savings.values(), key=lambda x: x["total_saved"], reverse=True)[:LEADERBOARD_SIZE]
    else:
        result = await asyncio.to_thread(
            lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved").gt("total_saved", 0).order("total_saved", desc=True).limit(LEADERBOARD_SIZE).execute()
        )
        result_data = result.data or []
        
        if len(result_data) < LEADERBOARD_SIZE:
            fill_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("telegram_id,username,first_name,total_saved").eq("total_saved", 0).order("created_at", desc=True).limit(LEADERBOARD_SIZE - len(result_data)).execute()
            )
            result_data.extend(fill_result.data or [])
    
    total_count = await asyncio.to_thread(lambda: db.client.table("users").select("id", count="exact").execute())
    total_users = total_count.count or 0
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    improved_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select("user_id", count="exact").eq("status", "completed").gte("created_at", today_start.isoformat()).execute()
    )
    improved_today = improved_result.count or 0
    
    db_user = await db.get_user_by_telegram_id(user.id)
    user_rank, user_saved = None, 0
    
    if db_user:
        user_saved = float(db_user.total_saved) if hasattr(db_user, 'total_saved') and db_user.total_saved else 0
        if user_saved > 0:
            rank_result = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").gt("total_saved", user_saved).execute()
            )
            user_rank = (rank_result.count or 0) + 1
        else:
            total_with_savings = await asyncio.to_thread(
                lambda: db.client.table("users").select("id", count="exact").gt("total_saved", 0).execute()
            )
            user_rank = (total_with_savings.count or 0) + 1
    
    leaderboard = []
    for i, entry in enumerate(result_data):
        tg_id = entry.get("telegram_id")
        display_name = entry.get("username") or entry.get("first_name") or (f"User{str(tg_id)[-4:]}" if tg_id else "User")
        if len(display_name) > 3:
            display_name = display_name[:3] + "***"
        
        leaderboard.append({
            "rank": i + 1, "name": display_name, "total_saved": float(entry.get("total_saved", 0)),
            "is_current_user": tg_id == user.id if tg_id else False
        })
    
    return {
        "leaderboard": leaderboard, "user_rank": user_rank, "user_saved": user_saved,
        "total_users": total_users, "improved_today": improved_today
    }


@router.post("/orders")
async def create_webapp_order(request: CreateOrderRequest, user=Depends(verify_telegram_auth)):
    """Create new order from Mini App. Supports both single product and cart-based orders."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cardlink_configured = bool(os.environ.get("CARDLINK_API_TOKEN") and os.environ.get("CARDLINK_SHOP_ID"))
    if cardlink_configured and db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "cardlink"
    elif db_user.language_code in ["ru", "uk", "be", "kk"]:
        payment_method = "aaio"
    else:
        payment_method = "stripe"
    
    payment_service = get_payment_service()
    
    if request.use_cart or (not request.product_id):
        from core.cart import get_cart_manager
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        
        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        total_amount, total_original = 0.0, 0.0
        order_items = []
        
        for item in cart.items:
            product = await db.get_product_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            
            if item.instant_quantity > 0:
                available_stock = await db.get_available_stock_count(item.product_id)
                if available_stock < item.instant_quantity:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")
            
            original_price = product.price * item.quantity
            discount_percent = item.discount_percent
            if cart.promo_code and cart.promo_discount_percent > 0:
                discount_percent = max(discount_percent, cart.promo_discount_percent)
            
            final_price = original_price * (1 - discount_percent / 100)
            total_amount += final_price
            total_original += original_price
            
            order_items.append({
                "product_id": item.product_id, "product_name": product.name,
                "quantity": item.quantity, "amount": final_price,
                "original_price": original_price, "discount_percent": discount_percent
            })
        
        first_item = order_items[0]
        order = await db.create_order(
            user_id=db_user.id, product_id=first_item["product_id"],
            amount=total_amount, original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_method=payment_method
        )
        
        product_names = ", ".join([item["product_name"] for item in order_items[:3]])
        if len(order_items) > 3:
            product_names += f" и еще {len(order_items) - 3}"
        
        payment_url = await payment_service.create_payment(
            order_id=order.id, amount=total_amount, product_name=product_names,
            method=payment_method, user_email=f"{user.id}@telegram.user"
        )
        
        if cart.promo_code:
            await db.use_promo_code(cart.promo_code)
        await cart_manager.clear_cart(user.id)
        
        return OrderResponse(
            order_id=order.id, amount=total_amount, original_price=total_original,
            discount_percent=int((1 - total_amount / total_original) * 100) if total_original > 0 else 0,
            payment_url=payment_url, payment_method=payment_method
        )
    
    else:
        if not request.product_id:
            raise HTTPException(status_code=400, detail="product_id is required")
        
        product = await db.get_product_by_id(request.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        quantity = request.quantity or 1
        available_stock = await db.get_available_stock_count(request.product_id)
        if available_stock < quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock. Available: {available_stock}")
        
        original_price = product.price * quantity
        discount_percent = 0
        
        stock_item = await db.get_available_stock_item(request.product_id)
        if stock_item:
            discount_percent = await db.calculate_discount(stock_item, product)
        
        if request.promo_code:
            promo = await db.validate_promo_code(request.promo_code)
            if promo:
                discount_percent = max(discount_percent, promo["discount_percent"])
        
        final_price = original_price * (1 - discount_percent / 100)
        
        order = await db.create_order(
            user_id=db_user.id, product_id=request.product_id,
            amount=final_price, original_price=original_price,
            discount_percent=discount_percent, payment_method=payment_method
        )
        
        payment_url = await payment_service.create_payment(
            order_id=order.id, amount=final_price, product_name=product.name,
            method=payment_method, user_email=f"{user.id}@telegram.user"
        )
        
        if request.promo_code:
            await db.use_promo_code(request.promo_code)
        
        return OrderResponse(
            order_id=order.id, amount=final_price, original_price=original_price,
            discount_percent=discount_percent, payment_url=payment_url, payment_method=payment_method
        )

