"""Referral Workers.

QStash workers for referral program operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request

from core.logging import get_logger, sanitize_id_for_logging
from core.routers.deps import get_notification_service, verify_qstash
from core.services.database import get_database
from core.services.money import to_float

logger = get_logger(__name__)

referral_router = APIRouter()


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _queue_replacement_for_stock(db: Any, ticket_id: str) -> None:
    """Queue ticket for replacement when stock becomes available."""
    await (
        db.client.table("insurance_replacements")
        .update(
            {
                "status": "queued",
                "notes": "Queued for auto-delivery when stock available",
            },
        )
        .eq("id", ticket_id)
        .execute()
    )

    logger.info(
        "Ticket %s queued for replacement when stock available",
        sanitize_id_for_logging(ticket_id),
    )


async def _notify_replacement_queued(
    notification_service: Any,
    user_telegram_id: int | None,
    _product_id: str,
) -> None:
    """Send notification about queued replacement. product_id kept for API consistency."""
    if not user_telegram_id:
        return

    try:
        await notification_service.send_system_notification(
            telegram_id=user_telegram_id,
            message=(
                "📋 Ваш запрос на замену добавлен в очередь.\n\n"
                "Мы автоматически доставим новый товар, когда он появится на складе."
            ),
        )
    except Exception as e:
        logger.warning("Failed to send replacement queued notification: %s", type(e).__name__)


async def _validate_replacement_ticket(db, ticket_id: str) -> dict | None:
    """Validate ticket exists and is approved for replacement (reduces complexity)."""
    ticket_res = (
        await db.client.table("tickets")
        .select("id, status, issue_type, user_id, order_id, item_id")
        .eq("id", ticket_id)
        .single()
        .execute()
    )

    if not ticket_res.data:
        return {"error": "Ticket not found"}

    if ticket_res.data["status"] != "approved":
        return {
            "skipped": True,
            "reason": f"Ticket status is {ticket_res.data['status']}, not approved",
        }

    if ticket_res.data["issue_type"] != "replacement":
        return {
            "skipped": True,
            "reason": f"Ticket issue_type is {ticket_res.data['issue_type']}, not replacement",
        }

    return None  # Valid ticket


async def _get_order_item_for_replacement(
    db: Any, item_id: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Get order item data for replacement (reduces complexity)."""
    item_res = (
        await db.client.table("order_items")
        .select("id, order_id, product_id, status, delivery_content, quantity")
        .eq("id", item_id)
        .single()
        .execute()
    )

    if not item_res.data:
        logger.error(
            "process-replacement: Order item %s not found",
            sanitize_id_for_logging(item_id),
        )
        return None, {"error": "Order item not found"}

    item_data = item_res.data  # .single() returns a dict, not a list
    if item_data.get("status") != "delivered":
        return None, {
            "skipped": True,
            "reason": f"Item status is {item_data.get('status')}, must be delivered",
        }

    return item_data, None


