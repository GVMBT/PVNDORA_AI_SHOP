"""
Admin Tickets Router

Support ticket management endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import verify_admin
from core.logging import get_logger, sanitize_id_for_logging
from core.services.database import get_database

logger = get_logger(__name__)

router = APIRouter(prefix="/tickets", tags=["admin-tickets"])

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def _format_ticket_data(ticket_row: dict) -> dict:
    """Format ticket data with user and order item info (reduces cognitive complexity)."""
    user_data = ticket_row.get("users", {}) or {}
    order_item_data = ticket_row.get("order_items", {}) or {}
    product_data = order_item_data.get("products", {}) or {} if order_item_data else {}

    formatted = {k: v for k, v in ticket_row.items() if k not in ("users", "order_items")}
    formatted.update(
        {
            "username": user_data.get("username"),
            "first_name": user_data.get("first_name"),
            "telegram_id": user_data.get("telegram_id"),
            "credentials": order_item_data.get("delivery_content") if order_item_data else None,
            "product_name": product_data.get("name") if product_data else None,
        }
    )
    return formatted


@router.get("")
async def get_tickets(
    status: str = Query(
        "open", description="Filter by status: open, approved, rejected, closed, all"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin=Depends(verify_admin),
):
    """Get support tickets with optional status filter. Includes item credentials for admin verification."""
    db = get_database()

    try:
        # Join with order_items to get credentials (delivery_content) for verification
        query = (
            db.client.table("tickets")
            .select(
                "*, users(username, first_name, telegram_id), order_items(delivery_content, products(name))"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        if status and status != "all":
            query = query.eq("status", status)

        result = await query.execute()

        tickets = [_format_ticket_data(t) for t in (result.data or [])]

        return {"tickets": tickets, "count": len(tickets)}

    except Exception as e:
        logger.exception("Error fetching tickets")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, admin=Depends(verify_admin)):
    """Get single ticket by ID with credentials for admin verification."""
    db = get_database()

    try:
        result = (
            await db.client.table("tickets")
            .select(
                "*, users(username, first_name, telegram_id), orders(id, amount, status), order_items(delivery_content, products(name))"
            )
            .eq("id", ticket_id)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Format ticket data using helper
        ticket_data = _format_ticket_data(result.data)

        return {"ticket": ticket_data}

    except HTTPException:
        raise
    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.exception("Error fetching ticket %s", sanitize_id_for_logging(ticket_id))
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions for resolve_ticket
async def _fetch_and_validate_ticket(db, ticket_id: str) -> dict:
    """Fetch ticket data and validate it can be resolved."""
    ticket_res = (
        await db.client.table("tickets")
        .select(
            "id, status, issue_type, item_id, order_id, user_id, users(telegram_id, language_code)"
        )
        .eq("id", ticket_id)
        .single()
        .execute()
    )

    if not ticket_res.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket_res.data["status"] != "open":
        raise HTTPException(
            status_code=400, detail=f"Ticket is already {ticket_res.data['status']}"
        )

    return ticket_res.data


async def _update_ticket_status(db, ticket_id: str, new_status: str, comment: str | None) -> None:
    """Update ticket status in database."""
    update_data = {"status": new_status}
    if comment:
        update_data["admin_comment"] = comment

    await db.client.table("tickets").update(update_data).eq("id", ticket_id).execute()


async def _handle_rejected_ticket(
    notification_service,
    ticket_id: str,
    user_telegram_id: int | None,
    user_language: str,
    comment: str | None,
) -> None:
    """Handle rejected ticket notification."""
    if not user_telegram_id:
        return

    try:
        await notification_service.send_ticket_rejected_notification(
            telegram_id=user_telegram_id,
            ticket_id=ticket_id[:8],
            reason=comment or "Your request was reviewed and could not be approved.",
            _language=user_language,
        )
        logger.info("Sent rejection notification for ticket %s", sanitize_id_for_logging(ticket_id))
    except Exception as e:
        logger.error("Failed to send rejection notification: %s", e, exc_info=True)


async def _handle_approved_replacement(
    publish_to_worker,
    endpoints,
    notification_service,
    ticket_id: str,
    item_id: str,
    order_id: str | None,
    issue_type: str,
    user_telegram_id: int | None,
    user_language: str,
) -> None:
    """Handle approved replacement ticket - trigger worker and notify user."""
    await publish_to_worker(
        endpoints.PROCESS_REPLACEMENT,
        {"ticket_id": ticket_id, "item_id": item_id, "order_id": order_id},
    )
    logger.info(
        "Triggered replacement worker for ticket %s, item %s",
        sanitize_id_for_logging(ticket_id),
        sanitize_id_for_logging(item_id),
    )

    if user_telegram_id:
        await notification_service.send_ticket_approved_notification(
            telegram_id=user_telegram_id,
            ticket_id=ticket_id[:8],
            issue_type=issue_type,
            _language=user_language,
        )


async def _handle_approved_refund(
    db,
    publish_to_worker,
    endpoints,
    notification_service,
    ticket_id: str,
    order_id: str,
    issue_type: str,
    user_telegram_id: int | None,
    user_language: str,
    comment: str | None,
) -> None:
    """Handle approved refund ticket - get order data, trigger worker and notify user."""
    order_res = (
        await db.client.table("orders")
        .select("amount, user_telegram_id, exchange_rate_snapshot, fiat_currency")
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order_res.data:
        return

    usd_rate = float(order_res.data.get("exchange_rate_snapshot") or 1.0)

    await publish_to_worker(
        endpoints.PROCESS_REFUND,
        {
            "order_id": order_id,
            "reason": comment or "Refund approved by admin",
            "usd_rate": usd_rate,
            "fiat_currency": order_res.data.get("fiat_currency", "USD"),
        },
    )
    logger.info(
        "Triggered refund worker for ticket %s, order %s",
        sanitize_id_for_logging(ticket_id),
        sanitize_id_for_logging(order_id),
    )

    if user_telegram_id:
        await notification_service.send_ticket_approved_notification(
            telegram_id=user_telegram_id,
            ticket_id=ticket_id[:8],
            issue_type=issue_type,
            _language=user_language,
        )


async def _process_approved_ticket(
    db,
    notification_service,
    ticket_id: str,
    issue_type: str,
    item_id: str | None,
    order_id: str | None,
    user_telegram_id: int | None,
    user_language: str,
    comment: str | None,
) -> None:
    """Process approved ticket - trigger appropriate worker based on issue type."""
    try:
        from core.routers.deps import get_queue_publisher

        publish_to_worker, endpoints = get_queue_publisher()

        if issue_type == "replacement" and item_id:
            await _handle_approved_replacement(
                publish_to_worker,
                endpoints,
                notification_service,
                ticket_id,
                item_id,
                order_id,
                issue_type,
                user_telegram_id,
                user_language,
            )
        elif issue_type == "refund" and order_id:
            await _handle_approved_refund(
                db,
                publish_to_worker,
                endpoints,
                notification_service,
                ticket_id,
                order_id,
                issue_type,
                user_telegram_id,
                user_language,
                comment,
            )
    except Exception as e:
        logger.error(
            "Failed to trigger automatic processing for ticket: %s",
            type(e).__name__,
            exc_info=True,
        )


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    approve: bool = Query(True, description="Approve (true) or reject (false)"),
    comment: str | None = Query(None, description="Admin comment"),
    admin=Depends(verify_admin),
):
    """Resolve a support ticket (approve or reject). Notifies user of decision."""
    db = get_database()
    from core.routers.deps import get_notification_service

    try:
        ticket_data = await _fetch_and_validate_ticket(db, ticket_id)

        issue_type = ticket_data.get("issue_type")
        item_id = ticket_data.get("item_id")
        order_id = ticket_data.get("order_id")
        user_data = ticket_data.get("users", {}) or {}
        user_telegram_id = user_data.get("telegram_id")
        user_language = user_data.get("language_code", "en")

        new_status = "approved" if approve else "rejected"
        await _update_ticket_status(db, ticket_id, new_status, comment)

        notification_service = get_notification_service()

        if not approve:
            await _handle_rejected_ticket(
                notification_service, ticket_id, user_telegram_id, user_language, comment
            )
        else:
            await _process_approved_ticket(
                db,
                notification_service,
                ticket_id,
                issue_type,
                item_id,
                order_id,
                user_telegram_id,
                user_language,
                comment,
            )

        return {"success": True, "status": new_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error resolving ticket %s", sanitize_id_for_logging(ticket_id))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: str, comment: str | None = Query(None), admin=Depends(verify_admin)
):
    """Close a ticket."""
    db = get_database()

    try:
        update_data = {"status": "closed"}
        if comment:
            update_data["admin_comment"] = comment

        await db.client.table("tickets").update(update_data).eq("id", ticket_id).execute()

        return {"success": True, "status": "closed"}

    except Exception as e:
        from core.logging import sanitize_id_for_logging

        logger.exception("Error closing ticket %s", sanitize_id_for_logging(ticket_id))
        raise HTTPException(status_code=500, detail=str(e))
