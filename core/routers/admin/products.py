"""Admin Products & Stock Router.

Product and stock management endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from core.auth import verify_admin
from core.routers.deps import get_notification_service
from core.services.database import get_database

from .models import AddStockRequest, BulkStockRequest, CreateProductRequest

# Error message constants
ERR_PRODUCT_NOT_FOUND = "Product not found"

# Valid values for constrained fields
VALID_STATUSES = {"active", "inactive", "out_of_stock", "discontinued", "coming_soon"}
VALID_TYPES = {"ai", "design", "dev", "music"}
VALID_FULFILLMENT_TYPES = {"auto", "manual"}

router = APIRouter(tags=["admin-products"])


def _validate_product_data(request: CreateProductRequest) -> dict[str, Any]:
    """Validate and prepare product data for database operations.

    Validates constrained fields (status, type, fulfillment_type) against
    allowed values and normalizes them (strip whitespace, lowercase).

    Returns:
        Dict with validated and prepared data ready for DB insert/update.

    Raises:
        HTTPException: If any field has an invalid value.
    """
    # Normalize and validate status
    status = (request.status or "active").strip().lower()
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{request.status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}",
        )

    # Normalize and validate type (category in frontend)
    product_type = (request.category or "ai").strip().lower()
    if product_type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{request.category}'. Allowed: {', '.join(sorted(VALID_TYPES))}",
        )

    # Normalize and validate fulfillment_type
    fulfillment_type = (request.fulfillmentType or "auto").strip().lower()
    if fulfillment_type not in VALID_FULFILLMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fulfillmentType '{request.fulfillmentType}'. Allowed: {', '.join(sorted(VALID_FULFILLMENT_TYPES))}",
        )

    return {
        "name": request.name,
        "description": request.description,
        # Category → type in DB
        "type": product_type,
        # Pricing
        "price": request.price,  # Base USD price
        "prices": request.prices or {},  # Anchor prices (JSONB)
        "msrp": request.msrp or request.price,  # MSRP in RUB
        "discount_price": request.discountPrice,
        "cost_price": request.costPrice,
        # Fulfillment
        "fulfillment_type": fulfillment_type,
        "fulfillment_time_hours": request.fulfillment,
        # Product Settings
        "warranty_hours": request.warranty,
        "duration_days": request.duration,
        "status": status,
        # Media
        "image_url": request.image,
        # Content
        "instructions": request.instructions,
    }


# ==================== PRODUCTS ====================


@router.post("/products")
async def admin_create_product(
    request: CreateProductRequest, admin: Any = Depends(verify_admin)
) -> dict[str, Any]:
    """Create a new product."""
    db = get_database()

    # Validate and prepare product data
    product_data = _validate_product_data(request)

    try:
        result = await db.client.table("products").insert(product_data).execute()

        if result.data:
            return {"success": True, "product": result.data[0]}
        raise HTTPException(status_code=500, detail="Failed to create product")
    except APIError as e:
        # Handle database constraint violations with helpful messages
        error_msg = str(e.message) if hasattr(e, "message") else str(e)
        if "check constraint" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Database constraint violation: {error_msg}. Check field values.",
            ) from e
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}") from e


@router.get("/products")
async def admin_get_products(admin: Any = Depends(verify_admin)) -> dict[str, Any]:
    """Get all products for admin (including inactive).

    Uses products_with_stock_summary VIEW to eliminate N+1 queries.
    Single query returns all products with stock_count and sold_count.
    """
    db = get_database()

    # Use VIEW for aggregated stock data (no N+1!)
    result = (
        await db.client.table("products_with_stock_summary")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    if not result.data:
        return {"products": []}

    products = []
    for p in result.data:
        # Stock counts from VIEW (already aggregated)
        stock_count = p.get("stock_count", 0) or 0
        sold_count = p.get("sold_count", 0) or 0

        # Map fields for frontend compatibility
        products.append(
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
                # Category (type in DB → category in frontend)
                "category": p.get("type", "ai"),
                # Pricing
                "price": float(p.get("price", 0)),  # Price in RUB
                "prices": p.get("prices") or {},  # Anchor prices (JSONB) - DEPRECATED
                "msrp": float(p.get("msrp") or p.get("price", 0)),  # MSRP in RUB
                "discountPrice": float(p.get("discount_price") or 0),
                "costPrice": float(p.get("cost_price") or 0),
                # Fulfillment
                "fulfillmentType": p.get("fulfillment_type", "auto"),
                "fulfillment": p.get("fulfillment_time_hours", 1),
                # Product Settings
                "warranty": p.get("warranty_hours", 168),
                "duration": p.get("duration_days", 30),
                "status": p.get("status", "active"),
                # Stock (read-only, from VIEW)
                "stock": stock_count,
                "sold": sold_count,
                # Media
                "image": p.get("image_url"),
                "video": p.get("video_url"),  # Video URL from DB if available
                # Content
                "instructions": p.get("instructions", ""),
                # Timestamps
                "created_at": p.get("created_at"),
            },
        )

    return {"products": products}


@router.put("/products/{product_id}")
async def admin_update_product(
    product_id: str,
    request: CreateProductRequest,
    admin: Any = Depends(verify_admin),
) -> dict[str, Any]:
    """Update a product."""
    db = get_database()

    # Validate and prepare update data
    update_data = _validate_product_data(request)

    try:
        result = await db.client.table("products").update(update_data).eq("id", product_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=ERR_PRODUCT_NOT_FOUND)

        return {"success": True, "updated": True, "product": result.data[0]}
    except APIError as e:
        # Handle database constraint violations with helpful messages
        error_msg = str(e.message) if hasattr(e, "message") else str(e)
        if "check constraint" in error_msg.lower():
            # Extract which constraint failed for better error message
            constraint_info = ""
            if "status_check" in error_msg.lower():
                constraint_info = f" Valid statuses: {', '.join(sorted(VALID_STATUSES))}."
            elif "type_check" in error_msg.lower():
                constraint_info = f" Valid types: {', '.join(sorted(VALID_TYPES))}."
            elif "fulfillment_type_check" in error_msg.lower():
                constraint_info = f" Valid fulfillment types: {', '.join(sorted(VALID_FULFILLMENT_TYPES))}."

            raise HTTPException(
                status_code=400,
                detail=f"Invalid field value.{constraint_info} Original error: {error_msg}",
            ) from e
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}") from e


@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: str, admin: Any = Depends(verify_admin)
) -> dict[str, Any]:
    """Permanently delete a product from database."""
    db = get_database()

    # Check if product has sold stock (cannot delete - has order history)
    sold_check = (
        await db.client.table("stock_items")
        .select("id", count="exact")
        .eq("product_id", product_id)
        .eq("status", "sold")
        .execute()
    )
    sold_count = getattr(sold_check, "count", 0) or 0

    if sold_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete product with {sold_count} sold items (order history exists).",
        )

    # Delete all stock items for this product first (FK constraint)
    await db.client.table("stock_items").delete().eq("product_id", product_id).execute()

    # Delete the product
    result = await db.client.table("products").delete().eq("id", product_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=ERR_PRODUCT_NOT_FOUND)

    return {"success": True, "deleted": True}


# ==================== STOCK ====================


@router.post("/stock")
async def admin_add_stock(
    request: AddStockRequest, admin: Any = Depends(verify_admin)
) -> dict[str, Any]:
    """Add single stock item for a product."""
    db = get_database()

    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=ERR_PRODUCT_NOT_FOUND)

    data = {"product_id": request.product_id, "content": request.content, "status": "available"}

    if request.expires_at:
        data["expires_at"] = request.expires_at
    if request.supplier_id:
        data["supplier_id"] = request.supplier_id

    result = await db.client.table("stock_items").insert(data).execute()

    await _notify_waitlist_for_product(db, product.name)

    return {"success": True, "stock_item": result.data[0]}


@router.post("/stock/bulk")
async def admin_add_stock_bulk(
    request: BulkStockRequest, admin: Any = Depends(verify_admin)
) -> dict[str, Any]:
    """Bulk add stock items for a product."""
    db = get_database()

    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail=ERR_PRODUCT_NOT_FOUND)

    items_data = []
    for content in request.items:
        content = content.strip()
        if not content:
            continue

        item = {"product_id": request.product_id, "content": content, "status": "available"}
        if request.expires_at:
            item["expires_at"] = request.expires_at
        if request.supplier_id:
            item["supplier_id"] = request.supplier_id

        items_data.append(item)

    if not items_data:
        raise HTTPException(status_code=400, detail="No valid items provided")

    result = await db.client.table("stock_items").insert(items_data).execute()

    await _notify_waitlist_for_product(db, product.name, request.product_id)

    return {"success": True, "added_count": len(result.data), "product_name": product.name}


@router.get("/stock")
async def admin_get_stock(
    product_id: str | None = None,
    available_only: bool = True,
    admin=Depends(verify_admin),
):
    """Get stock items."""
    db = get_database()

    query = (
        db.client.table("stock_items").select("*, products(name)").order("created_at", desc=True)
    )

    if product_id:
        query = query.eq("product_id", product_id)
    if available_only:
        query = query.eq("status", "available")

    result = await query.execute()
    return {"stock": result.data if result.data else []}


@router.delete("/stock/{stock_item_id}")
async def admin_delete_stock(
    stock_item_id: str, admin: Any = Depends(verify_admin)
) -> dict[str, Any]:
    """Delete a stock item."""
    db = get_database()

    # Check if stock item exists
    stock_result = (
        await db.client.table("stock_items")
        .select("id, status")
        .eq("id", stock_item_id)
        .single()
        .execute()
    )

    if not stock_result.data:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Only allow deletion of available items (safety check)
    if stock_result.data.get("status") != "available":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete stock item with status '{stock_result.data.get('status')}'",
        )

    # Delete the stock item
    await db.client.table("stock_items").delete().eq("id", stock_item_id).execute()

    return {"success": True, "deleted": True}


# ==================== HELPERS ====================


async def _notify_waitlist_for_product(
    db: Any, product_name: str, product_id: str | None = None
) -> None:
    """Notify users on waitlist when product becomes available."""
    waitlist = (
        await db.client.table("waitlist")
        .select("id,user_id,users(telegram_id,language_code)")
        .ilike("product_name", f"%{product_name}%")
        .execute()
    )

    if not waitlist.data:
        return

    in_stock = False
    if product_id:
        product = await db.get_product_by_id(product_id)
        if product:
            in_stock = product.stock_count > 0

    notification_service = get_notification_service()

    # Collect IDs for batch delete (avoid N+1)
    waitlist_ids_to_delete = []

    for item in waitlist.data:
        user = item.get("users")
        if user:
            await notification_service.send_waitlist_notification(
                telegram_id=user["telegram_id"],
                product_name=product_name,
                language=user.get("language_code", "en"),
                _product_id=product_id,
                in_stock=in_stock,
            )
            waitlist_ids_to_delete.append(item["id"])

    # Batch delete all notified items at once
    if waitlist_ids_to_delete:
        await db.client.table("waitlist").delete().in_("id", waitlist_ids_to_delete).execute()
