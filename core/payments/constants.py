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
    """
    Order status lifecycle.
    
    Flow:
        pending -> paid/prepaid -> partial -> delivered
                                -> cancelled
                                -> refunded
    
    - pending: Created, awaiting payment
    - paid: Payment confirmed + stock available
    - prepaid: Payment confirmed + stock unavailable (preorder)
    - partial: Some items delivered, others waiting
    - delivered: All items delivered (final)
    - cancelled: Order cancelled (expired/user/error) (final)
    - refunded: Funds returned to user (final)
    """
    PENDING = "pending"
    PAID = "paid"
    PREPAID = "prepaid"
    PARTIAL = "partial"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


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
}

# Statuses that indicate payment confirmed (can proceed with delivery)
PAID_STATES: Set[str] = {
    OrderStatus.PAID.value,
    OrderStatus.PREPAID.value,
    OrderStatus.PARTIAL.value,
}

# Final statuses (no further transitions)
FINAL_STATES: Set[str] = {
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELLED.value,
    OrderStatus.REFUNDED.value,
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

