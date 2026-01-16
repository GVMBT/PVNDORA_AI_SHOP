"""Admin API Pydantic Models.

Shared models for all admin endpoints.
"""

from typing import Any

from pydantic import BaseModel

# ==================== PRODUCT MODELS ====================


class CreateProductRequest(BaseModel):
    """Product creation/update request.

    Field mapping (frontend → DB):
    - category → type (ai, dev, design, music)
    - fulfillmentType → fulfillment_type (auto, manual)
    - price → price (base USD price)
    - prices → prices (anchor prices JSONB, e.g. {"RUB": 990, "USD": 10.50})
    - msrp → msrp
    - msrp_prices → msrp_prices (anchor MSRP)
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
    price: float = 0  # Base USD price
    prices: dict[str, Any] | None = None  # Anchor prices: {"RUB": 990, "USD": 10.50}
    msrp: float | None = None  # MSRP in RUB
    discountPrice: float | None = None  # discount_price
    costPrice: float | None = None  # cost_price

    # Fulfillment
    fulfillmentType: str = "auto"  # fulfillment_type: auto, manual
    fulfillment: int = 0  # fulfillment_time_hours

    # Product Settings
    warranty: int = 168  # warranty_hours (stored in hours, UI shows days)
    duration: int = 30  # duration_days
    status: str = "active"

    # Media
    image: str | None = None  # image_url
    video: str | None = None

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
    expires_at: str | None = None
    supplier_id: str | None = None


class BulkStockRequest(BaseModel):
    product_id: str
    items: list[str]
    expires_at: str | None = None
    supplier_id: str | None = None


# ==================== BROADCAST MODELS ====================


class BroadcastRequest(BaseModel):
    message: str
    exclude_dnd: bool = True


# ==================== REFERRAL MODELS ====================


class ReferralSettingsRequest(BaseModel):
    level2_threshold_usd: float | None = None
    level3_threshold_usd: float | None = None
    level1_commission_percent: float | None = None
    level2_commission_percent: float | None = None
    level3_commission_percent: float | None = None
    thresholds_by_currency: dict[str, dict[str, Any]] | None = (
        None  # Anchor thresholds: {"USD": {"level2": 250, "level3": 1000}, "RUB": {"level2": 20000, "level3": 80000}}
    )


class SetPartnerRequest(BaseModel):
    telegram_id: int
    is_partner: bool = True
    level_override: int | None = None  # 1, 2, or 3 - force unlock levels


class ReviewApplicationRequest(BaseModel):
    application_id: str
    approve: bool
    admin_comment: str | None = None
    level_override: int = 3  # Default to full access for approved partners


# ==================== WITHDRAWAL MODELS ====================


class ProcessWithdrawalRequest(BaseModel):
    admin_comment: str | None = None
