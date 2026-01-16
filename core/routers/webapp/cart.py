"""WebApp Cart Router.

Shopping cart endpoints with unified currency handling.

Response format:
- All amounts include both USD value and display value
- Frontend uses USD for calculations, display for UI
"""

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_telegram_auth

if TYPE_CHECKING:
    from core.cart.models import Cart
    from core.services.database import Database
    from core.utils.validators import TelegramUser
from core.db import get_redis
from core.logging import get_logger
from core.services.currency_response import CurrencyFormatter
from core.services.database import get_database
from core.services.money import to_float

from .models import AddToCartRequest, ApplyPromoRequest, UpdateCartItemRequest

logger = get_logger(__name__)

# Error message constants
ERR_CART_EMPTY = "Cart is empty"


# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def _calculate_display_prices(
    item: Any,
    product: Any,
    currency_service: Any,
    formatter: Any,
) -> tuple[float, float, float]:
    """Calculate display prices using anchor pricing.

    Args:
        item: Cart item with USD prices
        product: Product data
        currency_service: Currency service for anchor prices
        formatter: CurrencyFormatter for currency conversion

    Returns:
        (unit_price_display, final_price_display, total_price_display)

    """
    target_currency = formatter.currency

    # Try anchor price first (product-level pricing)
    if product and target_currency != "USD":
        try:
            anchor_price = currency_service.get_anchor_price(product, target_currency)
            if anchor_price and anchor_price > 0:
                unit_price_display = anchor_price
                # Apply discount if any
                discount = item.discount_percent or 0
                if discount > 0:
                    final_price_display = anchor_price * (1 - discount / 100)
                else:
                    final_price_display = anchor_price
                total_price_display = final_price_display * item.quantity
                return unit_price_display, final_price_display, total_price_display
        except Exception:
            pass

    # Fallback to exchange rate conversion
    unit_price_display = formatter.convert(item.unit_price)
    final_price_display = formatter.convert(item.final_price)
    total_price_display = formatter.convert(item.total_price)

    return unit_price_display, final_price_display, total_price_display


router = APIRouter(tags=["webapp-cart"])


