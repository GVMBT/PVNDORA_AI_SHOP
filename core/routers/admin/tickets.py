"""
Admin Tickets Router

Support ticket management endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import verify_admin
from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

router = APIRouter(prefix="/tickets", tags=["admin-tickets"])


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

        tickets = []
        for t in result.data or []:
            user_data = t.pop("users", {}) or {}
            order_item_data = t.pop("order_items", {}) or {}
            product_data = order_item_data.get("products", {}) or {} if order_item_data else {}

            tickets.append(
                {
                    **t,
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "telegram_id": user_data.get("telegram_id"),
                    # Credentials for admin verification
                    "credentials": (
                        order_item_data.get("delivery_content") if order_item_data else None
                    ),
                    "product_name": product_data.get("name") if product_data else None,
                }
            )

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

        # Extract credentials for admin verification
        ticket_data = result.data
        order_item_data = ticket_data.pop("order_items", {}) or {}
        product_data = order_item_data.get("products", {}) or {} if order_item_data else {}

        ticket_data["credentials"] = (
            order_item_data.get("delivery_content") if order_item_data else None
        )
        ticket_data["product_name"] = product_data.get("name") if product_data else None

        return {"ticket": ticket_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching ticket {ticket_id}")
        raise HTTPException(status_code=500, detail=str(e))


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
        # Get full ticket data including issue_type and item_id
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

        ticket_data = ticket_res.data
        issue_type = ticket_data.get("issue_type")
        item_id = ticket_data.get("item_id")
        order_id = ticket_data.get("order_id")
        user_data = ticket_data.get("users", {}) or {}
        user_telegram_id = user_data.get("telegram_id")
        user_language = user_data.get("language_code", "en")

        new_status = "approved" if approve else "rejected"
        update_data = {"status": new_status}
        if comment:
            update_data["admin_comment"] = comment

        await db.client.table("tickets").update(update_data).eq("id", ticket_id).execute()

        notification_service = get_notification_service()

        # If REJECTED, notify user
        if not approve and user_telegram_id:
            try:
                await notification_service.send_ticket_rejected_notification(
                    telegram_id=user_telegram_id,
                    ticket_id=ticket_id[:8],
                    reason=comment or "Your request was reviewed and could not be approved.",
                    language=user_language,
                )
                logger.info(f"Sent rejection notification for ticket {ticket_id}")
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}", exc_info=True)

        # If APPROVED, trigger automatic processing via QStash
        if approve and new_status == "approved":
            try:
                from core.routers.deps import get_queue_publisher

                publish_to_worker, WorkerEndpoints = get_queue_publisher()

                if issue_type == "replacement" and item_id:
                    # Trigger replacement worker - will queue if no stock
                    await publish_to_worker(
                        WorkerEndpoints.PROCESS_REPLACEMENT,
                        {"ticket_id": ticket_id, "item_id": item_id, "order_id": order_id},
                    )
                    logger.info(
                        f"Triggered replacement worker for ticket {ticket_id}, item {item_id}"
                    )

                    # Notify user that replacement is being processed
                    if user_telegram_id:
                        await notification_service.send_ticket_approved_notification(
                            telegram_id=user_telegram_id,
                            ticket_id=ticket_id[:8],
                            issue_type=issue_type,
                            language=user_language,
                        )

                elif issue_type == "refund" and order_id:
                    # Trigger refund worker
                    # Get order amount and exchange rate snapshot
                    order_res = (
                        await db.client.table("orders")
                        .select("amount, user_telegram_id, exchange_rate_snapshot, fiat_currency")
                        .eq("id", order_id)
                        .single()
                        .execute()
                    )

                    if order_res.data:
                        # Use exchange rate from order snapshot (or default to 1.0 for USD)
                        usd_rate = float(order_res.data.get("exchange_rate_snapshot") or 1.0)

                        await publish_to_worker(
                            WorkerEndpoints.PROCESS_REFUND,
                            {
                                "order_id": order_id,
                                "reason": comment or "Refund approved by admin",
                                "usd_rate": usd_rate,
                                "fiat_currency": order_res.data.get("fiat_currency", "USD"),
                            },
                        )
                        logger.info(
                            f"Triggered refund worker for ticket {ticket_id}, order {order_id}"
                        )

                        # Notify user that refund is being processed
                        if user_telegram_id:
                            await notification_service.send_ticket_approved_notification(
                                telegram_id=user_telegram_id,
                                ticket_id=ticket_id[:8],
                                issue_type=issue_type,
                                language=user_language,
                            )

            except Exception as e:
                # Log error but don't fail the request - ticket is already updated
                logger.error(
                    "Failed to trigger automatic processing for ticket %s: %s", ticket_id, e,
                    exc_info=True,
                )

        return {"success": True, "status": new_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error resolving ticket {ticket_id}")
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
        logger.exception(f"Error closing ticket {ticket_id}")
        raise HTTPException(status_code=500, detail=str(e))
