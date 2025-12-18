"""
Admin Products & Stock Router

Product and stock management endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from core.services.database import get_database
from core.auth import verify_admin
from core.routers.deps import get_notification_service
from .models import CreateProductRequest, AddStockRequest, BulkStockRequest

router = APIRouter(tags=["admin-products"])


# ==================== PRODUCTS ====================

@router.post("/products")
async def admin_create_product(request: CreateProductRequest, admin=Depends(verify_admin)):
    """Create a new product"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("products").insert({
            "name": request.name,
            "description": request.description,
            "price": request.price,
            "type": request.type,
            "fulfillment_time_hours": request.fulfillment_time_hours,
            "warranty_hours": request.warranty_hours,
            "instructions": request.instructions,
            "msrp": request.msrp,
            "duration_days": request.duration_days,
            "status": "active"
        }).execute()
    )
    
    if result.data:
        return {"success": True, "product": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create product")


@router.get("/products")
async def admin_get_products(admin=Depends(verify_admin)):
    """Get all products for admin (including inactive)"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("products").select("*").order("created_at", desc=True).execute()
    )
    
    if not result.data:
        return {"products": []}
    
    products = []
    for p in result.data:
        product_id = p["id"]
        stock_result = await asyncio.to_thread(
            lambda pid=product_id: db.client.table("stock_items").select("id", count="exact")
                .eq("product_id", pid).eq("status", "available").execute()
        )
        stock_count = getattr(stock_result, 'count', 0) or 0
        
        # Get sold count
        sold_result = await asyncio.to_thread(
            lambda pid=product_id: db.client.table("stock_items").select("id", count="exact")
                .eq("product_id", pid).eq("status", "sold").execute()
        )
        sold_count = getattr(sold_result, 'count', 0) or 0
        
        # Map fields for frontend compatibility
        products.append({
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "category": p.get("type", "ai"),  # type -> category
            "price": float(p.get("price", 0)),
            "msrp": float(p.get("msrp") or p.get("price", 0)),
            "type": "instant" if p.get("fulfillment_type") == "auto" else "preorder",
            "stock": stock_count,
            "fulfillment": p.get("fulfillment_time_hours", 1),
            "warranty": p.get("warranty_hours", 168),
            "duration": p.get("duration_days", 30),
            "sold": sold_count,
            "status": p.get("status", "active"),
            "vpn": False,  # TODO: add to DB if needed
            "image": p.get("image_url"),
            "instructions": p.get("instructions", ""),
            "created_at": p.get("created_at")
        })
    
    return {"products": products}


@router.put("/products/{product_id}")
async def admin_update_product(product_id: str, request: CreateProductRequest, admin=Depends(verify_admin)):
    """Update a product"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("products").update({
            "name": request.name,
            "description": request.description,
            "price": request.price,
            "type": request.type,
            "fulfillment_time_hours": request.fulfillment_time_hours,
            "warranty_hours": request.warranty_hours,
            "instructions": request.instructions,
            "msrp": request.msrp,
            "duration_days": request.duration_days
        }).eq("id", product_id).execute()
    )
    
    return {"success": True, "updated": len(result.data) > 0}


@router.delete("/products/{product_id}")
async def admin_delete_product(product_id: str, admin=Depends(verify_admin)):
    """Permanently delete a product from database"""
    db = get_database()
    
    # Check if product has sold stock (cannot delete - has order history)
    sold_check = await asyncio.to_thread(
        lambda: db.client.table("stock_items").select("id", count="exact")
            .eq("product_id", product_id).eq("status", "sold").execute()
    )
    sold_count = getattr(sold_check, 'count', 0) or 0
    
    if sold_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete product with {sold_count} sold items (order history exists)."
        )
    
    # Delete all stock items for this product first (FK constraint)
    await asyncio.to_thread(
        lambda: db.client.table("stock_items").delete()
            .eq("product_id", product_id).execute()
    )
    
    # Delete the product
    result = await asyncio.to_thread(
        lambda: db.client.table("products").delete()
            .eq("id", product_id).execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"success": True, "deleted": True}


# ==================== STOCK ====================

@router.post("/stock")
async def admin_add_stock(request: AddStockRequest, admin=Depends(verify_admin)):
    """Add single stock item for a product"""
    db = get_database()
    
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    data = {
        "product_id": request.product_id,
        "content": request.content,
        "status": "available"
    }
    
    if request.expires_at:
        data["expires_at"] = request.expires_at
    if request.supplier_id:
        data["supplier_id"] = request.supplier_id
    
    result = db.client.table("stock_items").insert(data).execute()
    
    await _notify_waitlist_for_product(db, product.name)
    
    return {"success": True, "stock_item": result.data[0]}


@router.post("/stock/bulk")
async def admin_add_stock_bulk(request: BulkStockRequest, admin=Depends(verify_admin)):
    """Bulk add stock items for a product"""
    db = get_database()
    
    product = await db.get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    items_data = []
    for content in request.items:
        content = content.strip()
        if not content:
            continue
            
        item = {
            "product_id": request.product_id,
            "content": content,
            "status": "available"
        }
        if request.expires_at:
            item["expires_at"] = request.expires_at
        if request.supplier_id:
            item["supplier_id"] = request.supplier_id
        
        items_data.append(item)
    
    if not items_data:
        raise HTTPException(status_code=400, detail="No valid items provided")
    
    result = db.client.table("stock_items").insert(items_data).execute()
    
    await _notify_waitlist_for_product(db, product.name, request.product_id)
    
    return {
        "success": True,
        "added_count": len(result.data),
        "product_name": product.name
    }


@router.get("/stock")
async def admin_get_stock(
    product_id: Optional[str] = None,
    available_only: bool = True,
    admin=Depends(verify_admin)
):
    """Get stock items"""
    db = get_database()
    
    def execute_query():
        query = db.client.table("stock_items").select(
            "*, products(name)"
        ).order("created_at", desc=True)
        
        if product_id:
            query = query.eq("product_id", product_id)
        if available_only:
            query = query.eq("status", "available")
        
        return query.execute()
    
    result = await asyncio.to_thread(execute_query)
    return {"stock": result.data if result.data else []}


# ==================== HELPERS ====================

async def _notify_waitlist_for_product(db, product_name: str, product_id: Optional[str] = None):
    """Notify users on waitlist when product becomes available"""
    waitlist = db.client.table("waitlist").select(
        "id,user_id,users(telegram_id,language_code)"
    ).ilike("product_name", f"%{product_name}%").execute()
    
    if not waitlist.data:
        return
    
    in_stock = False
    if product_id:
        product = await db.get_product_by_id(product_id)
        if product:
            in_stock = product.stock_count > 0
    
    notification_service = get_notification_service()
    
    for item in waitlist.data:
        user = item.get("users")
        if user:
            await notification_service.send_waitlist_notification(
                telegram_id=user["telegram_id"],
                product_name=product_name,
                language=user.get("language_code", "en"),
                product_id=product_id,
                in_stock=in_stock
            )
            
            db.client.table("waitlist").delete().eq("id", item["id"]).execute()
