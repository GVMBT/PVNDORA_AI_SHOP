"""Support-related tool handlers."""
import asyncio
from typing import Dict, Any

from .helpers import create_error_response


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
        print(f"ERROR: create_support_ticket failed: {e}")
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

