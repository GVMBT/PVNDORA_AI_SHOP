"""Support ticket endpoints.

User support ticket management.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import verify_telegram_auth
from core.services.database import get_database

from .constants import MAX_TICKETS_PER_USER, MIN_TICKET_MESSAGE_LENGTH

support_router = APIRouter(tags=["webapp-misc-support"])

# Constants (avoid string duplication)
ERROR_USER_NOT_FOUND = "User not found"


# --- Support Ticket Models ---
class CreateTicketRequest(BaseModel):
    message: str
    order_id: str | None = None
    item_id: str | None = None  # Specific order item ID (for item-level issues)
    issue_type: str = "general"  # general, payment, delivery, refund, other


class TicketMessageRequest(BaseModel):
    ticket_id: str
    message: str


@support_router.get("/support/tickets")
async def get_user_tickets(user=Depends(verify_telegram_auth)):
    """Get current user's support tickets."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    result = (
        await db.client.table("tickets")
        .select("id, status, issue_type, description, admin_comment, created_at, order_id, item_id")
        .eq("user_id", db_user.id)
        .order("created_at", desc=True)
        .limit(MAX_TICKETS_PER_USER)
        .execute()
    )

    tickets = []
    for t in result.data or []:
        tickets.append(
            {
                "id": t["id"],
                "status": t["status"],
                "issue_type": t.get("issue_type", "general"),
                "message": t.get("description", ""),
                "admin_reply": t.get("admin_comment"),
                "order_id": t.get("order_id"),
                "item_id": t.get("item_id"),  # Include item_id in response
                "created_at": t["created_at"],
            },
        )

    return {"tickets": tickets, "count": len(tickets)}


@support_router.post("/support/tickets")
async def create_user_ticket(request: CreateTicketRequest, user=Depends(verify_telegram_auth)):
    """Create a new support ticket."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    if len(request.message.strip()) < MIN_TICKET_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too short (min {MIN_TICKET_MESSAGE_LENGTH} characters)",
        )

    # Validate order_id if provided
    if request.order_id:
        order = await db.get_order_by_id(request.order_id)
        if not order or order.user_id != db_user.id:
            raise HTTPException(status_code=400, detail="Invalid order ID")

    # Validate item_id if provided (must belong to the order)
    if request.item_id and request.order_id:
        item_result = (
            await db.client.table("order_items")
            .select("id, order_id")
            .eq("id", request.item_id)
            .eq("order_id", request.order_id)
            .limit(1)
            .execute()
        )
        if not item_result.data:
            raise HTTPException(
                status_code=400,
                detail="Invalid item ID or item does not belong to the order",
            )

    ticket_data = {
        "user_id": db_user.id,
        "order_id": request.order_id,
        "issue_type": request.issue_type,
        "description": request.message.strip(),
        "status": "open",
    }

    if request.item_id:
        ticket_data["item_id"] = request.item_id

    result = await db.client.table("tickets").insert(ticket_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create ticket")

    ticket = result.data[0]
    return {
        "success": True,
        "ticket_id": ticket["id"],
        "message": "Ticket created successfully. Our team will respond soon.",
    }


@support_router.get("/support/tickets/{ticket_id}")
async def get_user_ticket(ticket_id: str, user=Depends(verify_telegram_auth)):
    """Get specific ticket details."""
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail=ERROR_USER_NOT_FOUND)

    result = (
        await db.client.table("tickets")
        .select("*")
        .eq("id", ticket_id)
        .eq("user_id", db_user.id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    t = result.data
    return {
        "ticket": {
            "id": t["id"],
            "status": t["status"],
            "issue_type": t.get("issue_type", "general"),
            "message": t.get("description", ""),
            "admin_reply": t.get("admin_comment"),
            "order_id": t.get("order_id"),
            "created_at": t["created_at"],
        },
    }
