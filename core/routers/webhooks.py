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
    """Lookup order by payment_id (reduces cognitive complexity)."""
    lookup_result = (
        await db.client.table("orders")
        .select("*")
        .eq("payment_id", invoice_id)
        .limit(1)
        .execute()
    )
    if not lookup_result.data:
        return None, ""

    raw_order = lookup_result.data[0]
    if not isinstance(raw_order, dict):
        logger.error("CrystalPay webhook: Invalid order data type: %s", type(raw_order))
        return None, "invalid_type"

    order_data = cast(dict[str, Any], raw_order)
    real_order_id = str(order_data.get("id", ""))
    logger.debug("CrystalPay webhook: mapped invoice %s -> order %s", invoice_id, real_order_id)
    return order_data, real_order_id


async def _lookup_order_by_id(db, order_id: str) -> tuple[dict[str, Any] | None, str]:
    """Lookup order by order_id (reduces cognitive complexity)."""
    direct_result = (
        await db.client.table("orders")
        .select("*")
        .eq("id", order_id)
        .limit(1)
        .execute()
    )
    if not direct_result.data:
        return None, ""

    raw_order = direct_result.data[0]
    if not isinstance(raw_order, dict):
        logger.error("CrystalPay webhook: Invalid order data type: %s", type(raw_order))
        return None, "invalid_type"

    order_data = cast(dict[str, Any], raw_order)
    real_order_id = str(order_data.get("id", ""))
    logger.debug("CrystalPay webhook: direct order lookup for %s", real_order_id)
    return order_data, real_order_id


async def _find_order_data(db, invoice_id: str, order_id: str) -> tuple[dict[str, Any] | None, str]:
    """Find order data by payment_id or order_id (reduces cognitive complexity)."""
    order_data, real_order_id = await _lookup_order_by_payment_id(db, invoice_id)
    if order_data:
        return order_data, real_order_id

    order_data, real_order_id = await _lookup_order_by_id(db, order_id)
    if order_data:
        return order_data, real_order_id

    logger.warning("CrystalPay webhook: Order not found for invoice %s, extra %s", invoice_id, order_id)
    return None, ""


async def _check_stock_availability(db, product_id: str) -> bool:
    """Check if product has available stock (reduces cognitive complexity)."""
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


async def _handle_cancelled_order_recovery(
    db, order_data: dict[str, Any], real_order_id: str, result: dict[str, Any]
) -> JSONResponse | None:
    """Handle recovery of cancelled order (reduces cognitive complexity)."""
    product_id = (
        str(order_data.get("product_id", ""))
        if order_data.get("product_id")
        else None
    )

    can_fulfill = await _check_stock_availability(db, product_id)

    if can_fulfill:
        logger.info("CrystalPay webhook: Restoring order %s - stock available", real_order_id)
        await db.client.table("orders").update(
            {"status": "pending", "notes": "Restored after late payment"}
        ).eq("id", real_order_id).execute()
        return None

    logger.warning("CrystalPay webhook: Order %s - no stock, creating refund ticket", real_order_id)
    user_id = (
        str(order_data.get("user_id", ""))
        if order_data.get("user_id")
        else None
    )
    result_dict = result if isinstance(result, dict) else {}
    amount = (
        float(result_dict.get("amount", 0))
        if isinstance(result_dict.get("amount"), (int, float))
        else 0.0
    )

    if user_id:
        try:
            await db.client.table("tickets").insert(
                {
                    "user_id": user_id,
                    "order_id": real_order_id,
                    "issue_type": "refund",
                    "description": f"Late payment after order expired. Amount: {amount}. Stock unavailable.",
                    "status": "open",
                }
            ).execute()
            await db.client.table("orders").update(
                {
                    "status": "refund_pending",
                    "refund_requested": True,
                    "notes": "Late payment - stock unavailable",
                }
            ).eq("id", real_order_id).execute()
        except Exception as e:
            logger.error("CrystalPay webhook: Failed to create refund ticket: %s", e, exc_info=True)

    return JSONResponse({"ok": True, "note": "refund_pending"}, status_code=200)


# ==================== CRYSTALPAY WEBHOOK ====================


