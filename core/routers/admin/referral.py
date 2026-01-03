"""
Admin Referral Router

Referral program settings, metrics, partners management, and applications.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from core.logging import get_logger
from core.services.database import get_database
from core.services.money import to_float
from core.auth import verify_admin
from .models import ReferralSettingsRequest, SetPartnerRequest, ReviewApplicationRequest

logger = get_logger(__name__)

router = APIRouter(tags=["admin-referral"])


# ==================== REFERRAL SETTINGS ====================

@router.get("/referral/settings")
async def admin_get_referral_settings(admin=Depends(verify_admin)):
    """Get current referral program settings"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("referral_settings").select("*").limit(1).execute()
    )
    
    if not result.data or len(result.data) == 0:
        return {
            "settings": {
                "level1_threshold_usd": 0,
                "level2_threshold_usd": 250,
                "level3_threshold_usd": 1000,
                "level1_commission_percent": 10,
                "level2_commission_percent": 7,
                "level3_commission_percent": 3
            }
        }
    
    return {"settings": result.data[0]}


@router.put("/referral/settings")
async def admin_update_referral_settings(request: ReferralSettingsRequest, admin=Depends(verify_admin)):
    """Update referral program settings (thresholds and commissions)"""
    db = get_database()
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if request.level2_threshold_usd is not None:
        if request.level2_threshold_usd < 0:
            raise HTTPException(status_code=400, detail="Threshold must be >= 0")
        update_data["level2_threshold_usd"] = request.level2_threshold_usd
        
    if request.level3_threshold_usd is not None:
        if request.level3_threshold_usd < 0:
            raise HTTPException(status_code=400, detail="Threshold must be >= 0")
        update_data["level3_threshold_usd"] = request.level3_threshold_usd
        
    if request.level1_commission_percent is not None:
        if not 0 <= request.level1_commission_percent <= 100:
            raise HTTPException(status_code=400, detail="Commission must be 0-100%")
        update_data["level1_commission_percent"] = request.level1_commission_percent
        
    if request.level2_commission_percent is not None:
        if not 0 <= request.level2_commission_percent <= 100:
            raise HTTPException(status_code=400, detail="Commission must be 0-100%")
        update_data["level2_commission_percent"] = request.level2_commission_percent
        
    if request.level3_commission_percent is not None:
        if not 0 <= request.level3_commission_percent <= 100:
            raise HTTPException(status_code=400, detail="Commission must be 0-100%")
        update_data["level3_commission_percent"] = request.level3_commission_percent
    
    await asyncio.to_thread(
        lambda: db.client.table("referral_settings").update(update_data).eq(
            "id", "00000000-0000-0000-0000-000000000001"
        ).execute()
    )
    
    return {"success": True, "updated": update_data}


# ==================== REFERRAL METRICS ====================

@router.get("/metrics/referral")
async def admin_get_referral_metrics(admin=Depends(verify_admin)):
    """Get detailed referral program metrics"""
    db = get_database()
    
    try:
        stats = await asyncio.to_thread(
            lambda: db.client.table("referral_program_metrics").select("*").single().execute()
        )
    except Exception as e:
        logger.warning(f"Failed to query referral_program_metrics: {e}")
        stats = type('obj', (object,), {'data': None})()
    
    try:
        top_referrers = await asyncio.to_thread(
            lambda: db.client.table("referral_stats_extended").select("*").order("total_referral_earnings", desc=True).limit(20).execute()
        )
    except Exception as e:
        logger.warning(f"Failed to query referral_stats_extended: {e}")
        top_referrers = type('obj', (object,), {'data': []})()
    
    return {
        "overview": stats.data if stats.data else {},
        "top_referrers": top_referrers.data or []
    }


# ==================== REFERRAL DASHBOARD (ROI + CRM) ====================

@router.get("/referral/dashboard")
async def admin_get_referral_dashboard(admin=Depends(verify_admin)):
    """
    ROI Dashboard - key metrics for referral channel effectiveness.
    """
    db = get_database()
    
    try:
        roi_result = await asyncio.to_thread(
            lambda: db.client.table("referral_roi_dashboard").select("*").execute()
        )
        roi = roi_result.data[0] if roi_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to query referral_roi_dashboard: {e}")
        roi = {}
    
    try:
        settings_result = await asyncio.to_thread(
            lambda: db.client.table("referral_settings").select("*").limit(1).execute()
        )
        settings = settings_result.data[0] if settings_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to query referral_settings: {e}")
        settings = {}
    
    return {
        "roi": {
            "total_referral_revenue": float(roi.get("total_referral_revenue", 0)),
            "total_payouts": float(roi.get("total_payouts", 0)),
            "revoked_payouts": float(roi.get("revoked_payouts", 0)),
            "net_profit": float(roi.get("net_profit", 0)),
            "margin_percent": float(roi.get("margin_percent", 100)),
        },
        "partners": {
            "active": roi.get("active_partners", 0),
            "total": roi.get("total_partners", 0),
            "vip": roi.get("vip_partners", 0)
        },
        "settings": {
            "level1_threshold": float(settings.get("level1_threshold_usd", 0)),
            "level2_threshold": float(settings.get("level2_threshold_usd", 250)),
            "level3_threshold": float(settings.get("level3_threshold_usd", 1000)),
            "level1_commission": float(settings.get("level1_commission_percent", 20)),
            "level2_commission": float(settings.get("level2_commission_percent", 10)),
            "level3_commission": float(settings.get("level3_commission_percent", 5))
        }
    }


