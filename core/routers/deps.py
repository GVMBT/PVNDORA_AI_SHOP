"""
Shared Dependencies for Routers

Lazy-loaded singletons to optimize cold start.
Import heavy modules only when needed.
"""

from typing import Optional, TYPE_CHECKING
from functools import lru_cache

if TYPE_CHECKING:
    from src.services.notifications import NotificationService
    from src.services.payments import PaymentService
    from core.cart import CartManager


# ==================== LAZY SINGLETONS ====================

_notification_service: Optional["NotificationService"] = None
_payment_service: Optional["PaymentService"] = None
_cart_manager: Optional["CartManager"] = None


def get_notification_service() -> "NotificationService":
    """Get or create NotificationService singleton (lazy loaded)"""
    global _notification_service
    if _notification_service is None:
        from src.services.notifications import NotificationService
        _notification_service = NotificationService()
    return _notification_service


def get_payment_service() -> "PaymentService":
    """Get or create PaymentService singleton (lazy loaded)"""
    global _payment_service
    if _payment_service is None:
        from src.services.payments import PaymentService
        _payment_service = PaymentService()
    return _payment_service


def get_cart_manager_lazy() -> "CartManager":
    """Get or create CartManager singleton (lazy loaded)"""
    global _cart_manager
    if _cart_manager is None:
        from core.cart import get_cart_manager
        _cart_manager = get_cart_manager()
    return _cart_manager


# ==================== QSTASH VERIFICATION ====================

@lru_cache(maxsize=1)
def get_qstash_verifier():
    """Get QStash verification function (cached import)"""
    from core.queue import verify_qstash_request
    return verify_qstash_request


async def verify_qstash(request) -> bool:
    """Verify QStash request signature"""
    verify_fn = get_qstash_verifier()
    return await verify_fn(request)


# ==================== QUEUE PUBLISHING ====================

def get_queue_publisher():
    """Get queue publishing functions (lazy loaded)"""
    from core.queue import publish_to_worker, WorkerEndpoints
    return publish_to_worker, WorkerEndpoints


# ==================== SHUTDOWN HELPERS ====================
async def shutdown_services():
    """Cleanly close singleton services (http clients, etc.)."""
    global _payment_service
    if _payment_service is not None:
        try:
            await _payment_service.aclose()
        finally:
            _payment_service = None

