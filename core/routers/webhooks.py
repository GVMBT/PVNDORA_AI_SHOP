"""
Webhooks Router

CrystalPay payment webhooks.
All webhooks verify signatures and delegate to QStash workers.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import hashlib
import hmac
import json
import os
from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.logging import get_logger
from core.routers.deps import get_notification_service, get_payment_service, get_queue_publisher

logger = get_logger(__name__)

router = APIRouter(tags=["webhooks"])


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


async def _lookup_order_by_payment_id(db, invoice_id: str) -> tuple[dict[str, Any] | None, str]:
    """Lookup order by payment_id."""
    lookup_result = (
        await db.client.table("orders").select("*").eq("payment_id", invoice_id).limit(1).execute()
    )
    if not lookup_result.data:
        return None, ""

    raw_order = lookup_result.data[0]
    if not isinstance(raw_order, dict):
        logger.error("CrystalPay webhook: Invalid order data type: %s", type(raw_order))
        raise TypeError("Invalid order data type")

    order_data = cast(dict[str, Any], raw_order)
    real_order_id = str(order_data.get("id", ""))
    logger.debug("CrystalPay webhook: mapped invoice %s -> order %s", invoice_id, real_order_id)
    return order_data, real_order_id


async def _lookup_order_by_id(db, order_id: str) -> tuple[dict[str, Any] | None, str]:
    """Lookup order by order_id."""
    direct_result = (
        await db.client.table("orders").select("*").eq("id", order_id).limit(1).execute()
    )
    if not direct_result.data:
        return None, ""

    raw_order = direct_result.data[0]
    if not isinstance(raw_order, dict):
        logger.error("CrystalPay webhook: Invalid order data type: %s", type(raw_order))
        raise TypeError("Invalid order data type")

    order_data = cast(dict[str, Any], raw_order)
    real_order_id = str(order_data.get("id", ""))
    return order_data, real_order_id


async def _find_order_data(db, invoice_id: str, order_id: str) -> tuple[dict[str, Any] | None, str]:
    """Find order data by payment_id or order_id."""
    order_data, real_order_id = await _lookup_order_by_payment_id(db, invoice_id)
    if order_data:
        return order_data, real_order_id

    order_data, real_order_id = await _lookup_order_by_id(db, order_id)
    if order_data:
        return order_data, real_order_id

    logger.warning("CrystalPay webhook: Order not found for invoice %s, extra %s", invoice_id, order_id)
    return None, ""


async def _check_stock_availability(db, product_id: str) -> bool:
    """Check if product has available stock."""
    if not product_id:
        return False
    try:
        stock_check = (
            await db.client.table("stock_items")
            .select("id")
            .eq("product_id", product_id)
            .eq("status", "available")
            .limit(1)
            .execute()
        )
        return bool(stock_check.data)
    except Exception as e:
        logger.error("CrystalPay webhook: Stock check error: %s", e, exc_info=True)
        return False


async def _create_refund_ticket(db, order_data: dict[str, Any], real_order_id: str, amount: float) -> None:
    """Create refund ticket for late payment when stock unavailable."""
    user_id = str(order_data.get("user_id", "")) if order_data.get("user_id") else None
    if not user_id:
        return

    try:
        await (
            db.client.table("tickets")
            .insert({
                "user_id": user_id,
                "order_id": real_order_id,
                "issue_type": "refund",
                "description": f"Late payment after order expired. Amount: {amount}. Stock unavailable.",
                "status": "open",
            })
            .execute()
        )
        await (
            db.client.table("orders")
            .update({
                "status": "refund_pending",
                "refund_requested": True,
                "notes": "Late payment - stock unavailable",
            })
            .eq("id", real_order_id)
            .execute()
        )
    except Exception as e:
        logger.error("CrystalPay webhook: Failed to create refund ticket: %s", e, exc_info=True)


async def _handle_cancelled_order_recovery(
    db, order_data: dict[str, Any], real_order_id: str, result: dict[str, Any]
) -> JSONResponse | None:
    """Handle recovery of cancelled order."""
    product_id = str(order_data.get("product_id", "")) if order_data.get("product_id") else None
    can_fulfill = await _check_stock_availability(db, product_id)

    if can_fulfill:
        logger.info("CrystalPay webhook: Restoring order %s - stock available", real_order_id)
        await (
            db.client.table("orders")
            .update({"status": "pending", "notes": "Restored after late payment"})
            .eq("id", real_order_id)
            .execute()
        )
        return None

    logger.warning("CrystalPay webhook: Order %s - no stock, creating refund ticket", real_order_id)
    result_dict = result if isinstance(result, dict) else {}
    amount = float(result_dict.get("amount", 0)) if isinstance(result_dict.get("amount"), (int, float)) else 0.0
    await _create_refund_ticket(db, order_data, real_order_id, amount)
    return JSONResponse({"ok": True, "note": "refund_pending"}, status_code=200)


async def _schedule_discount_delivery(db, order_data: dict[str, Any], real_order_id: str) -> None:
    """Schedule delayed delivery for discount channel orders."""
    order_items = (
        await db.client.table("order_items")
        .select("id, product_id")
        .eq("order_id", real_order_id)
        .limit(1)
        .execute()
    )

    if not order_items.data:
        return

    raw_order_item = order_items.data[0]
    if not isinstance(raw_order_item, dict):
        logger.error(f"CrystalPay webhook: Invalid order_item type: {type(raw_order_item)}")
        raise ValueError("Invalid order_item data")

    order_item = cast(dict[str, Any], raw_order_item)
    product_id = str(order_item.get("product_id", ""))

    stock_result = (
        await db.client.table("stock_items")
        .select("id")
        .eq("product_id", product_id)
        .eq("status", "available")
        .is_("sold_at", "null")
        .limit(1)
        .execute()
    )

    if not stock_result.data:
        logger.warning(f"CrystalPay webhook: No stock for discount order {real_order_id}")
        return

    raw_stock = stock_result.data[0]
    if not isinstance(raw_stock, dict):
        logger.error(f"CrystalPay webhook: Invalid stock_item type: {type(raw_stock)}")
        raise ValueError("Invalid stock_item data")

    stock_item_dict = cast(dict[str, Any], raw_stock)
    stock_item_id = str(stock_item_dict.get("id", ""))

    telegram_id_raw = order_data.get("user_telegram_id") if order_data else None
    telegram_id = (
        int(telegram_id_raw)
        if isinstance(telegram_id_raw, (int, str)) and str(telegram_id_raw).isdigit()
        else None
    )

    await (
        db.client.table("stock_items")
        .update({"status": "reserved"})
        .eq("id", stock_item_id)
        .execute()
    )

    from core.services.domains import DiscountOrderService
    discount_service = DiscountOrderService(db.client)
    order_item_id = str(order_item.get("id", ""))

    if not order_item_id or not stock_item_id or telegram_id is None:
        logger.error("CrystalPay webhook: Missing required fields for delayed delivery")
        raise ValueError("Missing required fields")

    await discount_service.schedule_delayed_delivery(
        order_id=real_order_id,
        order_item_id=order_item_id,
        telegram_id=telegram_id,
        stock_item_id=stock_item_id,
    )
    logger.info(f"CrystalPay webhook: Discount delivery scheduled for order {real_order_id}")


async def _process_instant_delivery(real_order_id: str) -> None:
    """Process instant delivery via QStash or direct fallback."""
    publish_to_worker, worker_endpoints = get_queue_publisher()

    delivery_result = await publish_to_worker(
        endpoint=worker_endpoints.DELIVER_GOODS,
        body={"order_id": real_order_id},
        retries=2,
        deduplication_id=f"deliver-{real_order_id}",
    )

    if delivery_result.get("queued"):
        return

    # FALLBACK: Direct delivery if QStash failed
    logger.warning(f"CrystalPay webhook: QStash failed, executing direct delivery for {real_order_id}")
    try:
        from core.services.database import get_database
        from core.routers.workers import _deliver_items_for_order

        notification_service = get_notification_service()
        fallback_result = await _deliver_items_for_order(
            get_database(), notification_service, real_order_id, only_instant=True
        )
        logger.info(f"CrystalPay webhook: Direct delivery completed: {fallback_result}")
    except Exception as fallback_err:
        logger.error(f"CrystalPay webhook: Direct delivery FAILED: {fallback_err}", exc_info=True)
        raise


def _verify_crystalpay_signature(received_signature: str, invoice_id: str) -> bool:
    """Verify CrystalPay webhook signature."""
    salt = os.environ.get("CRYSTALPAY_SALT", "")
    if not received_signature or not salt:
        return True  # Skip verification if no signature or salt

    sign_string = f"{invoice_id}:{salt}"
    # nosec B324 - SHA1 required by CrystalPay API
    expected_signature = hashlib.sha1(sign_string.encode()).hexdigest().lower()
    return hmac.compare_digest(received_signature, expected_signature)


async def _convert_payment_to_balance_currency(
    payment_amount: float, payment_currency: str, balance_currency: str
) -> float:
    """Convert payment amount to user's balance currency."""
    if payment_currency == balance_currency:
        return payment_amount

    from core.db import get_redis
    from core.services.currency import get_currency_service

    redis = get_redis()
    currency_service = get_currency_service(redis)

    payment_rate = await currency_service.get_exchange_rate(payment_currency) if payment_currency != "USD" else 1.0
    balance_rate = await currency_service.get_exchange_rate(balance_currency) if balance_currency != "USD" else 1.0

    amount_usd = payment_amount / payment_rate if payment_rate > 0 else payment_amount
    return amount_usd * balance_rate


