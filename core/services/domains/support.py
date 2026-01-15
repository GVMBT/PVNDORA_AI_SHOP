"""Support Domain Service.

Handles support tickets, FAQ, and refund requests.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


# Refund configuration
MAX_OPEN_REFUNDS_PER_USER = 3
ALLOWED_REFUND_STATUSES = {"pending", "paid", "prepaid", "partial", "delivered"}
FORBIDDEN_REFUND_STATUSES = {"refunded", "cancelled"}

# Replacement configuration (anti-abuse)
MAX_REPLACEMENTS_PER_MONTH = 20
MAX_REPLACEMENT_TICKETS_PER_DAY = 5
MIN_HOURS_BETWEEN_REPLACEMENTS = 1


@dataclass
class FAQEntry:
    """FAQ entry."""

    id: str
    question: str
    answer: str
    category: str | None = None


@dataclass
class SupportTicket:
    """Support ticket."""

    id: str
    user_id: str
    order_id: str | None
    issue_type: str | None
    message: str
    status: str


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _check_existing_replacement(db, item_id: str) -> dict | None:
    """Check if item already has an open/approved replacement ticket."""
    existing = (
        await db.client.table("tickets")
        .select("id, status, created_at")
        .eq("item_id", item_id)
        .eq("issue_type", "replacement")
        .in_("status", ["open", "approved"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return existing.data[0] if existing.data else None


async def _check_daily_replacement_limit(db, user_id: str) -> int:
    """Check number of replacement tickets created today."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    today_count = (
        await db.client.table("tickets")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("issue_type", "replacement")
        .gte("created_at", today_start.isoformat())
        .execute()
    )
    return today_count.count or 0


