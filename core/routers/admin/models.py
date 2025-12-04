"""
Admin API Pydantic Models

Shared models for all admin endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel


# ==================== PRODUCT MODELS ====================

class CreateProductRequest(BaseModel):
    name: str
    description: str
    price: float
    type: str = "subscription"
    fulfillment_time_hours: int = 0
    warranty_hours: int = 168
    instructions: str = ""
    msrp: Optional[float] = None
    duration_days: Optional[int] = None


# ==================== FAQ MODELS ====================

class CreateFAQRequest(BaseModel):
    question: str
    answer: str
    language_code: str = "ru"
    category: str = "general"


# ==================== USER MODELS ====================

class BanUserRequest(BaseModel):
    telegram_id: int
    ban: bool


# ==================== STOCK MODELS ====================

class AddStockRequest(BaseModel):
    product_id: str
    content: str
    expires_at: Optional[str] = None
    supplier_id: Optional[str] = None


class BulkStockRequest(BaseModel):
    product_id: str
    items: List[str]
    expires_at: Optional[str] = None
    supplier_id: Optional[str] = None


# ==================== BROADCAST MODELS ====================

class BroadcastRequest(BaseModel):
    message: str
    exclude_dnd: bool = True


# ==================== REFERRAL MODELS ====================

class ReferralSettingsRequest(BaseModel):
    level2_threshold_usd: Optional[float] = None
    level3_threshold_usd: Optional[float] = None
    level1_commission_percent: Optional[float] = None
    level2_commission_percent: Optional[float] = None
    level3_commission_percent: Optional[float] = None


class SetPartnerRequest(BaseModel):
    telegram_id: int
    is_partner: bool = True
    level_override: Optional[int] = None  # 1, 2, or 3 - force unlock levels


class ReviewApplicationRequest(BaseModel):
    application_id: str
    approve: bool
    admin_comment: str | None = None
    level_override: int = 3  # Default to full access for approved partners