@router.post("/api/webhook/crystalpay")
@router.post("/webhook/crystalpay")
async def crystalpay_webhook(request: Request):
    """
    Handle CrystalPay payment webhook.

    CrystalPay sends POST with JSON:
    - id: Invoice ID
    - signature: sha1(id + ':' + salt)
    - state: payed, notpayed, processing, cancelled
    - extra: Our order_id (stored during invoice creation)
    - amount, rub_amount, currency, etc.

    Must return HTTP 200 on success.

    Docs: https://docs.crystalpay.io/callback/invoice-uvedomleniya
    """
    try:
        # Parse JSON body
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

        # Log webhook receipt
        invoice_id = data.get("id") or "unknown"
        state = data.get("state") or "unknown"
        order_id = data.get("extra") or "unknown"
        logger.info(f"CrystalPay webhook: invoice={invoice_id}, state={state}, order_id={order_id}")

        payment_service = get_payment_service()
        result = await payment_service.verify_crystalpay_webhook(data)
        logger.debug(f"CrystalPay webhook verify result: {result}")

        if result["success"]:
            real_order_id = result["order_id"]

            from core.services.database import get_database

            db = get_database()

            try:
                order_data, real_order_id = await _find_order_data(db, invoice_id, order_id)
                if not order_data:
                    if real_order_id == "invalid_type":
                        return JSONResponse({"error": "Invalid order data"}, status_code=500)
                    return JSONResponse({"error": "Order not found"}, status_code=404)
            except Exception as e:
                logger.error("CrystalPay webhook: Order lookup error: %s", e, exc_info=True)
                return JSONResponse({"error": "Order lookup failed"}, status_code=500)

            order_status = str(order_data.get("status", "pending"))
            if order_status == "cancelled":
                logger.info("CrystalPay webhook: Order %s was %s, attempting recovery", real_order_id, order_status)
                recovery_response = await _handle_cancelled_order_recovery(db, order_data, real_order_id, result)
                if recovery_response:
                    return recovery_response

            # CRITICAL: Mark payment as confirmed
            try:
                from core.orders.status_service import OrderStatusService

                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=real_order_id, payment_id=invoice_id, check_stock=True
                )
                logger.info(
                    f"CrystalPay webhook: Payment confirmed for order {real_order_id}, status set to '{final_status}'"
                )
            except Exception as e:
                logger.error(
                    f"CrystalPay webhook: Failed to mark payment confirmed: {e}", exc_info=True
                )
                return JSONResponse({"error": f"Failed to confirm payment: {e!s}"}, status_code=500)

            publish_to_worker, WorkerEndpoints = get_queue_publisher()

            # Check if this is a discount channel order (delayed delivery)
            source_channel = (
                str(order_data.get("source_channel", ""))
                if (order_data and order_data.get("source_channel"))
                else None
            )

            if source_channel == "discount":
                # DISCOUNT BOT: Schedule delayed delivery via QStash (1-4 hours)
                logger.info(
                    f"CrystalPay webhook: Discount order {real_order_id} - scheduling delayed delivery"
                )
                try:
                    from core.services.domains import DiscountOrderService

                    order_items = (
                        await db.client.table("order_items")
                        .select("id, product_id")
                        .eq("order_id", real_order_id)
                        .limit(1)
                        .execute()
                    )

                    if order_items.data:
                        raw_order_item = order_items.data[0]
                        if not isinstance(raw_order_item, dict):
                            logger.error(
                                f"CrystalPay webhook: Invalid order_item type: {type(raw_order_item)}"
                            )
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

                        if stock_result.data:
                            raw_stock = stock_result.data[0]
                            if not isinstance(raw_stock, dict):
                                logger.error(
                                    f"CrystalPay webhook: Invalid stock_item type: {type(raw_stock)}"
                                )
                                raise ValueError("Invalid stock_item data")
                            stock_item_dict = cast(dict[str, Any], raw_stock)
                            stock_item_id = str(stock_item_dict.get("id", ""))

                            telegram_id_raw = (
                                order_data.get("user_telegram_id") if order_data else None
                            )
                            telegram_id = (
                                int(telegram_id_raw)
                                if isinstance(telegram_id_raw, (int, str))
                                and str(telegram_id_raw).isdigit()
                                else None
                            )

                            await db.client.table("stock_items").update({"status": "reserved"}).eq(
                                "id", stock_item_id
                            ).execute()

                            discount_service = DiscountOrderService(db.client)
                            order_item_id = str(order_item.get("id", ""))
                            if not order_item_id or not stock_item_id or telegram_id is None:
                                logger.error(
                                    "CrystalPay webhook: Missing required fields for delayed delivery"
                                )
                                raise ValueError("Missing required fields")
                            await discount_service.schedule_delayed_delivery(
                                order_id=real_order_id,
                                order_item_id=order_item_id,
                                telegram_id=telegram_id,
                                stock_item_id=stock_item_id,
                            )

                            logger.info(
                                f"CrystalPay webhook: Discount delivery scheduled for order {real_order_id}"
                            )
                        else:
                            logger.warning(
                                f"CrystalPay webhook: No stock for discount order {real_order_id}"
                            )
                except Exception as discount_err:
                    logger.error(
                        f"CrystalPay webhook: Discount delivery scheduling failed: {discount_err}",
                        exc_info=True,
                    )
            else:
                # PREMIUM (PVNDORA): Instant delivery via QStash
                delivery_result = await publish_to_worker(
                    endpoint=WorkerEndpoints.DELIVER_GOODS,
                    body={"order_id": real_order_id},
                    retries=2,
                    deduplication_id=f"deliver-{real_order_id}",
                )

                # FALLBACK: If QStash failed, deliver directly
                if not delivery_result.get("queued"):
                    logger.warning(
                        f"CrystalPay webhook: QStash failed, executing direct delivery for {real_order_id}"
                    )
                    try:
                        from core.routers.deps import get_notification_service
                        from core.routers.workers import _deliver_items_for_order

                        notification_service = get_notification_service()
                        fallback_result = await _deliver_items_for_order(
                            db, notification_service, real_order_id, only_instant=True
                        )
                        logger.info(
                            f"CrystalPay webhook: Direct delivery completed: {fallback_result}"
                        )
                    except Exception as fallback_err:
                        logger.error(
                            f"CrystalPay webhook: Direct delivery FAILED for {real_order_id}: {fallback_err}",
                            exc_info=True,
                        )
                        return JSONResponse(
                            {"error": f"Delivery failed: {str(fallback_err)[:100]}"},
                            status_code=500,
                        )

            # Calculate referral bonus (non-critical)
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": real_order_id},
                retries=2,
                deduplication_id=f"referral-{real_order_id}",
            )

            return JSONResponse({"ok": True}, status_code=200)

        # Log verification failure
        error_msg = result.get("error", "Unknown error")
        logger.warning(f"CrystalPay webhook failed: {error_msg}")

        return JSONResponse({"error": error_msg}, status_code=400)

    except Exception as e:
        logger.error(f"CrystalPay webhook error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/webhook/crystalpay/topup")
