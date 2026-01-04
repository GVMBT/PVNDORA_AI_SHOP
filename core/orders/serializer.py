"""Order response serializers and converters."""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from core.services.money import to_float, to_decimal, to_kopecks

if TYPE_CHECKING:
    from core.services.currency_response import CurrencyFormatter

logger = logging.getLogger(__name__)

# Delivered states where we show delivery content
DELIVERED_STATES = ["delivered", "partial", "completed"]


def convert_order_prices_with_formatter(
    amount: Decimal,
    original_price: Optional[Decimal],
    formatter: "CurrencyFormatter"
) -> Dict[str, Any]:
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


# Legacy function for backward compatibility
async def convert_order_prices(
    amount: Decimal,
    original_price: Optional[Decimal],
    currency: str,
    currency_service
) -> tuple[float, Optional[float]]:
    """
    Convert order prices to target currency.
    
    DEPRECATED: Use convert_order_prices_with_formatter instead.
    
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
        "expires_at": item_data.get("expires_at"),
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
    product: Dict[str, Any],
    amount_converted: float,
    original_price_converted: Optional[float],
    currency: str,
    items: Optional[List[Dict[str, Any]]] = None,
    # New unified fields
    amount_usd: Optional[float] = None,
    original_price_usd: Optional[float] = None,
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
        amount_usd: Amount in USD (for calculations)
        original_price_usd: Original price in USD (for calculations)
        
    Returns:
        Formatted order payload dict
    """
    # Derive product name from items (source of truth) or fallback to legacy product
    product_name = "Unknown Product"
    if items and len(items) > 0:
        item_names = [it.get("product_name", "Unknown") for it in items[:3]]
        product_name = ", ".join(item_names)
        if len(items) > 3:
            product_name += f" и еще {len(items) - 3}"
    elif product:
        product_name = product.get("name", "Unknown Product")
    
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
        "order_type": getattr(order, 'order_type', 'instant'),
        "currency": currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "delivered_at": order.delivered_at.isoformat() if hasattr(order, 'delivered_at') and order.delivered_at else None,
        "expires_at": order.expires_at.isoformat() if order.expires_at else None,
        "fulfillment_deadline": order.fulfillment_deadline.isoformat() if hasattr(order, 'fulfillment_deadline') and order.fulfillment_deadline else None,
        "warranty_until": order.warranty_until.isoformat() if hasattr(order, 'warranty_until') and order.warranty_until else None,
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
    if order.status == "pending" and hasattr(order, 'payment_url') and order.payment_url:
        payload["payment_url"] = order.payment_url
    
    # Include payment info for pending orders (to check payment status)
    if order.status == "pending":
        if hasattr(order, 'payment_id') and order.payment_id:
            payload["payment_id"] = order.payment_id
        if hasattr(order, 'payment_gateway') and order.payment_gateway:
            payload["payment_gateway"] = order.payment_gateway
    
    return payload