# =============================================================================
# CrystalPay Webhook Endpoints
# =============================================================================


@router.post("/api/webhook/crystalpay")
@router.post("/webhook/crystalpay")
async def crystalpay_webhook(request: Request):
    """Handle CrystalPay payment webhook."""
    try:
        raw_body = await request.body()
        logger.debug(f"CrystalPay webhook raw body length: {len(raw_body)}")

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("CrystalPay webhook: Could not parse JSON body")
            return JSONResponse({"error": "Could not parse JSON"}, status_code=400)

        if not data:
            logger.warning("CrystalPay webhook: Empty request body")
            return JSONResponse({"error": "Empty request body"}, status_code=400)

        invoice_id = data.get("id") or "unknown"
        state = data.get("state") or "unknown"
        order_id = data.get("extra") or "unknown"
        logger.info(f"CrystalPay webhook: invoice={invoice_id}, state={state}, order_id={order_id}")

        payment_service = get_payment_service()
        result = await payment_service.verify_crystalpay_webhook(data)
        logger.debug(f"CrystalPay webhook verify result: {result}")

        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"CrystalPay webhook failed: {error_msg}")
            return JSONResponse({"error": error_msg}, status_code=400)

        real_order_id = result["order_id"]
        from core.services.database import get_database
        db = get_database()

        # Find order
        try:
            order_data, real_order_id = await _find_order_data(db, invoice_id, order_id)
        except TypeError:
            return JSONResponse({"error": "Invalid order data"}, status_code=500)

        if not order_data:
            return JSONResponse({"error": "Order not found"}, status_code=404)

        # Handle cancelled order recovery
        order_status = str(order_data.get("status", "pending"))
        if order_status == "cancelled":
            logger.info("CrystalPay webhook: Order %s was cancelled, attempting recovery", real_order_id)
            recovery_response = await _handle_cancelled_order_recovery(db, order_data, real_order_id, result)
            if recovery_response:
                return recovery_response

        # Mark payment as confirmed
        try:
            from core.orders.status_service import OrderStatusService
            status_service = OrderStatusService(db)
            final_status = await status_service.mark_payment_confirmed(
                order_id=real_order_id, payment_id=invoice_id, check_stock=True
            )
            logger.info(f"CrystalPay webhook: Payment confirmed for order {real_order_id}, status='{final_status}'")
        except Exception as e:
            logger.error(f"CrystalPay webhook: Failed to mark payment confirmed: {e}", exc_info=True)
            return JSONResponse({"error": f"Failed to confirm payment: {e!s}"}, status_code=500)

        # Process delivery based on source channel
        source_channel = str(order_data.get("source_channel", "")) if order_data.get("source_channel") else None

        if source_channel == "discount":
            logger.info(f"CrystalPay webhook: Discount order {real_order_id} - scheduling delayed delivery")
            try:
                await _schedule_discount_delivery(db, order_data, real_order_id)
            except Exception as discount_err:
                logger.error(f"CrystalPay webhook: Discount delivery scheduling failed: {discount_err}", exc_info=True)
        else:
            try:
                await _process_instant_delivery(real_order_id)
            except Exception as e:
                return JSONResponse({"error": f"Delivery failed: {str(e)[:100]}"}, status_code=500)

        # Calculate referral bonus
        publish_to_worker, worker_endpoints = get_queue_publisher()
        await publish_to_worker(
            endpoint=worker_endpoints.CALCULATE_REFERRAL,
            body={"order_id": real_order_id},
            retries=2,
            deduplication_id=f"referral-{real_order_id}",
        )

        return JSONResponse({"ok": True}, status_code=200)

    except Exception as e:
        logger.error(f"CrystalPay webhook error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/webhook/crystalpay/topup")