async def _format_cart_response(
    cart: "Cart", db: "Database", user_telegram_id: int
) -> dict[str, Any]:
    """Build cart response with unified currency handling.

    Response includes:
    - *_usd fields: values in USD for calculations
    - * fields: values in user's currency for display (using anchor prices!)
    - currency: user's preferred currency
    - exchange_rate: for frontend fallback conversion
    """
    redis = get_redis()
    formatter = CurrencyFormatter.create(user_telegram_id, db, redis)

    # Get currency service for anchor pricing
    from core.services.currency import get_currency_service

    currency_service = get_currency_service(redis)

    if not cart:
        return {
            "cart": None,
            "items": [],
            # USD values (for calculations)
            "total_usd": 0.0,
            "subtotal_usd": 0.0,
            "instant_total_usd": 0.0,
            "prepaid_total_usd": 0.0,
            # Display values (for UI)
            "total": 0.0,
            "subtotal": 0.0,
            "instant_total": 0.0,
            "prepaid_total": 0.0,
            # Promo
            "promo_code": None,
            "promo_discount_percent": 0.0,
            "original_total_usd": 0.0,
            "original_total": 0.0,
            # Currency info
            "currency": formatter.currency,
            "exchange_rate": formatter.exchange_rate,
        }

    # OPTIMIZATION: Batch fetch all products in one query instead of N+1
    product_ids = [item.product_id for item in cart.items]
    products_result = await db.client.table("products").select("*").in_("id", product_ids).execute()
    products_map = {p["id"]: p for p in (products_result.data or [])}
    products = [products_map.get(item.product_id) for item in cart.items]

    items_with_details = []
    for item, product in zip(cart.items, products, strict=False):
        unit_price_usd = to_float(item.unit_price)
        final_price_usd = to_float(item.final_price)
        total_price_usd = to_float(item.total_price)

        (
            unit_price_display,
            final_price_display,
            total_price_display,
        ) = _calculate_display_prices(item, product, currency_service, formatter)

        items_with_details.append(
            {
                "product_id": item.product_id,
                "product_name": product.get("name") if product else "Unknown",
                "image_url": product.get("image_url") if product else None,
                "quantity": item.quantity,
                "instant_quantity": item.instant_quantity,
                "prepaid_quantity": item.prepaid_quantity,
                "discount_percent": item.discount_percent,
                # USD values (for calculations)
                "unit_price_usd": unit_price_usd,
                "final_price_usd": final_price_usd,
                "total_price_usd": total_price_usd,
                # Display values (for UI) - using anchor prices!
                "unit_price": unit_price_display,
                "final_price": final_price_display,
                "total_price": total_price_display,
                # Currency (for this item)
                "currency": formatter.currency,
            },
        )

    # Calculate original total (before promo) if promo applied
    original_total_usd = to_float(cart.subtotal) if cart.promo_code else to_float(cart.total)

    # CRITICAL: Calculate display totals using anchor prices from items, NOT conversion from USD
    # This ensures totals match item prices (which use anchor prices)
    subtotal_display = sum(
        item["total_price"] for item in items_with_details
    )  # Before promo (if promo exists, it's applied at cart level)
    instant_total_display = sum(
        item["unit_price"] * item["instant_quantity"] for item in items_with_details
    )
    prepaid_total_display = sum(
        item["unit_price"] * item["prepaid_quantity"] for item in items_with_details
    )

    # Apply cart-level promo discount to subtotal if promo exists
    if cart.promo_code and cart.promo_discount_percent > 0:
        promo_multiplier = 1 - (to_float(cart.promo_discount_percent) / 100)
        total_display = subtotal_display * promo_multiplier
        original_total_display = subtotal_display
    else:
        total_display = subtotal_display
        original_total_display = subtotal_display

    # Round totals for integer currencies
    if formatter.currency in ["RUB", "UAH", "TRY", "INR"]:
        total_display = round(total_display)
        subtotal_display = round(subtotal_display)
        instant_total_display = round(instant_total_display)
        prepaid_total_display = round(prepaid_total_display)
        original_total_display = round(original_total_display)

    return {
        "cart": {
            "user_telegram_id": cart.user_telegram_id,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
        },
        "items": items_with_details,
        # USD values (for calculations)
        "total_usd": to_float(cart.total),
        "subtotal_usd": to_float(cart.subtotal),
        "instant_total_usd": to_float(cart.instant_total),
        "prepaid_total_usd": to_float(cart.prepaid_total),
        "original_total_usd": original_total_usd,
        # Display values (for UI) - using anchor prices from items!
        "total": total_display,
        "subtotal": subtotal_display,
        "instant_total": instant_total_display,
        "prepaid_total": prepaid_total_display,
        "original_total": original_total_display,
        # Promo
        "promo_code": cart.promo_code,
        "promo_discount_percent": cart.promo_discount_percent,
        # Currency info (for frontend)
        "currency": formatter.currency,
        "exchange_rate": formatter.exchange_rate,
    }


def _ensure_product_orderable(product: Any) -> str:
    """Validate product status for cart operations."""
    status = getattr(product, "status", "active")
    if status == "discontinued":
        raise HTTPException(
            status_code=400,
            detail="Product is discontinued and unavailable for order.",
        )
    if status == "coming_soon":
        raise HTTPException(
            status_code=400,
            detail="Product is coming soon. Use waitlist to be notified.",
        )
    return str(status)


