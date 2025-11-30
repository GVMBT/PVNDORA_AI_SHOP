"""
Pydantic Models - Data Schemas for AI and API

Contains all Pydantic models used throughout the application:
- AI Response schemas (for Gemini Structured Outputs)
- API request/response models
- Database entity representations
"""

from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class IntentType(str, Enum):
    """User intent types detected by AI."""
    DISCOVERY = "discovery"  # Looking for product info
    PURCHASE = "purchase"  # Ready to buy
    SUPPORT = "support"  # Need help/replacement
    COMPARISON = "comparison"  # Comparing products
    FAQ = "faq"  # General question
    GREETING = "greeting"  # Hello/small talk
    OTHER = "other"


class ActionType(str, Enum):
    """AI action types in response."""
    OFFER_PAYMENT = "offer_payment"
    ADD_TO_CART = "add_to_cart"
    UPDATE_CART = "update_cart"
    SHOW_CATALOG = "show_catalog"
    ADD_TO_WAITLIST = "add_to_waitlist"
    CREATE_TICKET = "create_ticket"
    SHOW_ORDERS = "show_orders"
    SHOW_WISHLIST = "show_wishlist"
    COMPARE_PRODUCTS = "compare_products"
    NONE = "none"


class OrderType(str, Enum):
    """Order fulfillment type."""
    INSTANT = "instant"  # In stock, immediate delivery
    PREPAID = "prepaid"  # Needs to be ordered


class OrderStatus(str, Enum):
    """Order status lifecycle."""
    PENDING = "pending"
    PREPAID = "prepaid"
    FULFILLING = "fulfilling"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class TicketStatus(str, Enum):
    """Support ticket status."""
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class ProductType(str, Enum):
    """Product/subscription type."""
    STUDENT = "student"  # Educational discount
    TRIAL = "trial"  # Trial period
    SHARED = "shared"  # Shared access
    KEY = "key"  # API key


# ============================================================
# AI Response Models (for Gemini Structured Outputs)
# ============================================================

class CartItemResponse(BaseModel):
    """Cart item in AI response."""
    product_id: str = Field(description="Product UUID")
    product_name: str = Field(description="Product name")
    quantity: int = Field(description="Requested quantity", ge=1)
    instant_quantity: int = Field(description="Quantity available in stock", ge=0)
    prepaid_quantity: int = Field(description="Quantity to order", ge=0)
    unit_price: float = Field(description="Price per unit after discount")
    discount_percent: float = Field(description="Applied discount percentage", ge=0, le=100, default=0)


class AIResponse(BaseModel):
    """
    Structured response from Gemini AI.
    
    Used with response_schema parameter for deterministic outputs.
    """
    thought: str = Field(
        description="Internal reasoning (for logging, not shown to user)"
    )
    reply_text: str = Field(
        description="Message to send to the user"
    )
    action: ActionType = Field(
        default=ActionType.NONE,
        description="Action to perform after response"
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Product UUID if action involves specific product"
    )
    quantity: int = Field(
        default=1,
        description="Quantity of product to purchase (1-99)"
    )
    product_ids: Optional[List[str]] = Field(
        default=None,
        description="Multiple product UUIDs for comparison/catalog"
    )
    cart_items: Optional[List[CartItemResponse]] = Field(
        default=None,
        description="Cart items for cart operations"
    )
    total_amount: Optional[float] = Field(
        default=None,
        description="Total amount for payment"
    )
    requires_validation: bool = Field(
        default=False,
        description="Whether real-time stock validation is needed"
    )
    ticket_type: Optional[str] = Field(
        default=None,
        description="Type of support ticket if creating one"
    )


class PurchaseIntent(BaseModel):
    """Detected purchase intent from user message."""
    intent_type: IntentType = Field(description="Type of user intent")
    product_id: Optional[str] = Field(default=None, description="Specific product if identified")
    product_name: Optional[str] = Field(default=None, description="Product name mentioned")
    quantity: int = Field(default=1, description="Requested quantity")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    user_message: str = Field(description="Original user message")


class SupportIntent(BaseModel):
    """Detected support/help intent."""
    needs_replacement: bool = Field(description="User requesting replacement")
    needs_refund: bool = Field(description="User requesting refund")
    order_id: Optional[str] = Field(default=None, description="Related order ID")
    issue_description: str = Field(description="Description of the issue")
    within_warranty: bool = Field(default=False, description="Whether within warranty period")


# ============================================================
# Product Models
# ============================================================

class ProductBase(BaseModel):
    """Base product model."""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    type: ProductType
    warranty_days: int = 1
    duration_days: Optional[int] = None
    instructions: Optional[str] = None
    status: str = "active"


