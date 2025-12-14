"""Database Models - Pydantic models for all entities."""
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from core.services.money import to_decimal as _to_decimal


class User(BaseModel):
    """User model."""
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: str = "en"
    preferred_currency: Optional[str] = None  # User preferred currency (RUB, USD, EUR, etc.)
    interface_language: Optional[str] = None  # User preferred interface language (ru, en, etc.)
    balance: Decimal = Decimal("0")
    referrer_id: Optional[str] = None
    personal_ref_percent: int = 20
    is_admin: bool = False
    is_banned: bool = False
    warnings_count: int = 0
    do_not_disturb: bool = False
    total_saved: Decimal = Decimal("0")
    total_referral_earnings: Decimal = Decimal("0")
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # Partner/Referral fields
    is_partner: bool = False
    partner_level_override: Optional[int] = None
    partner_mode: str = "commission"  # commission | discount
    partner_discount_percent: int = 0
    referral_program_unlocked: bool = False
    turnover_usd: Decimal = Decimal("0")
    total_purchases_amount: Decimal = Decimal("0")
    # Referral click tracking
    referral_clicks: int = 0
    # Profile photo from Telegram
    photo_url: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignore unknown fields from DB
    
    @field_validator("balance", "total_saved", "total_referral_earnings", "turnover_usd", "total_purchases_amount", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        return _to_decimal(v)


class Product(BaseModel):
    """Product model."""
    id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    type: str  # student, trial, shared, key
    status: str = "active"
    warranty_hours: int = 24
    instructions: Optional[str] = None
    terms: Optional[str] = None
    supplier_id: Optional[str] = None
    stock_count: int = 0
    fulfillment_time_hours: int = 48
    requires_prepayment: bool = False
    prepayment_percent: int = 100
    categories: list[str] = []  # text, video, image, code, audio
    msrp: Optional[Decimal] = None
    duration_days: Optional[int] = None
    instruction_files: Optional[list] = None
    image_url: Optional[str] = None
    
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
    expires_at: Optional[datetime] = None
    supplier_id: Optional[str] = None
    created_at: Optional[datetime] = None
    reserved_at: Optional[datetime] = None
    sold_at: Optional[datetime] = None
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
    product_id: Optional[str] = None  # Use order_items instead
    stock_item_id: Optional[str] = None  # Use order_items instead
    delivery_content: Optional[str] = None  # Use order_items instead
    delivery_instructions: Optional[str] = None  # Use order_items instead
    # Active fields
    amount: Decimal
    original_price: Optional[Decimal] = None
    discount_percent: int = 0
    status: str = "pending"
    payment_method: Optional[str] = None
    payment_gateway: Optional[str] = None
    expires_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    refund_requested: bool = False
    created_at: Optional[datetime] = None
    user_telegram_id: Optional[int] = None
    payment_id: Optional[str] = None
    payment_url: Optional[str] = None
    order_type: Optional[str] = "instant"
    fulfillment_deadline: Optional[datetime] = None
    
    class Config:
        extra = "ignore"  # Ignore unknown fields from DB
    
    @field_validator("amount", "original_price", mode="before")
    @classmethod
    def convert_amount_to_decimal(cls, v):
        return _to_decimal(v) if v is not None else None


class OrderItem(BaseModel):
    """Order item model (per-product in order)."""
    id: str
    order_id: str
    product_id: str
    stock_item_id: Optional[str] = None
    quantity: int = 1
    status: str = "pending"
    fulfillment_type: str = "instant"  # instant | preorder
    delivery_content: Optional[str] = None
    delivery_instructions: Optional[str] = None
    price: Optional[Decimal] = None
    discount_percent: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    @field_validator("price", mode="before")
    @classmethod
    def convert_item_price_to_decimal(cls, v):
        return _to_decimal(v) if v is not None else None