@router.post("/webhook/crystalpay/topup")
async def crystalpay_topup_webhook(request: Request):
    """CrystalPay webhook handler for balance TOP-UP payments."""
    try:
        body = await request.body()
        logger.info(f"CrystalPay TOPUP webhook received: {len(body)} bytes")

        try:
            data = await request.json()
        except Exception:
            logger.warning("CrystalPay TOPUP webhook: Invalid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        invoice_id = data.get("id") or "unknown"
        state = data.get("state") or "unknown"
        extra = data.get("extra") or ""
        received_signature = str(data.get("signature", "")).strip().lower()

        logger.info(f"CrystalPay TOPUP webhook: invoice={invoice_id}, state={state}, extra={extra}")

        # Verify this is a topup transaction
        if not extra.startswith("topup_"):
            logger.warning(f"CrystalPay TOPUP webhook: Not a topup transaction (extra={extra})")
            return JSONResponse({"error": "Not a topup transaction"}, status_code=400)

        topup_id = extra.replace("topup_", "")

        # Verify signature
        if not _verify_crystalpay_signature(received_signature, invoice_id):
            logger.warning("CrystalPay TOPUP webhook: Signature mismatch")
            return JSONResponse({"error": "Invalid signature"}, status_code=400)

        # Check payment state
        if state.lower() != "payed":
            logger.info(f"CrystalPay TOPUP webhook: Payment not successful (state={state})")
            return JSONResponse({"ok": True, "message": f"State {state} acknowledged"}, status_code=200)

        from core.services.database import get_database
        db = get_database()

        # Find topup transaction
        tx_result = (
            await db.client.table("balance_transactions")
            .select("*")
            .eq("id", topup_id)
            .single()
            .execute()
        )

        if not tx_result.data:
            logger.warning(f"CrystalPay TOPUP webhook: Transaction {topup_id} not found")
            return JSONResponse({"error": "Transaction not found"}, status_code=404)

        raw_tx = tx_result.data
        if not isinstance(raw_tx, dict):
            logger.error(f"CrystalPay TOPUP webhook: Invalid transaction data type: {type(raw_tx)}")
            return JSONResponse({"error": "Invalid transaction data"}, status_code=500)

        tx = cast(dict[str, Any], raw_tx)

        # Idempotency check
        if tx.get("status") == "completed":
            logger.info(f"CrystalPay TOPUP webhook: Transaction {topup_id} already completed")
            return JSONResponse({"ok": True}, status_code=200)

        user_id = str(tx.get("user_id")) if tx.get("user_id") else None

        # Get payment details
        tx_metadata = cast(dict[str, Any], tx.get("metadata")) if isinstance(tx.get("metadata"), dict) else {}
        payment_amount_raw = tx_metadata.get("payment_amount") or tx.get("amount") or 0
        payment_amount = float(payment_amount_raw) if isinstance(payment_amount_raw, (int, float)) else 0.0
        payment_currency = str(tx_metadata.get("payment_currency") or tx.get("currency") or "RUB")

        # Get user data
        user_result = (
            await db.client.table("users")
            .select("balance, balance_currency, telegram_id")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            logger.warning(f"CrystalPay TOPUP webhook: User {user_id} not found")
            return JSONResponse({"error": "User not found"}, status_code=404)

        raw_user = user_result.data
        if not isinstance(raw_user, dict):
            logger.error(f"CrystalPay TOPUP webhook: Invalid user data type: {type(raw_user)}")
            return JSONResponse({"error": "Invalid user data"}, status_code=500)

        user_data = cast(dict[str, Any], raw_user)
        current_balance = float(user_data.get("balance") or 0)
        balance_currency = str(user_data.get("balance_currency") or "USD")
        user_telegram_id_raw = user_data.get("telegram_id")
        user_telegram_id = int(user_telegram_id_raw) if isinstance(user_telegram_id_raw, (int, str)) and str(user_telegram_id_raw).isdigit() else None

        # Convert payment to user's balance currency
        try:
            amount_to_add = await _convert_payment_to_balance_currency(payment_amount, payment_currency, balance_currency)
            logger.info(f"Top-up conversion: {payment_amount} {payment_currency} → {amount_to_add:.2f} {balance_currency}")
        except Exception:
            logger.exception("Currency conversion failed")
            raise

        # Round appropriately
        if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
            amount_to_add = round(amount_to_add)
        else:
            amount_to_add = round(amount_to_add, 2)

        new_balance = current_balance + amount_to_add

        # Update user balance and transaction
        await db.client.table("users").update({"balance": new_balance}).eq("id", user_id).execute()
        await (
            db.client.table("balance_transactions")
            .update({"status": "completed", "balance_before": current_balance, "balance_after": new_balance})
            .eq("id", topup_id)
            .execute()
        )

        logger.info(f"CrystalPay TOPUP webhook: SUCCESS! User {user_id} balance: {current_balance:.2f} -> {new_balance:.2f} {balance_currency}")

        # Send notification
        if user_telegram_id:
            try:
                notification_service = get_notification_service()
                await notification_service.send_topup_success_notification(
                    telegram_id=user_telegram_id,
                    amount=amount_to_add,
                    currency=balance_currency,
                    new_balance=new_balance,
                )
            except Exception as e:
                logger.warning(f"Failed to send topup notification: {e}")

        return JSONResponse({"ok": True}, status_code=200)

    except Exception as e:
        logger.error(f"CrystalPay TOPUP webhook error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
