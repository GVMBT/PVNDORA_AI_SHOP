"""
Notification Service Module

Unified notification service combining all notification types.
Backward compatible - exposes NotificationService as main class.
"""

from .base import (
    _msg,
    get_referral_settings,
    get_user_language,
)
from .delivery import DeliveryNotificationsMixin
from .misc import MiscNotificationsMixin
from .orders import OrderNotificationsMixin
from .payments import PaymentNotificationsMixin
from .referral import ReferralNotificationsMixin
from .support import SupportNotificationsMixin
from .withdrawals import WithdrawalNotificationsMixin


class NotificationService(
    DeliveryNotificationsMixin,
    OrderNotificationsMixin,
    SupportNotificationsMixin,
    ReferralNotificationsMixin,
    PaymentNotificationsMixin,
    WithdrawalNotificationsMixin,
    MiscNotificationsMixin,
):
    """
    Service for sending notifications and fulfilling orders.

    Combines all notification mixins into a single service class.

    NOTE: fulfill_order() was removed - DEPRECATED
    Use workers._deliver_items_for_order() instead for order fulfillment.
    """

    def __init__(self):
        super().__init__()


# Re-export for backward compatibility
__all__ = [
    "NotificationService",
    "_msg",
    "get_referral_settings",
    "get_user_language",
]
