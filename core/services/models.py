"""Database Models - Pydantic models for all entities."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from core.services.money import to_decimal as _to_decimal


class User(BaseModel):
    """User model."""

    id: str
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    language_code: str = "en"
    preferred_currency: str | None = None  # User preferred currency (RUB, USD, EUR, etc.)
    interface_language: str | None = None  # User preferred interface language (ru, en, etc.)
    balance: Decimal = Decimal("0")
    balance_currency: str = "USD"  # Currency of user's balance (RUB, USD)
    referrer_id: str | None = None
    personal_ref_percent: int = 10  # Default L1 commission (actual from referral_settings)
    is_admin: bool = False
    is_banned: bool = False
    warnings_count: int = 0
    do_not_disturb: bool = False
    total_saved: Decimal = Decimal("0")
    total_referral_earnings: Decimal = Decimal("0")
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
    # Partner/Referral fields
    is_partner: bool = False
    partner_level_override: int | None = None
    partner_mode: str = "commission"  # commission | discount
    partner_discount_percent: int = 0
    referral_program_unlocked: bool = False
    turnover_usd: Decimal = Decimal("0")
    total_purchases_amount: Decimal = Decimal("0")
    # Referral click tracking
    referral_clicks: int = 0
    # Profile photo from Telegram
    photo_url: str | None = None

    class Config:
        extra = "ignore"  # Ignore unknown fields from DB

    @field_validator(
        "balance",
        "total_saved",
        "total_referral_earnings",
        "turnover_usd",
        "total_purchases_amount",
        mode="before",
    )
    @classmethod
    def convert_to_decimal(cls, v):
        return _to_decimal(v)


class Product(BaseModel):
    """Product model."""

    id: str
    name: str
    description: str | None = None
    price: Decimal  # Base price in USD
    prices: dict | None = None  # Anchor prices: {"RUB": 990, "USD": 10.50}
    msrp_prices: dict | None = None  # Anchor MSRP: {"RUB": 20000, "USD": 250}
    type: str  # student, trial, shared, key
    status: str = "active"
    warranty_hours: int = 24
    instructions: str | None = None
    terms: str | None = None
    supplier_id: str | None = None
    stock_count: int = 0
    fulfillment_time_hours: int = 48
    requires_prepayment: bool = False
    prepayment_percent: int = 100
    categories: list[str] = []  # text, video, image, code, audio
    msrp: Decimal | None = None  # Base MSRP in USD
    duration_days: int | None = None
    instruction_files: list | None = None
    image_url: str | None = None
    video_url: str | None = None
    logo_svg_url: str | None = None

    @field_validator("price", mode="before")
    @classmethod
    def convert_price_to_decimal(cls, v):
        return _to_decimal(v)


class StockItem(BaseModel):
    """Stock item model."""

    id: str
    product_id: str
    content: str
    status: str = "available"  # available | reserved | sold
    expires_at: datetime | None = None
    supplier_id: str | None = None
    created_at: datetime | None = None
    reserved_at: datetime | None = None
    sold_at: datetime | None = None
    discount_percent: Decimal = Decimal("0")

    @field_validator("discount_percent", mode="before")
    @classmethod
    def convert_discount_to_decimal(cls, v):
        return _to_decimal(v) if v is not None else Decimal("0")


class Order(BaseModel):
    """Order model.

    Note: product_id, stock_item_id, delivery_content, delivery_instructions
    are deprecated. Use order_items table for this data.
    """

    id: str
    user_id: str
    # DEPRECATED fields - will be removed after migration
    product_id: str | None = None  # Use order_items instead
    stock_item_id: str | None = None  # Use order_items instead
    delivery_content: str | None = None  # Use order_items instead
    delivery_instructions: str | None = None  # Use order_items instead
    # Active fields
    amount: Decimal  # Always in USD (base currency for accounting)
    original_price: Decimal | None = None
    discount_percent: int = 0
    status: str = "pending"
    payment_method: str | None = None
    payment_gateway: str | None = None
    expires_at: datetime | None = None
    delivered_at: datetime | None = None
    warranty_until: datetime | None = None
    refund_requested: bool = False
    created_at: datetime | None = None
    user_telegram_id: int | None = None
    payment_id: str | None = None
    payment_url: str | None = None
    order_type: str | None = "instant"
    fulfillment_deadline: datetime | None = None
    # Currency snapshot fields (for accurate accounting)
    fiat_amount: Decimal | None = None  # Amount in user's currency
    fiat_currency: str | None = None  # User's currency code (RUB, USD, etc.)
    exchange_rate_snapshot: Decimal | None = None  # Rate at order creation (1 USD = X fiat)

    class Config:
        extra = "ignore"  # Ignore unknown fields from DB

    @field_validator(
        "amount", "original_price", "fiat_amount", "exchange_rate_snapshot", mode="before"
    )
    @classmethod
    def convert_amount_to_decimal(cls, v):
        return _to_decimal(v) if v is not None else None


class OrderItem(BaseModel):
    """Order item model (per-product in order)."""

    id: str
    order_id: str
    product_id: str
    stock_item_id: str | None = None
    quantity: int = 1
    status: str = "pending"
    fulfillment_type: str = "instant"  # instant | preorder
    delivery_content: str | None = None
    delivery_instructions: str | None = None
    price: Decimal | None = None
    discount_percent: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    delivered_at: datetime | None = None

    @field_validator("price", mode="before")
    @classmethod
    def convert_item_price_to_decimal(cls, v):
        return _to_decimal(v) if v is not None else None
