"""Order response serializers and converters."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from core.services.money import to_decimal, to_float, to_kopecks

if TYPE_CHECKING:
    from core.services.currency_response import CurrencyFormatter

logger = logging.getLogger(__name__)

# Delivered states where we show delivery content
DELIVERED_STATES = ["delivered", "partial", "completed"]


def _extract_name_from_item(item: dict[str, Any]) -> str | None:
    """Extract product name from order item. Returns None if not found."""
    # Try nested product dict first
    product_dict = item.get("product")
    if isinstance(product_dict, dict):
        name = product_dict.get("name")
        if name is not None:
            return str(name)

    # Try direct product_name
    if "product_name" in item:
        name = item["product_name"]
        if name is not None:
            return str(name)

    return None


def _extract_name_from_product(product: Any) -> str | None:
    """Extract product name from product object. Returns None if not found."""
    if not product:
        return None

    if isinstance(product, dict):
        name = product.get("name")
        if name is not None:
            return str(name)
    else:
        name = getattr(product, "name", None)
        if name is not None:
            return str(name)

    return None


def _derive_product_name(items: list[dict[str, Any]] | None, product: Any) -> str:
    """Derive product name from order items, falling back to product object.

    Args:
        items: List of order items with product info
        product: Legacy product object (fallback)

    Returns:
        Product name string

    """
    # Try to extract from first item
    if items:
        first_item = items[0]
        if isinstance(first_item, dict):
            name = _extract_name_from_item(first_item)
            if name:
                return name

    # Fallback to product object
    name = _extract_name_from_product(product)
    if name:
        return name

    return "Unknown"


def convert_order_prices_with_formatter(
    amount: Decimal,
    original_price: Decimal | None,
    formatter: "CurrencyFormatter",
) -> dict[str, Any]:
    """Convert order prices using unified CurrencyFormatter.

    Returns dict with both USD and display values.
    """
    amount_usd = to_float(amount)
    original_price_usd = to_float(original_price) if original_price else None

    return {
        "amount_usd": amount_usd,
        "amount": formatter.convert(amount),
        "original_price_usd": original_price_usd,
        "original_price": formatter.convert(original_price) if original_price else None,
    }


# NOTE: convert_order_prices() was removed - DEPRECATED
# Use convert_order_prices_with_formatter() instead


def build_item_payload(
    item_data: dict[str, Any],
    product: dict[str, Any],
    has_review: bool = False,
) -> dict[str, Any]:
    """Build order item payload for API response.

    Args:
        item_data: Raw item data from database
        product: Product data from products map
        has_review: Whether this order has a review submitted

    Returns:
        Formatted item payload dict

    """
    status_lower = str(item_data.get("status", "")).lower()

    payload = {
        "id": item_data.get("id"),
        "product_id": item_data.get("product_id"),
        "product_name": product.get("name", "Unknown Product"),
        "status": status_lower,
        "fulfillment_type": item_data.get("fulfillment_type"),
        "created_at": item_data.get("created_at"),
        "delivered_at": item_data.get("delivered_at"),
        "expires_at": item_data.get("expires_at"),
        "fulfillment_deadline": item_data.get(
            "fulfillment_deadline",
        ),  # When we promise to deliver prepaid items
        "has_review": has_review,
    }

    # Include delivery content only for delivered states
    if status_lower in DELIVERED_STATES:
        if item_data.get("delivery_content"):
            payload["delivery_content"] = item_data.get("delivery_content")
        if item_data.get("delivery_instructions"):
            payload["delivery_instructions"] = item_data.get("delivery_instructions")
        elif product.get("instructions"):
            payload["delivery_instructions"] = product.get("instructions")

    return payload


# Helper: Format datetime fields (reduces cognitive complexity)
def _format_order_dates(order: Any) -> dict[str, Any]:
    """Format all datetime fields from order."""
    return {
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "delivered_at": (
            order.delivered_at.isoformat()
            if hasattr(order, "delivered_at") and order.delivered_at
            else None
        ),
        "expires_at": order.expires_at.isoformat() if order.expires_at else None,
        "fulfillment_deadline": (
            order.fulfillment_deadline.isoformat()
            if hasattr(order, "fulfillment_deadline") and order.fulfillment_deadline
            else None
        ),
        "warranty_until": (
            order.warranty_until.isoformat()
            if hasattr(order, "warranty_until") and order.warranty_until
            else None
        ),
    }


# Helper: Add minor units (kopecks/cents) to payload (reduces cognitive complexity)
def _add_minor_units(
    payload: dict[str, Any], amount_converted: float, original_price_converted: float | None
) -> None:
    """Add minor units (kopecks/cents) from converted amounts."""
    try:
        payload["amount_minor"] = to_kopecks(to_decimal(amount_converted))
        if original_price_converted is not None:
            payload["original_price_minor"] = to_kopecks(to_decimal(original_price_converted))
    except Exception:
        pass


# Helper: Add payment info for pending orders (reduces cognitive complexity)
def _add_payment_info(payload: dict[str, Any], order: Any) -> None:
    """Add payment URL and payment details for pending orders."""
    if order.status != "pending":
        return

    if hasattr(order, "payment_url") and order.payment_url:
        payload["payment_url"] = order.payment_url

    if hasattr(order, "payment_id") and order.payment_id:
        payload["payment_id"] = order.payment_id

    if hasattr(order, "payment_gateway") and order.payment_gateway:
        payload["payment_gateway"] = order.payment_gateway


def build_order_payload(
    order: Any,
    product: dict[str, Any],
    amount_converted: float,
    original_price_converted: float | None,
    currency: str,
    items: list[dict[str, Any]] | None = None,
    # New unified fields
    amount_usd: float | None = None,
    original_price_usd: float | None = None,
) -> dict[str, Any]:
    """Build order payload for API response.

    Args:
        order: Order model instance
        product: Product data from products map (legacy, now derived from items)
        amount_converted: Converted amount in target currency
        original_price_converted: Converted original price (optional)
        currency: Target currency code
        items: List of order items (source of truth for products)
        amount_usd: Amount in USD (for calculations)
        original_price_usd: Original price in USD (for calculations)

    Returns:
        Formatted order payload dict

    """
    product_name = _derive_product_name(items, product)

    payload = {
        "id": order.id,
        "product_name": product_name,
        # USD values (for calculations)
        "amount_usd": amount_usd if amount_usd is not None else to_float(order.amount),
        "original_price_usd": original_price_usd,
        # Display values (for UI)
        "amount": amount_converted,
        "original_price": original_price_converted,
        "discount_percent": order.discount_percent,
        "status": order.status,
        "order_type": getattr(order, "order_type", "instant"),
        "currency": currency,
        **_format_order_dates(order),
    }

    # Minor units (kopecks/cents) from converted amounts
    _add_minor_units(payload, amount_converted, original_price_converted)

    # Attach items (source of truth for products and delivery content)
    if items:
        payload["items"] = items

    # Include payment info for pending orders
    _add_payment_info(payload, order)

    return payload
