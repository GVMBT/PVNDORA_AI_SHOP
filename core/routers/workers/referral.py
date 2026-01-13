"""
Referral Workers

QStash workers for referral program operations.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request

from core.logging import get_logger
from core.routers.deps import get_notification_service, verify_qstash
from core.services.database import get_database
from core.services.money import to_float

logger = get_logger(__name__)

referral_router = APIRouter()


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
    return (
        buyer_result.data.get("username")
        or buyer_result.data.get("first_name")
        or "Реферал"
    )


async def _send_level_bonus_notification(
    db, notification_service, buyer_id: str, buyer_name: str, level: int, bonus_amount: float, purchase_amount: float
):
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
    db, notification_service, bonuses: dict, buyer_id: str, purchase_amount: float
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
                    db, notification_service, buyer_id, buyer_name, level, bonus_amount, purchase_amount
                )
    except Exception as e:
        logger.warning("Failed to send referral bonus notifications: %s", e)


# Helper to unlock referral program (reduces cognitive complexity)
async def _unlock_referral_program(
    db, user_id: str, was_unlocked: bool, is_partner: bool, telegram_id: int | None, notification_service
):
    """Unlock referral program for first purchase (reduces cognitive complexity)."""
    if was_unlocked:
        return

    await db.client.table("users").update({"referral_program_unlocked": True}).eq(
        "id", user_id
    ).execute()

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
    notification_service,
):
    """Send level up notification if applicable (reduces cognitive complexity)."""
    if not (level_up and new_level > 0 and telegram_id):
        return

    if is_partner and partner_level_override == 3:
        logger.debug("Skipping level_up notification for VIP partner %s (already has level 3)", user_id)
        return

    await notification_service.send_referral_level_up_notification(telegram_id, new_level)


@referral_router.post("/calculate-referral")
async def worker_calculate_referral(request: Request):
    """
    QStash Worker: Calculate and apply referral bonuses.

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
            "amount, user_id, user_telegram_id, users(referrer_id, referral_program_unlocked, is_partner, partner_level_override)"
        )
        .eq("id", order_id)
        .single()
        .execute()
    )

    if not order.data:
        return {"error": "Order not found"}

    user_id = order.data.get("user_id")
    amount = to_float(order.data["amount"])
    telegram_id = order.data.get("user_telegram_id")
    was_unlocked = order.data.get("users", {}).get("referral_program_unlocked", False)
    is_partner = order.data.get("users", {}).get("is_partner", False)
    partner_level_override = order.data.get("users", {}).get("partner_level_override")

    # Update buyer's turnover
    turnover_result = await db.client.rpc(
        "update_user_turnover",
        {"p_user_id": user_id, "p_amount_rub": amount, "p_usd_rate": usd_rate},
    ).execute()

    turnover_data = turnover_result.data if turnover_result.data else {}
    level_up = turnover_data.get("level_up", False)
    new_level = turnover_data.get("new_level", 0)

    # Unlock referral program
    await _unlock_referral_program(
        db, user_id, was_unlocked, is_partner, telegram_id, notification_service
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
    referrer_id = order.data.get("users", {}).get("referrer_id")
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
        bonuses = bonus_result.data if bonus_result.data else {}

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
        logger.warning(f"Referral bonus failed for order {order_id}: {e}", exc_info=True)
        return {
            "success": True,
            "turnover": turnover_data,
            "first_unlock": not was_unlocked,
            "level_up": level_up,
            "new_level": new_level,
            "bonuses": "skipped_due_to_error",
        }


@referral_router.post("/process-replacement")
async def worker_process_replacement(request: Request):
    """
    QStash Worker: Process account replacement for approved replacement tickets.

    Finds new stock item for the same product and updates order_item with new credentials.
    """
    data = await verify_qstash(request)
    ticket_id = data.get("ticket_id")
    item_id = data.get("item_id")
    # order_id available in data but not used in this worker

    if not ticket_id or not item_id:
        return {"error": "ticket_id and item_id required"}

    db = get_database()
    notification_service = get_notification_service()

    # Get ticket to verify it's approved
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

    # Get order item to replace (include quantity for bulk replacements)
    item_res = (
        await db.client.table("order_items")
        .select("id, order_id, product_id, status, delivery_content, quantity")
        .eq("id", item_id)
        .single()
        .execute()
    )

    if not item_res.data or len(item_res.data) == 0:
        logger.error(f"process-replacement: Order item {item_id} not found")
        return {"error": "Order item not found"}

    item_data = item_res.data[0]
    product_id = item_data.get("product_id")
    order_id_from_item = item_data.get("order_id")
    # NOTE: Each order_item now has quantity=1 (split in persist_order_items)
    # This allows independent processing - replace 1 order_item = replace 1 key

    # Get order to get user_telegram_id
    order_res = (
        await db.client.table("orders")
        .select("user_telegram_id")
        .eq("id", order_id_from_item)
        .single()
        .execute()
    )

    user_telegram_id = None
    if order_res.data:
        user_telegram_id = order_res.data.get("user_telegram_id")

    if item_data.get("status") != "delivered":
        return {
            "skipped": True,
            "reason": f"Item status is {item_data.get('status')}, must be delivered",
        }

    # Find available stock for the same product (need 1 stock item for replacement)
    # Since each order_item = 1 key, we replace 1 order_item = 1 key
    now = datetime.now(UTC)
    stock_res = (
        await db.client.table("stock_items")
        .select("id, content")
        .eq("product_id", product_id)
        .eq("status", "available")
        .limit(1)
        .execute()
    )

    if not stock_res.data:
        # No stock available - keep ticket approved, will be processed by auto_alloc cron
        await db.client.table("tickets").update(
            {
                "admin_comment": "Replacement queued: waiting for stock. Will be auto-delivered when available."
            }
        ).eq("id", ticket_id).execute()

        # Notify user that replacement is queued
        if user_telegram_id:
            try:
                # Get product name for notification
                product_res = (
                    await db.client.table("products")
                    .select("name")
                    .eq("id", product_id)
                    .single()
                    .execute()
                )
                _product_name = (
                    product_res.data.get("name", "Product") if product_res.data else "Product"
                )

                await notification_service.send_message(
                    telegram_id=user_telegram_id,
                    text=(
                        f"⏳ <b>Replacement Queued</b>\n\n"
                        f"Your replacement for {_product_name} has been approved, "
                        f"but no stock is currently available.\n\n"
                        f"You will automatically receive a new account as soon as stock arrives."
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to send queue notification: {e}")

        return {
            "queued": True,
            "reason": "No stock available - queued for auto-delivery",
            "ticket_status": "approved",
        }

    # Reserve 1 stock item for replacement (each order_item = 1 key, simple replacement)
    stock_item = stock_res.data[0]
    stock_id = stock_item["id"]
    stock_content = stock_item.get("content", "")

    # Atomically reserve stock (only update if status is still available)
    try:
        update_result = (
            await db.client.table("stock_items")
            .update({"status": "sold", "reserved_at": now.isoformat(), "sold_at": now.isoformat()})
            .eq("id", stock_id)
            .eq("status", "available")
            .execute()
        )

        if not update_result.data:
            logger.warning(f"process-replacement: stock {stock_id} was already reserved")
            return {
                "queued": True,
                "reason": "Stock item was already reserved - will retry",
                "ticket_status": "approved",
            }
    except Exception as e:
        logger.error(
            f"process-replacement: Failed to mark stock sold {stock_id}: {e}", exc_info=True
        )
        return {"error": "Failed to reserve stock"}

    # Get product info for expiration calculation
    product_res = (
        await db.client.table("products")
        .select("duration_days, name")
        .eq("id", product_id)
        .single()
        .execute()
    )

    if not product_res.data or len(product_res.data) == 0:
        logger.error(f"process-replacement: Product {product_id} not found")
        # Rollback stock reservation
        await db.client.table("stock_items").update(
            {"status": "available", "reserved_at": None, "sold_at": None}
        ).eq("id", stock_id).execute()
        return {"error": f"Product {product_id} not found"}

    product = product_res.data[0]
    duration_days = product.get("duration_days")
    product_name = product.get("name", "Product")

    # Calculate expires_at
    expires_at_str = None
    if duration_days and duration_days > 0:
        expires_at = now + timedelta(days=duration_days)
        expires_at_str = expires_at.isoformat()

    # Update order item: Replace delivery_content with new key (simple replacement)
    # Since each order_item = 1 key, we just replace the key
    # NOTE: delivered_at is NOT updated - warranty period counts from original delivery, not replacement
    # Otherwise users could abuse the system (buy 1-month account, replace it every week for free)
    try:
        update_data = {
            "stock_item_id": stock_id,  # Update stock_item_id reference
            "delivery_content": stock_content,  # Replace with new key (simple replacement)
            "updated_at": now.isoformat(),
            "status": "delivered",  # Ensure status is delivered
        }
        if expires_at_str:
            update_data["expires_at"] = expires_at_str

        await db.client.table("order_items").update(update_data).eq("id", item_id).execute()
        logger.info(f"process-replacement: Replaced key for order_item {item_id} (1 key replaced)")
    except Exception as e:
        logger.error(
            f"process-replacement: Failed to update order item {item_id}: {e}", exc_info=True
        )
        # Rollback stock reservation
        try:
            await db.client.table("stock_items").update(
                {"status": "available", "reserved_at": None, "sold_at": None}
            ).eq("id", stock_id).execute()
        except Exception:
            logger.exception("process-replacement: Failed to rollback stock item")
        return {"error": "Failed to update order item"}

    # Close ticket
    await db.client.table("tickets").update(
        {
            "status": "closed",
            "admin_comment": "Replacement completed automatically. New account delivered.",
        }
    ).eq("id", ticket_id).execute()

    # Notify user
    if user_telegram_id:
        try:
            await notification_service.send_replacement_notification(
                telegram_id=user_telegram_id,
                product_name=product_name,
                item_id=item_id[:8],  # Short ID for display
            )
        except Exception as e:
            logger.error(f"process-replacement: Failed to send notification: {e}", exc_info=True)

    logger.info(
        f"process-replacement: Successfully replaced key for item {item_id} (1 key replaced)"
    )

    return {
        "success": True,
        "item_id": item_id,
        "stock_id": stock_id,
        "ticket_id": ticket_id,
        "message": "Replacement completed (1 key replaced)",
    }