async def _check_replacement_cooldown(db, user_id: str) -> float | None:
    """Check hours since last replacement request. Returns None if no previous requests."""
    last_replacement = (
        await db.client.table("tickets")
        .select("created_at")
        .eq("user_id", user_id)
        .eq("issue_type", "replacement")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not last_replacement.data:
        return None

    last_time = datetime.fromisoformat(
        last_replacement.data[0]["created_at"],
    )
    return (datetime.now(UTC) - last_time).total_seconds() / 3600


async def _check_monthly_replacement_limit(db, user_id: str, order_id: str | None) -> bool:
    """Check if user has exceeded monthly replacement limit. Returns True if allowed."""
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_count = (
        await db.client.table("tickets")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("issue_type", "replacement")
        .in_("status", ["open", "approved"])
        .gte("created_at", month_start.isoformat())
        .execute()
    )

    if (monthly_count.count or 0) < MAX_REPLACEMENTS_PER_MONTH:
        return True

    # Allow if this item belongs to an order with existing replacement tickets
    if order_id:
        order_replacements = (
            await db.client.table("tickets")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("order_id", order_id)
            .eq("issue_type", "replacement")
            .in_("status", ["open", "approved"])
            .execute()
        )
        return (order_replacements.count or 0) > 0

    return False


async def _validate_replacement_request(
    db, user_id: str, item_id: str, order_id: str | None,
) -> dict | None:
    """Validate replacement request against anti-abuse rules. Returns error dict or None if valid."""
    # Check 1: Existing replacement for this item
    if await _check_existing_replacement(db, item_id):
        return {
            "success": False,
            "reason": "This account has already been requested for replacement. Please wait for processing.",
        }

    # Check 2: Daily limit
    if await _check_daily_replacement_limit(db, user_id) >= MAX_REPLACEMENT_TICKETS_PER_DAY:
        return {
            "success": False,
            "reason": f"Too many replacement requests today (limit: {MAX_REPLACEMENT_TICKETS_PER_DAY}). Please try again tomorrow.",
        }

    # Check 3: Cooldown
    hours_since = await _check_replacement_cooldown(db, user_id)
    if hours_since is not None and hours_since < MIN_HOURS_BETWEEN_REPLACEMENTS:
        return {
            "success": False,
            "reason": f"Please wait {MIN_HOURS_BETWEEN_REPLACEMENTS} hour(s) between replacement requests.",
        }

    # Check 4: Monthly limit
    if not await _check_monthly_replacement_limit(db, user_id, order_id):
        return {
            "success": False,
            "reason": f"Monthly replacement limit reached ({MAX_REPLACEMENTS_PER_MONTH}). Contact support for assistance.",
        }

    return None


async def _send_ticket_admin_alert(
    db, ticket_id: str, user_id: str, issue_type: str | None, order_id: str | None,
) -> None:
    """Send admin alert for new ticket."""
    try:
        from core.services.admin_alerts import get_admin_alert_service

        user_result = (
            await db.client.table("users")
            .select("telegram_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        tg_id = user_result.data.get("telegram_id", 0) if user_result.data else 0

        alert_service = get_admin_alert_service()
        await alert_service.alert_support_ticket(
            ticket_id=ticket_id,
            user_telegram_id=tg_id,
            issue_type=issue_type or "general",
            order_id=order_id,
        )
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.warning(
            "Failed to send admin alert for ticket %s: %s",
            sanitize_id_for_logging(ticket_id),
            type(e).__name__,
        )


def _validate_refund_status(order) -> dict | None:
    """Validate order status for refund. Returns error dict or None if valid."""
    if order.refund_requested:
        return {"success": False, "reason": "Refund already requested"}

    status_lower = (order.status or "").lower()
    if status_lower in FORBIDDEN_REFUND_STATUSES:
        return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}
    if status_lower not in ALLOWED_REFUND_STATUSES:
        return {"success": False, "reason": f"Refund not allowed for status '{order.status}'"}

    return None


# =============================================================================
# Service Class
# =============================================================================


class SupportService:
    """Support domain service."""

    def __init__(self, db) -> None:
        self.db = db

    async def create_ticket(
        self,
        user_id: str,
        message: str,
        order_id: str | None = None,
        item_id: str | None = None,
        issue_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a support ticket."""
        try:
            # Anti-abuse checks for replacement requests
            if issue_type == "replacement" and item_id:
                validation_error = await _validate_replacement_request(
                    self.db, user_id, item_id, order_id,
                )
                if validation_error:
                    return validation_error

            ticket_data = {
                "user_id": user_id,
                "description": message,
                "status": "open",
            }
            if order_id:
                ticket_data["order_id"] = order_id
            if item_id:
                ticket_data["item_id"] = item_id
            if issue_type:
                ticket_data["issue_type"] = issue_type

            result = await self.db.client.table("tickets").insert(ticket_data).execute()

            if not result.data:
                return {"success": False, "reason": "Failed to create ticket"}

            ticket_id = result.data[0].get("id")
            await _send_ticket_admin_alert(self.db, ticket_id, user_id, issue_type, order_id)

            return {
                "success": True,
                "ticket_id": ticket_id,
                "message": "Support ticket created",
            }

        except Exception as e:
            logger.error("Failed to create ticket: %s", type(e).__name__, exc_info=True)
            return {"success": False, "reason": "Database error"}

    async def get_faq(self, language: str = "en") -> list[FAQEntry]:
        """Get FAQ entries."""
        try:
            entries = await self.db.get_faq(language)
            return [
                FAQEntry(
                    id=e.get("id", ""),
                    question=e.get("question", ""),
                    answer=e.get("answer", ""),
                    category=e.get("category"),
                )
                for e in entries
            ]
        except Exception as e:
            logger.error("Failed to get FAQ: %s", type(e).__name__, exc_info=True)
            return []

    async def search_faq(self, question: str, language: str = "en") -> FAQEntry | None:
        """Search FAQ for an answer."""
        entries = await self.get_faq(language)
        question_lower = question.lower()

        for entry in entries:
            if any(word in question_lower for word in entry.question.lower().split()):
                return entry

        return None

    async def request_refund(self, user_id: str, order_id: str, reason: str = "") -> dict[str, Any]:
        """Request a refund for an order."""
        # Get order
        order = await self.db.get_order_by_id(order_id)
        if not order:
            return {"success": False, "reason": "Order not found"}

        # Validate ownership
        if order.user_id != user_id:
            return {"success": False, "reason": "Not your order"}

        # Validate status
        status_error = _validate_refund_status(order)
        if status_error:
            return status_error

        # Check refund quota
        try:
            open_count = (
                await self.db.client.table("orders")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("refund_requested", True)
                .execute()
            )
            if (open_count.count or 0) >= MAX_OPEN_REFUNDS_PER_USER:
                return {"success": False, "reason": "Refund request limit reached"}
        except Exception:
            logger.exception("Failed to check refund quota")
            return {"success": False, "reason": "Failed to validate refund limits"}

        # Create ticket and mark order
        try:
            ticket_result = (
                await self.db.client.table("tickets")
                .insert(
                    {
                        "user_id": user_id,
                        "order_id": order_id,
                        "issue_type": "refund",
                        "description": reason,
                        "status": "open",
                    },
                )
                .execute()
            )

            if not ticket_result.data:
                return {"success": False, "reason": "Failed to create support ticket"}

            await (
                self.db.client.table("orders")
                .update({"refund_requested": True})
                .eq("id", order_id)
                .execute()
            )

            return {
                "success": True,
                "message": "Refund request submitted for review",
                "ticket_id": ticket_result.data[0].get("id"),
            }
        except Exception as e:
            logger.error("Failed to process refund request: %s", type(e).__name__, exc_info=True)
            return {"success": False, "reason": "Failed to process refund request"}

    async def get_user_tickets(
        self, user_id: str, status: str | None = None, limit: int = 20,
    ) -> list[SupportTicket]:
        """Get user's support tickets."""
        try:
            query = self.db.client.table("tickets").select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status)
            query = query.order("created_at", desc=True).limit(limit)

            result = await query.execute()

            return [
                SupportTicket(
                    id=t.get("id", ""),
                    user_id=t.get("user_id", ""),
                    order_id=t.get("order_id"),
                    issue_type=t.get("issue_type"),
                    message=t.get("message", t.get("description", "")),
                    status=t.get("status", "unknown"),
                )
                for t in result.data or []
            ]
        except Exception as e:
            logger.error("Failed to get user tickets: %s", type(e).__name__, exc_info=True)
            return []
