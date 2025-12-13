"""
Admin Orders & FAQ Router

Order and FAQ management endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from src.services.database import get_database
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
    from datetime import datetime, timezone
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
        
        # Format date (relative time like "10m ago")
        created_at = order.get("created_at")
        date_str = "Unknown"
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                diff = now - created_dt
                
                if diff.total_seconds() < 60:
                    date_str = f"{int(diff.total_seconds())}s ago"
                elif diff.total_seconds() < 3600:
                    date_str = f"{int(diff.total_seconds() / 60)}m ago"
                elif diff.total_seconds() < 86400:
                    date_str = f"{int(diff.total_seconds() / 3600)}h ago"
                else:
                    date_str = f"{int(diff.total_seconds() / 86400)}d ago"
            except:
                date_str = created_at[:10]  # Fallback to date
        
        # Format payment method
        payment_method = order.get("payment_method", "").upper()
        payment_gateway = order.get("payment_gateway", "")
        if payment_gateway:
            method_display = payment_gateway.upper()
        elif payment_method == "BALANCE":
            method_display = "INTERNAL"
        else:
            method_display = payment_method or "UNKNOWN"
        
        # Format order ID (short format like "ORD-9921")
        order_id_short = order.get("id", "")[:8].upper().replace("-", "")
        order_id_display = f"ORD-{order_id_short[:4]}" if len(order_id_short) >= 4 else f"ORD-{order_id_short}"
        
        # Format status (uppercase like "PAID", "REFUNDED")
        status_display = order.get("status", "PENDING").upper()
        
        formatted_orders.append({
            "id": order_id_display,
            "user": user_handle,
            "product": product_name,
            "amount": float(order.get("amount", 0)),
            "status": status_display,
            "date": date_str,
            "method": method_display
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