class ProductWithStock(ProductBase):
    """Product with availability info."""
    available_count: int = 0
    can_fulfill_on_demand: bool = False
    fulfillment_time_hours: int = 48
    discount_percent: float = 0.0
    final_price: float = 0.0


class ProductSocialProof(BaseModel):
    """Social proof data for product."""
    rating: float = 0.0
    review_count: int = 0
    sales_count: int = 0
    recent_reviews: List[dict] = []


class ProductDetail(ProductWithStock):
    """Full product details with social proof."""
    msrp: Optional[float] = None
    social_proof: Optional[ProductSocialProof] = None


# ============================================================
# User Models
# ============================================================

class UserBase(BaseModel):
    """Base user model."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: str = "en"


class UserProfile(UserBase):
    """User profile with stats."""
    balance: float = 0.0
    total_saved: float = 0.0
    personal_ref_percent: int = 20
    is_admin: bool = False
    is_banned: bool = False
    referral_count: int = 0


# ============================================================
# Order Models
# ============================================================

class OrderBase(BaseModel):
    """Base order model."""
    id: str
    user_telegram_id: int
    product_id: str
    amount: float
    status: OrderStatus
    order_type: OrderType = OrderType.INSTANT
    created_at: datetime


class OrderDetail(OrderBase):
    """Order with full details."""
    product_name: str
    original_price: float
    discount_percent: float = 0.0
    stock_item_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    fulfillment_deadline: Optional[datetime] = None
    content: Optional[str] = None  # Delivered content (login:pass)


class OrderHistory(BaseModel):
    """Order history item for display."""
    id: str
    product_name: str
    amount: float
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    can_review: bool = False
    can_reorder: bool = True


# ============================================================
# Review Models
# ============================================================

class ReviewCreate(BaseModel):
    """Create review request."""
    order_id: str
    rating: int = Field(ge=1, le=5)
    text: Optional[str] = None


class ReviewResponse(BaseModel):
    """Review display model."""
    id: str
    user_first_name: str
    rating: int
    text: Optional[str]
    created_at: datetime


# ============================================================
# Promo Code Models
# ============================================================

class PromoCodeCheck(BaseModel):
    """Promo code validation result."""
    code: str
    is_valid: bool
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    min_order_amount: float = 0.0
    error_message: Optional[str] = None


# ============================================================
# API Request/Response Models
# ============================================================

class WebhookResponse(BaseModel):
    """Standard webhook response."""
    ok: bool = True


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "PVNDORA"
    version: str = "1.0.0"


# ============================================================
# Leaderboard Models
# ============================================================

class LeaderboardEntry(BaseModel):
    """Single leaderboard entry."""
    rank: int
    user_id: int
    username: Optional[str]
    first_name: str
    total_saved: float


class LeaderboardResponse(BaseModel):
    """Leaderboard API response."""
    leaderboard: List[LeaderboardEntry]
    user_rank: Optional[int] = None
    user_saved: float = 0.0


# ============================================================
# FAQ Models
# ============================================================

class FAQItem(BaseModel):
    """FAQ entry."""
    id: str
    question: str
    answer: str
    category: str


# ============================================================
# Notification Models
# ============================================================

class BroadcastRequest(BaseModel):
    """Broadcast message request."""
    message: str
    parse_mode: str = "HTML"
    include_inactive: bool = False


class BroadcastStatus(BaseModel):
    """Broadcast status response."""
    total_users: int
    sent: int
    failed: int
    skipped: int  # do_not_disturb users


# ============================================================
# Function Call Schemas (for AI)
# ============================================================

class CheckAvailabilityParams(BaseModel):
    """Parameters for check_product_availability function."""
    product_id: str = Field(description="Product UUID to check")


class CheckAvailabilityResult(BaseModel):
    """Result of availability check."""
    product_id: str
    product_name: str
    available: bool
    stock_count: int
    can_fulfill_on_demand: bool
    fulfillment_time_hours: int
    price: float
    discount_percent: float
    final_price: float
    warranty_days: int


class AddToCartParams(BaseModel):
    """Parameters for add_to_cart function."""
    product_id: str = Field(description="Product UUID")
    quantity: int = Field(description="Quantity to add", ge=1, default=1)


class UpdateCartParams(BaseModel):
    """Parameters for update_cart function."""
    operation: Literal["update_quantity", "remove_item", "clear"] = Field(
        description="Cart operation type"
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Product UUID (required for update_quantity and remove_item)"
    )
    quantity: Optional[int] = Field(
        default=None,
        description="New quantity (required for update_quantity)"
    )


class CheckPromoCodeParams(BaseModel):
    """Parameters for check_promo_code function."""
    code: str = Field(description="Promo code to validate")


class GetFAQAnswerParams(BaseModel):
    """Parameters for get_faq_answer function."""
    question: str = Field(description="User question to search FAQ")


