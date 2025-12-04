"""
Admin Users & Tickets Router

User management and support tickets endpoints.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
from core.auth import verify_admin
from core.routers.deps import get_notification_service
from .models import BanUserRequest, BroadcastRequest

router = APIRouter(tags=["admin-users"])


# ==================== USERS ====================

@router.get("/users")
async def admin_get_users(
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get all users"""
    db = get_database()
    
    result = db.client.table("users").select("*").order(
        "created_at", desc=True
    ).range(offset, offset + limit - 1).execute()
    
    return result.data


@router.get("/users/{telegram_id}")
async def admin_get_user(telegram_id: int, admin=Depends(verify_admin)):
    """Get specific user details"""
    db = get_database()
    user = await db.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.get_user_orders(user.id, limit=20)
    
    return {
        "user": user,
        "orders": orders
    }


@router.post("/users/ban")
async def admin_ban_user(request: BanUserRequest, admin=Depends(verify_admin)):
    """Ban or unban a user"""
    db = get_database()
    await db.ban_user(request.telegram_id, request.ban)
    
    return {"success": True, "banned": request.ban}


@router.post("/users/{telegram_id}/warning")
async def admin_add_warning(telegram_id: int, admin=Depends(verify_admin)):
    """Add warning to user (auto-ban after 3)"""
    db = get_database()
    new_count = await db.add_warning(telegram_id)
    
    return {
        "success": True,
        "warnings_count": new_count,
        "auto_banned": new_count >= 3
    }


# ==================== BROADCAST ====================

@router.post("/broadcast")
async def admin_broadcast(request: BroadcastRequest, admin=Depends(verify_admin)):
    """Send broadcast message to all users"""
    notification_service = get_notification_service()
    
    sent_count = await notification_service.send_broadcast(
        message=request.message,
        exclude_dnd=request.exclude_dnd
    )
    
    return {"success": True, "sent_count": sent_count}


# ==================== SUPPORT TICKETS ====================

@router.get("/tickets")
async def admin_get_tickets(
    status: Optional[str] = None,
    admin=Depends(verify_admin)
):
    """Get support tickets"""
    db = get_database()
    
    query = db.client.table("support_tickets").select(
        "*, users(telegram_id, username)"
    ).order("created_at", desc=True)
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    return {"tickets": result.data if result.data else []}


@router.post("/tickets/{ticket_id}/resolve")
async def admin_resolve_ticket(
    ticket_id: str,
    resolution: str = "resolved",
    admin=Depends(verify_admin)
):
    """Resolve a support ticket"""
    db = get_database()
    
    ticket = db.client.table("support_tickets").select(
        "*, users(telegram_id), orders(id)"
    ).eq("id", ticket_id).single().execute()
    
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    db.client.table("support_tickets").update({
        "status": "resolved",
        "resolution": resolution,
        "resolved_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", ticket_id).execute()
    
    return {"success": True, "ticket_id": ticket_id}
