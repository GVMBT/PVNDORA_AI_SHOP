"""
WebApp Public Router

Public endpoints that don't require authentication.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.services.database import get_database
from src.services.currency import get_currency_service
from core.db import get_redis

router = APIRouter(tags=["webapp-public"])


@router.get("/products/{product_id}")
async def get_webapp_product(
    product_id: str,
    language_code: Optional[str] = Query(None, description="User language code for currency conversion")
):
    """Get product with discount and social proof for Mini App."""
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("available_stock_with_discounts").select("*").eq("product_id", product_id).limit(1).execute()
    )
    
    discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
    rating_info = await db.get_product_rating(product_id)
    
    # Get currency service and convert prices
    try:
        redis = await get_redis()
        currency_service = get_currency_service(redis)
        currency = currency_service.get_user_currency(language_code)
        
        # Prices in database are in USD
        price_usd = float(product.price)
        msrp_usd = float(product.msrp) if hasattr(product, 'msrp') and product.msrp else None
        
        original_price = await currency_service.convert_price(price_usd, currency, round_to_int=True)
        final_price_usd = price_usd * (1 - discount_percent / 100)
        final_price = await currency_service.convert_price(final_price_usd, currency, round_to_int=True)
        
        msrp = None
        if msrp_usd:
            msrp = await currency_service.convert_price(msrp_usd, currency, round_to_int=True)
    except Exception as e:
        print(f"Warning: Currency conversion failed: {e}, using USD")
        currency = "USD"
        original_price = float(product.price)
        final_price = original_price * (1 - discount_percent / 100)
        msrp = float(product.msrp) if hasattr(product, 'msrp') and product.msrp else None
    
    fulfillment_time_hours = getattr(product, 'fulfillment_time_hours', 48)
    
    return {
        "product": {
            "id": product.id, "name": product.name, "description": product.description,
            "original_price": original_price, "price": original_price,
            "price_usd": float(product.price),  # Keep USD for reference
            "msrp": msrp,  # Converted MSRP
            "currency": currency,
            "discount_percent": discount_percent, "final_price": round(final_price, 2),
            "warranty_days": product.warranty_hours // 24 if hasattr(product, 'warranty_hours') else 1,
            "duration_days": getattr(product, 'duration_days', None),
            "available_count": product.stock_count, "available": product.stock_count > 0,
            "can_fulfill_on_demand": product.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours if product.status == 'active' else None,
            "type": product.type, "instructions": product.instructions,
            "rating": rating_info["average"], "reviews_count": rating_info["count"]
        }
    }


@router.get("/products")
async def get_webapp_products(
    language_code: Optional[str] = Query(None, description="User language code for currency conversion")
):
    """Get all active products for Mini App catalog."""
    db = get_database()
    products = await db.get_products(status="active")
    
    # Get currency service and convert prices
    try:
        redis = await get_redis()
        currency_service = get_currency_service(redis)
        currency = currency_service.get_user_currency(language_code)
    except Exception as e:
        print(f"Warning: Currency service unavailable: {e}, using USD")
        currency = "USD"
        currency_service = None
    
    result = []
    for p in products:
        stock_result = await asyncio.to_thread(
            lambda pid=p.id: db.client.table("available_stock_with_discounts").select("*").eq("product_id", pid).limit(1).execute()
        )
        discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
        rating_info = await db.get_product_rating(p.id)
        
        # Prices in database are in USD
        price_usd = float(p.price)
        if currency_service:
            original_price = await currency_service.convert_price(price_usd, currency, round_to_int=True)
            final_price_usd = price_usd * (1 - discount_percent / 100)
            final_price = await currency_service.convert_price(final_price_usd, currency, round_to_int=True)
        else:
            original_price = price_usd
            final_price = price_usd * (1 - discount_percent / 100)
        
        result.append({
            "id": p.id, "name": p.name, "description": p.description,
            "original_price": original_price, "price": original_price,
            "price_usd": price_usd,  # Keep USD for reference
            "currency": currency,
            "discount_percent": discount_percent, "final_price": round(final_price, 2),
            "available_count": p.stock_count, "available": p.stock_count > 0,
            "can_fulfill_on_demand": p.status == 'active',
            "type": p.type, "rating": rating_info["average"], "reviews_count": rating_info["count"]
        })
    
    return {"products": result, "count": len(result)}
