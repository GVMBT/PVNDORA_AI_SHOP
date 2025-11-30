"""
Payments Module - Payment Provider Helpers

Handles signature verification and payment processing for:
- AAIO
- YooKassa (ЮKassa)
- Stripe (optional)
"""

import os
import hmac
import hashlib
from typing import Optional


# Environment
AAIO_SECRET_KEY = os.environ.get("AAIO_SECRET_KEY", "")
AAIO_MERCHANT_ID = os.environ.get("AAIO_MERCHANT_ID", "")
YUKASSA_SHOP_ID = os.environ.get("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET_KEY = os.environ.get("YUKASSA_SECRET_KEY", "")


# ============================================================
# AAIO Payment Provider
# ============================================================

def verify_aaio_signature(data: dict) -> bool:
    """
    Verify AAIO webhook signature.
    
    Args:
        data: Form data from webhook
    
    Returns:
        True if signature is valid
    """
    if not AAIO_SECRET_KEY:
        return False
    
    received_sign = data.get("sign", "")
    
    # Build sign string
    # Format: merchant_id:amount:currency:order_id:secret_key
    sign_string = ":".join([
        data.get("merchant_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("order_id", ""),
        AAIO_SECRET_KEY
    ])
    
    expected_sign = hashlib.sha256(sign_string.encode()).hexdigest()
    
    return hmac.compare_digest(received_sign, expected_sign)


def generate_aaio_payment_url(
    order_id: str,
    amount: float,
    currency: str = "RUB",
    description: Optional[str] = None
) -> str:
    """
    Generate AAIO payment URL.
    
    Args:
        order_id: Order UUID
        amount: Payment amount
        currency: Currency code (default RUB)
        description: Payment description
    
    Returns:
        Payment URL to redirect user
    """
    import urllib.parse
    
    # Build sign
    sign_string = ":".join([
        AAIO_MERCHANT_ID,
        str(amount),
        currency,
        order_id,
        AAIO_SECRET_KEY
    ])
    sign = hashlib.sha256(sign_string.encode()).hexdigest()
    
    params = {
        "merchant_id": AAIO_MERCHANT_ID,
        "amount": str(amount),
        "currency": currency,
        "order_id": order_id,
        "sign": sign
    }
    
    if description:
        params["desc"] = description
    
    base_url = "https://aaio.io/merchant/pay"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


# ============================================================
# YooKassa (ЮKassa) Payment Provider
# ============================================================

def verify_yukassa_signature(body: bytes, signature: str) -> bool:
    """
    Verify YooKassa webhook signature.
    
    Note: YooKassa uses IP whitelist instead of signatures for webhooks.
    This function is a placeholder for additional validation if needed.
    
    Args:
        body: Raw request body
        signature: Signature header (if provided)
    
    Returns:
        True (always, as YooKassa relies on IP whitelist)
    """
    # YooKassa webhooks are verified by IP whitelist, not signatures
    # The shop_id in the payload should match our configured shop_id
    return True


async def create_yukassa_payment(
    order_id: str,
    amount: float,
    currency: str = "RUB",
    description: Optional[str] = None,
    return_url: Optional[str] = None
) -> dict:
    """
    Create YooKassa payment.
    
    Args:
        order_id: Order UUID
        amount: Payment amount
        currency: Currency code
        description: Payment description
        return_url: URL to redirect after payment
    
    Returns:
        Payment object with confirmation_url
    """
    import httpx
    import uuid
    
    if not YUKASSA_SHOP_ID or not YUKASSA_SECRET_KEY:
        raise ValueError("YooKassa credentials not configured")
    
    idempotence_key = str(uuid.uuid4())
    
    payload = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": currency
        },
        "capture": True,
        "metadata": {
            "order_id": order_id
        }
    }
    
    if description:
        payload["description"] = description
    
    if return_url:
        payload["confirmation"] = {
            "type": "redirect",
            "return_url": return_url
        }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",
            json=payload,
            auth=(YUKASSA_SHOP_ID, YUKASSA_SECRET_KEY),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json"
            }
        )
        
        response.raise_for_status()
        return response.json()


# ============================================================
# Payment URL Generator
# ============================================================

async def get_payment_url(
    provider: str,
    order_id: str,
    amount: float,
    currency: str = "RUB",
    description: Optional[str] = None,
    return_url: Optional[str] = None
) -> str:
    """
    Get payment URL for specified provider.
    
    Args:
        provider: Payment provider ("aaio" or "yukassa")
        order_id: Order UUID
        amount: Payment amount
        currency: Currency code
        description: Payment description
        return_url: Return URL after payment
    
    Returns:
        Payment URL
    """
    if provider == "aaio":
        return generate_aaio_payment_url(
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description
        )
    
    elif provider == "yukassa":
        payment = await create_yukassa_payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            return_url=return_url
        )
        return payment.get("confirmation", {}).get("confirmation_url", "")
    
    else:
        raise ValueError(f"Unknown payment provider: {provider}")


# ============================================================
# Order Amount Calculation
# ============================================================

async def calculate_order_amount(
    product_id: str,
    quantity: int = 1,
    promo_code: Optional[str] = None,
    supabase = None
) -> dict:
    """
    Calculate order amount with discounts.
    
    Args:
        product_id: Product UUID
        quantity: Order quantity
        promo_code: Optional promo code
        supabase: Supabase client
    
    Returns:
        Dict with amount details
    """
    if supabase is None:
        from core.db import get_supabase
        supabase = await get_supabase()
    
    # Get product with stock discount
    stock = await supabase.table("available_stock_with_discounts").select(
        "*"
    ).eq("product_id", product_id).limit(1).execute()
    
    if stock.data:
        base_price = stock.data[0].get("final_price", 0)
        stock_discount = stock.data[0].get("discount_percent", 0)
    else:
        # No stock - get base product price
        product = await supabase.table("products").select(
            "price"
        ).eq("id", product_id).single().execute()
        
        if not product.data:
            raise ValueError("Product not found")
        
        base_price = product.data["price"]
        stock_discount = 0
    
    subtotal = base_price * quantity
    promo_discount = 0
    
    # Apply promo code
    if promo_code:
        promo = await supabase.table("promo_codes").select(
            "*"
        ).eq("code", promo_code.upper()).single().execute()
        
        if promo.data:
            # Validate promo
            from datetime import datetime
            
            if promo.data.get("expires_at"):
                expires = datetime.fromisoformat(
                    promo.data["expires_at"].replace("Z", "+00:00")
                )
                if expires < datetime.now(expires.tzinfo):
                    promo.data = None  # Expired
            
            if promo.data and promo.data.get("usage_limit"):
                if promo.data.get("usage_count", 0) >= promo.data["usage_limit"]:
                    promo.data = None  # Limit reached
            
            if promo.data and promo.data.get("min_order_amount"):
                if subtotal < promo.data["min_order_amount"]:
                    promo.data = None  # Below minimum
        
        if promo.data:
            if promo.data.get("discount_percent"):
                promo_discount = subtotal * (promo.data["discount_percent"] / 100)
            elif promo.data.get("discount_amount"):
                promo_discount = min(promo.data["discount_amount"], subtotal)
    
    total = subtotal - promo_discount
    
    return {
        "subtotal": subtotal,
        "stock_discount_percent": stock_discount,
        "promo_code": promo_code.upper() if promo_code else None,
        "promo_discount": promo_discount,
        "total": max(0, total)
    }



