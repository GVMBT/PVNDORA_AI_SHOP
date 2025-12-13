"""
Webhooks Router

Payment and notification webhooks.
All webhooks verify signatures and delegate to QStash workers.
"""

import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from core.routers.deps import get_payment_service, get_queue_publisher

router = APIRouter(tags=["webhooks"])


# ==================== 1PLAT WEBHOOK ====================

@router.post("/api/webhook/1plat")
@router.post("/webhook/1plat")
async def onplat_webhook(request: Request):
    """
    Handle 1Plat payment webhook.
    
    Supports both JSON and form-data formats.
    Signature verification is handled in PaymentService.
    """
    try:
        # Get raw body for potential signature verification from headers
        raw_body = await request.body()
            
        # Try to parse as JSON first
        data = None
        try:
            data = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Try form data
            try:
                form_data = await request.form()
                data = dict(form_data)
            except:
                # Try query parameters as fallback
                data = dict(request.query_params)
        
        if not data:
            print("1Plat webhook: Could not parse request body")
            return JSONResponse(
                {"ok": False, "error": "Could not parse webhook data"},
                status_code=400
            )
        
        # Log webhook receipt (without sensitive data)
        order_id = data.get("order_id") or data.get("orderId") or "unknown"
        print(f"1Plat webhook received for order: {order_id}")
        
        payment_service = get_payment_service()
        result = await payment_service.verify_1plat_webhook(data)
        
        if result["success"]:
            order_id = result["order_id"]
            payment_id = result.get("payment_id") or result.get("invoice_id")
            
            print(f"1Plat webhook verified successfully for order: {order_id}")
            
            # CRITICAL: Mark payment as confirmed using centralized service
            from src.services.database import get_database
            db = get_database()
            try:
                from core.orders.status_service import OrderStatusService
                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=order_id,
                    payment_id=payment_id,
                    check_stock=True
                )
                print(f"1Plat webhook: Payment confirmed for order {order_id}, status set to '{final_status}'")
            except Exception as e:
                print(f"1Plat webhook: Failed to mark payment confirmed: {e}")
                return JSONResponse(
                    {"ok": False, "error": f"Failed to confirm payment: {str(e)}"},
                    status_code=500
                )
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Try QStash first, fallback to direct delivery if it fails
            delivery_result = await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"deliver-{order_id}"
            )
            
            # FALLBACK: If QStash failed, deliver directly
            if not delivery_result.get("queued"):
                print(f"1Plat webhook: QStash failed, executing direct delivery for {order_id}")
                try:
                    from src.services.database import get_database
                    from core.routers.workers import _deliver_items_for_order
                    from core.routers.deps import get_notification_service
                    db = get_database()
                    notification_service = get_notification_service()
                    await _deliver_items_for_order(db, notification_service, order_id, only_instant=True)
                except Exception as fallback_err:
                    print(f"1Plat webhook: Direct delivery failed: {fallback_err}")
            
            # Calculate referral bonus (non-critical)
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"referral-{order_id}"
            )
            
            return JSONResponse({"ok": True})
        
        # Log verification failure
        error_msg = result.get("error", "Unknown error")
        print(f"1Plat webhook verification failed: {error_msg}")
        
        return JSONResponse(
            {"ok": False, "error": error_msg},
            status_code=400
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"1Plat webhook error: {e}")
        print(f"Traceback: {error_trace}")
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )


# ==================== FREEKASSA WEBHOOK ====================

