"""
Webhooks Router

Payment and notification webhooks.
All webhooks verify signatures and delegate to QStash workers.
"""

import json

from fastapi import APIRouter, Request
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



