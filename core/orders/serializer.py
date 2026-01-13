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


def convert_order_prices_with_formatter(
    amount: Decimal, original_price: Decimal | None, formatter: "CurrencyFormatter"
) -> dict[str, Any]:
    """
    Convert order prices using unified CurrencyFormatter.

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
    item_data: dict[str, Any], product: dict[str, Any], has_review: bool = False
) -> dict[str, Any]:
    """
    Build order item payload for API response.

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
            "fulfillment_deadline"
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


def build_order_payload(
    order,
    product: dict[str, Any],
    amount_converted: float,
    original_price_converted: float | None,
    currency: str,
    items: list[dict[str, Any]] | None = None,
    # New unified fields
    amount_usd: float | None = None,
    original_price_usd: float | None = None,
) -> dict[str, Any]:
    """
    Build order payload for API response.

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

    # Minor units (kopecks/cents) from converted amounts
    try:
        payload["amount_minor"] = to_kopecks(to_decimal(amount_converted))
        if original_price_converted is not None:
            payload["original_price_minor"] = to_kopecks(to_decimal(original_price_converted))
    except Exception:
        pass

    # Attach items (source of truth for products and delivery content)
    if items:
        payload["items"] = items

    # Include payment_url ONLY for pending orders
    if order.status == "pending" and hasattr(order, "payment_url") and order.payment_url:
        payload["payment_url"] = order.payment_url

    # Include payment info for pending orders (to check payment status)
    if order.status == "pending":
        if hasattr(order, "payment_id") and order.payment_id:
            payload["payment_id"] = order.payment_id
        if hasattr(order, "payment_gateway") and order.payment_gateway:
            payload["payment_gateway"] = order.payment_gateway

    return payload
