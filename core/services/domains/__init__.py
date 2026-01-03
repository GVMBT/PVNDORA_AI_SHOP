"""Domain services wrapping repositories."""
from .users import UsersDomain
from .products import ProductsDomain
from .stock import StockDomain
from .orders import OrdersDomain
from .chat import ChatDomain

# New domain services (Service Layer for AI tools)
from .catalog import CatalogService
from .wishlist import WishlistService
from .referral import ReferralService
from .support import SupportService

# Discount channel services
from .insurance import InsuranceService
from .promo import PromoCodeService, PromoTriggers
from .discount_orders import DiscountOrderService
from .offers import OffersService

__all__ = [
    # Legacy domain wrappers
    "UsersDomain",
    "ProductsDomain",
    "StockDomain",
    "OrdersDomain",
    "ChatDomain",
    # Service Layer
    "CatalogService",
    "WishlistService", 
    "ReferralService",
    "SupportService",
    # Discount channel
    "InsuranceService",
    "PromoCodeService",
    "PromoTriggers",
    "DiscountOrderService",
    "OffersService",
]