@router.post("/webhook/crystalpay/topup")
async def crystalpay_topup_webhook(request: Request):
    """
    CrystalPay webhook handler for balance TOP-UP payments.

    Credits user balance instead of delivering goods.
    """
    try:
        body = await request.body()
        logger.info(f"CrystalPay TOPUP webhook received: {len(body)} bytes")

        try:
            data = await request.json()
        except Exception:
            logger.warning("CrystalPay TOPUP webhook: Invalid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        # Extract fields
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
        salt = os.environ.get("CRYSTALPAY_SALT", "")
        if received_signature and salt:
            sign_string = f"{invoice_id}:{salt}"
            # nosec B324 - SHA1 required by CrystalPay API for signature verification
            expected_signature = hashlib.sha1(sign_string.encode()).hexdigest().lower()

            if not hmac.compare_digest(received_signature, expected_signature):
                logger.warning("CrystalPay TOPUP webhook: Signature mismatch")
                return JSONResponse({"error": "Invalid signature"}, status_code=400)

        # Check payment state
        if state.lower() != "payed":
            logger.info(f"CrystalPay TOPUP webhook: Payment not successful (state={state})")
            return JSONResponse(
                {"ok": True, "message": f"State {state} acknowledged"}, status_code=200
            )

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
        tx_status = str(tx.get("status", "")) if tx.get("status") else ""
        if tx_status == "completed":
            logger.info(f"CrystalPay TOPUP webhook: Transaction {topup_id} already completed")
            return JSONResponse({"ok": True}, status_code=200)

        user_id_raw = tx.get("user_id")
        user_id = str(user_id_raw) if user_id_raw is not None else None

        # Get payment details from metadata (what user actually paid)
        # Transaction amount/currency is in balance_currency (what gets credited)
        tx_metadata_raw = tx.get("metadata")
        tx_metadata = (
            cast(dict[str, Any], tx_metadata_raw) if isinstance(tx_metadata_raw, dict) else {}
        )
        payment_amount_raw = tx_metadata.get("payment_amount") or tx.get("amount") or 0
        payment_amount = (
            float(payment_amount_raw) if isinstance(payment_amount_raw, (int, float)) else 0.0
        )
        payment_currency_raw = tx_metadata.get("payment_currency") or tx.get("currency") or "RUB"
        payment_currency = str(payment_currency_raw) if payment_currency_raw else "RUB"

        # Get user current balance, balance_currency and telegram_id
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

        balance_raw = user_data.get("balance") or 0
        current_balance = float(balance_raw) if isinstance(balance_raw, (int, float)) else 0.0
        balance_currency_raw = user_data.get("balance_currency") or "USD"
        balance_currency = str(balance_currency_raw) if balance_currency_raw else "USD"
        user_telegram_id_raw = user_data.get("telegram_id")
        user_telegram_id = (
            int(user_telegram_id_raw)
            if isinstance(user_telegram_id_raw, (int, str)) and str(user_telegram_id_raw).isdigit()
            else None
        )

        # Convert payment to user's balance currency if needed
        from core.db import get_redis
        from core.services.currency import get_currency_service

        redis = get_redis()
        currency_service = get_currency_service(redis)

        if payment_currency == balance_currency:
            # Same currency, add directly
            amount_to_add = payment_amount
            logger.info(f"Top-up: {payment_amount} {payment_currency} (same as balance currency)")
        else:
            # Need to convert
            try:
                # Get rates for both currencies
                payment_rate = (
                    await currency_service.get_exchange_rate(payment_currency)
                    if payment_currency != "USD"
                    else 1.0
                )
                balance_rate = (
                    await currency_service.get_exchange_rate(balance_currency)
                    if balance_currency != "USD"
                    else 1.0
                )

                # Convert: payment_currency → USD → balance_currency
                amount_usd = payment_amount / payment_rate if payment_rate > 0 else payment_amount
                amount_to_add = amount_usd * balance_rate

                logger.info(
                    f"Top-up conversion: {payment_amount} {payment_currency} → {amount_usd:.2f} USD → {amount_to_add:.2f} {balance_currency}"
                )
            except Exception:
                logger.exception("Currency conversion failed")
                raise

        # Round appropriately for the balance currency
        if balance_currency in ["RUB", "UAH", "TRY", "INR"]:
            amount_to_add = round(amount_to_add)  # Integer currencies - round to whole number
        else:
            amount_to_add = round(
                amount_to_add, 2
            )  # Decimal currencies - round to 2 decimal places

        new_balance = current_balance + amount_to_add

        # Update user balance
        await db.client.table("users").update({"balance": new_balance}).eq("id", user_id).execute()

        # Update transaction status
        await db.client.table("balance_transactions").update(
            {
                "status": "completed",
                "balance_before": current_balance,
                "balance_after": new_balance,
            }
        ).eq("id", topup_id).execute()

        logger.info(
            f"CrystalPay TOPUP webhook: SUCCESS! User {user_id} balance: {current_balance:.2f} {balance_currency} -> {new_balance:.2f} {balance_currency}"
        )

        # Send user notification (best-effort)
        if user_telegram_id:
            try:
                notification_service = get_notification_service()
                await notification_service.send_topup_success_notification(
                    telegram_id=user_telegram_id,
                    amount=amount_to_add,  # Amount actually credited to balance
                    currency=balance_currency,  # Currency of user's balance
                    new_balance=new_balance,
                )
            except Exception as e:
                logger.warning(f"Failed to send topup notification: {e}")

        return JSONResponse({"ok": True}, status_code=200)

    except Exception as e:
        logger.error(f"CrystalPay TOPUP webhook error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)
