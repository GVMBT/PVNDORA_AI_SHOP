"""Catalog Tools for Shop Agent.

Product browsing, search, and availability checking.
"""

from typing import Any

from langchain_core.tools import tool

from core.logging import get_logger

from .base import get_db, get_user_context

logger = get_logger(__name__)


@tool
async def get_catalog() -> dict[str, Any]:
    """Get full product catalog with prices and availability.
    Prices are automatically converted to user's currency (from context).

    Returns:
        List of all active products with stock status and prices in user's currency

    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        db = get_db()
        ctx = get_user_context()
        products = await db.get_products(status="active")

        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency

        logger.info(f"get_catalog: using context currency={target_currency}")

        result_products = []
        for p in products:
            price_usd = float(p.price or 0)

            if target_currency != "USD":
                try:
                    price_converted = currency_service.convert_price(
                        price_usd,
                        target_currency,
                    )
                except Exception:
                    price_converted = price_usd
            else:
                price_converted = price_usd

            price_formatted = currency_service.format_price(price_converted, target_currency)

            result_products.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "price": price_converted,
                    "price_usd": price_usd,
                    "currency": target_currency,
                    "price_formatted": price_formatted,
                    "in_stock": p.stock_count > 0,
                    "stock_count": p.stock_count,
                    "status": p.status,
                },
            )

        return {
            "success": True,
            "count": len(result_products),
            "currency": target_currency,
            "products": result_products,
        }
    except Exception as e:
        logger.exception("get_catalog error")
        return {"success": False, "error": str(e)}


@tool
async def search_products(query: str) -> dict[str, Any]:
    """Search products by name or description.
    Use when user asks about specific products.
    Prices are automatically converted to user's currency.

    Args:
        query: Search query (product name, category, etc.)

    Returns:
        Matching products with prices in user's currency

    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        db = get_db()
        ctx = get_user_context()
        products = await db.search_products(query)

        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency

        logger.info(f"search_products: query='{query}', currency={target_currency}")

        result_products = []
        for p in products:
            price_usd = float(p.price or 0)

            if target_currency != "USD":
                try:
                    price_converted = currency_service.convert_price(
                        price_usd,
                        target_currency,
                    )
                except Exception:
                    logger.exception("Currency conversion failed")
                    price_converted = price_usd
            else:
                price_converted = price_usd

            price_formatted = currency_service.format_price(price_converted, target_currency)

            result_products.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "price": price_converted,
                    "price_usd": price_usd,
                    "price_formatted": price_formatted,
                    "currency": target_currency,
                    "in_stock": p.stock_count > 0,
                    "stock_count": p.stock_count,
                },
            )

        return {
            "success": True,
            "count": len(result_products),
            "currency": target_currency,
            "products": result_products,
        }
    except Exception as e:
        logger.exception("search_products error")
        return {"success": False, "error": str(e)}


@tool
async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed info about a specific product.
    Prices are automatically converted to user's currency.

    Args:
        product_id: Product UUID

    Returns:
        Full product details including description, pricing, availability

    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        db = get_db()
        ctx = get_user_context()
        product = await db.get_product_by_id(product_id)
        if not product:
            return {"success": False, "error": "Product not found"}

        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency

        price_usd = float(product.price or 0)

        if target_currency != "USD":
            try:
                price_converted = currency_service.convert_price(price_usd, target_currency)
            except Exception:
                price_converted = price_usd
        else:
            price_converted = price_usd

        price_formatted = currency_service.format_price(price_converted, target_currency)

        is_russian = ctx.language in ["ru", "be", "kk"]
        if product.stock_count > 0:
            availability = (
                f"В наличии ({product.stock_count} шт), мгновенная доставка"
                if is_russian
                else f"In stock ({product.stock_count}), instant delivery"
            )
        else:
            hours = getattr(product, "fulfillment_time_hours", 48) or 48
            availability = (
                f"Предзаказ, доставка {hours}ч" if is_russian else f"Preorder, delivery in {hours}h"
            )

        warranty_hours = getattr(product, "warranty_hours", None)

        return {
            "success": True,
            "id": product.id,
            "name": product.name,
            "description": product.description or "",
            "price": price_converted,
            "price_usd": price_usd,
            "currency": target_currency,
            "price_formatted": price_formatted,
            "in_stock": product.stock_count > 0,
            "stock_count": product.stock_count,
            "availability": availability,
            "status": product.status,
            "warranty_hours": warranty_hours,
            "fulfillment_hours": getattr(product, "fulfillment_time_hours", 48),
            "categories": getattr(product, "categories", []),
        }
    except Exception as e:
        logger.exception("get_product_details error")
        return {"success": False, "error": str(e)}


@tool
async def check_product_availability(product_name: str) -> dict[str, Any]:
    """Check if a product is available for purchase.
    Use before adding to cart or purchasing.

    Args:
        product_name: Name or partial name of the product

    Returns:
        Availability info with price in user's currency

    """
    try:
        from core.db import get_redis
        from core.services.currency import get_currency_service

        db = get_db()
        ctx = get_user_context()
        products = await db.search_products(product_name)

        if not products:
            return {
                "success": False,
                "found": False,
                "message": f"Product '{product_name}' not found",
            }

        redis = get_redis()
        currency_service = get_currency_service(redis)
        target_currency = ctx.currency

        p = products[0]  # Best match
        price_usd = float(p.price or 0)

        if target_currency != "USD":
            try:
                price_converted = currency_service.convert_price(price_usd, target_currency)
            except Exception:
                price_converted = price_usd
        else:
            price_converted = price_usd

        price_formatted = currency_service.format_price(price_converted, target_currency)

        return {
            "success": True,
            "found": True,
            "product_id": p.id,
            "name": p.name,
            "price": price_converted,
            "price_usd": price_usd,
            "price_formatted": price_formatted,
            "currency": target_currency,
            "in_stock": p.stock_count > 0,
            "stock_count": p.stock_count,
            "status": p.status,
            "availability": "instant" if p.stock_count > 0 else "prepaid (24-48h)",
        }
    except Exception as e:
        logger.exception("check_product_availability error")
        return {"success": False, "error": str(e)}
