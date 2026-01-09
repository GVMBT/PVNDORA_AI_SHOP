"""
Admin API Pydantic Models

Shared models for all admin endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel


# ==================== PRODUCT MODELS ====================

class CreateProductRequest(BaseModel):
    """
    Product creation/update request.
    
    Field mapping (frontend → DB):
    - category → type (ai, dev, design, music)
    - fulfillmentType → fulfillment_type (auto, manual)
    - price → price
    - msrp → msrp
    - discountPrice → discount_price
    - costPrice → cost_price
    - fulfillment → fulfillment_time_hours
    - warranty → warranty_hours
    - duration → duration_days
    - requiresPrepayment → requires_prepayment
    - prepaymentPercent → prepayment_percent
    """
    name: str
    description: str = ""
    
    # Category (maps to `type` in DB)
    category: str = "ai"  # ai, dev, design, music
    
    # Pricing
    price: float = 0
    msrp: Optional[float] = None
    discountPrice: Optional[float] = None  # discount_price
    costPrice: Optional[float] = None  # cost_price
    
    # Fulfillment
    fulfillmentType: str = "auto"  # fulfillment_type: auto, manual
    fulfillment: int = 0  # fulfillment_time_hours
    
    # Product Settings
    warranty: int = 168  # warranty_hours
    duration: int = 30  # duration_days
    status: str = "active"
    
    # Prepayment
    requiresPrepayment: bool = False
    prepaymentPercent: int = 100
    
    # Media
    image: Optional[str] = None  # image_url
    video: Optional[str] = None
    
    # Content
    instructions: str = ""


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


class UpdateBalanceRequest(BaseModel):
    amount: float


class UpdateWarningsRequest(BaseModel):
    count: int


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


# ==================== WITHDRAWAL MODELS ====================

class ProcessWithdrawalRequest(BaseModel):
    admin_comment: str | None = None