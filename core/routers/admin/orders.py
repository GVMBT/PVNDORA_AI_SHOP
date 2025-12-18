"""
Admin Orders & FAQ Router

Order and FAQ management endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from core.services.database import get_database
from core.auth import verify_admin
from .models import CreateFAQRequest

router = APIRouter(tags=["admin-orders"])


# ==================== ORDERS ====================

@router.get("/orders")
async def admin_get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get all orders with optional filtering - formatted for admin panel"""
    db = get_database()
    
    def execute_query():
        query = db.client.table("orders").select(
            "id, status, amount, payment_method, payment_gateway, created_at, "
            "users(telegram_id, username, first_name), "
            "order_items(product_id, product_name, quantity)"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)
        
        if status:
            query = query.eq("status", status)
        
        return query.execute()
    
    result = await asyncio.to_thread(execute_query)
    orders_data = result.data if result.data else []
    
    # Format orders for admin panel (matching mock data structure)
    formatted_orders = []
    for order in orders_data:
        # Get user handle
        user_data = order.get("users") or {}
        username = user_data.get("username") or user_data.get("first_name", "Unknown")
        user_handle = f"@{username}" if username != "Unknown" else "Unknown"
        
        # Get product name from order_items
        items = order.get("order_items", [])
        product_name = "Unknown Product"
        if items and len(items) > 0:
            product_name = items[0].get("product_name", "Unknown Product")
            if len(items) > 1:
                product_name += f" +{len(items)-1}"
        
        created_at = order.get("created_at")
        
        formatted_orders.append({
            "id": order.get("id"),  # Full UUID for API compatibility
            "user_id": user_data.get("telegram_id"),
            "user_handle": user_handle,
            "product_name": product_name,
            "amount": float(order.get("amount", 0)),
            "status": order.get("status", "pending"),
            "payment_method": order.get("payment_method", "unknown"),
            "created_at": created_at
        })
    
    return {"orders": formatted_orders}


# ==================== FAQ ====================

@router.post("/faq")
async def admin_create_faq(request: CreateFAQRequest, admin=Depends(verify_admin)):
    """Create a FAQ entry"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("faq").insert({
            "question": request.question,
            "answer": request.answer,
            "language_code": request.language_code,
            "category": request.category,
            "is_active": True
        }).execute()
    )
    
    if result.data:
        return {"success": True, "faq": result.data[0]}
    raise HTTPException(status_code=500, detail="Failed to create FAQ")


@router.get("/faq")
async def admin_get_faq(admin=Depends(verify_admin)):
    """Get all FAQ entries for admin"""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("faq").select("*").order("language_code").order("category").execute()
    )
    
    return {"faq": result.data}
