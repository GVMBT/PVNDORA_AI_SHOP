"""
QStash Module - Message Queue for Guaranteed Delivery

Provides QStash client for publishing tasks to worker endpoints.
Used for critical operations that must be guaranteed to execute:
- Goods delivery after payment
- Referral bonus calculation
- Supplier notifications
- Leaderboard updates
"""

import os
from typing import Optional
from functools import wraps

from fastapi import Request, HTTPException


# Environment variables
QSTASH_TOKEN = os.environ.get("QSTASH_TOKEN", "")
QSTASH_URL = os.environ.get("QSTASH_URL", "https://qstash.upstash.io")
QSTASH_CURRENT_SIGNING_KEY = os.environ.get("QSTASH_CURRENT_SIGNING_KEY", "")
QSTASH_NEXT_SIGNING_KEY = os.environ.get("QSTASH_NEXT_SIGNING_KEY", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
BASE_URL = os.environ.get("BASE_URL", "")


# Singleton QStash client
_qstash_client = None


def get_qstash():
    """
    Get QStash client (singleton).
    
    Returns QStash client for publishing messages to worker endpoints.
    """
    global _qstash_client
    
    if _qstash_client is None:
        if not QSTASH_TOKEN:
            raise ValueError("QSTASH_TOKEN must be set")
        
        from qstash import QStash
        _qstash_client = QStash(token=QSTASH_TOKEN)
    
    return _qstash_client


def get_base_url() -> str:
    """Get base URL for worker endpoints.
    
    IMPORTANT: Use fixed production URL (WEBAPP_URL or BASE_URL).
    Vercel preview URLs change with each deployment, which breaks QStash
    workers that get published during one deployment but execute during
    another.
    """
    # Priority: WEBAPP_URL (production) > BASE_URL
    if WEBAPP_URL:
        if WEBAPP_URL.startswith("http"):
            return WEBAPP_URL.rstrip("/")
        return f"https://{WEBAPP_URL}"
    
    if BASE_URL:
        if BASE_URL.startswith("http"):
            return BASE_URL.rstrip("/")
        return f"https://{BASE_URL}"
    
    # Local development fallback
    return "http://localhost:8000"


async def publish_to_worker(
    endpoint: str,
    body: dict,
    retries: int = 0,
    delay: Optional[int] = None,
    deduplication_id: Optional[str] = None
) -> dict:
    """
    Publish a task to a QStash worker endpoint.
    
    Args:
        endpoint: Worker endpoint path (e.g., "/api/workers/deliver-goods")
        body: JSON body to send to the worker
        retries: Number of retry attempts on failure (default: 3)
        delay: Delay in seconds before processing (optional)
        deduplication_id: ID to prevent duplicate processing (optional)
    
    Returns:
        QStash publish response with message_id
    
    Example:
        await publish_to_worker(
            endpoint="/api/workers/deliver-goods",
            body={"order_id": "123", "user_id": "456"},
            retries=3
        )
    """
    qstash = get_qstash()
    base_url = get_base_url()
    url = f"{base_url}{endpoint}"
    
    # Build headers
    headers = {}
    if deduplication_id:
        headers["Upstash-Deduplication-Id"] = deduplication_id
    
    # Cap retries at 2 for Free tier safety (limit is 3, but be conservative)
    safe_retries = min(retries, 2)
    
    try:
        result = qstash.message.publish_json(
            url=url,
            body=body,
            retries=safe_retries,
            delay=f"{delay}s" if delay else None,
            headers=headers if headers else None
        )
        return {"message_id": result.message_id, "queued": True}
    except Exception as e:
        # Log error but don't raise - let caller handle fallback
        print(f"QStash publish failed: {e}")
        return {"message_id": None, "queued": False, "error": str(e)}


async def publish_to_queue(
    queue_name: str,
    endpoint: str,
    body: dict,
    deduplication_id: Optional[str] = None
) -> dict:
    """
    Publish a task to a QStash queue for ordered processing.
    
    Args:
        queue_name: Name of the queue (e.g., "broadcast")
        endpoint: Worker endpoint path
        body: JSON body to send
        deduplication_id: ID to prevent duplicates
    
    Returns:
        QStash enqueue response
    """
    qstash = get_qstash()
    base_url = get_base_url()
    url = f"{base_url}{endpoint}"
    
    result = qstash.message.enqueue_json(
        queue=queue_name,
        url=url,
        body=body,
        deduplication_id=deduplication_id
    )
    
    return {"message_id": result.message_id}


def verify_qstash_signature(body: bytes, signature: str, url: str = "") -> bool:
    """
    Verify QStash webhook signature using QStash Receiver.
    
    Args:
        body: Raw request body bytes
        signature: Signature from Upstash-Signature header
        url: The full URL that received the request
    
    Returns:
        True if signature is valid
    """
    if not QSTASH_CURRENT_SIGNING_KEY:
        # Skip verification in development
        print("QStash: No signing key configured, skipping verification")
        return True
    
    try:
        from qstash import Receiver
        
        receiver = Receiver(
            current_signing_key=QSTASH_CURRENT_SIGNING_KEY,
            next_signing_key=QSTASH_NEXT_SIGNING_KEY or None,
        )
        
        # Verify signature (QStash uses JWT which includes URL)
        receiver.verify(
            body=body.decode('utf-8') if isinstance(body, bytes) else body,
            signature=signature,
            url=url,
        )
        return True
    except Exception as e:
        print(f"QStash signature verification failed: {e}")
        return False


async def verify_qstash_request(request: Request) -> dict:
    """
    Verify QStash request and return parsed body.
    
    Raises HTTPException 401 if signature is invalid.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Parsed JSON body
    """
    signature = request.headers.get("Upstash-Signature", "")
    body = await request.body()
    
    # Build full URL for verification (QStash JWT includes URL)
    url = str(request.url)
    
    if not verify_qstash_signature(body, signature, url):
        print(f"QStash verification failed for URL: {url}")
        raise HTTPException(status_code=401, detail="Invalid QStash signature")
    
    import json
    return json.loads(body)


def qstash_protected(func):
    """
    Decorator to protect worker endpoints with QStash signature verification.
    
    Usage:
        @app.post("/api/workers/deliver-goods")
        @qstash_protected
        async def deliver_goods(request: Request):
            data = await verify_qstash_request(request)
            # Process data...
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Verify signature
        await verify_qstash_request(request)
        return await func(request, *args, **kwargs)
    
    return wrapper


# Worker endpoint paths (constants for consistency)
class WorkerEndpoints:
    """Constants for QStash worker endpoint paths."""
    
    # Delivery
    DELIVER_GOODS = "/api/workers/deliver-goods"
    DELIVER_BATCH = "/api/workers/deliver-batch"
    
    # Notifications
    NOTIFY_SUPPLIER = "/api/workers/notify-supplier"
    NOTIFY_SUPPLIER_PREPAID = "/api/workers/notify-supplier-prepaid"
    NOTIFY_WAITLIST = "/api/workers/notify-waitlist"
    SEND_BROADCAST = "/api/workers/send-broadcast"
    
    # Processing
    CALCULATE_REFERRAL = "/api/workers/calculate-referral"
    UPDATE_LEADERBOARD = "/api/workers/update-leaderboard"
    PROCESS_REFUND = "/api/workers/process-refund"
    PROCESS_REVIEW_CASHBACK = "/api/workers/process-review-cashback"

