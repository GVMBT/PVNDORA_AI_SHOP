"""Support Tools for Shop Agent.

FAQ search, ticket creation, refunds.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import re
from datetime import UTC, datetime

from langchain_core.tools import tool

from core.logging import get_logger

from .base import get_db, get_user_context

logger = get_logger(__name__)


def _extract_item_id_from_message(message: str, provided_item_id: str | None) -> str | None:
    """Extract item_id from message if not provided (reduces cognitive complexity)."""
    if provided_item_id:
        return provided_item_id
    if "Item ID:" in message or "item_id" in message.lower():
        item_id_match = re.search(r"Item ID:\s*([a-f0-9\-]{36})", message, re.IGNORECASE)
        if item_id_match:
            return item_id_match.group(1)
    return None


def _calculate_warranty_status(delivered_at: str | None, warranty_hours: int) -> str:
    """Calculate warranty status based on delivery time (reduces cognitive complexity)."""
    if not delivered_at:
        return "unknown"
    try:
        item_delivered = datetime.fromisoformat(delivered_at)
        now = datetime.now(UTC)
        days_since = (now - item_delivered).days
        warranty_days = warranty_hours / 24
        return "in_warranty" if days_since <= warranty_days else "out_of_warranty"
    except Exception:
        return "unknown"


def _calculate_order_warranty_status(order_date: datetime | None, product_name: str) -> str:
    """Calculate warranty status for order level (reduces cognitive complexity)."""
    if not order_date:
        return "unknown"
    now = datetime.now(UTC)
    days_since = (now - order_date).days
    product_name_lower = product_name.lower()
    is_trial = (
        "trial" in product_name_lower
        or "7 дней" in product_name_lower
        or "7 day" in product_name_lower
    )
    warranty_days = 1 if is_trial else 14
    return "in_warranty" if days_since <= warranty_days else "out_of_warranty"


async def _get_warranty_status(db, order, extracted_item_id: str | None) -> str:
    """Get warranty status for order/item (reduces cognitive complexity)."""
    if extracted_item_id:
        item_result = (
            await db.client.table("order_items")
            .select("id, order_id, delivered_at, product_id")
            .eq("id", extracted_item_id)
            .eq("order_id", order.id)
            .limit(1)
            .execute()
        )
        if item_result.data:
            item_data = item_result.data[0]
            product_result = (
                await db.client.table("products")
                .select("name, warranty_hours")
                .eq("id", item_data.get("product_id"))
                .limit(1)
                .execute()
            )
            warranty_hours = 168
            if product_result.data:
                warranty_hours = product_result.data[0].get("warranty_hours", 168)
            return _calculate_warranty_status(item_data.get("delivered_at"), warranty_hours)

    # Check order-level warranty
    items = await db.get_order_items_by_order(order.id)
    if items and order.created_at:
        product_name = items[0].get("product_name", "")
        return _calculate_order_warranty_status(order.created_at, product_name)

    return "unknown"


@tool
async def search_faq(question: str) -> dict:
    """Search FAQ for answer to common question.
    Use first before creating support ticket.
    Uses language from context.

    Args:
        question: User's question

    Returns:
        Matching FAQ entry if found

    """
    try:
        ctx = get_user_context()
        db = get_db()
        faq_entries = await db.get_faq(ctx.language)

        if not faq_entries:
            return {"success": True, "found": False}

        question_lower = question.lower()
        for entry in faq_entries:
            q = entry.get("question", "").lower()
            if any(word in q for word in question_lower.split() if len(word) > 3):
                return {
                    "success": True,
                    "found": True,
                    "question": entry["question"],
                    "answer": entry["answer"],
                }

        return {"success": True, "found": False}
    except Exception as e:
        logger.exception("search_faq error")
        return {"success": False, "error": str(e)}


@tool
async def create_support_ticket(
    issue_type: str,
    message: str,
    order_id_prefix: str | None = None,
    item_id: str | None = None,
) -> dict:
    """Create support ticket for user's issue.
    All tickets require manual review by admin/support.
    Uses user_id from context.

    IMPORTANT FOR REPLACEMENT TICKETS:
    - You MUST provide order_id_prefix for replacement/refund issues
    - You SHOULD provide item_id for account-specific problems

    Args:
        issue_type: Type of issue (replacement, refund, technical_issue, other)
        message: Issue description
        order_id_prefix: First 8 chars of related order ID (REQUIRED for replacement/refund)
        item_id: Specific order item ID (REQUIRED for account replacements)

    Returns:
        Ticket info with status

    """
    if issue_type in ("replacement", "refund") and not order_id_prefix:
        return {
            "success": False,
            "error": "order_id_prefix required for replacement/refund tickets. First call get_user_orders to find the order, then ask user which one has the problem.",
        }
    try:
        ctx = get_user_context()
        db = get_db()

        order_id = None
        warranty_status = "unknown"
        extracted_item_id = _extract_item_id_from_message(message, item_id)

        if order_id_prefix:
            orders = await db.get_user_orders(ctx.user_id, limit=20)
            order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)

            if order:
                order_id = order.id
                warranty_status = await _get_warranty_status(db, order, extracted_item_id)

        result = await db.support_domain.create_ticket(
            user_id=ctx.user_id,
            message=message,
            order_id=order_id,
            item_id=extracted_item_id,
            issue_type=issue_type,
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("reason", "Failed to create ticket")}

        ticket_id = result.get("ticket_id", "")
        ticket_id_short = ticket_id[:8] if ticket_id else None

        return {
            "success": True,
            "ticket_id": ticket_id,
            "ticket_id_short": ticket_id_short,
            "status": "open",
            "warranty_status": warranty_status,
            "message": f"Заявка #{ticket_id_short} создана. Наша команда поддержки рассмотрит её в ближайшее время.",
        }
    except Exception as e:
        logger.error(f"create_support_ticket error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def request_refund(order_id: str, reason: str) -> dict:
    """Request refund for an order.
    Uses user_id from context.

    Args:
        order_id: Order ID (full or prefix)
        reason: Reason for refund

    Returns:
        Ticket ID for refund request

    """
    try:
        ctx = get_user_context()
        db = get_db()

        orders = await db.get_user_orders(ctx.user_id, limit=20)
        order = next((o for o in orders if o.id.startswith(order_id)), None)

        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}

        result = await db.create_ticket(
            user_id=ctx.user_id,
            subject=f"Refund Request: {order_id[:8]}",
            message=f"Refund requested for order {order_id[:8]}. Reason: {reason}",
            order_id=order.id,
        )

        return {
            "success": True,
            "ticket_id": result.get("id", "")[:8] if result else None,
            "message": f"Refund request created for order {order_id[:8]}. We'll review it soon.",
        }
    except Exception as e:
        logger.exception("request_refund error")
        return {"success": False, "error": str(e)}
