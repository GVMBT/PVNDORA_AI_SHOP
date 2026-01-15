"""Domain services wrapping repositories."""

# New domain services (Service Layer for AI tools)
from .catalog import CatalogService
from .chat import ChatDomain
from .discount_orders import DiscountOrderService

# Discount channel services
from .insurance import InsuranceService
from .offers import OffersService
from .orders import OrdersDomain
from .products import ProductsDomain
from .promo import PromoCodeService, PromoTriggers
from .referral import ReferralService
from .stock import StockDomain
from .support import SupportService
from .users import UsersDomain
from .wishlist import WishlistService

__all__ = [
    # Service Layer
    "CatalogService",
    "ChatDomain",
    "DiscountOrderService",
    # Discount channel
    "InsuranceService",
    "OffersService",
    "OrdersDomain",
    "ProductsDomain",
    "PromoCodeService",
    "PromoTriggers",
    "ReferralService",
    "StockDomain",
    "SupportService",
    # Legacy domain wrappers
    "UsersDomain",
    "WishlistService",
]
