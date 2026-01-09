"""
WebApp API Pydantic Models

Shared models for all webapp endpoints.
"""
from typing import Optional
from pydantic import BaseModel


# ==================== AUTH MODELS ====================

class TelegramLoginData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class SessionTokenRequest(BaseModel):
    session_token: str


# ==================== ORDER MODELS ====================

class CreateOrderRequest(BaseModel):
    product_id: str | None = None
    quantity: int | None = 1
    promo_code: str | None = None
    use_cart: bool = False
    payment_method: str | None = None  # card, sbp, qr, crypto
    payment_gateway: str | None = None  # crystalpay


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: Optional[str] = None  # None for balance payments, URL for external gateways
    payment_method: str


class ConfirmPaymentRequest(BaseModel):
    """Request to confirm manual payment (H2H)."""
    order_id: str
    hash: Optional[str] = None


# ==================== CART MODELS ====================

class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    product_id: str
    quantity: int = 1  # 0 означает удалить


class ApplyPromoRequest(BaseModel):
    code: str


# ==================== PROFILE MODELS ====================

class UpdatePreferencesRequest(BaseModel):
    preferred_currency: Optional[str] = None  # RUB, USD, EUR, etc.
    interface_language: Optional[str] = None  # ru, en, etc.


class ConvertBalanceRequest(BaseModel):
    """Request to convert user balance to a different currency."""
    target_currency: str  # USD, RUB, EUR, etc.


class WithdrawalRequest(BaseModel):
    amount: float
    method: str  # card, phone, crypto
    details: str


class TopUpRequest(BaseModel):
    amount: float  # Amount in user's currency (RUB or USD)
    currency: str = "RUB"  # RUB or USD


class PromoCheckRequest(BaseModel):
    code: str


class WebAppReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: str | None = None
    product_id: str | None = None  # Optional: specific product to review (for multi-item orders)
    order_item_id: str | None = None  # Optional: specific order item to review


# ==================== PARTNER MODELS ====================

class PartnerApplicationRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    source: str  # instagram, youtube, telegram_channel, website, other
    audience_size: str  # 1k-10k, 10k-50k, 50k-100k, 100k+
    description: str  # Why they want partnership
    expected_volume: str | None = None  # Expected monthly volume
    social_links: dict | None = None  # {instagram: url, youtube: url, ...}
