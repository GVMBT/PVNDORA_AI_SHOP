"""
WebApp Public Router

Public endpoints that don't require authentication.
All prices include both USD and display values for unified currency handling.
Supports anchor pricing (fixed prices per currency).
"""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query

from core.db import get_redis
from core.logging import get_logger
from core.services.currency import get_currency_service
from core.services.currency_response import CurrencyFormatter
from core.services.database import get_database

logger = get_logger(__name__)

router = APIRouter(tags=["webapp-public"])


@router.get("/products/{product_id}")
async def get_webapp_product(
    product_id: str,
    language_code: str | None = Query(
        None, description="User language code for currency conversion"
    ),
    currency: str | None = Query(None, description="User preferred currency (USD, RUB, EUR, etc.)"),
):
    """Get product with discount and social proof for Mini App.

    Uses products_with_stock_summary VIEW for aggregated data.
    Uses anchor pricing: if product has fixed price in user's currency, uses that.
    Otherwise falls back to dynamic conversion from USD.
    """
    db = get_database()

    # Use VIEW for product data with aggregated stock info (includes max_discount_percent)
    product_result = (
        await db.client.table("products_with_stock_summary")
        .select("*")
        .eq("id", product_id)
        .execute()
    )

    if not product_result.data:
        raise HTTPException(status_code=404, detail="Product not found")

    product_raw = product_result.data[0]
    if not isinstance(product_raw, dict):
        raise HTTPException(status_code=500, detail="Invalid product data format")
    product = cast(dict[str, Any], product_raw)

    # Discount from VIEW (already aggregated)
    discount_percent = product.get("max_discount_percent", 0) or 0

    rating_info = await db.get_product_rating(product_id)

    # Unified currency formatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(
        user_telegram_id=None,
        db=db,
        redis=redis,
        preferred_currency=currency,
        language_code=language_code,
    )

    # Get currency service for anchor pricing
    currency_service = get_currency_service(redis)

    # USD values (base)
    price_raw = product.get("price", 0)
    price_usd = float(price_raw) if isinstance(price_raw, (int, float, str)) else 0.0
    final_price_usd = price_usd * (1 - discount_percent / 100)
    msrp_raw = product.get("msrp")
    msrp_usd = float(msrp_raw) if msrp_raw and isinstance(msrp_raw, (int, float, str)) else None

    # Get anchor price (fixed or converted)
    product_dict = {"price": product.get("price", 0), "prices": product.get("prices") or {}}
    anchor_price = float(await currency_service.get_anchor_price(product_dict, formatter.currency))
    is_anchor_price = currency_service.has_anchor_price(product_dict, formatter.currency)

    # Apply discount to anchor price
    anchor_final_price = anchor_price * (1 - discount_percent / 100)

    # Get anchor MSRP (fixed or converted)
    msrp_prices = product.get("msrp_prices") or {}
    anchor_msrp = None
    if msrp_usd:
        # Check for anchor MSRP in target currency
        if msrp_prices and formatter.currency in msrp_prices:
            anchor_msrp_value = msrp_prices[formatter.currency]
            if anchor_msrp_value is not None:
                anchor_msrp = float(anchor_msrp_value)
        # Fallback: convert from USD MSRP
        if anchor_msrp is None:
            anchor_msrp = formatter.convert(msrp_usd)

    fulfillment_time_hours = product.get("fulfillment_time_hours", 48)
    stock_count = product.get("stock_count", 0) or 0

    # Get social proof data
    try:
        social_proof_result = (
            await db.client.table("product_social_proof")
            .select("*")
            .eq("product_id", product_id)
            .single()
            .execute()
        )
        social_proof_data = social_proof_result.data if social_proof_result.data else {}
    except Exception as e:
        logger.warning(f"Failed to get social proof: {e}")
        social_proof_data = {}

    social_proof = {
        "rating": rating_info.get("average", 0),
        "review_count": rating_info.get("count", 0),
        "sales_count": social_proof_data.get("sales_count", 0),
        "recent_reviews": social_proof_data.get("recent_reviews", []),
    }

    instruction_files = product.get("instruction_files") or []

    return {
        "product": {
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description"),
            # USD values (for calculations)
            "price_usd": price_usd,
            "final_price_usd": final_price_usd,
            "msrp_usd": msrp_usd,
            # Display values (for UI) - now using anchor prices
            "original_price": anchor_price,
            "price": anchor_price,
            "final_price": anchor_final_price,
            "msrp": anchor_msrp,
            # Currency info
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
            "is_anchor_price": is_anchor_price,  # True if price is fixed, False if dynamically converted
            # Other fields
            "discount_percent": discount_percent,
            "warranty_days": (
                product.get("warranty_hours", 0) // 24 if product.get("warranty_hours") else 0
            ),
            "duration_days": product.get("duration_days"),
            "available_count": stock_count,
            "available": stock_count > 0,
            "can_fulfill_on_demand": product.get("status") == "active",
            "fulfillment_time_hours": (
                fulfillment_time_hours if product.get("status") == "active" else None
            ),
            "type": product.get("type"),
            "instructions": product.get("instructions"),
            "instruction_files": instruction_files,
            "rating": rating_info.get("average", 0),
            "reviews_count": rating_info.get("count", 0),
            "categories": product.get("categories") or [],
            "status": product.get("status"),
            "sales_count": social_proof_data.get("sales_count", 0),
            "image_url": product.get("image_url"),
            "video_url": product.get("video_url"),
            "logo_svg_url": product.get("logo_svg_url"),
        },
        "social_proof": social_proof,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


@router.get("/products")
async def get_webapp_products(
    language_code: str | None = Query(
        None, description="User language code for currency conversion"
    ),
    currency: str | None = Query(None, description="User preferred currency (USD, RUB, EUR, etc.)"),
):
    """Get all active products for Mini App catalog.

    Uses products_with_stock_summary VIEW to eliminate N+1 queries.
    Uses anchor pricing: if product has fixed price in user's currency, uses that.
    Otherwise falls back to dynamic conversion from USD.
    """
    db = get_database()

    # Use VIEW directly for all product data including stock counts and max discount
    # This eliminates N+1 queries (previously 50+ queries, now 1-2)
    products_result = (
        await db.client.table("products_with_stock_summary")
        .select("*")
        .eq("status", "active")
        .execute()
    )

    products_raw = products_result.data or []
    products: list[dict[str, Any]] = []
    for p_raw in products_raw:
        if isinstance(p_raw, dict):
            products.append(cast(dict[str, Any], p_raw))

    # Unified currency formatter
    redis = get_redis()
    formatter = await CurrencyFormatter.create(
        user_telegram_id=None,
        db=db,
        redis=redis,
        preferred_currency=currency,
        language_code=language_code,
    )

    # Get currency service for anchor pricing
    currency_service = get_currency_service(redis)

    # Batch fetch social proof data (single query for all products)
    product_ids = [p["id"] for p in products]
    social_proof_map = {}
    try:
        if product_ids:
            social_proof_result = (
                await db.client.table("product_social_proof")
                .select("product_id,sales_count")
                .in_("product_id", product_ids)
                .execute()
            )
            for sp_raw in social_proof_result.data or []:
                if isinstance(sp_raw, dict):
                    sp = cast(dict[str, Any], sp_raw)
                    product_id = sp.get("product_id")
                    if product_id:
                        social_proof_map[product_id] = sp
    except Exception as e:
        logger.warning(f"Failed to batch fetch social proof: {e}")

    # Batch fetch ratings (single query for all products)
    ratings_map: dict[str, list[float]] = {}
    try:
        if product_ids:
            ratings_result = (
                await db.client.table("reviews")
                .select("product_id,rating")
                .in_("product_id", product_ids)
                .execute()
            )

            # Aggregate ratings per product
            for r in ratings_result.data or []:
                pid = r["product_id"]
                if pid not in ratings_map:
                    ratings_map[pid] = []
                if r.get("rating"):
                    ratings_map[pid].append(r["rating"])
    except Exception as e:
        logger.warning(f"Failed to batch fetch ratings: {e}")

    result = []
    for p in products:
        # Discount from VIEW (max_discount_percent already aggregated)
        discount_percent = p.get("max_discount_percent", 0) or 0

        # Rating from batch-loaded data
        product_ratings = ratings_map.get(p["id"], [])
        rating_info = {
            "average": (
                round(sum(product_ratings) / len(product_ratings), 1) if product_ratings else 0
            ),
            "count": len(product_ratings),
        }

        sp_data = social_proof_map.get(p["id"], {})
        sales_count = sp_data.get("sales_count", 0)

        # USD values (base)
        price_usd = float(p.get("price", 0))
        final_price_usd = price_usd * (1 - discount_percent / 100)
        msrp_raw = p.get("msrp")
        msrp_usd = float(msrp_raw) if msrp_raw and isinstance(msrp_raw, (int, float, str)) else None

        # Get anchor price (fixed or converted)
        product_dict = {"price": p.get("price", 0), "prices": p.get("prices") or {}}
        anchor_price = float(
            await currency_service.get_anchor_price(product_dict, formatter.currency)
        )
        is_anchor_price = currency_service.has_anchor_price(product_dict, formatter.currency)

        # Apply discount to anchor price
        anchor_final_price = anchor_price * (1 - discount_percent / 100)

        # Get anchor MSRP (fixed or converted)
        msrp_prices = p.get("msrp_prices") or {}
        anchor_msrp = None
        if msrp_usd:
            if msrp_prices and formatter.currency in msrp_prices:
                anchor_msrp_value = msrp_prices[formatter.currency]
                if anchor_msrp_value is not None:
                    anchor_msrp = float(anchor_msrp_value)
            if anchor_msrp is None:
                anchor_msrp = formatter.convert(msrp_usd)

        warranty_days = p.get("warranty_hours", 0) // 24 if p.get("warranty_hours") else 0
        duration_days = p.get("duration_days")
        fulfillment_time_hours = p.get("fulfillment_time_hours", 48)
        stock_count = p.get("stock_count", 0) or 0

        result.append(
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description"),
                # USD values (for calculations)
                "price_usd": price_usd,
                "final_price_usd": final_price_usd,
                "msrp_usd": msrp_usd,
                # Display values (for UI) - now using anchor prices
                "original_price": anchor_price,
                "price": anchor_price,
                "final_price": anchor_final_price,
                "msrp": anchor_msrp,
                # Currency
                "currency": formatter.currency,
                "is_anchor_price": is_anchor_price,
                # Other fields
                "discount_percent": discount_percent,
                "warranty_days": warranty_days,
                "duration_days": duration_days,
                "available_count": stock_count,
                "available": stock_count > 0,
                "can_fulfill_on_demand": p.get("status") == "active",
                "fulfillment_time_hours": (
                    fulfillment_time_hours if p.get("status") == "active" else None
                ),
                "type": p.get("type"),
                "rating": rating_info.get("average", 0),
                "reviews_count": rating_info.get("count", 0),
                "sales_count": sales_count,
                "categories": p.get("categories") or [],
                "status": p.get("status"),
                "image_url": p.get("image_url"),
                "video_url": p.get("video_url"),
                "logo_svg_url": p.get("logo_svg_url"),
            }
        )

    return {
        "products": result,
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }
