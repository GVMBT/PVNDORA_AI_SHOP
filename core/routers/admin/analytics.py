"""
Admin Analytics Router

Sales analytics and business metrics endpoints.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from core.services.database import get_database
from core.auth import verify_admin

router = APIRouter(tags=["admin-analytics"])


@router.get("/analytics")
async def admin_get_analytics(
    days: int = 7,
    admin=Depends(verify_admin)
):
    """Get sales analytics"""
    db = get_database()
    
    end_date = datetime.now(timezone.utc)
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
