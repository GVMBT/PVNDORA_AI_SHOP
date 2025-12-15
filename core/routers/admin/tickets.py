"""
Admin Tickets Router

Support ticket management endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query

from core.services.database import get_database
from core.auth import verify_admin
from core.logging import get_logger

logger = get_logger(__name__)

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
        logger.error(f"Error fetching tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, admin=Depends(verify_admin)):
    """Get single ticket by ID."""
    db = get_database()
    
    try:
        result = await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .select("*, users(username, first_name, telegram_id), orders(id, amount, status)")
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
        logger.error(f"Error fetching ticket {ticket_id}: {e}")
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
        # Get full ticket data including issue_type and item_id
        ticket_res = await asyncio.to_thread(
            lambda: db.client.table("tickets")
            .select("id, status, issue_type, item_id, order_id, user_id")
            .eq("id", ticket_id)
            .single()
            .execute()
        )
        
        if not ticket_res.data:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        if ticket_res.data["status"] != "open":
            raise HTTPException(status_code=400, detail=f"Ticket is already {ticket_res.data['status']}")
        
        ticket_data = ticket_res.data
        issue_type = ticket_data.get("issue_type")
        item_id = ticket_data.get("item_id")
        order_id = ticket_data.get("order_id")
        
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
        
        # If approved, trigger automatic processing via QStash
        if approve and new_status == "approved":
            try:
                from core.queue import publish_to_worker, WorkerEndpoints
                from core.routers.deps import get_queue_publisher
                
                publish_to_worker, WorkerEndpoints = get_queue_publisher()
                
                if issue_type == "replacement" and item_id:
                    # Trigger replacement worker
                    await publish_to_worker(
                        WorkerEndpoints.PROCESS_REPLACEMENT,
                        {
                            "ticket_id": ticket_id,
                            "item_id": item_id,
                            "order_id": order_id
                        }
                    )
                    logger.info(f"Triggered replacement worker for ticket {ticket_id}, item {item_id}")
                
                elif issue_type == "refund" and order_id:
                    # Trigger refund worker
                    from core.services.money import to_float
                    
                    # Get order amount
                    order_res = await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .select("amount, user_telegram_id")
                        .eq("id", order_id)
                        .single()
                        .execute()
                    )
                    
                    if order_res.data:
                        amount = to_float(order_res.data.get("amount", 0))
                        usd_rate = 100  # Default, should be fetched from currency service
                        
                        await publish_to_worker(
                            WorkerEndpoints.PROCESS_REFUND,
                            {
                                "order_id": order_id,
                                "reason": comment or "Refund approved by admin",
                                "usd_rate": usd_rate
                            }
                        )
                        logger.info(f"Triggered refund worker for ticket {ticket_id}, order {order_id}")
                
            except Exception as e:
                # Log error but don't fail the request - ticket is already updated
                logger.error(f"Failed to trigger automatic processing for ticket {ticket_id}: {e}", exc_info=True)
        
        return {"success": True, "status": new_status}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving ticket {ticket_id}: {e}")
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
        logger.error(f"Error closing ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))









