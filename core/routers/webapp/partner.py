"""
WebApp Partner Router

Partner dashboard and application endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends

from pydantic import BaseModel
from typing import Optional

from core.logging import get_logger
from core.services.database import get_database
from core.services.money import to_float
from core.auth import verify_telegram_auth
from .models import PartnerApplicationRequest

logger = get_logger(__name__)


class PartnerModeRequest(BaseModel):
    mode: str  # 'commission' or 'discount'
    discount_percent: Optional[int] = 15

router = APIRouter(tags=["webapp-partner"])


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
    
    # Check if user is a partner (from referral_stats_extended view)
    try:
        extended_stats_result = await db.client.table("referral_stats_extended").select(
            "is_partner"
        ).eq("user_id", db_user.id).limit(1).execute()
        
        is_partner = False
        if extended_stats_result.data and len(extended_stats_result.data) > 0:
            is_partner = extended_stats_result.data[0].get("is_partner", False) or False
        
        if not is_partner:
            raise HTTPException(status_code=403, detail="Partner access required")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check partner status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify partner status")
    
    # Get partner analytics from view
    try:
        analytics_result = await db.client.table("partner_analytics").select("*").eq(
            "user_id", db_user.id
        ).execute()
        analytics = analytics_result.data[0] if analytics_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to query partner_analytics: {e}")
        analytics = {}
    
    # Get direct referrals with their purchase info
    try:
        referrals_result = await db.client.from_("users").select(
            "id, telegram_id, username, first_name, created_at"
        ).eq("referrer_id", db_user.id).order("created_at", desc=True).limit(50).execute()
        
        # Enrich with purchase data
        referrals = []
        for ref in (referrals_result.data or []):
            orders_result = await db.client.table("orders").select(
                "amount, status, created_at"
            ).eq("user_id", ref["id"]).eq("status", "delivered").execute()
            orders = orders_result.data or []
            total_spent = sum(to_float(o.get("amount", 0)) for o in orders)
            
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
        logger.warning(f"Failed to query referrals: {e}")
        referrals = []
    
    # Get earnings history (last 7 days)
    try:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        earnings_result = await db.client.table("referral_bonuses").select(
            "amount, level, created_at"
        ).eq("user_id", db_user.id).eq("eligible", True).gte(
            "created_at", seven_days_ago
        ).order("created_at", desc=True).execute()
        
        # Group by day
        daily_earnings = defaultdict(float)
        for bonus in (earnings_result.data or []):
            day = bonus.get("created_at", "")[:10]  # YYYY-MM-DD
            daily_earnings[day] += to_float(bonus.get("amount", 0))
        
        earnings_history = [
            {"date": day, "amount": amount} 
            for day, amount in sorted(daily_earnings.items(), reverse=True)
        ]
    except Exception as e:
        logger.warning(f"Failed to query earnings history: {e}")
        earnings_history = []
    
    # Get top purchased products by referrals
    try:
        top_products_result = await db.client.rpc("get_partner_top_products", {
            "p_partner_id": str(db_user.id),
            "p_limit": 5
        }).execute()
        top_products = top_products_result.data or []
    except Exception as e:
        logger.warning(f"get_partner_top_products RPC not available: {e}")
        top_products = []
    
    # Calculate summary
    total_referrals = len(referrals)
    paying_referrals = sum(1 for r in referrals if r.get("is_paying"))
    conversion_rate = (paying_referrals / total_referrals * 100) if total_referrals > 0 else 0
    
    # Get partner mode
    partner_mode = getattr(db_user, 'partner_mode', 'commission') or 'commission'
    partner_discount_percent = getattr(db_user, 'partner_discount_percent', 0) or 0
    
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
        "referral_link": f"https://t.me/pvndora_ai_bot?start=ref_{user.id}",
        "partner_mode": partner_mode,
        "partner_discount_percent": partner_discount_percent
    }


@router.post("/partner/mode")
async def set_partner_mode(request: PartnerModeRequest, user=Depends(verify_telegram_auth)):
    """
    Toggle partner mode between commission and discount.
    
    In discount mode:
    - Partner gives up commission earnings
    - Their level 1 referrals get a discount (default 15%) on all purchases
    
    In commission mode:
    - Partner receives commission on referral purchases
    - Referrals pay normal prices
    """
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is a partner (from referral_stats_extended view)
    try:
        extended_stats_result = await db.client.table("referral_stats_extended").select(
            "is_partner"
        ).eq("user_id", db_user.id).limit(1).execute()
        
        is_partner = False
        if extended_stats_result.data and len(extended_stats_result.data) > 0:
            is_partner = extended_stats_result.data[0].get("is_partner", False) or False
        
        if not is_partner:
            raise HTTPException(status_code=403, detail="Partner access required")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check partner status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify partner status")
    
    # Validate mode
    if request.mode not in ['commission', 'discount']:
        raise HTTPException(status_code=400, detail="Mode must be 'commission' or 'discount'")
    
    # Validate discount percent
    discount_percent = 0
    if request.mode == 'discount':
        discount_percent = min(max(request.discount_percent or 15, 5), 25)  # 5-25% range
    
    # Update user
    try:
        result = await db.client.table("users").update({
            "partner_mode": request.mode,
            "partner_discount_percent": discount_percent
        }).eq("id", db_user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update partner mode")
        
        return {
            "success": True,
            "mode": request.mode,
            "discount_percent": discount_percent,
            "message": "Режим скидок активирован" if request.mode == 'discount' else "Режим комиссий активирован"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update partner mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update partner mode")


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
    
    # Check if already a partner (from referral_stats_extended view)
    try:
        extended_stats_result = await db.client.table("referral_stats_extended").select(
            "is_partner"
        ).eq("user_id", db_user.id).limit(1).execute()
        
        is_partner = False
        if extended_stats_result.data and len(extended_stats_result.data) > 0:
            is_partner = extended_stats_result.data[0].get("is_partner", False) or False
        
        if is_partner:
            raise HTTPException(status_code=400, detail="You are already a partner")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to check partner status: {e}")
    
    # Check for existing pending application
    existing = await db.client.table("partner_applications").select(
        "id, status"
    ).eq("user_id", db_user.id).eq("status", "pending").execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="You already have a pending application")
    
    # Insert application
    result = await db.client.table("partner_applications").insert({
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
    
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create application")
    
    application_id = result.data[0]["id"]
    
    # Send admin alert (best-effort)
    try:
        from core.services.admin_alerts import get_admin_alert_service
        alert_service = get_admin_alert_service()
        await alert_service.alert_new_partner_application(
            user_telegram_id=user.id,
            username=getattr(user, 'username', None),
            source=request.source,
            audience_size=request.audience_size
        )
    except Exception as e:
        logger.warning(f"Failed to send admin alert for partner application: {e}")
    
    return {
        "success": True,
        "message": "Application submitted successfully",
        "application_id": application_id
    }


@router.get("/partner/application-status")
async def get_partner_application_status(user=Depends(verify_telegram_auth)):
    """Get status of user's partner application."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already partner (from referral_stats_extended view)
    try:
        extended_stats_result = await db.client.table("referral_stats_extended").select(
            "is_partner"
        ).eq("user_id", db_user.id).limit(1).execute()
        
        is_partner = False
        if extended_stats_result.data and len(extended_stats_result.data) > 0:
            is_partner = extended_stats_result.data[0].get("is_partner", False) or False
        
        if is_partner:
            return {
                "is_partner": True,
                "application": None,
                "message": "You are already a partner"
            }
    except Exception as e:
        logger.warning(f"Failed to check partner status: {e}")
    
    # Get latest application
    result = await db.client.table("partner_applications").select(
        "id, status, created_at, admin_comment, reviewed_at"
    ).eq("user_id", db_user.id).order("created_at", desc=True).limit(1).execute()
    
    application = result.data[0] if result.data else None
    
    return {
        "is_partner": False,
        "application": application,
        "can_apply": application is None or application.get("status") in ["rejected"]
    }
