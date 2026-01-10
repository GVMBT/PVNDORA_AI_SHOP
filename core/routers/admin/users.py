"""
Admin Users CRM Router

Extended user analytics and management.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from core.logging import get_logger
from core.services.database import get_database
from core.services.money import to_float
from core.auth import verify_admin
from core.routers.admin.models import UpdateBalanceRequest, UpdateWarningsRequest

logger = get_logger(__name__)

router = APIRouter(tags=["admin-users"])


@router.get("/users")
async def admin_get_users(
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get users for admin panel - simplified view"""
    db = get_database()
    
    try:
        # Get users with order counts
        result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("id, telegram_id, username, first_name, balance, balance_currency, is_banned, is_admin, is_partner, created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        users = []
        for u in (result.data or []):
            user_id = u.get("id")
            
            # Get orders count and total spent
            orders_result = await asyncio.to_thread(
                lambda uid=user_id: db.client.table("orders")
                .select("id, amount", count="exact")
                .eq("user_id", uid)
                .eq("status", "delivered")
                .execute()
            )
            orders_count = orders_result.count or 0
            total_spent = sum(float(o.get("amount", 0)) for o in (orders_result.data or []))
            
            # Determine role
            role = "user"
            if u.get("is_admin"):
                role = "admin"
            elif u.get("is_partner"):
                role = "vip"
            
            users.append({
                "id": user_id,
                "telegram_id": str(u.get("telegram_id", "")),
                "username": u.get("username") or u.get("first_name") or "Unknown",
                "role": role,
                "balance": to_float(u.get("balance", 0)),
                "balance_currency": u.get("balance_currency") or "USD",
                "total_spent": total_spent,
                "orders_count": orders_count,
                "is_banned": u.get("is_banned", False),
                "created_at": u.get("created_at")
            })
        
        return {"users": users}
    except Exception as e:
        logger.error(f"Failed to get users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load users")


@router.get("/users/crm")
async def admin_get_users_crm(
    sort_by: str = "total_orders",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = Query(None, description="Search by username, first_name, or telegram_id"),
    filter_banned: Optional[bool] = Query(None, description="Filter by banned status"),
    filter_partner: Optional[bool] = Query(None, description="Filter by partner status"),
    admin=Depends(verify_admin)
):
    """Get all users with extended analytics (orders, refunds, tickets, etc.)"""
    db = get_database()
    
    try:
        # Build query
        query = db.client.table("users_extended_analytics").select("*")
        
        # Apply search filter
        if search:
            try:
                # Try to search by telegram_id (if search is numeric)
                telegram_id = int(search)
                query = query.or_(f"telegram_id.eq.{telegram_id},username.ilike.%{search}%,first_name.ilike.%{search}%")
            except ValueError:
                # Search by username or first_name
                query = query.or_(f"username.ilike.%{search}%,first_name.ilike.%{search}%")
        
        # Apply filters
        if filter_banned is not None:
            query = query.eq("is_banned", filter_banned)
        if filter_partner is not None:
            query = query.eq("is_partner", filter_partner)
        
        # Validate sort_by
        valid_sorts = [
            "total_orders", "delivered_orders", "refunded_orders", "total_spent",
            "total_tickets", "open_tickets", "total_reviews", "avg_rating",
            "total_referrals", "total_withdrawals", "joined_at", "last_activity_at",
            "balance", "total_referral_earnings", "warnings_count"
        ]
        if sort_by not in valid_sorts:
            sort_by = "total_orders"
        
        # Execute query with sorting and pagination
        result = await asyncio.to_thread(
            lambda: query.order(sort_by, desc=(sort_order == "desc"))
            .range(offset, offset + limit - 1)
            .execute()
        )
        
        # Get total count
        count_query = db.client.table("users_extended_analytics").select("user_id", count="exact")
        if search:
            try:
                telegram_id = int(search)
                count_query = count_query.or_(f"telegram_id.eq.{telegram_id},username.ilike.%{search}%,first_name.ilike.%{search}%")
            except ValueError:
                count_query = count_query.or_(f"username.ilike.%{search}%,first_name.ilike.%{search}%")
        if filter_banned is not None:
            count_query = count_query.eq("is_banned", filter_banned)
        if filter_partner is not None:
            count_query = count_query.eq("is_partner", filter_partner)
        
        count_result = await asyncio.to_thread(
            lambda: count_query.execute()
        )
        
        users = []
        for u in (result.data or []):
            user_data = {
                "user_id": u.get("user_id"),
                "telegram_id": u.get("telegram_id"),
                "username": u.get("username"),
                "first_name": u.get("first_name"),
                "language_code": u.get("language_code"),
                "joined_at": u.get("joined_at"),
                "is_admin": u.get("is_admin", False),
                "is_banned": u.get("is_banned", False),
                "is_partner": u.get("is_partner", False),
                "balance": to_float(u.get("balance", 0)),
                "total_referral_earnings": to_float(u.get("total_referral_earnings", 0)),
                "total_saved": to_float(u.get("total_saved", 0)),
                "warnings_count": u.get("warnings_count", 0),
                "do_not_disturb": u.get("do_not_disturb", False),
                "last_activity_at": u.get("last_activity_at"),
                "referral_program_unlocked": u.get("referral_program_unlocked", False),
                "turnover_usd": to_float(u.get("turnover_usd", 0)),
                "total_purchases_amount": to_float(u.get("total_purchases_amount", 0)),
                
                # Orders metrics
                "total_orders": u.get("total_orders", 0),
                "delivered_orders": u.get("delivered_orders", 0),
                "pending_orders": u.get("pending_orders", 0),
                "paid_orders": u.get("paid_orders", 0),
                "refunded_orders": u.get("refunded_orders", 0),
                "refund_requests": u.get("refund_requests", 0),
                "total_spent": to_float(u.get("total_spent", 0)),
                "total_refunded": to_float(u.get("total_refunded", 0)),
                
                # Tickets metrics
                "total_tickets": u.get("total_tickets", 0),
                "open_tickets": u.get("open_tickets", 0),
                "approved_tickets": u.get("approved_tickets", 0),
                "rejected_tickets": u.get("rejected_tickets", 0),
                "closed_tickets": u.get("closed_tickets", 0),
                
                # Reviews metrics
                "total_reviews": u.get("total_reviews", 0),
                "avg_rating": float(u.get("avg_rating", 0)),
                
                # Referral metrics
                "total_referrals": u.get("total_referrals", 0),
                "active_referrals": u.get("active_referrals", 0),
                
                # Withdrawal metrics
                "total_withdrawals": u.get("total_withdrawals", 0),
                "pending_withdrawals": u.get("pending_withdrawals", 0),
                "total_withdrawn": float(u.get("total_withdrawn", 0)),
                
                # Chat metrics
                "total_chat_messages": u.get("total_chat_messages", 0),
                "last_chat_message_at": u.get("last_chat_message_at"),
            }
            users.append(user_data)
        
        return {
            "users": users,
            "total": count_result.count or 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to query users_extended_analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load users.")


@router.post("/users/{user_id}/ban")
async def admin_ban_user(
    user_id: str,
    ban: bool = True,
    admin=Depends(verify_admin)
):
    """Ban or unban a user"""
    db = get_database()
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .update({"is_banned": ban})
            .eq("id", user_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "is_banned": ban}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ban user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user ban status")


@router.post("/users/{user_id}/balance")
async def admin_update_user_balance(
    user_id: str,
    request: UpdateBalanceRequest,
    admin=Depends(verify_admin)
):
    """
    Update user balance (add or subtract).
    
    IMPORTANT: Amount is in user's balance_currency (not USD).
    If user has balance_currency=RUB, amount should be in RUB.
    """
    db = get_database()
    
    try:
        # Get current balance and balance_currency
        user_result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .select("balance, balance_currency, telegram_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_balance = float(user_result.data.get("balance", 0))
        balance_currency = user_result.data.get("balance_currency") or "USD"
        new_balance = current_balance + request.amount
        
        # Use RPC function to update balance and log transaction atomically
        # RPC function handles currency correctly and prevents negative balance
        try:
            await asyncio.to_thread(
                lambda: db.client.rpc("add_to_user_balance", {
                    "p_user_id": user_id,
                    "p_amount": request.amount,  # Amount in user's balance_currency
                    "p_reason": f"Admin manual adjustment (admin_id: {admin.get('id', 'unknown')})"
                }).execute()
            )
            
            # Get updated balance to return
            updated_user = await asyncio.to_thread(
                lambda: db.client.table("users")
                .select("balance")
                .eq("id", user_id)
                .single()
                .execute()
            )
            new_balance = float(updated_user.data.get("balance", 0)) if updated_user.data else current_balance
        except Exception as e:
            error_msg = str(e).lower()
            if "negative" in error_msg or "insufficient" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set negative balance. Current: {current_balance} {balance_currency}"
                )
            logger.error(f"Failed to update balance via RPC: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update user balance")
        
        return {
            "success": True,
            "old_balance": current_balance,
            "new_balance": new_balance,
            "currency": balance_currency
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user balance")


@router.post("/users/{user_id}/warnings")
async def admin_update_warnings(
    user_id: str,
    request: UpdateWarningsRequest,
    admin=Depends(verify_admin)
):
    """Update user warnings count"""
    db = get_database()
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .update({"warnings_count": request.count})
            .eq("id", user_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "warnings_count": request.count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update warnings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update warnings")


@router.post("/users/{user_id}/vip")
async def admin_toggle_vip(
    user_id: str,
    is_partner: bool = True,
    partner_level_override: Optional[int] = None,
    admin=Depends(verify_admin)
):
    """
    Grant or revoke VIP partner status.
    
    Args:
        user_id: UUID of the user
        is_partner: True to grant VIP, False to revoke
        partner_level_override: Optional level override (1, 2, or 3)
    """
    db = get_database()
    
    try:
        # Validate partner_level_override
        if partner_level_override is not None and partner_level_override not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="partner_level_override must be 1, 2, or 3")
        
        update_data = {
            "is_partner": is_partner,
        }
        
        if is_partner:
            # If granting VIP, optionally set level override
            if partner_level_override:
                update_data["partner_level_override"] = partner_level_override
            # Also unlock referral program if not already
            update_data["referral_program_unlocked"] = True
        else:
            # If revoking VIP, clear level override
            update_data["partner_level_override"] = None
        
        result = await asyncio.to_thread(
            lambda: db.client.table("users")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Log the action
        user = result.data[0]
        username = user.get("username") or user.get("first_name") or "Unknown"
        logger.info(f"Admin {'granted' if is_partner else 'revoked'} VIP for user {username} (level_override={partner_level_override})")
        
        return {
            "success": True,
            "is_partner": is_partner,
            "partner_level_override": partner_level_override if is_partner else None,
            "message": f"VIP статус {'выдан' if is_partner else 'отозван'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle VIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update VIP status")
