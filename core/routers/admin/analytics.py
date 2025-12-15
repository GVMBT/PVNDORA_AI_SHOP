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
    """Get comprehensive sales analytics with real data from database"""
    db = get_database()
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    chart_days_start = today_start - timedelta(days=12)  # Last 12 days for chart
    
    # 1. Total Revenue (all time, only delivered orders)
    def get_total_revenue():
        return db.client.table("orders").select(
            "amount"
        ).eq("status", "delivered").execute()
    
    # 2. Orders today
    def get_orders_today():
        return db.client.table("orders").select(
            "id", count="exact"
        ).gte("created_at", today_start.isoformat()).execute()
    
    # 3. Orders this week
    def get_orders_week():
        return db.client.table("orders").select(
            "id", count="exact"
        ).gte("created_at", week_start.isoformat()).execute()
    
    # 4. Orders this month
    def get_orders_month():
        return db.client.table("orders").select(
            "id", count="exact"
        ).gte("created_at", month_start.isoformat()).execute()
    
    # 5. Active users (users with orders in last 30 days)
    def get_active_users():
        return db.client.table("orders").select(
            "user_id"
        ).gte("created_at", month_start.isoformat()).execute()
    
    # 7. Open tickets count
    def get_open_tickets():
        return db.client.table("tickets").select(
            "id", count="exact"
        ).eq("status", "open").execute()
    
    # 6. Revenue by day (last 12 days for chart)
    def get_revenue_by_day():
        return db.client.table("orders").select(
            "amount, created_at"
        ).eq("status", "delivered").gte("created_at", chart_days_start.isoformat()).execute()
    
    # 8. Top products (all time)
    def get_top_products():
        return db.client.table("orders").select(
            "products(name)"
        ).eq("status", "delivered").execute()
    
    # Execute all queries
    revenue_result = await asyncio.to_thread(get_total_revenue)
    orders_today_result = await asyncio.to_thread(get_orders_today)
    orders_week_result = await asyncio.to_thread(get_orders_week)
    orders_month_result = await asyncio.to_thread(get_orders_month)
    active_users_result = await asyncio.to_thread(get_active_users)
    revenue_by_day_result = await asyncio.to_thread(get_revenue_by_day)
    open_tickets_result = await asyncio.to_thread(get_open_tickets)
    top_products_result = await asyncio.to_thread(get_top_products)
    
    # Calculate total revenue
    total_revenue = sum(float(o.get("amount", 0)) for o in (revenue_result.data or []))
    
    # Count orders (use count from result for accuracy)
    orders_today = orders_today_result.count or 0
    orders_this_week = orders_week_result.count or 0
    orders_this_month = orders_month_result.count or 0
    
    # Count active users (unique user_ids)
    active_user_ids = set()
    for o in (active_users_result.data or []):
        user_id = o.get("user_id")
        if user_id:
            active_user_ids.add(user_id)
    active_users = len(active_user_ids)
    
    # Count open tickets
    open_tickets = open_tickets_result.count or 0
    
    # Calculate revenue by day for chart
    revenue_by_day_map = {}
    for o in (revenue_by_day_result.data or []):
        created_at = o.get("created_at")
        if created_at:
            # Parse date and get date string (YYYY-MM-DD)
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%Y-%m-%d')
                amount = float(o.get("amount", 0))
                revenue_by_day_map[date_str] = revenue_by_day_map.get(date_str, 0) + amount
            except (ValueError, AttributeError):
                continue
    
    # Sort by date and format for frontend
    revenue_by_day = [
        {"date": date, "amount": amount}
        for date, amount in sorted(revenue_by_day_map.items())
    ]
    
    # Calculate top products
    product_counts = {}
    for o in (top_products_result.data or []):
        products = o.get("products")
        if products and isinstance(products, dict):
            product_name = products.get("name", "Unknown")
            product_counts[product_name] = product_counts.get(product_name, 0) + 1
    
    top_products = [
        {"name": name, "sales": count, "revenue": 0}  # revenue can be calculated separately if needed
        for name, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return {
        "total_revenue": total_revenue,
        "orders_today": orders_today,
        "orders_this_week": orders_this_week,
        "orders_this_month": orders_this_month,
        "active_users": active_users,
        "revenue_by_day": revenue_by_day,
        "open_tickets": open_tickets,
        "top_products": top_products
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
