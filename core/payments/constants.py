"""Payment constants, enums, and aliases."""
from enum import Enum
from typing import Set


class PaymentGateway(str, Enum):
    """Supported payment gateways."""
    RUKASSA = "rukassa"
    CRYSTALPAY = "crystalpay"
    FREEKASSA = "freekassa"
    ONEPLAT = "1plat"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CARD = "card"
    SBP = "sbp"
    SBP_QR = "sbp_qr"
    CRYPTO = "crypto"


class OrderStatus(str, Enum):
    """Order statuses."""
    PENDING = "pending"
    PREPAID = "prepaid"
    PARTIAL = "partial"
    DELIVERED = "delivered"
    FULFILLED = "fulfilled"
    COMPLETED = "completed"
    READY = "ready"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    FAILED = "failed"
    ERROR = "error"


# Gateway name aliases (input -> canonical)
GATEWAY_ALIASES: dict[str, str] = {
    "rukassa": PaymentGateway.RUKASSA.value,
    "crystalpay": PaymentGateway.CRYSTALPAY.value,
    "crystal_pay": PaymentGateway.CRYSTALPAY.value,
    "crystal-pay": PaymentGateway.CRYSTALPAY.value,
    "freekassa": PaymentGateway.FREEKASSA.value,
    "free_kassa": PaymentGateway.FREEKASSA.value,
    "1plat": PaymentGateway.ONEPLAT.value,
    "oneplat": PaymentGateway.ONEPLAT.value,
    "one_plat": PaymentGateway.ONEPLAT.value,
    "onplat": PaymentGateway.ONEPLAT.value,
}

# Statuses that indicate delivery completed
DELIVERED_STATES: Set[str] = {
    OrderStatus.DELIVERED.value,
    OrderStatus.FULFILLED.value,
    OrderStatus.COMPLETED.value,
    OrderStatus.READY.value,
}

# Gateway -> currency map (for payment creation)
GATEWAY_CURRENCY: dict[str, str] = {
    PaymentGateway.RUKASSA.value: "RUB",
    PaymentGateway.CRYSTALPAY.value: "RUB",  # default, CrystalPay supports RUB; switch if USDC configured
    PaymentGateway.FREEKASSA.value: "USD",   # Freekassa typically in USD (configurable if needed)
    PaymentGateway.ONEPLAT.value: "RUB",     # 1Plat in RUB minor units
}


def normalize_gateway(gateway: str) -> str:
    """
    Normalize gateway name to canonical form.
    
    Args:
        gateway: Gateway name (any case, with aliases)
        
    Returns:
        Canonical gateway name (lowercase)
        
    Example:
        normalize_gateway("CrystalPay") -> "crystalpay"
        normalize_gateway("oneplat") -> "1plat"
    """
    if not gateway:
        return PaymentGateway.RUKASSA.value
    
    normalized = gateway.lower().strip()
    return GATEWAY_ALIASES.get(normalized, normalized)

