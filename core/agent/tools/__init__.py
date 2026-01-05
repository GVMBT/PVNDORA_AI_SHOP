"""
LangChain Tools for Shop Agent

Complete toolset covering all app functionality:
- Catalog & Search
- Cart Management  
- Orders & Credentials
- User Profile & Referrals
- Wishlist & Waitlist
- Support & FAQ

User context (user_id, telegram_id, language, currency) is auto-injected
via set_user_context() before each agent call.
"""

# Base functions - context management
from .base import (
    set_db,
    get_db,
    set_user_context,
    get_user_context,
)

# Catalog tools
from .catalog import (
    get_catalog,
    search_products,
    get_product_details,
    check_product_availability,
)

# Cart tools
from .cart import (
    get_user_cart,
    add_to_cart,
    remove_from_cart,
    update_cart_quantity,
    clear_cart,
    apply_promo_code,
)

# Order tools
from .orders import (
    get_user_orders,
    get_order_credentials,
    resend_order_credentials,
)

# Profile tools
from .profile import (
    get_user_profile,
    get_referral_info,
    get_balance_history,
)

# Wishlist tools
from .wishlist import (
    add_to_wishlist,
    get_wishlist,
    remove_from_wishlist,
    add_to_waitlist,
)

# Support tools
from .support import (
    search_faq,
    create_support_ticket,
    request_refund,
)

# Checkout tools
from .checkout import (
    checkout_cart,
    pay_cart_from_balance,
)


def get_all_tools():
    """Get all available tools for the agent."""
    return [
        # Catalog
        get_catalog,
        search_products,
        get_product_details,
        check_product_availability,
        # Cart & Checkout
        get_user_cart,
        add_to_cart,
        remove_from_cart,
        update_cart_quantity,
        clear_cart,
        apply_promo_code,
        checkout_cart,  # CRITICAL: Creates order and returns payment link
        # Orders
        get_user_orders,
        get_order_credentials,
        resend_order_credentials,
        # User & Referrals
        get_user_profile,
        get_referral_info,
        get_balance_history,
        pay_cart_from_balance,
        # Wishlist & Waitlist
        add_to_wishlist,
        get_wishlist,
        remove_from_wishlist,
        add_to_waitlist,
        # Support
        search_faq,
        create_support_ticket,
        request_refund,
    ]


__all__ = [
    # Base
    "set_db",
    "get_db",
    "set_user_context",
    "get_user_context",
    # Catalog
    "get_catalog",
    "search_products",
    "get_product_details",
    "check_product_availability",
    # Cart
    "get_user_cart",
    "add_to_cart",
    "remove_from_cart",
    "update_cart_quantity",
    "clear_cart",
    "apply_promo_code",
    # Orders
    "get_user_orders",
    "get_order_credentials",
    "resend_order_credentials",
    # Profile
    "get_user_profile",
    "get_referral_info",
    "get_balance_history",
    # Wishlist
    "add_to_wishlist",
    "get_wishlist",
    "remove_from_wishlist",
    "add_to_waitlist",
    # Support
    "search_faq",
    "create_support_ticket",
    "request_refund",
    # Checkout
    "checkout_cart",
    "pay_cart_from_balance",
    # Registry
    "get_all_tools",
]
