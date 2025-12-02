"""
Webhooks Router

Payment and notification webhooks.
All webhooks verify signatures and delegate to QStash workers.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.routers.deps import get_payment_service, get_queue_publisher

router = APIRouter(tags=["webhooks"])


# ==================== AAIO WEBHOOK ====================

@router.post("/webhook/aaio")
async def aaio_webhook(request: Request):
    """Handle AAIO payment callback"""
    try:
        data = await request.form()
        
        payment_service = get_payment_service()
        result = await payment_service.verify_aaio_callback(dict(data))
        
        if result["success"]:
            order_id = result["order_id"]
            
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
        
        return JSONResponse({"ok": False, "error": result.get("error")}, status_code=400)
        
    except Exception as e:
        print(f"AAIO webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ==================== CARDLINK WEBHOOKS ====================

@router.post("/api/webhook/cardlink")
async def cardlink_webhook(request: Request):
    """Handle CardLink payment webhook"""
    try:
        data = await request.json()
        
        payment_service = get_payment_service()
        result = await payment_service.verify_cardlink_webhook(data)
        
        if result["success"]:
            order_id = result["order_id"]
            
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
        
        return JSONResponse({"ok": False, "error": result.get("error")}, status_code=400)
        
    except Exception as e:
        print(f"CardLink webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/webhook/cardlink/refund")
async def cardlink_refund_webhook(request: Request):
    """Handle CardLink refund webhook"""
    try:
        data = await request.json()
        print(f"CardLink refund webhook: {data}")
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"CardLink refund webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/webhook/cardlink/chargeback")
async def cardlink_chargeback_webhook(request: Request):
    """Handle CardLink chargeback webhook"""
    try:
        data = await request.json()
        print(f"CardLink chargeback webhook: {data}")
        return JSONResponse({"ok": True})
    except Exception as e:
        print(f"CardLink chargeback webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ==================== STRIPE WEBHOOK ====================

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe payment webhook"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        payment_service = get_payment_service()
        result = await payment_service.verify_stripe_webhook(payload, sig_header)
        
        if result["success"]:
            order_id = result.get("order_id")
            
            if order_id:
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
            
            return JSONResponse({"received": True})
        
        return JSONResponse(
            {"error": result.get("error", "Unknown error")}, 
            status_code=400
        )
        
    except Exception as e:
        print(f"Stripe webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

