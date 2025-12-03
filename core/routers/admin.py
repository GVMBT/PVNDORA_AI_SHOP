"""
Admin API Router

Admin-only endpoints for managing products, users, orders, and stock.
Requires Telegram Mini App authentication with admin privileges.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from src.services.database import get_database
from core.routers.deps import get_notification_service
from core.auth import verify_admin  # Uses Telegram initData + is_admin check

router = APIRouter(tags=["admin"])


# ==================== PYDANTIC MODELS ====================

class CreateProductRequest(BaseModel):
    name: str
    description: str
    price: float
    type: str = "subscription"
    fulfillment_time_hours: int = 0
    warranty_hours: int = 168
    instructions: str = ""
    msrp: Optional[float] = None
    duration_days: Optional[int] = None


class CreateFAQRequest(BaseModel):
    question: str
    answer: str
    language_code: str = "ru"
    category: str = "general"


class BanUserRequest(BaseModel):
    telegram_id: int
    ban: bool


class AddStockRequest(BaseModel):
    product_id: str
    content: str
    expires_at: Optional[str] = None
    supplier_id: Optional[str] = None


class BulkStockRequest(BaseModel):
    product_id: str
    items: List[str]
    expires_at: Optional[str] = None
    supplier_id: Optional[str] = None


class BroadcastRequest(BaseModel):
    message: str
    exclude_dnd: bool = True


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
                .eq("product_id", pid).eq("is_sold", False).execute()
        )
        p["stock_count"] = getattr(stock_result, 'count', 0) or 0
        products.append(p)
    
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


# ==================== ORDERS ====================

@router.get("/orders")
async def admin_get_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get all orders with optional filtering"""
    db = get_database()
    
    def execute_query():
        query = db.client.table("orders").select(
            "*, users(telegram_id, username, first_name), products(name)"
        ).order("created_at", desc=True).range(offset, offset + limit - 1)
        
        if status:
            query = query.eq("status", status)
        
        return query.execute()
    
    result = await asyncio.to_thread(execute_query)
    return {"orders": result.data if result.data else []}


# ==================== USERS ====================

@router.get("/users")
async def admin_get_users(
    limit: int = 50,
    offset: int = 0,
    admin=Depends(verify_admin)
):
    """Get all users"""
    db = get_database()
    
    result = db.client.table("users").select("*").order(
        "created_at", desc=True
    ).range(offset, offset + limit - 1).execute()
    
    return result.data


@router.get("/users/{telegram_id}")
async def admin_get_user(telegram_id: int, admin=Depends(verify_admin)):
    """Get specific user details"""
    db = get_database()
    user = await db.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.get_user_orders(user.id, limit=20)
    
    return {
        "user": user,
        "orders": orders
    }


@router.post("/users/ban")
async def admin_ban_user(request: BanUserRequest, admin=Depends(verify_admin)):
    """Ban or unban a user"""
    db = get_database()
    await db.ban_user(request.telegram_id, request.ban)
    
    return {"success": True, "banned": request.ban}


@router.post("/users/{telegram_id}/warning")
async def admin_add_warning(telegram_id: int, admin=Depends(verify_admin)):
    """Add warning to user (auto-ban after 3)"""
    db = get_database()
    new_count = await db.add_warning(telegram_id)
    
    return {
        "success": True,
        "warnings_count": new_count,
        "auto_banned": new_count >= 3
    }


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
        "is_sold": False
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
            "is_sold": False
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
            query = query.eq("is_sold", False)
        
        return query.execute()
    
    result = await asyncio.to_thread(execute_query)
    return {"stock": result.data if result.data else []}


# ==================== BROADCAST ====================

@router.post("/broadcast")
async def admin_broadcast(request: BroadcastRequest, admin=Depends(verify_admin)):
    """Send broadcast message to all users"""
    notification_service = get_notification_service()
    
    sent_count = await notification_service.send_broadcast(
        message=request.message,
        exclude_dnd=request.exclude_dnd
    )
    
    return {"success": True, "sent_count": sent_count}


# ==================== ANALYTICS ====================

@router.get("/analytics")
async def admin_get_analytics(
    days: int = 7,
    admin=Depends(verify_admin)
):
    """Get sales analytics"""
    db = get_database()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    start_iso = start_date.isoformat()
    
    def get_orders():
        return db.client.table("orders").select(
            "amount, status, created_at, products(name)"
        ).gte("created_at", start_iso).execute()
    
    orders_result = await asyncio.to_thread(get_orders)
    
    orders_data = orders_result.data if orders_result.data else []
    total_orders = len(orders_data)
    completed_orders = [o for o in orders_data if o.get("status") in ["delivered", "completed"]]
    total_revenue = sum(o.get("amount", 0) for o in completed_orders)
    avg_order_value = total_revenue / len(completed_orders) if completed_orders else 0
    
    product_counts = {}
    for o in orders_data:
        if o.get("products") and isinstance(o["products"], dict):
            product_name = o["products"].get("name", "Unknown")
            product_counts[product_name] = product_counts.get(product_name, 0) + 1
    
    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "period_days": days,
        "total_orders": total_orders,
        "completed_orders": len(completed_orders),
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "top_products": [{"name": p[0], "count": p[1]} for p in top_products]
    }