@router.get("/referral/partners-crm")
async def admin_get_partners_crm(
    sort_by: str = "referral_revenue",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    partner_type: str = "all",
    admin=Depends(verify_admin)
):
    """CRM table with full partner analytics."""
    db = get_database()
    
    try:
        valid_sorts = ["referral_revenue", "total_earned", "total_referrals", "paying_referrals", "conversion_rate", "joined_at"]
        if sort_by not in valid_sorts:
            sort_by = "referral_revenue"
        
        if partner_type == "business":
            view_name = "business_partners_analytics"
        elif partner_type == "referral":
            view_name = "referral_program_partners_analytics"
        else:
            view_name = "partner_analytics"
        
        try:
            await asyncio.to_thread(
                lambda: db.client.table(view_name).select("user_id").limit(1).execute()
            )
        except Exception as view_error:
            error_msg = str(view_error)
            if "relation" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise HTTPException(
                    status_code=500, 
                    detail=f"View '{view_name}' not found. Please apply migration."
                )
            raise
        
        result = await asyncio.to_thread(
            lambda: db.client.table(view_name).select("*").order(
                sort_by, desc=(sort_order == "desc")
            ).range(offset, offset + limit - 1).execute()
        )
        
        count_result = await asyncio.to_thread(
            lambda: db.client.table(view_name).select("user_id", count="exact").execute()
        )
        
        partners = []
        for p in (result.data or []):
            partner_data = {
                "user_id": p.get("user_id"),
                "telegram_id": p.get("telegram_id"),
                "username": p.get("username"),
                "first_name": p.get("first_name"),
                "status": "VIP" if p.get("is_partner") else "Regular",
                "effective_level": p.get("effective_level", 0),
                "joined_at": p.get("joined_at"),
                "total_referrals": p.get("total_referrals", 0),
                "paying_referrals": p.get("paying_referrals", 0),
                "conversion_rate": float(p.get("conversion_rate", 0)),
                "referral_revenue": float(p.get("referral_revenue", 0)),
                "total_earned": float(p.get("total_earned", 0)),
                "current_balance": float(p.get("current_balance", 0)),
                "level1_referrals": p.get("level1_referrals", 0),
                "level2_referrals": p.get("level2_referrals", 0),
                "level3_referrals": p.get("level3_referrals", 0),
            }
            partners.append(partner_data)
        
        return {
            "partners": partners,
            "total": count_result.count or 0,
            "limit": limit,
            "offset": offset
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query partner_analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load partners.")


@router.get("/referral-metrics")
async def admin_get_referral_metrics_detailed(admin=Depends(verify_admin)):
    """Get comprehensive referral program metrics (detailed version)"""
    db = get_database()
    
    try:
        metrics_result = await asyncio.to_thread(
            lambda: db.client.table("referral_program_metrics").select("*").execute()
        )
        metrics = metrics_result.data[0] if metrics_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to query referral_program_metrics: {e}")
        metrics = {}
    
    top_earners = await asyncio.to_thread(
        lambda: db.client.table("users").select(
            "id, telegram_id, username, first_name, total_referral_earnings, turnover_usd, is_partner"
        ).gt("total_referral_earnings", 0).order("total_referral_earnings", desc=True).limit(20).execute()
    )
    
    pending_bonuses = await asyncio.to_thread(
        lambda: db.client.table("referral_bonuses").select(
            "amount, level, ineligible_reason"
        ).eq("eligible", False).execute()
    )
    
    pending_by_level = {"level1": 0, "level2": 0, "level3": 0}
    for bonus in (pending_bonuses.data or []):
        level_key = f"level{bonus.get('level', 1)}"
        pending_by_level[level_key] += to_float(bonus.get("amount", 0))
    
    return {
        "overview": {
            "total_active_users": metrics.get("total_active_users", 0),
            "total_partners": metrics.get("total_partners", 0),
            "level1_users": metrics.get("level1_users", 0),
            "level2_users": metrics.get("level2_users", 0),
            "level3_users": metrics.get("level3_users", 0),
            "total_paid_bonuses": to_float(metrics.get("total_paid_bonuses", 0)),
            "total_revoked_bonuses": to_float(metrics.get("total_revoked_bonuses", 0)),
            "total_network_turnover_usd": to_float(metrics.get("total_network_turnover_usd", 0))
        },
        "pending_by_level": pending_by_level,
        "top_earners": top_earners.data or [],
        "thresholds_usd": {
            "level1": 50,
            "level2": 250,
            "level3": 1000
        }
    }


# ==================== PARTNERS MANAGEMENT ====================

@router.get("/partners")
async def admin_get_partners(admin=Depends(verify_admin)):
    """Get all partners (VIP referrers)"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("users").select(
            "id, telegram_id, username, first_name, is_partner, partner_level_override, "
            "turnover_usd, referral_program_unlocked, total_referral_earnings, balance, "
            "level1_unlocked_at, level2_unlocked_at, level3_unlocked_at, created_at"
        ).eq("is_partner", True).order("total_referral_earnings", desc=True).execute()
    )
    
    partners = []
    for p in (result.data or []):
        try:
            stats_result = await asyncio.to_thread(
                lambda uid=p["id"]: db.client.table("referral_stats_extended").select(
                    "level1_count, level2_count, level3_count, effective_level"
                ).eq("user_id", uid).execute()
            )
            stats = stats_result.data[0] if stats_result.data else {}
        except Exception as e:
            logger.warning(f"Failed to query referral_stats_extended for partner {p['id']}: {e}")
            stats = {}
        partners.append({
            **p,
            "referral_counts": {
                "level1": stats.get("level1_count", 0),
                "level2": stats.get("level2_count", 0),
                "level3": stats.get("level3_count", 0)
            },
            "effective_level": stats.get("effective_level", 0)
        })
    
    return {"partners": partners, "count": len(partners)}


@router.post("/partners/set")
async def admin_set_partner(request: SetPartnerRequest, admin=Depends(verify_admin)):
    """Set user as partner and optionally force-unlock referral levels."""
    db = get_database()
    
    user_result = await asyncio.to_thread(
        lambda: db.client.table("users").select("id, username").eq(
            "telegram_id", request.telegram_id
        ).single().execute()
    )
    
    if not user_result.data:
        raise HTTPException(status_code=404, detail=f"User with telegram_id {request.telegram_id} not found")
    
    user_id = user_result.data["id"]
    
    result = await asyncio.to_thread(
        lambda: db.client.rpc("admin_set_partner_level", {
            "p_user_id": user_id,
            "p_level": request.level_override if request.level_override is not None else 0,
            "p_is_partner": request.is_partner
        }).execute()
    )
    
    rpc_result = result.data
    if isinstance(rpc_result, list):
        rpc_result = rpc_result[0] if rpc_result else {}
    
    if rpc_result and rpc_result.get("success"):
        return {
            "success": True,
            "user_id": user_id,
            "username": user_result.data.get("username"),
            "is_partner": request.is_partner,
            "level_override": request.level_override
        }
    
    error_msg = rpc_result.get("error", "Failed to update partner status") if rpc_result else "No response from database"
    raise HTTPException(status_code=500, detail=error_msg)


# ==================== PARTNER APPLICATIONS ====================

@router.get("/partner-applications")
async def admin_get_partner_applications(
    status: str = "pending",
    admin=Depends(verify_admin)
):
    """Get partner applications with filtering."""
    db = get_database()
    
    query = db.client.table("partner_applications").select("*")
    
    if status != "all":
        query = query.eq("status", status)
    
    result = await asyncio.to_thread(
        lambda: query.order("created_at", desc=True).execute()
    )
    
    return {
        "applications": result.data or [],
        "count": len(result.data or [])
    }


@router.post("/partner-applications/review")
async def admin_review_application(request: ReviewApplicationRequest, admin=Depends(verify_admin)):
    """Review (approve/reject) a partner application."""
    db = get_database()
    
    app_result = await asyncio.to_thread(
        lambda: db.client.table("partner_applications").select(
            "id, user_id, status"
        ).eq("id", request.application_id).single().execute()
    )
    
    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if app_result.data["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already reviewed")
    
    user_id = app_result.data["user_id"]
    new_status = "approved" if request.approve else "rejected"
    
    admin_id = str(admin.id) if admin and admin.id else None
    if not admin_id:
        raise HTTPException(status_code=500, detail="Admin ID not available")
    
    await asyncio.to_thread(
        lambda: db.client.table("partner_applications").update({
            "status": new_status,
            "admin_comment": request.admin_comment,
            "reviewed_by": admin_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", request.application_id).execute()
    )
    
    if request.approve:
        await asyncio.to_thread(
            lambda: db.client.rpc("admin_set_partner_level", {
                "p_user_id": user_id,
                "p_level": request.level_override,
                "p_is_partner": True
            }).execute()
        )
    
    return {
        "success": True,
        "application_id": request.application_id,
        "new_status": new_status,
        "user_id": user_id
    }
