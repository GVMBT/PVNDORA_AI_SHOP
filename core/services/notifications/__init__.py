"""
Notification Service Module

Unified notification service combining all notification types.
Backward compatible - exposes NotificationService as main class.
"""
from .base import (
    get_user_language,
    get_referral_settings,
    _msg,
)
from .delivery import DeliveryNotificationsMixin
from .orders import OrderNotificationsMixin
from .support import SupportNotificationsMixin
from .referral import ReferralNotificationsMixin
from .payments import PaymentNotificationsMixin
from .withdrawals import WithdrawalNotificationsMixin
from .misc import MiscNotificationsMixin


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
    "get_user_language",
    "get_referral_settings",
    "_msg",
]
