"""Database Models - Pydantic models for all entities."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    """User model."""
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: str = "en"
    balance: float = 0
    referrer_id: Optional[str] = None
    personal_ref_percent: int = 20
    is_admin: bool = False
    is_banned: bool = False
    warnings_count: int = 0
    do_not_disturb: bool = False
    total_saved: float = 0
    total_referral_earnings: float = 0
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # Partner/Referral fields
    is_partner: bool = False
    partner_level_override: Optional[int] = None
    partner_mode: str = "commission"  # commission | discount
    partner_discount_percent: int = 0
    referral_program_unlocked: bool = False
    turnover_usd: float = 0
    total_purchases_amount: float = 0
    
    class Config:
        extra = "ignore"  # Ignore unknown fields from DB


class Product(BaseModel):
    """Product model."""
    id: str
    name: str
    description: Optional[str] = None
    price: float
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


class StockItem(BaseModel):
    """Stock item model."""
    id: str
    product_id: str
    content: str
    is_sold: bool = False
    expires_at: Optional[datetime] = None
    supplier_id: Optional[str] = None
    created_at: Optional[datetime] = None


class Order(BaseModel):
    """Order model."""
    id: str
    user_id: str
    product_id: str
    stock_item_id: Optional[str] = None
    amount: float
    original_price: Optional[float] = None
    discount_percent: int = 0
    status: str = "pending"
    payment_method: Optional[str] = None
    expires_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    refund_requested: bool = False
    created_at: Optional[datetime] = None

