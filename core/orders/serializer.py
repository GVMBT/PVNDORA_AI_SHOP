"""Order response serializers and converters."""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List

from core.services.money import to_float, to_decimal, to_kopecks
from core.payments import DELIVERED_STATES

logger = logging.getLogger(__name__)


async def convert_order_prices(
    amount: Decimal,
    original_price: Optional[Decimal],
    currency: str,
    currency_service
) -> tuple[float, Optional[float]]:
    """
    Convert order prices to target currency.
    
    Args:
        amount: Order amount in USD
        original_price: Original price in USD (optional)
        currency: Target currency code
        currency_service: Currency service instance
        
    Returns:
        Tuple of (converted_amount, converted_original_price)
    """
    amount_converted = to_float(amount)
    original_price_converted = to_float(original_price) if original_price else None
    
    if currency_service and currency != "USD":
        try:
            amount_converted = await currency_service.convert_price(amount, currency, round_to_int=True)
            if original_price_converted:
                original_price_converted = await currency_service.convert_price(original_price, currency, round_to_int=True)
        except Exception as e:
            logger.warning(f"Failed to convert order prices: {e}")
    
    return amount_converted, original_price_converted


def build_item_payload(
    item_data: Dict[str, Any],
    product: Dict[str, Any],
    has_review: bool = False
) -> Dict[str, Any]:
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
        "expires_at": item_data.get("expires_at"),  # License expiration for this specific item
        "has_review": has_review,
    }
    
    # Include delivery content only for delivered states
    if status_lower in DELIVERED_STATES:
        if item_data.get("delivery_content"):
            payload["delivery_content"] = item_data.get("delivery_content")
        # instructions: prefer item-specific, fallback to product instructions
        if item_data.get("delivery_instructions"):
            payload["delivery_instructions"] = item_data.get("delivery_instructions")
        elif product.get("instructions"):
            payload["delivery_instructions"] = product.get("instructions")
    
    return payload


def build_order_payload(
    order,
    product: Dict[str, Any],
    amount_converted: float,
    original_price_converted: Optional[float],
    currency: str,
    items: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Build order payload for API response.
    
    Args:
        order: Order model instance
        product: Product data from products map (legacy, now derived from items)
        amount_converted: Converted amount in target currency
        original_price_converted: Converted original price (optional)
        currency: Target currency code
        items: List of order items (source of truth for products)
        
    Returns:
        Formatted order payload dict
    """
    # Derive product name from items (source of truth) or fallback to legacy product
    product_name = "Unknown Product"
    if items and len(items) > 0:
        # Build product name from items
        item_names = [it.get("product_name", "Unknown") for it in items[:3]]
        product_name = ", ".join(item_names)
        if len(items) > 3:
            product_name += f" и еще {len(items) - 3}"
    elif product:
        product_name = product.get("name", "Unknown Product")
    
    payload = {
        "id": order.id,
        "product_name": product_name,
        "amount": amount_converted,
        "original_price": original_price_converted,
        "discount_percent": order.discount_percent,
        "status": order.status,
        "order_type": getattr(order, 'order_type', 'instant'),
        "currency": currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "delivered_at": order.delivered_at.isoformat() if hasattr(order, 'delivered_at') and order.delivered_at else None,
        # expires_at = payment deadline (relevant only for pending orders)
        "expires_at": order.expires_at.isoformat() if order.expires_at else None,
        # fulfillment_deadline = delivery deadline (relevant for prepaid orders)
        "fulfillment_deadline": order.fulfillment_deadline.isoformat() if hasattr(order, 'fulfillment_deadline') and order.fulfillment_deadline else None,
        # warranty_until = warranty end date (for delivered orders)
        "warranty_until": order.warranty_until.isoformat() if hasattr(order, 'warranty_until') and order.warranty_until else None,
    }

    # Minor units (kopecks/cents) from converted amounts
    try:
        payload["amount_minor"] = to_kopecks(to_decimal(amount_converted))
        if original_price_converted is not None:
            payload["original_price_minor"] = to_kopecks(to_decimal(original_price_converted))
    except Exception:
        # Fallback silently if conversion fails; keep float fields
        pass
    
    # Attach items (source of truth for products and delivery content)
    if items:
        payload["items"] = items
    
    # Include payment_url ONLY for pending orders (payment NOT confirmed yet)
    # For prepaid orders, payment is ALREADY confirmed - no need for payment_url
    if order.status == "pending" and hasattr(order, 'payment_url') and order.payment_url:
        payload["payment_url"] = order.payment_url
    
    return payload

