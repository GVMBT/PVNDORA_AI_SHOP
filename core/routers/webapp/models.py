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


class OrderResponse(BaseModel):
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


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

class WithdrawalRequest(BaseModel):
    amount: float
    method: str  # card, phone, crypto
    details: str


class PromoCheckRequest(BaseModel):
    code: str


class WebAppReviewRequest(BaseModel):
    order_id: str
    rating: int
    text: str | None = None


# ==================== PARTNER MODELS ====================

class PartnerApplicationRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    source: str  # instagram, youtube, telegram_channel, website, other
    audience_size: str  # 1k-10k, 10k-50k, 50k-100k, 100k+
    description: str  # Why they want partnership
    expected_volume: str | None = None  # Expected monthly volume
    social_links: dict | None = None  # {instagram: url, youtube: url, ...}