async def _reserve_stock_for_replacement(
    db: Any,
    product_id: str,
    now: datetime,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Find and reserve stock for replacement (reduces complexity)."""
    stock_res = (
        await db.client.table("stock_items")
        .select("id, content")
        .eq("product_id", product_id)
        .eq("status", "available")
        .limit(1)
        .execute()
    )

    if not stock_res.data:
        return None, None  # No stock available

    stock_item = stock_res.data[0]
    stock_id = stock_item["id"]

    try:
        update_result = (
            await db.client.table("stock_items")
            .update({"status": "sold", "reserved_at": now.isoformat(), "sold_at": now.isoformat()})
            .eq("id", stock_id)
            .eq("status", "available")
            .execute()
        )

        if not update_result.data:
            logger.warning(
                "process-replacement: stock %s was already reserved",
                sanitize_id_for_logging(stock_id),
            )
            return None, {
                "queued": True,
                "reason": "Stock item was already reserved - will retry",
                "ticket_status": "approved",
            }
    except Exception as e:
        error_type = type(e).__name__
        logger.warning(
            "process-replacement: Failed to mark stock sold %s: %s",
            sanitize_id_for_logging(stock_id),
            error_type,
        )
        return None, {"error": "Failed to reserve stock"}

    return stock_item, None


async def _rollback_stock_reservation(db: Any, stock_id: str) -> None:
    """Rollback stock reservation on failure (reduces complexity)."""
    try:
        await (
            db.client.table("stock_items")
            .update({"status": "available", "reserved_at": None, "sold_at": None})
            .eq("id", stock_id)
            .execute()
        )
    except Exception:
        logger.exception("process-replacement: Failed to rollback stock item")


async def _update_order_item_with_replacement(
    db: Any,
    item_id: str,
    stock_id: str,
    stock_content: str,
    expires_at_str: str | None,
    now: datetime,
) -> dict[str, Any] | None:
    """Update order item with replacement content (reduces complexity)."""
    update_data = {
        "stock_item_id": stock_id,
        "delivery_content": stock_content,
        "updated_at": now.isoformat(),
        "status": "delivered",
    }
    if expires_at_str:
        update_data["expires_at"] = expires_at_str

    try:
        await db.client.table("order_items").update(update_data).eq("id", item_id).execute()
        logger.info(
            "process-replacement: Replaced key for order_item %s (1 key replaced)",
            sanitize_id_for_logging(item_id),
        )
        return None
    except Exception as e:
        error_type = type(e).__name__
        logger.warning(
            "process-replacement: Failed to update order item %s: %s",
            sanitize_id_for_logging(item_id),
            error_type,
        )
        return {"error": "Failed to update order item"}


async def _close_replacement_ticket(db: Any, ticket_id: str) -> None:
    """Close ticket after successful replacement (reduces complexity)."""
    await (
        db.client.table("tickets")
        .update(
            {
                "status": "closed",
                "admin_comment": "Replacement completed automatically. New account delivered.",
            },
        )
        .eq("id", ticket_id)
        .execute()
    )


async def _notify_replacement_success(
    notification_service: Any,
    user_telegram_id: int | None,
    product_name: str,
    item_id: str,
    credentials: str | None = None,
) -> None:
    """Send notification about successful replacement (reduces complexity)."""
    if not user_telegram_id:
        return

    try:
        await notification_service.send_replacement_notification(
            telegram_id=user_telegram_id,
            product_name=product_name,
            item_id=item_id[:8],
            credentials=credentials,
        )
    except Exception as e:
        error_type = type(e).__name__
        logger.warning("process-replacement: Failed to send notification: %s", error_type)


async def _get_user_telegram_id_from_order(
    db: Any, order_id: str
) -> int | None:
    """Get user telegram_id from order (reduces cognitive complexity)."""
    order_res = (
        await db.client.table("orders")
        .select("user_telegram_id")
        .eq("id", order_id)
        .single()
        .execute()
    )
    if (
        order_res.data
        and isinstance(order_res.data, dict)
        and order_res.data.get("user_telegram_id")
    ):
        return int(order_res.data.get("user_telegram_id", 0))
    return None


async def _handle_no_stock_replacement(
    db: Any,
    notification_service: Any,
    ticket_id: str,
    user_telegram_id: int | None,
    product_id_str: str,
) -> dict[str, Any]:
    """Handle case when no stock is available for replacement (reduces cognitive complexity)."""
    await _queue_replacement_for_stock(db, ticket_id)
    await _notify_replacement_queued(notification_service, user_telegram_id, product_id_str)
    return {
        "queued": True,
        "reason": "No stock available - queued for auto-delivery",
        "ticket_status": "approved",
    }


async def _get_product_info_for_replacement(
    db: Any, product_id: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Get product info for replacement (reduces cognitive complexity)."""
    product_res = (
        await db.client.table("products")
        .select("duration_days, name")
        .eq("id", product_id)
        .single()
        .execute()
    )

    if not product_res.data:
        logger.error(
            "process-replacement: Product %s not found",
            sanitize_id_for_logging(product_id),
        )
        return (None, {"error": "Product not found"})

    product = product_res.data if isinstance(product_res.data, dict) else {}
    return (product, None)


async def _process_stock_replacement(
    db: Any,
    notification_service: Any,
    ticket_id: str,
    item_id: str,
    stock_item: dict[str, Any],
    product: dict[str, Any],
    user_telegram_id: int | None,
    now: datetime,
) -> dict[str, Any]:
    """Process stock replacement and update order item (reduces cognitive complexity)."""
    stock_id = stock_item["id"]
    stock_content = stock_item.get("content", "")

    product_name = str(product.get("name", "Product"))
    duration_days = float(product.get("duration_days", 0)) if product.get("duration_days") else 0

    # Calculate expires_at
    expires_at_str = None
    if duration_days and duration_days > 0:
        expires_at_str = (now + timedelta(days=float(duration_days))).isoformat()

    # Update order item with replacement
    update_error = await _update_order_item_with_replacement(
        db,
        item_id,
        stock_id,
        stock_content,
        expires_at_str,
        now,
    )
    if update_error:
        await _rollback_stock_reservation(db, stock_id)
        return update_error

    # Close ticket and notify
    await _close_replacement_ticket(db, ticket_id)
    await _notify_replacement_success(
        notification_service,
        user_telegram_id,
        product_name,
        str(item_id) if item_id else "",
        credentials=stock_content,
    )

    logger.info(
        "process-replacement: Successfully replaced key for item %s",
        sanitize_id_for_logging(item_id),
    )

    return {
        "success": True,
        "item_id": item_id,
        "stock_id": stock_id,
        "ticket_id": ticket_id,
        "message": "Replacement completed (1 key replaced)",
    }


async def _get_buyer_name(db, buyer_id: str) -> str:
    """Get buyer name for notification (reduces cognitive complexity)."""
    buyer_result = (
        await db.client.table("users")
        .select("username, first_name")
        .eq("id", buyer_id)
        .single()
        .execute()
    )
    if not buyer_result.data:
        return "Реферал"
    return buyer_result.data.get("username") or buyer_result.data.get("first_name") or "Реферал"


async def _send_level_bonus_notification(
    db: Any,
    notification_service: Any,
    buyer_id: str,
    buyer_name: str,
    level: int,
    bonus_amount: float,
    purchase_amount: float,
) -> None:
    """Send notification for a specific level bonus (reduces cognitive complexity)."""
    bonus_record = (
        await db.client.table("referral_bonuses")
        .select("user_id, users(telegram_id)")
        .eq("from_user_id", buyer_id)
        .eq("level", level)
        .eq("eligible", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not bonus_record.data:
        return

    referrer_telegram_id = bonus_record.data[0].get("users", {}).get("telegram_id")
    if not referrer_telegram_id:
        return

    try:
        await notification_service.send_referral_bonus_notification(
            telegram_id=referrer_telegram_id,
            bonus_amount=float(bonus_amount),
            referral_name=buyer_name,
            purchase_amount=purchase_amount,
            line=level,
        )
    except Exception as e:
        logger.warning("Failed to send referral bonus notification (level %s): %s", level, e)


async def _send_referral_bonus_notifications(
    db: Any,
    notification_service: Any,
    bonuses: dict[str, Any],
    buyer_id: str,
    purchase_amount: float,
) -> None:
    """Send notifications to referrers about their earned bonuses."""
    if not bonuses or not bonuses.get("success"):
        return

    try:
        buyer_name = await _get_buyer_name(db, buyer_id)

        for level in [1, 2, 3]:
            bonus_key = f"level{level}"
            bonus_amount = bonuses.get(bonus_key)

            if bonus_amount and float(bonus_amount) > 0:
                await _send_level_bonus_notification(
                    db,
                    notification_service,
                    buyer_id,
                    buyer_name,
                    level,
                    bonus_amount,
                    purchase_amount,
                )
    except Exception as e:
        logger.warning("Failed to send referral bonus notifications: %s", e)


# Helper to unlock referral program (reduces cognitive complexity)
async def _unlock_referral_program(
    db: Any,
    user_id: str,
    was_unlocked: bool,
    is_partner: bool,
    telegram_id: int | None,
    notification_service: Any,
) -> None:
    """Unlock referral program for first purchase (reduces cognitive complexity)."""
    if was_unlocked:
        return

    await (
        db.client.table("users")
        .update({"referral_program_unlocked": True})
        .eq("id", user_id)
        .execute()
    )

    if not is_partner and telegram_id:
        await notification_service.send_referral_unlock_notification(telegram_id)
    elif is_partner:
        logger.debug("VIP partner %s first purchase - skipping unlock notification", user_id)


# Helper to send level up notification (reduces cognitive complexity)
async def _send_level_up_notification(
    level_up: bool,
    new_level: int,
    telegram_id: int | None,
    is_partner: bool,
    partner_level_override: int | None,
    user_id: str,
    notification_service: Any,
) -> None:
    """Send level up notification if applicable (reduces cognitive complexity)."""
    if not (level_up and new_level > 0 and telegram_id):
        return

    if is_partner and partner_level_override == 3:
        logger.debug(
            "Skipping level_up notification for VIP partner %s (already has level 3)",
            user_id,
        )
        return

    await notification_service.send_referral_level_up_notification(telegram_id, new_level)


@referral_router.post("/calculate-referral")
async def worker_calculate_referral(request: Request) -> dict[str, Any]:
    """QStash Worker: Calculate and apply referral bonuses.

    Logic:
    1. Update buyer's turnover (in USD) - recalculates as own orders + referral orders (may unlock new levels)
    2. Check if referral program should be unlocked (first purchase)
    3. Process referral bonuses - ONLY for levels that referrer has unlocked
    """
    data = await verify_qstash(request)
    order_id = data.get("order_id")
    usd_rate = data.get("usd_rate", 100)

    if not order_id:
        return {"error": "order_id required"}

    db = get_database()
    notification_service = get_notification_service()

    order = (
        await db.client.table("orders")
        .select(
            "amount, user_id, user_telegram_id, users(referrer_id, referral_program_unlocked, is_partner, partner_level_override)",
        )
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order.data:
        return {"error": "Order not found"}

    user_id_val = order.data.get("user_id")
    user_id = str(user_id_val) if user_id_val else ""
    amount_val = order.data.get("amount", 0)
    amount = to_float(str(amount_val) if not isinstance(amount_val, (int, float)) else amount_val)
    telegram_id_val = order.data.get("user_telegram_id")
    telegram_id = (
        int(telegram_id_val)
        if telegram_id_val and isinstance(telegram_id_val, (int, str))
        else None
    )
    users_data = order.data.get("users", {})
    if not isinstance(users_data, dict):
        users_data = {}
    was_unlocked = bool(users_data.get("referral_program_unlocked", False))
    is_partner = bool(users_data.get("is_partner", False))
    partner_level_override_val = users_data.get("partner_level_override")
    partner_level_override = (
        int(partner_level_override_val)
        if partner_level_override_val and isinstance(partner_level_override_val, (int, str))
        else None
    )

    # Update buyer's turnover
    turnover_result = await db.client.rpc(
        "update_user_turnover",
        {"p_user_id": user_id, "p_amount_rub": float(amount), "p_usd_rate": float(usd_rate)},
    ).execute()

    turnover_data = turnover_result.data if isinstance(turnover_result.data, dict) else {}
    level_up = bool(turnover_data.get("level_up", False))
    new_level = int(turnover_data.get("new_level", 0))

    # Unlock referral program
    await _unlock_referral_program(
        db,
        user_id,
        was_unlocked,
        is_partner,
        telegram_id,
        notification_service,
    )

    # Send level up notification
    await _send_level_up_notification(
        level_up,
        new_level,
        telegram_id,
        is_partner,
        partner_level_override,
        user_id,
        notification_service,
    )

    # Process referral bonuses
    referrer_id = str(users_data.get("referrer_id", "")) if users_data.get("referrer_id") else None
    if not referrer_id:
        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "bonuses": "no_referrer",
        }

    try:
        bonus_result = await db.client.rpc(
            "process_referral_bonus",
            {"p_buyer_id": user_id, "p_order_id": order_id, "p_order_amount": amount},
        ).execute()
        bonuses = bonus_result.data if isinstance(bonus_result.data, dict) else {}

        # Send notifications to referrers about earned bonuses
        await _send_referral_bonus_notifications(db, notification_service, bonuses, user_id, amount)

        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "level_up": level_up,
            "new_level": new_level,
            "bonuses": bonuses,
        }
    except Exception as e:
        # If referral program not unlocked or percent is null, skip bonus and continue
        error_type = type(e).__name__
        logger.warning(
            "Referral bonus failed for order %s: %s",
            sanitize_id_for_logging(order_id),
            error_type,
        )
        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "level_up": level_up,
            "new_level": new_level,
            "bonuses": "skipped_due_to_error",
        }


@referral_router.post("/process-replacement")
async def worker_process_replacement(request: Request) -> dict[str, Any]:
    """QStash Worker: Process account replacement for approved replacement tickets.

    Finds new stock item for the same product and updates order_item with new credentials.
    """
    data = await verify_qstash(request)
    ticket_id = data.get("ticket_id")
    item_id = data.get("item_id")

    if not ticket_id or not item_id:
        return {"error": "ticket_id and item_id required"}

    db = get_database()
    notification_service = get_notification_service()

    # Validate ticket
    ticket_error = await _validate_replacement_ticket(db, ticket_id)
    if ticket_error:
        return ticket_error

    # Get order item
    item_data, item_error = await _get_order_item_for_replacement(db, item_id)
    if item_error:
        return item_error

    product_id = item_data.get("product_id")
    order_id_from_item = item_data.get("order_id")

    # Get user telegram_id for notifications
    user_telegram_id = await _get_user_telegram_id_from_order(db, order_id_from_item)

    # Reserve stock
    now = datetime.now(UTC)
    product_id_str = str(product_id) if product_id else ""
    stock_item, reserve_error = await _reserve_stock_for_replacement(db, product_id_str, now)

    if not stock_item and not reserve_error:
        # No stock available - queue for later
        return await _handle_no_stock_replacement(
            db, notification_service, ticket_id, user_telegram_id, product_id_str
        )

    if reserve_error:
        return reserve_error

    # Get product info for expiration
    product, product_error = await _get_product_info_for_replacement(db, product_id_str)
    if product_error:
        await _rollback_stock_reservation(db, stock_item["id"])
        return product_error

    # Process stock replacement
    return await _process_stock_replacement(
        db,
        notification_service,
        ticket_id,
        item_id,
        stock_item,
        product,
        user_telegram_id,
        now,
    )
