"""
Support Tools for Shop Agent.

FAQ search, ticket creation, refunds.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import re
from datetime import UTC, datetime

from langchain_core.tools import tool

from core.logging import get_logger

from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def search_faq(question: str) -> dict:
    """
    Search FAQ for answer to common question.
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
    """
    Create support ticket for user's issue.
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
        extracted_item_id = item_id

        if not extracted_item_id and ("Item ID:" in message or "item_id" in message.lower()):
            item_id_match = re.search(r"Item ID:\s*([a-f0-9\-]{36})", message, re.IGNORECASE)
            if item_id_match:
                extracted_item_id = item_id_match.group(1)

        if order_id_prefix:
            orders = await db.get_user_orders(ctx.user_id, limit=20)
            order = next((o for o in orders if o.id.startswith(order_id_prefix)), None)

            if order:
                order_id = order.id

                if extracted_item_id:
                    item_result = (
                        await db.client.table("order_items")
                        .select("id, order_id, delivered_at, product_id")
                        .eq("id", extracted_item_id)
                        .eq("order_id", order_id)
                        .limit(1)
                        .execute()
                    )
                    if item_result.data:
                        item_data = item_result.data[0]
                        if item_data.get("delivered_at"):
                            item_delivered = datetime.fromisoformat(
                                item_data["delivered_at"].replace("Z", "+00:00")
                            )
                            now = datetime.now(UTC)
                            days_since = (now - item_delivered).days

                            product_result = (
                                await db.client.table("products")
                                .select("name, warranty_hours")
                                .eq("id", item_data.get("product_id"))
                                .limit(1)
                                .execute()
                            )
                            if product_result.data:
                                product = product_result.data[0]
                                warranty_hours = product.get("warranty_hours", 168)
                                warranty_days = warranty_hours / 24

                                if days_since <= warranty_days:
                                    warranty_status = "in_warranty"
                                else:
                                    warranty_status = "out_of_warranty"
                else:
                    items = await db.get_order_items_by_order(order.id)

                    if items and order.created_at:
                        order_date = order.created_at
                        now = datetime.now(UTC)
                        days_since = (now - order_date).days

                        product_name = items[0].get("product_name", "").lower()
                        if (
                            "trial" in product_name
                            or "7 дней" in product_name
                            or "7 day" in product_name
                        ):
                            warranty_days = 1
                        else:
                            warranty_days = 14

                        if days_since <= warranty_days:
                            warranty_status = "in_warranty"
                        else:
                            warranty_status = "out_of_warranty"

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
    """
    Request refund for an order.
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
