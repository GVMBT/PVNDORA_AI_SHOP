"""
Pydantic models for API request/response schemas.

These models are used for data validation and serialization
across all API endpoints.
"""
from pydantic import BaseModel
from typing import Optional


class ProductResponse(BaseModel):
    """Product data returned from API."""
    id: str
    name: str
    description: Optional[str]
    price: float
    type: str
    status: str
    stock_count: int
    warranty_hours: int
    rating: float = 0
    reviews_count: int = 0


class WithdrawalRequest(BaseModel):
    """Request to withdraw balance."""
    amount: float
    method: str  # card, phone, crypto
    details: str


class PromoCheckRequest(BaseModel):
    """Request to check promo code validity."""
    code: str


class WebAppReviewRequest(BaseModel):
    """Submit review from Mini App."""
    order_id: str
    rating: int
    text: Optional[str] = None


class CreateOrderRequest(BaseModel):
    """Create new order request."""
    product_id: Optional[str] = None
    quantity: Optional[int] = 1
    promo_code: Optional[str] = None
    # For cart-based orders
    use_cart: Optional[bool] = False


class OrderResponse(BaseModel):
    """Order creation response."""
    order_id: str
    amount: float
    original_price: float
    discount_percent: int
    payment_url: str
    payment_method: str


class SubmitReviewRequest(BaseModel):
    """Submit product review request."""
    order_id: str
    rating: int  # 1-5
    text: Optional[str] = None

