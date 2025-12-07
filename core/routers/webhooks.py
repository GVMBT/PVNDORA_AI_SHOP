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
            
            print(f"1Plat webhook verified successfully for order: {order_id}")
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=5,
                deduplication_id=f"deliver-{order_id}"
            )
            
            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=3,
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
            
            print(f"Freekassa webhook verified successfully for order: {order_id}")
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": order_id},
                retries=5,
                deduplication_id=f"deliver-{order_id}"
            )
            
            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": order_id},
                retries=3,
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
            try:
                import asyncio
                lookup_result = await asyncio.to_thread(
                    lambda: db.client.table("orders")
                    .select("id")
                    .eq("payment_id", payment_order_id)
                    .limit(1)
                    .execute()
                )
                if lookup_result.data:
                    real_order_id = lookup_result.data[0]["id"]
                    print(f"Rukassa webhook: mapped payment_id {payment_order_id} -> order_id {real_order_id}")
                else:
                    # Fallback: try direct lookup (backward compatibility)
                    direct_result = await asyncio.to_thread(
                        lambda: db.client.table("orders")
                        .select("id")
                        .eq("id", payment_order_id)
                        .limit(1)
                        .execute()
                    )
                    if direct_result.data:
                        real_order_id = direct_result.data[0]["id"]
                        print(f"Rukassa webhook: direct order lookup succeeded for {real_order_id}")
                    else:
                        print(f"Rukassa webhook: Order not found for payment_id {payment_order_id}")
                        return Response(content="ERROR ORDER NOT FOUND", status_code=404)
            except Exception as e:
                print(f"Rukassa webhook: Order lookup error: {e}")
                # Continue with payment_order_id as fallback
            
            print(f"Rukassa webhook processing delivery for order: {real_order_id}")
            
            publish_to_worker, WorkerEndpoints = get_queue_publisher()
            
            # Guaranteed delivery via QStash
            await publish_to_worker(
                endpoint=WorkerEndpoints.DELIVER_GOODS,
                body={"order_id": real_order_id},
                retries=5,
                deduplication_id=f"deliver-{real_order_id}"
            )
            
            # Calculate referral bonus
            await publish_to_worker(
                endpoint=WorkerEndpoints.CALCULATE_REFERRAL,
                body={"order_id": real_order_id},
                retries=3,
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



