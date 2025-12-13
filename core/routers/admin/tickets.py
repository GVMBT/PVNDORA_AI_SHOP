"""
Admin Tickets Router

Support ticket management endpoints.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query

from src.services.database import get_database
from core.auth import verify_admin

router = APIRouter(prefix="/tickets", tags=["admin-tickets"])


@router.get("")
async def get_tickets(
    status: str = Query("open", description="Filter by status: open, approved, rejected, closed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(verify_admin)
):
    """Get support tickets with optional status filter."""
    db = get_database()
    
    try:
        query = db.client.table("tickets").select(
            "*, users(username, first_name, telegram_id)"
        ).order("created_at", desc=True).limit(limit).offset(offset)
        
        if status and status != "all":
            query = query.eq("status", status)
        
        result = await asyncio.to_thread(lambda: query.execute())
        
        tickets = []
        for t in (result.data or []):
            user_data = t.pop("users", {}) or {}
            tickets.append({
                **t,
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "telegram_id": user_data.get("telegram_id"),
            })
        
        return {"tickets": tickets, "count": len(tickets)}
    
    except Exception as e:
        print(f"Error fetching tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, admin=Depends(verify_admin)):
    """Get single ticket by ID."""
    db = get_database()
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .select("*, users(username, first_name, telegram_id), orders(id, amount, status, product_id)")
            .eq("id", ticket_id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return {"ticket": result.data}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    approve: bool = Query(True, description="Approve (true) or reject (false)"),
    comment: Optional[str] = Query(None, description="Admin comment"),
    admin=Depends(verify_admin)
):
    """Resolve a support ticket (approve or reject)."""
    db = get_database()
    
    try:
        # Check ticket exists and is open
        ticket_res = await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .select("id, status")
            .eq("id", ticket_id)
            .single()
            .execute()
        )
        
        if not ticket_res.data:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        if ticket_res.data["status"] != "open":
            raise HTTPException(status_code=400, detail=f"Ticket is already {ticket_res.data['status']}")
        
        new_status = "approved" if approve else "rejected"
        update_data = {"status": new_status}
        if comment:
            update_data["admin_comment"] = comment
        
        await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .update(update_data)
            .eq("id", ticket_id)
            .execute()
        )
        
        return {"success": True, "status": new_status}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resolving ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: str,
    comment: Optional[str] = Query(None),
    admin=Depends(verify_admin)
):
    """Close a ticket."""
    db = get_database()
    
    try:
        update_data = {"status": "closed"}
        if comment:
            update_data["admin_comment"] = comment
        
        await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .update(update_data)
            .eq("id", ticket_id)
            .execute()
        )
        
        return {"success": True, "status": "closed"}
    
    except Exception as e:
        print(f"Error closing ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))







