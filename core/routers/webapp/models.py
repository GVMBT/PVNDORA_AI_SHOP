"""WebApp API Pydantic Models.

Shared models for all webapp endpoints.
"""

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
    payment_url: str | None = None  # None for balance payments, URL for external gateways
    payment_method: str


class ConfirmPaymentRequest(BaseModel):
    """Request to confirm manual payment (H2H)."""

    order_id: str
    hash: str | None = None


class OrderStatusResponse(BaseModel):
    """Order status with delivery progress."""

    order_id: str
    status: str
    progress: int  # 0-100%
    delivered_quantity: int
    total_quantity: int
    estimated_delivery_at: str | None = None
    payment_url: str | None = None


class OrderHistoryResponse(BaseModel):
    """Order in history list."""

    order_id: str
    status: str
    amount: float
    display_amount: str  # Formatted in user's currency
    display_currency: str
    created_at: str | None = None
    product_name: str
    quantity: int
    delivered_quantity: int
    progress: int
    payment_method: str | None = None
    payment_url: str | None = None
    items: list = []
    image_url: str | None = None


class OrdersListResponse(BaseModel):
    """Orders list response with metadata."""

    orders: list[dict]  # Use dict to match APIOrder structure from frontend
    count: int
    currency: str


class PaymentMethod(BaseModel):
    """Payment method info."""

    id: str
    name: str
    description: str
    icon: str
    available: bool
    min_amount: float | None = None
    max_amount: float | None = None
    fee_percent: float = 0
    processing_time: str
    currency: str


class PaymentMethodsResponse(BaseModel):
    """Available payment methods."""

    methods: list[PaymentMethod]
    default_currency: str
    recommended_method: str


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
    preferred_currency: str | None = None  # RUB, USD, EUR, etc.
    interface_language: str | None = None  # ru, en, etc.


class ConvertBalanceRequest(BaseModel):
    """Request to convert user balance to a different currency."""

    target_currency: str  # USD, RUB, EUR, etc.


class WithdrawalPreviewRequest(BaseModel):
    amount: float


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
