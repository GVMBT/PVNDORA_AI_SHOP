"""Admin Users CRM Router.

Extended user analytics and management.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as PydanticBaseModel

from core.auth import verify_admin
from core.logging import get_logger
from core.routers.admin.models import UpdateBalanceRequest, UpdateWarningsRequest
from core.services.database import get_database
from core.services.money import to_float


class ToggleVIPRequest(PydanticBaseModel):
    is_partner: bool = True
    partner_level_override: int | None = None


logger = get_logger(__name__)

# Error message constants
ERR_USER_NOT_FOUND = "User not found"


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def _sanitize_search_input(search: str) -> str | None:
    """Sanitize search input to prevent SQL injection."""
    sanitized = search.strip().replace("%", "").replace("'", "").replace('"', "")
    return sanitized if sanitized else None


def _apply_search_filter(query, search: str | None):
    """Apply search filter to query (reduces cognitive complexity)."""
    if not search:
        return query

    sanitized_search = _sanitize_search_input(search)
    if not sanitized_search:
        return query

    try:
        # Try to search by telegram_id (if search is numeric)
        telegram_id = int(sanitized_search)
        return query.or_(
            f"telegram_id.eq.{telegram_id},"
            f"username.ilike.%{sanitized_search}%,"
            f"first_name.ilike.%{sanitized_search}%",
        )
    except ValueError:
        # Search by username or first_name
        return query.or_(
            f"username.ilike.%{sanitized_search}%,first_name.ilike.%{sanitized_search}%",
        )


def _apply_filters(query, filter_banned: bool | None, filter_partner: bool | None):
    """Apply boolean filters to query (reduces cognitive complexity)."""
    if filter_banned is not None:
        query = query.eq("is_banned", filter_banned)
    if filter_partner is not None:
        query = query.eq("is_partner", filter_partner)
    return query


def _validate_sort_by(sort_by: str) -> str:
    """Validate and return sort_by field (reduces cognitive complexity)."""
    valid_sorts = [
        "total_orders",
        "delivered_orders",
        "refunded_orders",
        "total_spent",
        "total_tickets",
        "open_tickets",
        "total_reviews",
        "avg_rating",
        "total_referrals",
        "total_withdrawals",
        "joined_at",
        "last_activity_at",
        "balance",
        "total_referral_earnings",
        "warnings_count",
    ]
    return sort_by if sort_by in valid_sorts else "total_orders"


def _format_user_crm_data(u: dict) -> dict:
    """Format user data for CRM response (reduces cognitive complexity)."""
    return {
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


def _prepare_partner_grant_data(
    update_data: dict,
    partner_level_override: int | None,
    now,
) -> int | None:
    """Prepare update data for granting VIP partner status."""
    update_data["partner_granted_at"] = now.isoformat()
    update_data["level1_unlocked_at"] = now.isoformat()
    update_data["referral_program_unlocked"] = True

    final_level_override = None
    if partner_level_override:
        update_data["partner_level_override"] = partner_level_override
        final_level_override = partner_level_override
        # Unlock levels based on override
        if partner_level_override >= 2:
            update_data["level2_unlocked_at"] = now.isoformat()
        if partner_level_override >= 3:
            update_data["level3_unlocked_at"] = now.isoformat()

    return final_level_override


def _prepare_partner_revoke_data(update_data: dict) -> None:
    """Prepare update data for revoking VIP partner status."""
    update_data["partner_granted_at"] = None
    update_data["partner_level_override"] = None


async def _send_vip_notification(telegram_id: int | None, is_partner: bool) -> None:
    """Send VIP status notification to user (best-effort)."""
    if not telegram_id:
        return

    try:
        from core.routers.deps import get_notification_service

        notification_service = get_notification_service()

        if is_partner:
            await notification_service.send_system_notification(
                telegram_id=telegram_id,
                message="🌟 Поздравляем! Вам присвоен VIP-статус партнёра!\n\n"
                "Теперь у вас есть доступ к расширенным возможностям реферальной программы.",
            )
        else:
            await notification_service.send_system_notification(
                telegram_id=telegram_id,
                message="ℹ️ Ваш VIP-статус партнёра был отозван.",
            )
    except Exception as e:
        logger.warning(f"Failed to send VIP notification to {telegram_id}: {e}")


router = APIRouter(tags=["admin-users"])


@router.get("/users")
async def admin_get_users(limit: int = 50, offset: int = 0, admin=Depends(verify_admin)):
    """Get users for admin panel - uses users_extended_analytics VIEW to avoid N+1 queries."""
    db = get_database()

    try:
        # Use VIEW that pre-aggregates orders count and total spent
        # This eliminates N+1 queries (was: 1 query per user for orders)
        result = (
            await db.client.table("users_extended_analytics")
            .select(
                "id, telegram_id, username, first_name, balance, is_admin, "
                "total_referral_earnings, created_at, orders_count, total_spent",
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Get additional user fields not in VIEW (is_banned, is_partner, partner_mode, balance_currency)
        user_ids = [u["id"] for u in (result.data or [])]
        extra_fields = {}
        if user_ids:
            extra_result = (
                await db.client.table("users")
                .select("id, is_banned, is_partner, partner_mode, balance_currency")
                .in_("id", user_ids)
                .execute()
            )
            extra_fields = {u["id"]: u for u in (extra_result.data or [])}

        users = []
        for u in result.data or []:
            user_id = u.get("id")
            extra = extra_fields.get(user_id, {})

            # Determine role
            role = "user"
            if u.get("is_admin"):
                role = "admin"
            elif extra.get("is_partner"):
                role = "vip"

            users.append(
                {
                    "id": user_id,
                    "telegram_id": str(u.get("telegram_id", "")),
                    "username": u.get("username") or u.get("first_name") or "Unknown",
                    "role": role,
                    "balance": to_float(u.get("balance", 0)),
                    "balance_currency": extra.get("balance_currency") or "RUB",
                    "total_spent": to_float(u.get("total_spent", 0)),
                    "orders_count": u.get("orders_count", 0),
                    "is_banned": extra.get("is_banned", False),
                    "is_partner": extra.get("is_partner", False),
                    "partner_mode": extra.get("partner_mode") or "commission",
                    "total_referral_earnings": to_float(u.get("total_referral_earnings", 0)),
                    "created_at": u.get("created_at"),
                },
            )

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
    search: Annotated[
        str | None, Query(description="Search by username, first_name, or telegram_id")
    ] = None,
    filter_banned: Annotated[bool | None, Query(description="Filter by banned status")] = None,
    filter_partner: Annotated[bool | None, Query(description="Filter by partner status")] = None,
    admin=Depends(verify_admin),
):
    """Get all users with extended analytics (orders, refunds, tickets, etc.)."""
    db = get_database()

    try:
        # Build query
        query = db.client.table("users_extended_analytics").select("*")

        # Apply search filter
        query = _apply_search_filter(query, search)

        # Apply filters
        query = _apply_filters(query, filter_banned, filter_partner)

        # Validate sort_by
        validated_sort_by = _validate_sort_by(sort_by)

        # Execute query with sorting and pagination
        result = (
            await query.order(validated_sort_by, desc=(sort_order == "desc"))
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Get total count with same filters
        count_query = db.client.table("users_extended_analytics").select("user_id", count="exact")
        count_query = _apply_search_filter(count_query, search)
        count_query = _apply_filters(count_query, filter_banned, filter_partner)

        count_result = await count_query.execute()

        users = [_format_user_crm_data(u) for u in (result.data or [])]

        return {"users": users, "total": count_result.count or 0, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Failed to query users_extended_analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load users.")


@router.post("/users/{user_id}/ban")
async def admin_ban_user(user_id: str, ban: bool = True, admin=Depends(verify_admin)):
    """Ban or unban a user."""
    db = get_database()

    try:
        result = (
            await db.client.table("users").update({"is_banned": ban}).eq("id", user_id).execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

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
    admin=Depends(verify_admin),
):
    """Update user balance (add or subtract).

    IMPORTANT: Amount is in user's balance_currency (not USD).
    If user has balance_currency=RUB, amount should be in RUB.
    """
    db = get_database()

    try:
        # Get current balance and balance_currency
        user_result = (
            await db.client.table("users")
            .select("balance, balance_currency, telegram_id")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

        current_balance = float(user_result.data.get("balance", 0))
        balance_currency = user_result.data.get("balance_currency") or "RUB"
        new_balance = current_balance + request.amount

        # Use RPC function to update balance and log transaction atomically
        # RPC function handles currency correctly and prevents negative balance
        admin_id = admin.get("id", "unknown")
        try:
            await db.client.rpc(
                "add_to_user_balance",
                {
                    "p_user_id": user_id,
                    "p_amount": request.amount,  # Amount in user's balance_currency
                    "p_reason": "Корректировка баланса администратором",
                    "p_reference_type": "admin_adjustment",
                    "p_reference_id": str(admin_id),
                    "p_metadata": {
                        "admin_id": str(admin_id),
                        "adjustment_type": "manual",
                        "amount": request.amount,
                        "currency": balance_currency,
                    },
                },
            ).execute()

            # Get updated balance to return
            updated_user = (
                await db.client.table("users")
                .select("balance")
                .eq("id", user_id)
                .single()
                .execute()
            )
            new_balance = (
                float(updated_user.data.get("balance", 0)) if updated_user.data else current_balance
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "negative" in error_msg or "insufficient" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set negative balance. Current: {current_balance} {balance_currency}",
                )
            logger.error(f"Failed to update balance via RPC: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update user balance")

        return {
            "success": True,
            "old_balance": current_balance,
            "new_balance": new_balance,
            "currency": balance_currency,
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
    admin=Depends(verify_admin),
):
    """Update user warnings count."""
    db = get_database()

    try:
        result = (
            await db.client.table("users")
            .update({"warnings_count": request.count})
            .eq("id", user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

        return {"success": True, "warnings_count": request.count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update warnings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update warnings")


@router.post("/users/{user_id}/vip")
async def admin_toggle_vip(user_id: str, request: ToggleVIPRequest, admin=Depends(verify_admin)):
    """Grant or revoke VIP partner status.

    Args:
        user_id: UUID of the user
        request.is_partner: True to grant VIP, False to revoke
        request.partner_level_override: Optional level override (1, 2, or 3)

    """
    is_partner = request.is_partner
    partner_level_override = request.partner_level_override
    db = get_database()

    try:
        # Validate partner_level_override
        if partner_level_override is not None and partner_level_override not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="partner_level_override must be 1, 2, or 3")

        update_data = {"is_partner": is_partner}

        from datetime import UTC, datetime

        now = datetime.now(UTC)

        if is_partner:
            final_level_override = _prepare_partner_grant_data(
                update_data,
                partner_level_override,
                now,
            )
        else:
            _prepare_partner_revoke_data(update_data)
            final_level_override = None

        result = await db.client.table("users").update(update_data).eq("id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=ERR_USER_NOT_FOUND)

        user = result.data[0]
        username = user.get("username") or user.get("first_name") or "Unknown"
        telegram_id = user.get("telegram_id")

        logger.info(
            "Admin %s VIP for user %s (level_override=%s)",
            "granted" if is_partner else "revoked",
            username,
            final_level_override if is_partner else None,
        )

        await _send_vip_notification(telegram_id, is_partner)

        return {
            "success": True,
            "is_partner": is_partner,
            "partner_level_override": final_level_override if is_partner else None,
            "message": f"VIP статус {'выдан' if is_partner else 'отозван'}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle VIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update VIP status")
