"""Support-related tool handlers."""
import asyncio
from typing import Dict, Any

from .helpers import create_error_response
from core.logging import get_logger

logger = get_logger(__name__)

MAX_OPEN_REFUNDS_PER_USER = 3
ALLOWED_REFUND_STATUSES = {"pending", "paid", "delivered", "fulfilled", "completed"}
FORBIDDEN_REFUND_STATUSES = {"refund_pending", "refunded", "cancelled", "rejected", "failed"}


async def handle_create_support_ticket(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Create a support ticket when user reports an issue."""
    try:
        issue = arguments.get("issue_description", "")
        order_id = arguments.get("order_id")
        
        ticket_data = {
            "user_id": user_id,
            "message": issue,
            "status": "open"
        }
        if order_id:
            ticket_data["order_id"] = order_id
        
        await asyncio.to_thread(
            lambda: db.client.table("tickets").insert(ticket_data).execute()
        )
        
        return {
            "success": True,
            "message": "Support ticket created"
        }
    except Exception as e:
        logger.error(f"create_support_ticket failed: {e}")
        return create_error_response(e, "Failed to create support ticket.")


async def handle_get_faq_answer(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Get answer from FAQ for common questions."""
    question = arguments.get("question", "")
    faq_entries = await db.get_faq(language)
    
    # Simple keyword matching for FAQ
    question_lower = question.lower()
    for entry in faq_entries:
        if any(word in question_lower for word in entry.get("question", "").lower().split()):
            return {
                "found": True,
                "question": entry["question"],
                "answer": entry["answer"]
            }
    
    return {"found": False}


async def handle_request_refund(
    arguments: Dict[str, Any],
    user_id: str,
    db,
    language: str
) -> Dict[str, Any]:
    """Request a refund for a problematic order."""
    order_id = arguments.get("order_id")
    reason = arguments.get("reason", "")
    
    order = await db.get_order_by_id(order_id)
    if not order:
        return {"success": False, "reason": "Order not found"}
    
    if order.user_id != user_id:
        return {"success": False, "reason": "Not your order"}
    
    if order.refund_requested:
        return {"success": False, "reason": "Refund already requested"}
    
    status_lower = (order.status or "").lower()
    if status_lower in FORBIDDEN_REFUND_STATUSES:
        return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}
    if ALLOWED_REFUND_STATUSES and status_lower and status_lower not in ALLOWED_REFUND_STATUSES:
        return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}
    
    try:
        # Check quota of open refunds per user
        def _count_open():
            result = db.client.table("orders").select("id", count="exact").eq("user_id", user_id).eq("refund_requested", True).execute()
            return result.count or 0
        open_refunds = await asyncio.to_thread(_count_open)
        if open_refunds >= MAX_OPEN_REFUNDS_PER_USER:
            return {"success": False, "reason": "Refund request limit reached"}
    except Exception as e:
        return create_error_response(e, "Failed to validate refund limits.")
    
    try:
        # Create ticket first
        ticket_result = await asyncio.to_thread(
            lambda: db.client.table("tickets").insert({
                "user_id": user_id,
                "order_id": order_id,
                "issue_type": "refund",
                "description": reason,
                "status": "open"
            }).execute()
        )
        
        if not ticket_result.data:
            return {"success": False, "reason": "Failed to create support ticket"}
        
        # Then update order
        await asyncio.to_thread(
            lambda: db.client.table("orders").update({
                "refund_requested": True
            }).eq("id", order_id).execute()
        )
        
        return {
            "success": True,
            "message": "Refund request submitted for review",
            "ticket_id": ticket_result.data[0].get("id")
        }
    except Exception as e:
        return create_error_response(e, "Failed to process refund request.")


# Export handlers mapping
SUPPORT_HANDLERS = {
    "create_support_ticket": handle_create_support_ticket,
    "get_faq_answer": handle_get_faq_answer,
    "request_refund": handle_request_refund,
}

