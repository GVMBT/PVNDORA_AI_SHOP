"""
WebApp Public Router

Public endpoints that don't require authentication.
All prices include both USD and display values for unified currency handling.
Supports anchor pricing (fixed prices per currency).
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.services.database import get_database
from core.services.currency_response import CurrencyFormatter
from core.services.currency import get_currency_service
from core.db import get_redis
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["webapp-public"])


@router.get("/products/{product_id}")
async def get_webapp_product(
    product_id: str,
    language_code: Optional[str] = Query(None, description="User language code for currency conversion"),
    currency: Optional[str] = Query(None, description="User preferred currency (USD, RUB, EUR, etc.)")
):
    """Get product with discount and social proof for Mini App.
    
    Uses anchor pricing: if product has fixed price in user's currency, uses that.
    Otherwise falls back to dynamic conversion from USD.
    """
    db = get_database()
    product = await db.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stock_result = await asyncio.to_thread(
        lambda: db.client.table("available_stock_with_discounts").select("*").eq("product_id", product_id).limit(1).execute()
    )
    
    discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
    rating_info = await db.get_product_rating(product_id)
    
    # Unified currency formatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(
        user_telegram_id=None,
        db=db,
        redis=redis,
        preferred_currency=currency,
        language_code=language_code
    )
    
    # Get currency service for anchor pricing
    currency_service = get_currency_service(redis)
    
    # USD values (base)
    price_usd = float(product.price)
    final_price_usd = price_usd * (1 - discount_percent / 100)
    msrp_usd = float(product.msrp) if hasattr(product, 'msrp') and product.msrp else None
    
    # Get anchor price (fixed or converted)
    product_dict = {
        "price": product.price,
        "prices": getattr(product, 'prices', None) or {}
    }
    anchor_price = float(await currency_service.get_anchor_price(product_dict, formatter.currency))
    is_anchor_price = currency_service.has_anchor_price(product_dict, formatter.currency)
    
    # Apply discount to anchor price
    anchor_final_price = anchor_price * (1 - discount_percent / 100)
    
    fulfillment_time_hours = getattr(product, 'fulfillment_time_hours', 48)
    
    # Get social proof data
    try:
        social_proof_result = await asyncio.to_thread(
            lambda: db.client.table("product_social_proof").select("*").eq("product_id", product_id).single().execute()
        )
        social_proof_data = social_proof_result.data if social_proof_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to get social proof: {e}")
        social_proof_data = {}
    
    social_proof = {
        "rating": rating_info.get("average", 0),
        "review_count": rating_info.get("count", 0),
        "sales_count": social_proof_data.get("sales_count", 0),
        "recent_reviews": social_proof_data.get("recent_reviews", [])
    }
    
    instruction_files = getattr(product, 'instruction_files', None) or []
    
    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            # USD values (for calculations)
            "price_usd": price_usd,
            "final_price_usd": final_price_usd,
            "msrp_usd": msrp_usd,
            # Display values (for UI) - now using anchor prices
            "original_price": anchor_price,
            "price": anchor_price,
            "final_price": anchor_final_price,
            "msrp": formatter.convert(msrp_usd) if msrp_usd else None,
            # Currency info
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
            "is_anchor_price": is_anchor_price,  # True if price is fixed, False if dynamically converted
            # Other fields
            "discount_percent": discount_percent,
            "warranty_days": product.warranty_hours // 24 if hasattr(product, 'warranty_hours') and product.warranty_hours else 0,
            "duration_days": getattr(product, 'duration_days', None),
            "available_count": product.stock_count,
            "available": product.stock_count > 0,
            "can_fulfill_on_demand": product.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours if product.status == 'active' else None,
            "type": product.type,
            "instructions": product.instructions,
            "instruction_files": instruction_files,
            "rating": rating_info.get("average", 0),
            "reviews_count": rating_info.get("count", 0),
            "categories": getattr(product, 'categories', []) or [],
            "status": product.status,
            "sales_count": social_proof_data.get("sales_count", 0),
            "image_url": getattr(product, 'image_url', None),
            "video_url": getattr(product, 'video_url', None),
            "logo_svg_url": getattr(product, 'logo_svg_url', None),
        },
        "social_proof": social_proof,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


@router.get("/products")
async def get_webapp_products(
    language_code: Optional[str] = Query(None, description="User language code for currency conversion"),
    currency: Optional[str] = Query(None, description="User preferred currency (USD, RUB, EUR, etc.)")
):
    """Get all active products for Mini App catalog.
    
    Uses anchor pricing: if product has fixed price in user's currency, uses that.
    Otherwise falls back to dynamic conversion from USD.
    """
    db = get_database()
    products = await db.get_products(status="active")
    
    # Unified currency formatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(
        user_telegram_id=None,
        db=db,
        redis=redis,
        preferred_currency=currency,
        language_code=language_code
    )
    
    # Get currency service for anchor pricing
    currency_service = get_currency_service(redis)
    
    # Batch fetch social proof data
    product_ids = [p.id for p in products]
    social_proof_map = {}
    try:
        if product_ids:
            social_proof_result = await asyncio.to_thread(
                lambda: db.client.table("product_social_proof").select("product_id,sales_count").in_("product_id", product_ids).execute()
            )
            social_proof_map = {sp["product_id"]: sp for sp in (social_proof_result.data or [])}
    except Exception as e:
        logger.warning(f"Failed to batch fetch social proof: {e}")
    
    result = []
    for p in products:
        stock_result = await asyncio.to_thread(
            lambda pid=p.id: db.client.table("available_stock_with_discounts").select("*").eq("product_id", pid).limit(1).execute()
        )
        discount_percent = stock_result.data[0].get("discount_percent", 0) if stock_result.data else 0
        rating_info = await db.get_product_rating(p.id)
        
        sp_data = social_proof_map.get(p.id, {})
        sales_count = sp_data.get("sales_count", 0)
        
        # USD values (base)
        price_usd = float(p.price)
        final_price_usd = price_usd * (1 - discount_percent / 100)
        msrp_usd = float(p.msrp) if hasattr(p, 'msrp') and p.msrp else None
        
        # Get anchor price (fixed or converted)
        product_dict = {
            "price": p.price,
            "prices": getattr(p, 'prices', None) or {}
        }
        anchor_price = float(await currency_service.get_anchor_price(product_dict, formatter.currency))
        is_anchor_price = currency_service.has_anchor_price(product_dict, formatter.currency)
        
        # Apply discount to anchor price
        anchor_final_price = anchor_price * (1 - discount_percent / 100)
        
        warranty_days = p.warranty_hours // 24 if hasattr(p, 'warranty_hours') and p.warranty_hours else 0
        duration_days = getattr(p, 'duration_days', None)
        fulfillment_time_hours = getattr(p, 'fulfillment_time_hours', 48)
        
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            # USD values (for calculations)
            "price_usd": price_usd,
            "final_price_usd": final_price_usd,
            "msrp_usd": msrp_usd,
            # Display values (for UI) - now using anchor prices
            "original_price": anchor_price,
            "price": anchor_price,
            "final_price": anchor_final_price,
            "msrp": formatter.convert(msrp_usd) if msrp_usd else None,
            # Currency
            "currency": formatter.currency,
            "is_anchor_price": is_anchor_price,
            # Other fields
            "discount_percent": discount_percent,
            "warranty_days": warranty_days,
            "duration_days": duration_days,
            "available_count": p.stock_count,
            "available": p.stock_count > 0,
            "can_fulfill_on_demand": p.status == 'active',
            "fulfillment_time_hours": fulfillment_time_hours if p.status == 'active' else None,
            "type": p.type,
            "rating": rating_info.get("average", 0),
            "reviews_count": rating_info.get("count", 0),
            "sales_count": sales_count,
            "categories": getattr(p, 'categories', []) or [],
            "status": p.status,
            "image_url": getattr(p, 'image_url', None),
            "video_url": getattr(p, 'video_url', None),
            "logo_svg_url": getattr(p, 'logo_svg_url', None),
        })
    
    return {
        "products": result,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }
