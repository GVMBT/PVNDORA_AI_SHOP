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
from core.services.currency import CurrencyService, get_currency_service
from core.services.currency_response import CurrencyFormatter
from core.services.database import Database, get_database

logger = get_logger(__name__)

router = APIRouter(tags=["webapp-public"])


# =============================================================================
# Helper functions to reduce cognitive complexity
# =============================================================================


def _compute_anchor_msrp(
    msrp_usd: float | None,
    msrp_prices: dict[str, Any],
    target_currency: str,
    formatter: CurrencyFormatter,
) -> float | None:
    """Compute anchor MSRP: fixed price if available, otherwise convert from USD."""
    if not msrp_usd:
        return None

    # Check for anchor MSRP in target currency
    if msrp_prices and target_currency in msrp_prices:
        anchor_value = msrp_prices[target_currency]
        if anchor_value is not None:
            return float(anchor_value)

    # Fallback: convert from USD MSRP
    return formatter.convert(msrp_usd)


async def _fetch_single_product(db: Database, product_id: str) -> dict[str, Any]:
    """Fetch and validate a single product from database."""
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

    return cast(dict[str, Any], product_raw)


async def _fetch_social_proof_single(db: Database, product_id: str) -> dict[str, Any]:
    """Fetch social proof for a single product."""
    try:
        result = (
            await db.client.table("product_social_proof")
            .select("*")
            .eq("product_id", product_id)
            .single()
            .execute()
        )
        return cast(dict[str, Any], result.data) if result.data else {}
    except Exception as e:
        logger.warning("Failed to get social proof: %s", type(e).__name__)
        return {}


async def _batch_fetch_social_proof(
    db: Database, product_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Batch fetch social proof data for multiple products."""
    if not product_ids:
        return {}

    social_proof_map: dict[str, dict[str, Any]] = {}
    try:
        result = (
            await db.client.table("product_social_proof")
            .select("product_id,sales_count")
            .in_("product_id", product_ids)
            .execute()
        )
        for sp_raw in result.data or []:
            if isinstance(sp_raw, dict):
                sp = cast(dict[str, Any], sp_raw)
                pid = sp.get("product_id")
                if pid:
                    social_proof_map[pid] = sp
    except Exception as e:
        logger.warning("Failed to batch fetch social proof: %s", type(e).__name__)

    return social_proof_map


async def _batch_fetch_ratings(db: Database, product_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Batch fetch and aggregate ratings for multiple products."""
    if not product_ids:
        return {}

    ratings_map: dict[str, list[float]] = {}
    try:
        result = (
            await db.client.table("reviews")
            .select("product_id,rating")
            .in_("product_id", product_ids)
            .execute()
        )
        for r in cast(list[dict[str, Any]], result.data or []):
            pid = str(r["product_id"])
            if pid not in ratings_map:
                ratings_map[pid] = []
            rating = r.get("rating")
            if rating is not None:
                ratings_map[pid].append(float(rating))
    except Exception as e:
        logger.warning("Failed to batch fetch ratings: %s", type(e).__name__)

    # Compute aggregates
    result_map: dict[str, dict[str, Any]] = {}
    for pid, ratings_list in ratings_map.items():
        result_map[pid] = {
            "average": round(sum(ratings_list) / len(ratings_list), 1) if ratings_list else 0,
            "count": len(ratings_list),
        }

    return result_map


async def _compute_price_info(
    product: dict[str, Any],
    currency_service: CurrencyService,
    formatter: CurrencyFormatter,
    discount_percent: float,
) -> dict[str, Any]:
    """Compute all price-related fields for a product."""
    # USD values (base)
    price_raw = product.get("price", 0)
    price_usd = float(price_raw) if isinstance(price_raw, (int, float, str)) else 0.0
    final_price_usd = price_usd * (1 - discount_percent / 100)

    msrp_raw = product.get("msrp")
    msrp_usd = float(msrp_raw) if msrp_raw and isinstance(msrp_raw, (int, float, str)) else None

    # Get anchor price (fixed or converted)
    # Handle None values for prices field
    prices_raw = product.get("prices")
    prices = prices_raw if prices_raw is not None else {}
    product_dict = {"price": product.get("price", 0), "prices": prices}
    anchor_price = float(await currency_service.get_anchor_price(product_dict, formatter.currency))
    is_anchor_price = currency_service.has_anchor_price(product_dict, formatter.currency)

    # Apply discount to anchor price
    anchor_final_price = anchor_price * (1 - discount_percent / 100)

    # Get anchor MSRP
    # msrp_prices may not exist in products_with_stock_summary VIEW
    msrp_prices = product.get("msrp_prices")
    if msrp_prices is None:
        msrp_prices = {}
    anchor_msrp = _compute_anchor_msrp(msrp_usd, msrp_prices, formatter.currency, formatter)

    return {
        "price_usd": price_usd,
        "final_price_usd": final_price_usd,
        "msrp_usd": msrp_usd,
        "anchor_price": anchor_price,
        "anchor_final_price": anchor_final_price,
        "anchor_msrp": anchor_msrp,
        "is_anchor_price": is_anchor_price,
    }


def _build_product_response(
    product: dict[str, Any],
    price_info: dict[str, Any],
    rating_info: dict[str, Any],
    formatter: CurrencyFormatter,
    discount_percent: float,
    sales_count: int = 0,
    include_full_details: bool = False,
    social_proof_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build product response object with all computed fields."""
    stock_count = product.get("stock_count", 0) or 0
    fulfillment_time_hours = product.get("fulfillment_time_hours", 48)
    warranty_days = product.get("warranty_hours", 0) // 24 if product.get("warranty_hours") else 0

    base_response = {
        "id": product["id"],
        "name": product["name"],
        "description": product.get("description"),
        # USD values (for calculations)
        "price_usd": price_info["price_usd"],
        "final_price_usd": price_info["final_price_usd"],
        "msrp_usd": price_info["msrp_usd"],
        # Display values (for UI) - anchor prices
        "original_price": price_info["anchor_price"],
        "price": price_info["anchor_price"],
        "final_price": price_info["anchor_final_price"],
        "msrp": price_info["anchor_msrp"],
        # Currency
        "currency": formatter.currency,
        "is_anchor_price": price_info["is_anchor_price"],
        # Other fields
        "discount_percent": discount_percent,
        "warranty_days": warranty_days,
        "available_count": stock_count,
        "available": stock_count > 0,
        "can_fulfill_on_demand": product.get("status") == "active",
        "fulfillment_time_hours": fulfillment_time_hours
        if product.get("status") == "active"
        else None,
        "type": product.get("type"),
        "rating": rating_info.get("average", 0),
        "reviews_count": rating_info.get("count", 0),
        "sales_count": sales_count,
        "categories": product.get("categories") or [],
        "status": product.get("status"),
        "image_url": product.get("image_url"),
        "video_url": None,  # Field removed from products table
        "logo_svg_url": product.get("logo_svg_url"),
    }

    if include_full_details:
        base_response.update(
            {
                "exchange_rate": formatter.exchange_rate,
                "duration_days": product.get("duration_days"),
                "instructions": product.get("instructions"),
                "instruction_files": product.get("instruction_files") or [],
            }
        )
        # Override sales_count from social_proof_data if provided
        if social_proof_data:
            base_response["sales_count"] = social_proof_data.get("sales_count", 0)

    else:
        base_response["duration_days"] = product.get("duration_days")

    return base_response


# =============================================================================
# API Endpoints
# =============================================================================


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
    redis = get_redis()

    # Fetch product
    product = await _fetch_single_product(db, product_id)

    # Discount from VIEW
    discount_percent = product.get("max_discount_percent", 0) or 0

    # Rating and social proof
    rating_info = await db.get_product_rating(product_id)
    social_proof_data = await _fetch_social_proof_single(db, product_id)

    # Currency services
    formatter = await CurrencyFormatter.create(
        user_telegram_id=None,
        db=db,
        redis=redis,
        preferred_currency=currency,
        language_code=language_code,
    )
    currency_service = get_currency_service(redis)

    # Compute prices
    price_info = await _compute_price_info(product, currency_service, formatter, discount_percent)

    # Build product response
    product_response = _build_product_response(
        product=product,
        price_info=price_info,
        rating_info=rating_info,
        formatter=formatter,
        discount_percent=discount_percent,
        include_full_details=True,
        social_proof_data=social_proof_data,
    )

    social_proof = {
        "rating": rating_info.get("average", 0),
        "review_count": rating_info.get("count", 0),
        "sales_count": social_proof_data.get("sales_count", 0),
        "recent_reviews": social_proof_data.get("recent_reviews", []),
    }

    return {
        "product": product_response,
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
    from core.logging import get_logger

    logger = get_logger(__name__)

    try:
        db = get_database()
        redis = get_redis()

        # Fetch all active products
        products_result = (
            await db.client.table("products_with_stock_summary")
            .select("*")
            .eq("status", "active")
            .execute()
        )

        products_raw = products_result.data or []
        products: list[dict[str, Any]] = [
            cast(dict[str, Any], p) for p in products_raw if isinstance(p, dict)
        ]

        # Currency services
        formatter = await CurrencyFormatter.create(
            user_telegram_id=None,
            db=db,
            redis=redis,
            preferred_currency=currency,
            language_code=language_code,
        )
        currency_service = get_currency_service(redis)

        # Batch fetch data
        product_ids = [p["id"] for p in products]
        social_proof_map = await _batch_fetch_social_proof(db, product_ids)
        ratings_map = await _batch_fetch_ratings(db, product_ids)

        # Build result list
        result = []
        for p in products:
            try:
                discount_percent = p.get("max_discount_percent", 0) or 0
                rating_info = ratings_map.get(p["id"], {"average": 0, "count": 0})
                sp_data = social_proof_map.get(p["id"], {})
                sales_count = sp_data.get("sales_count", 0)

                price_info = await _compute_price_info(p, currency_service, formatter, discount_percent)

                product_data = _build_product_response(
                    product=p,
                    price_info=price_info,
                    rating_info=rating_info,
                    formatter=formatter,
                    discount_percent=discount_percent,
                    sales_count=sales_count,
                )
                result.append(product_data)
            except Exception as e:
                logger.warning(
                    f"Failed to process product {p.get('id', 'unknown')}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                # Skip this product and continue with others
                continue

        return {
            "products": result,
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
        }
    except Exception as e:
        logger.error(f"Failed to fetch products: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch products")