@router.post("/api/webhook/freekassa")
@router.post("/webhook/freekassa")
@router.get("/api/webhook/freekassa")
@router.get("/webhook/freekassa")
async def freekassa_webhook(request: Request):
    """
    Handle Freekassa payment webhook.
    
    Freekassa sends webhooks as form data or query parameters.
    Must return "YES" to confirm receipt.
    """
    try:
        # Freekassa sends data as form data or query parameters
        data = {}
        
        # Try form data first
        try:
            form_data = await request.form()
            data = dict(form_data)
        except:
            # Fallback to query parameters
            data = dict(request.query_params)
        
        if not data:
            print("Freekassa webhook: Could not parse request data")
            return JSONResponse(
                {"error": "Could not parse webhook data"},
                status_code=400
            )
        
        # Log webhook receipt (without sensitive data)
        order_id = data.get("MERCHANT_ORDER_ID") or "unknown"
        print(f"Freekassa webhook received for order: {order_id}")
        
        payment_service = get_payment_service()
        result = await payment_service.verify_freekassa_webhook(data)
        
        if result["success"]:
            order_id = result["order_id"]
            payment_id = result.get("payment_id")
            
            print(f"Freekassa webhook verified successfully for order: {order_id}")
            
            # CRITICAL: Mark payment as confirmed using centralized service
            from src.services.database import get_database
            db = get_database()
            try:
                from core.orders.status_service import OrderStatusService
                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=order_id,
                    payment_id=payment_id,
                    check_stock=True
                )
                print(f"Freekassa webhook: Payment confirmed for order {order_id}, status set to '{final_status}'")
            except Exception as e:
                print(f"Freekassa webhook: Failed to mark payment confirmed: {e}")
                return JSONResponse(
                    {"error": f"Failed to confirm payment: {str(e)}"},
                    status_code=500
                )
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Try QStash first, fallback to direct delivery if it fails
            delivery_result = await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"deliver-{order_id}"
            )
            
            # FALLBACK: If QStash failed, deliver directly
            if not delivery_result.get("queued"):
                print(f"Freekassa webhook: QStash failed, executing direct delivery for {order_id}")
                try:
                    from src.services.database import get_database
                    from core.routers.workers import _deliver_items_for_order
                    from core.routers.deps import get_notification_service
                    db = get_database()
                    notification_service = get_notification_service()
                    await _deliver_items_for_order(db, notification_service, order_id, only_instant=True)
                except Exception as fallback_err:
                    print(f"Freekassa webhook: Direct delivery failed: {fallback_err}")
            
            # Calculate referral bonus (non-critical)
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=2,
                deduplication_id=f"referral-{order_id}"
            )
            
            # Freekassa requires "YES" response to confirm receipt
            return JSONResponse(content="YES", media_type="text/plain")
        
        # Log verification failure
        error_msg = result.get("error", "Unknown error")
        print(f"Freekassa webhook verification failed: {error_msg}")
        
        return JSONResponse(
            {"error": error_msg},
            status_code=400
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Freekassa webhook error: {e}")
        print(f"Traceback: {error_trace}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


# ==================== RUKASSA WEBHOOK ====================

@router.post("/api/webhook/rukassa")
@router.post("/webhook/rukassa")
async def rukassa_webhook(request: Request):
    """
    Handle Rukassa payment webhook.
    
    Rukassa sends POST with form data:
    - id: Payment ID in Rukassa
    - order_id: Our order ID
    - amount: Expected amount
    - in_amount: Actually paid amount
    - data: Custom data (JSON string)
    - createdDateTime: Payment creation time
    - status: PAID if successful
    
    Signature in header: Signature
    Formula: hmac_sha256(id + '|' + createdDateTime + '|' + amount, token)
    
    Must return 'OK' on success.
    """
    try:
        # Get signature from header
        signature = request.headers.get("Signature") or request.headers.get("signature") or ""
        
        # Parse form data (Rukassa sends as POST form)
        data = None
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            raw_body = await request.body()
            data = json.loads(raw_body.decode('utf-8'))
        else:
            # Form data
            form_data = await request.form()
            data = dict(form_data)
        
        if not data:
            print("Rukassa webhook: Could not parse request body")
            return Response(content="ERROR PARSE", status_code=400)
        
        # Log webhook receipt
        order_id = data.get("order_id") or "unknown"
        payment_id = data.get("id") or "unknown"
        status = data.get("status") or "unknown"
        print(f"Rukassa webhook: order={order_id}, id={payment_id}, status={status}")
        
        payment_service = get_payment_service()
        result = await payment_service.verify_rukassa_webhook(data, signature=signature)
        
        if result["success"]:
            payment_order_id = result["order_id"]  # This is the temp UUID we sent to Rukassa
            
            print(f"Rukassa webhook verified for payment_id: {payment_order_id}")
            
            # Find real order by payment_id field (maps temp_order_id -> real order)
            from src.services.database import get_database
            db = get_database()
            
            real_order_id = payment_order_id  # Default fallback
            order_data = None
            try:
                import asyncio
                lookup_result = await asyncio.to_thread(
                    lambda: db.client.table("orders")
                    .select("*")
                    .eq("payment_id", payment_order_id)
                    .limit(1)
                    .execute()
                )
                if lookup_result.data:
                    order_data = lookup_result.data[0]
                    real_order_id = order_data["id"]
                    print(f"Rukassa webhook: mapped payment_id {payment_order_id} -> order_id {real_order_id}")
                else:
                    # Fallback: try direct lookup (backward compatibility)
                    direct_result = await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .select("*")
                        .eq("id", payment_order_id)
                        .limit(1)
                        .execute()
                    )
                    if direct_result.data:
                        order_data = direct_result.data[0]
                        real_order_id = order_data["id"]
                        print(f"Rukassa webhook: direct order lookup succeeded for {real_order_id}")
                    else:
                        print(f"Rukassa webhook: Order not found for payment_id {payment_order_id}")
                        return Response(content="ERROR ORDER NOT FOUND", status_code=404)
            except Exception as e:
                print(f"Rukassa webhook: Order lookup error: {e}")
                # Continue with payment_order_id as fallback
            
            # Handle edge case: payment came after order expired/cancelled
            order_status = order_data.get("status", "pending") if order_data else "pending"
            if order_status in ("expired", "cancelled"):
                print(f"Rukassa webhook: Order {real_order_id} was {order_status}, attempting recovery")
                
                # Check if product is still available
                product_id = order_data.get("product_id") if order_data else None
                can_fulfill = False
                
                if product_id:
                    try:
                        stock_check = await asyncio.to_thread(
                            lambda: db.client.table("stock_items")
                            .select("id")
                            .eq("product_id", product_id)
                            .eq("status", "available")
                            .limit(1)
                            .execute()
                        )
                        can_fulfill = bool(stock_check.data)
                    except Exception as e:
                        print(f"Rukassa webhook: Stock check error: {e}")
                
                if can_fulfill:
                    # Restore order and proceed with delivery
                    print(f"Rukassa webhook: Restoring order {real_order_id} - stock available")
                    await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .update({"status": "pending", "notes": "Restored after late payment"})
                        .eq("id", real_order_id)
                        .execute()
                    )
                else:
                    # No stock - credit to user balance or create refund ticket
                    print(f"Rukassa webhook: Order {real_order_id} - no stock, creating refund ticket")
                    user_id = order_data.get("user_id") if order_data else None
                    amount = result.get("amount", 0)
                    
                    if user_id:
                        try:
                            await asyncio.to_thread(
                                lambda: db.client.table("tickets").insert({
                                    "user_id": user_id,
                                    "order_id": real_order_id,
                                    "issue_type": "refund",
                                    "description": f"Late payment after order expired. Amount: {amount}. Stock unavailable.",
                                    "status": "open"
                                }).execute()
                            )
                            # Mark order as needing refund
                            await asyncio.to_thread(
                                lambda: db.client.table("orders")
                                .update({"status": "refund_pending", "refund_requested": True, "notes": "Late payment - stock unavailable"})
                                .eq("id", real_order_id)
                                .execute()
                            )
                        except Exception as e:
                            print(f"Rukassa webhook: Failed to create refund ticket: {e}")
                    
                    # Still return OK to acknowledge webhook
                    return Response(content="OK", status_code=200)
            
            print(f"Rukassa webhook processing delivery for order: {real_order_id}")
            
            # CRITICAL: Mark payment as confirmed using centralized service
            try:
                from core.orders.status_service import OrderStatusService
                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=real_order_id,
                    payment_id=payment_order_id,
                    check_stock=True
                )
                print(f"Rukassa webhook: Payment confirmed for order {real_order_id}, status set to '{final_status}'")
            except Exception as e:
                print(f"Rukassa webhook: Failed to mark payment confirmed: {e}")
                return Response(content=f"ERROR Failed to confirm payment: {str(e)}", status_code=500)
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Try QStash first, fallback to direct delivery if it fails
            delivery_result = await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": real_order_id},
                retries=2,
                deduplication_id=f"deliver-{real_order_id}"
            )
            
            # FALLBACK: If QStash failed, deliver directly
            if not delivery_result.get("queued"):
                print(f"Rukassa webhook: QStash failed, executing direct delivery for {real_order_id}")
                try:
                    from core.routers.workers import _deliver_items_for_order
                    from core.routers.deps import get_notification_service
                    notification_service = get_notification_service()
                    await _deliver_items_for_order(db, notification_service, real_order_id, only_instant=True)
                except Exception as fallback_err:
                    print(f"Rukassa webhook: Direct delivery failed: {fallback_err}")
            
            # Calculate referral bonus (non-critical)
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": real_order_id},
                retries=2,
                deduplication_id=f"referral-{real_order_id}"
            )
            
            # Rukassa expects 'OK' response
            return Response(content="OK", status_code=200)
        
        # Log verification failure
        error_msg = result.get("error", "Unknown error")
        print(f"Rukassa webhook failed: {error_msg}")
        
        # Return error message for Rukassa
        return Response(content=f"ERROR {error_msg}", status_code=400)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Rukassa webhook error: {e}")
        print(f"Traceback: {error_trace}")
        return Response(content=f"ERROR {str(e)}", status_code=500)


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
    # FIRST LINE: Log that we received ANY request
    print(f"CrystalPay webhook RECEIVED: method={request.method}, url={request.url}")
    
    try:
        # Parse JSON body
        raw_body = await request.body()
        print(f"CrystalPay webhook raw body length: {len(raw_body)}")
        try:
            data = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print("CrystalPay webhook: Could not parse JSON body")
            return JSONResponse(
                {"error": "Could not parse JSON"},
                status_code=400
            )
        
        if not data:
            print("CrystalPay webhook: Empty request body")
            return JSONResponse(
                {"error": "Empty request body"},
                status_code=400
            )
        
        # Log webhook receipt
        invoice_id = data.get("id") or "unknown"
        state = data.get("state") or "unknown"
        order_id = data.get("extra") or "unknown"  # we pass real order_id in extra
        print(f"CrystalPay webhook: invoice={invoice_id}, state={state}, order_id={order_id}")
        
        payment_service = get_payment_service()
        result = await payment_service.verify_crystalpay_webhook(data)
        print(f"CrystalPay webhook verify result: {result}")
        
        if result["success"]:
            real_order_id = result["order_id"]
            
            print(f"CrystalPay webhook verified for order: {real_order_id}")
            
            # Find real order by payment_id field (maps invoice_id -> real order)
            from src.services.database import get_database
            db = get_database()
            
            order_data = None
            try:
                import asyncio
                # Try lookup by payment_id (invoice_id saved during creation)
                lookup_result = await asyncio.to_thread(
                    lambda: db.client.table("orders")
                    .select("*")
                    .eq("payment_id", invoice_id)
                    .limit(1)
                    .execute()
                )
                if lookup_result.data:
                    order_data = lookup_result.data[0]
                    real_order_id = order_data["id"]
                    print(f"CrystalPay webhook: mapped invoice {invoice_id} -> order {real_order_id}")
                else:
                    # Fallback: try direct lookup by order_id from extra (real order_id)
                    direct_result = await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .select("*")
                        .eq("id", order_id)
                        .limit(1)
                        .execute()
                    )
                    if direct_result.data:
                        order_data = direct_result.data[0]
                        real_order_id = order_data["id"]
                        print(f"CrystalPay webhook: direct order lookup for {real_order_id}")
                    else:
                        print(f"CrystalPay webhook: Order not found for invoice {invoice_id}, extra {order_id}")
                        return JSONResponse(
                            {"error": "Order not found"},
                            status_code=404
                        )
            except Exception as e:
                print(f"CrystalPay webhook: Order lookup error: {e}")
                # Continue with order_id from extra as fallback
            
            # Handle edge case: payment came after order expired/cancelled
            order_status = order_data.get("status", "pending") if order_data else "pending"
            if order_status in ("expired", "cancelled"):
                print(f"CrystalPay webhook: Order {real_order_id} was {order_status}, attempting recovery")
                
                # Check if product is still available
                product_id = order_data.get("product_id") if order_data else None
                can_fulfill = False
                
                if product_id:
                    try:
                        stock_check = await asyncio.to_thread(
                            lambda: db.client.table("stock_items")
                            .select("id")
                            .eq("product_id", product_id)
                            .eq("status", "available")
                            .limit(1)
                            .execute()
                        )
                        can_fulfill = bool(stock_check.data)
                    except Exception as e:
                        print(f"CrystalPay webhook: Stock check error: {e}")
                
                if can_fulfill:
                    # Restore order and proceed with delivery
                    print(f"CrystalPay webhook: Restoring order {real_order_id} - stock available")
                    await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .update({"status": "pending", "notes": "Restored after late payment"})
                        .eq("id", real_order_id)
                        .execute()
                    )
                else:
                    # No stock - credit to user balance or create refund ticket
                    print(f"CrystalPay webhook: Order {real_order_id} - no stock, creating refund ticket")
                    user_id = order_data.get("user_id") if order_data else None
                    amount = result.get("amount", 0)
                    
                    if user_id:
                        try:
                            await asyncio.to_thread(
                                lambda: db.client.table("tickets").insert({
                                    "user_id": user_id,
                                    "order_id": real_order_id,
                                    "issue_type": "refund",
                                    "description": f"Late payment after order expired. Amount: {amount}. Stock unavailable.",
                                    "status": "open"
                                }).execute()
                            )
                            # Mark order as needing refund
                            await asyncio.to_thread(
                                lambda: db.client.table("orders")
                                .update({"status": "refund_pending", "refund_requested": True, "notes": "Late payment - stock unavailable"})
                                .eq("id", real_order_id)
                                .execute()
                            )
                        except Exception as e:
                            print(f"CrystalPay webhook: Failed to create refund ticket: {e}")
                    
                    # Still return 200 to acknowledge webhook
                    return JSONResponse({"ok": True, "note": "refund_pending"}, status_code=200)
            
            print(f"CrystalPay webhook processing delivery for order: {real_order_id}")
            
            # CRITICAL: Mark payment as confirmed using centralized service
            # This ensures proper status transition and stock checking
            try:
                from core.orders.status_service import OrderStatusService
                status_service = OrderStatusService(db)
                final_status = await status_service.mark_payment_confirmed(
                    order_id=real_order_id,
                    payment_id=invoice_id,
                    check_stock=True
                )
                print(f"CrystalPay webhook: Payment confirmed for order {real_order_id}, status set to '{final_status}'")
            except Exception as e:
                print(f"CrystalPay webhook: Failed to mark payment confirmed: {e}")
                # Don't continue if payment confirmation failed
                return JSONResponse(
                    {"error": f"Failed to confirm payment: {str(e)}"},
                    status_code=500
                )
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Try QStash first, fallback to direct delivery if it fails
            delivery_result = await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": real_order_id},
                retries=2,
                deduplication_id=f"deliver-{real_order_id}"
            )
            
            # FALLBACK: If QStash failed, deliver directly
            if not delivery_result.get("queued"):
                print(f"CrystalPay webhook: QStash failed (error={delivery_result.get('error')}), executing direct delivery for {real_order_id}")
                try:
                    from core.routers.workers import _deliver_items_for_order
                    from core.routers.deps import get_notification_service
                    notification_service = get_notification_service()
                    fallback_result = await _deliver_items_for_order(db, notification_service, real_order_id, only_instant=True)
                    print(f"CrystalPay webhook: Direct delivery completed: {fallback_result}")
                except Exception as fallback_err:
                    import traceback
                    print(f"CrystalPay webhook: Direct delivery FAILED for {real_order_id}: {fallback_err}")
                    print(f"CrystalPay webhook: Traceback: {traceback.format_exc()}")
                    # Return 500 to signal CrystalPay to retry
                    return JSONResponse(
                        {"error": f"Delivery failed: {str(fallback_err)[:100]}"},
                        status_code=500
                    )
            
            # Calculate referral bonus (non-critical, ignore failures)
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": real_order_id},
                retries=2,
                deduplication_id=f"referral-{real_order_id}"
            )
            
            # CrystalPay expects HTTP 200 response
            return JSONResponse({"ok": True}, status_code=200)
        
        # Log verification failure
        error_msg = result.get("error", "Unknown error")
        print(f"CrystalPay webhook failed: {error_msg}")
        
        return JSONResponse(
            {"error": error_msg},
            status_code=400
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"CrystalPay webhook error: {e}")
        print(f"Traceback: {error_trace}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )



