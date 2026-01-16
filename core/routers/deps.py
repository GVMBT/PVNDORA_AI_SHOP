"""Shared Dependencies for Routers.

Lazy-loaded singletons to optimize cold start.
Import heavy modules only when needed.
"""

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from aiogram import Bot
    from fastapi import Request

    from core.cart import CartManager
    from core.services.admin_alerts import AdminAlertService
    from core.services.notifications import NotificationService
    from core.services.payments import PaymentService


# ==================== LAZY SINGLETONS ====================

_notification_service: Optional["NotificationService"] = None
_payment_service: Optional["PaymentService"] = None
_admin_alert_service: Optional["AdminAlertService"] = None
_cart_manager: Optional["CartManager"] = None
_bot: Optional["Bot"] = None


def get_notification_service() -> "NotificationService":
    """Get or create NotificationService singleton (lazy loaded)."""
    global _notification_service
    if _notification_service is None:
        from core.services.notifications import NotificationService

        _notification_service = NotificationService()
    return _notification_service


def get_payment_service() -> "PaymentService":
    """Get or create PaymentService singleton (lazy loaded)."""
    global _payment_service
    if _payment_service is None:
        from core.services.payments import PaymentService

        _payment_service = PaymentService()
    return _payment_service


def get_admin_alerts() -> "AdminAlertService":
    """Get or create AdminAlertService singleton (lazy loaded)."""
    global _admin_alert_service
    if _admin_alert_service is None:
        from core.services.admin_alerts import AdminAlertService

        _admin_alert_service = AdminAlertService()
    return _admin_alert_service


def get_cart_manager_lazy() -> "CartManager":
    """Get or create CartManager singleton (lazy loaded)."""
    global _cart_manager
    if _cart_manager is None:
        from core.cart import get_cart_manager

        _cart_manager = get_cart_manager()
    return _cart_manager


def get_bot() -> Optional["Bot"]:
    """Get or create Bot singleton (lazy loaded)."""
    global _bot
    if _bot is None:
        telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
        if telegram_token:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            _bot = Bot(
                token=telegram_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
    return _bot


def get_webapp_url() -> str:
    """Get WebApp URL from environment."""
    return os.environ.get("WEBAPP_URL", "https://pvndora.app")


# ==================== QSTASH VERIFICATION ====================


@lru_cache(maxsize=1)
def get_qstash_verifier() -> Any:
    """Get QStash verification function (cached import)."""
    from core.queue import verify_qstash_request

    return verify_qstash_request


async def verify_qstash(request: "Request") -> dict[str, Any]:
    """Verify QStash request signature and return parsed body."""
    verify_fn = get_qstash_verifier()
    return await verify_fn(request)  # Returns dict with parsed JSON body


# ==================== QUEUE PUBLISHING ====================


def get_queue_publisher() -> tuple[Any, Any]:
    """Get queue publishing functions (lazy loaded)."""
    from core.queue import WorkerEndpoints, publish_to_worker

    return publish_to_worker, WorkerEndpoints


# ==================== SHUTDOWN HELPERS ====================
async def shutdown_services() -> None:
    """Cleanly close singleton services (http clients, etc.)."""
    global _payment_service
    if _payment_service is not None:
        try:
            await _payment_service.aclose()
        finally:
            _payment_service = None