@router.get("/metrics/business")
async def admin_get_business_metrics(
    days: int = 30,
    admin=Depends(verify_admin)
):
    """Get comprehensive business metrics from views"""
    db = get_database()
    
    # Get daily metrics
    daily = await asyncio.to_thread(
        lambda: db.client.table("business_metrics").select("*").limit(days).execute()
    )
    
    # Get referral program metrics
    referral = await asyncio.to_thread(
        lambda: db.client.table("referral_program_metrics").select("*").single().execute()
    )
    
    # Get product metrics
    products = await asyncio.to_thread(
        lambda: db.client.table("product_metrics").select("*").limit(10).execute()
    )
    
    # Get retention cohorts
    retention = await asyncio.to_thread(
        lambda: db.client.table("retention_cohorts").select("*").limit(8).execute()
    )
    
    # Calculate summary
    daily_data = daily.data or []
    summary = {
        "total_revenue": sum(d.get("revenue", 0) for d in daily_data),
        "total_orders": sum(d.get("completed_orders", 0) for d in daily_data),
        "total_new_users": sum(d.get("new_users", 0) for d in daily_data),
        "avg_daily_revenue": sum(d.get("revenue", 0) for d in daily_data) / len(daily_data) if daily_data else 0,
        "avg_conversion_rate": sum(d.get("order_conversion_rate", 0) for d in daily_data) / len(daily_data) if daily_data else 0,
        "avg_order_value": sum(d.get("avg_order_value", 0) for d in daily_data) / len([d for d in daily_data if d.get("avg_order_value", 0) > 0]) if any(d.get("avg_order_value", 0) > 0 for d in daily_data) else 0
    }
    
    return {
        "period_days": days,
        "summary": summary,
        "daily_metrics": daily_data,
        "referral_metrics": referral.data if referral.data else {},
        "product_metrics": products.data or [],
        "retention_cohorts": retention.data or []
    }


@router.get("/metrics/referral")
async def admin_get_referral_metrics(admin=Depends(verify_admin)):
    """Get detailed referral program metrics"""
    db = get_database()
    
    # Get overall stats
    stats = await asyncio.to_thread(
        lambda: db.client.table("referral_program_metrics").select("*").single().execute()
    )
    
    # Get extended stats for top referrers
    top_referrers = await asyncio.to_thread(
        lambda: db.client.table("referral_stats_extended").select("*").order("total_referral_earnings", desc=True).limit(20).execute()
    )
    
    return {
        "overview": stats.data if stats.data else {},
        "top_referrers": top_referrers.data or []
    }


# ==================== SUPPORT TICKETS ====================

@router.get("/tickets")
async def admin_get_tickets(
    status: Optional[str] = None,
    admin=Depends(verify_admin)
):
    """Get support tickets"""
    db = get_database()
    
    query = db.client.table("support_tickets").select(
        "*, users(telegram_id, username)"
    ).order("created_at", desc=True)
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    return {"tickets": result.data if result.data else []}


@router.post("/tickets/{ticket_id}/resolve")
async def admin_resolve_ticket(
    ticket_id: str,
    resolution: str = "resolved",
    admin=Depends(verify_admin)
):
    """Resolve a support ticket"""
    db = get_database()
    
    ticket = db.client.table("support_tickets").select(
        "*, users(telegram_id), orders(id)"
    ).eq("id", ticket_id).single().execute()
    
    if not ticket.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    db.client.table("support_tickets").update({
        "status": "resolved",
        "resolution": resolution,
        "resolved_at": datetime.utcnow().isoformat()
    }).eq("id", ticket_id).execute()
    
    return {"success": True, "ticket_id": ticket_id}


# ==================== RAG INDEX ====================

@router.post("/index-products")
async def admin_index_products(authorization: str = Header(None)):
    """Index all products for RAG (semantic search)"""
    cron_secret = os.environ.get("CRON_SECRET", "")
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        from core.rag import get_product_search
        search = get_product_search()
        
        if not search.is_available:
            return {"success": False, "error": "RAG not available"}
        
        indexed = await search.index_all_products()
        return {"success": True, "indexed_products": indexed}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


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

