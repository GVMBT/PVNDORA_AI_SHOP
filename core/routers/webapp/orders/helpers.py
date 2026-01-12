"""
Order Helper Functions

Shared utilities for order creation and payment processing.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from core.services.money import to_float
from core.services.models import Order

logger = logging.getLogger(__name__)


async def create_payment_wrapper(
    payment_service,
    order_id: str, 
    amount: Decimal, 
    product_name: str,
    gateway: str = "crystalpay", 
    payment_method: str = "card",
    user_email: str = "",
    user_id: int = 0,
    currency: str = "RUB",
    is_telegram_miniapp: bool = True
) -> Dict[str, Any]:
    """
    Async wrapper for synchronous payment creation.
    Returns dict with payment_url and invoice_id.
    """
    formatted_amount = to_float(amount)
    
    if gateway == "crystalpay":
        async def _make_crystalpay_invoice():
            invoice_data = await payment_service.create_payment(
                order_id=order_id,
                amount=formatted_amount,
                product_name=product_name,
                user_id=str(user_id),
                currency=currency,
                is_telegram_miniapp=is_telegram_miniapp
            )
            
            if isinstance(invoice_data, dict):
                return {
                    "payment_url": invoice_data.get("payment_url") or invoice_data.get("url"),
                    "invoice_id": invoice_data.get("invoice_id") or invoice_data.get("id")
                }
            elif hasattr(invoice_data, 'url') or hasattr(invoice_data, 'payment_url'):
                return {
                    "payment_url": getattr(invoice_data, 'payment_url', None) or getattr(invoice_data, 'url', None),
                    "invoice_id": getattr(invoice_data, 'invoice_id', None) or getattr(invoice_data, 'id', None)
                }
            else:
                raise ValueError(f"Unexpected response type from CrystalPay: {type(invoice_data)}")
        return await _make_crystalpay_invoice()
    else:
        raise ValueError(f"Unsupported payment gateway: {gateway}")


async def persist_order(
    db, 
    user_id: str, 
    amount: Decimal,
    original_price: Decimal,
    discount_percent: int,
    payment_method: str,
    payment_gateway: Optional[str],
    user_telegram_id: int,
    expires_at: datetime,
    fiat_amount: Optional[Decimal] = None,
    fiat_currency: Optional[str] = None,
    exchange_rate_snapshot: Optional[float] = None,
):
    """Create order record in database using thread for sync operation."""
    order_payload = {
        "user_id": user_id,
        "amount": to_float(amount),
        "original_price": to_float(original_price),
        "discount_percent": discount_percent,
        "status": "pending",
        "payment_method": payment_method,
        "payment_gateway": payment_gateway,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_telegram_id": user_telegram_id,
        "expires_at": expires_at.isoformat(),
    }
    
    # Add fiat fields if provided
    if fiat_amount is not None:
        order_payload["fiat_amount"] = to_float(fiat_amount)
    if fiat_currency:
        order_payload["fiat_currency"] = fiat_currency
    if exchange_rate_snapshot is not None:
        order_payload["exchange_rate_snapshot"] = exchange_rate_snapshot
    
    result = await db.client.table("orders").insert(order_payload).execute()
    row = result.data[0]
    return Order(
        id=row["id"],
        user_id=row["user_id"],
        amount=row["amount"],
        status=row["status"],
        created_at=row.get("created_at"),
        payment_method=row.get("payment_method"),
        payment_gateway=row.get("payment_gateway"),
        original_price=row.get("original_price"),
        discount_percent=row.get("discount_percent"),
        user_telegram_id=row.get("user_telegram_id"),
        items=None
    )


async def persist_order_items(db, order_id: str, items: List[Dict[str, Any]]) -> None:
    """Insert multiple order_items in bulk. 
    
    CRITICAL: Each order_item now has quantity=1 (split bulk orders into separate items).
    This allows independent processing of each key (delivery, replacement, tickets).
    
    Example: If user orders 3x GPT GO, create 3 separate order_items (quantity=1 each).
    
    Maps cart data (instant_quantity, prepaid_quantity) to DB schema (fulfillment_type).
    Note: instant_quantity/prepaid_quantity are cart-only fields, not stored in order_items table.
    """
    if not items:
        return
    
    rows = []
    for item in items:
        # Determine fulfillment_type from instant_quantity/prepaid_quantity if present
        # If instant_quantity > 0, it's instant; otherwise preorder
        fulfillment_type = "instant"  # default
        if "instant_quantity" in item and "prepaid_quantity" in item:
            fulfillment_type = "instant" if item.get("instant_quantity", 0) > 0 else "preorder"
        elif "fulfillment_type" in item:
            fulfillment_type = item["fulfillment_type"]
        
        # Split quantity into separate order_items (quantity=1 each)
        # This allows independent processing (delivery, replacement, tickets)
        item_quantity = item.get("quantity", 1)
        total_amount = to_float(item["amount"])  # Total price for all quantity
        unit_price = total_amount / item_quantity if item_quantity > 0 else total_amount  # Price per unit
        
        for _ in range(item_quantity):
            row = {
                "order_id": order_id,
                "product_id": item["product_id"],
                "quantity": 1,  # Always 1 - each order_item = 1 key
                "price": unit_price,  # Price per unit (not total)
                "discount_percent": item.get("discount_percent", 0),
                "fulfillment_type": fulfillment_type,
            }
            rows.append(row)
    
    await db.client.table("order_items").insert(rows).execute()