@router.get("/cart")
async def get_webapp_cart(user: Any = Depends(verify_telegram_auth)) -> dict[str, Any]:
    """Get user's shopping cart with currency conversion."""
    from core.cart import get_cart_manager

    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        if not cart:
            return {
                "items": [],
                "total": 0,
                "total_usd": 0,
                "currency": "USD",
                "exchange_rate": 1.0,
            }
        db = get_database()

        return await _format_cart_response(cart, db, user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cart: {e!s}")


@router.post("/cart/add")
async def add_to_cart(
    request: AddToCartRequest, user: Any = Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Add item to cart (with instant/prepaid split)."""
    from core.cart import get_cart_manager

    db = get_database()
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _ensure_product_orderable(product)

    available_stock = await db.get_available_stock_count(request.product_id)

    cart_manager = get_cart_manager()
    try:
        await cart_manager.add_item(
            user_telegram_id=user.id,
            product_id=request.product_id,
            product_name=product.name,
            quantity=request.quantity,
            available_stock=available_stock,
            unit_price=float(product.price),
            discount_percent=0.0,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to add to cart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add item to cart")

    cart = await cart_manager.get_cart(user.id)
    if not cart:
        return {"items": [], "total": 0, "total_usd": 0, "currency": "USD", "exchange_rate": 1.0}
    return await _format_cart_response(cart, db, user.id)


@router.patch("/cart/item")
async def update_cart_item(
    request: UpdateCartItemRequest, user: "TelegramUser" = Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Update cart item quantity (0 = remove)."""
    from core.cart import get_cart_manager

    db = get_database()
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _ensure_product_orderable(product)

    available_stock = await db.get_available_stock_count(request.product_id)

    cart_manager = get_cart_manager()
    try:
        await cart_manager.update_item_quantity(
            user_telegram_id=user.id,
            product_id=request.product_id,
            new_quantity=request.quantity,
            available_stock=available_stock,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to update cart item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update cart item")

    cart = await cart_manager.get_cart(user.id)
    if not cart:
        return {"items": [], "total": 0, "total_usd": 0, "currency": "USD", "exchange_rate": 1.0}
    return await _format_cart_response(cart, db, user.id)


@router.delete("/cart/item")
async def remove_cart_item(
    product_id: str, user: Any = Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Remove item from cart."""
    from core.cart import get_cart_manager

    cart_manager = get_cart_manager()
    try:
        await cart_manager.remove_item(user.id, product_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to remove cart item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove cart item")

    db = get_database()
    cart = await cart_manager.get_cart(user.id)
    if not cart:
        return {"items": [], "total": 0, "total_usd": 0, "currency": "USD", "exchange_rate": 1.0}
    return await _format_cart_response(cart, db, user.id)


@router.post("/cart/promo/apply")
async def apply_cart_promo(
    request: ApplyPromoRequest, user: "TelegramUser" = Depends(verify_telegram_auth)
) -> dict[str, Any]:
    """Apply promo code to cart.

    Supports both cart-wide and product-specific promo codes:
    - If promo.product_id is NULL: applies to entire cart
    - If promo.product_id is set: applies only to that product in cart
    """
    from core.cart import get_cart_manager

    db = get_database()
    code = request.code.strip().upper()
    promo = await db.validate_promo_code(code)
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")

    product_id = promo.get("product_id")  # NULL = cart-wide, NOT NULL = product-specific

    # For product-specific promos, verify product is in cart
    if product_id:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user.id)
        if cart is None:
            raise HTTPException(status_code=400, detail=ERR_CART_EMPTY)

        # Check if product is in cart
        product_in_cart = any(item.product_id == product_id for item in cart.items)
        if not product_in_cart:
            raise HTTPException(
                status_code=400,
                detail=f"Promo code is valid only for product {product_id}, which is not in your cart",
            )

    cart_manager = get_cart_manager()
    try:
        cart = await cart_manager.apply_promo_code(
            user.id,  # user.id is telegram_id
            code,
            promo["discount_percent"],
            product_id=product_id,  # Pass product_id (can be None for cart-wide)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if cart is None:
        raise HTTPException(status_code=400, detail=ERR_CART_EMPTY)

    return await _format_cart_response(cart, db, user.id)  # user.id is telegram_id


@router.post("/cart/promo/remove")
async def remove_cart_promo(user: Any = Depends(verify_telegram_auth)) -> dict[str, Any]:
    """Remove promo code from cart."""
    from core.cart import get_cart_manager

    cart_manager = get_cart_manager()
    cart = await cart_manager.remove_promo_code(user.id)
    if cart is None:
        raise HTTPException(status_code=400, detail=ERR_CART_EMPTY)

    db = get_database()
    return await _format_cart_response(cart, db, user.id)
