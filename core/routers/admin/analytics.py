"""
Admin Analytics Router

Sales analytics and business metrics endpoints.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""
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
    
    # Execute all queries directly with await
    revenue_result = await db.client.table("orders").select(
        "amount"
    ).eq("status", "delivered").execute()
    
    orders_today_result = await db.client.table("orders").select(
        "id", count="exact"
    ).gte("created_at", today_start.isoformat()).execute()
    
    orders_week_result = await db.client.table("orders").select(
        "id", count="exact"
    ).gte("created_at", week_start.isoformat()).execute()
    
    orders_month_result = await db.client.table("orders").select(
        "id", count="exact"
    ).gte("created_at", month_start.isoformat()).execute()
    
    total_users_result = await db.client.table("users").select(
        "id", count="exact"
    ).execute()
    
    pending_orders_result = await db.client.table("orders").select(
        "id", count="exact"
    ).in_("status", ["pending", "paid", "processing"]).execute()
    
    open_tickets_result = await db.client.table("tickets").select(
        "id", count="exact"
    ).eq("status", "open").execute()
    
    revenue_by_day_result = await db.client.table("orders").select(
        "amount, created_at"
    ).eq("status", "delivered").gte("created_at", chart_days_start.isoformat()).execute()
    
    top_products_result = await db.client.table("order_items").select(
        "products(name)"
    ).eq("status", "delivered").execute()
    
    user_balances_result = await db.client.table("users").select("balance").execute()
    
    pending_withdrawals_result = await db.client.table("withdrawal_requests").select(
        "amount"
    ).eq("status", "pending").execute()
    
    # Calculate total revenue
    total_revenue = sum(float(o.get("amount", 0)) for o in (revenue_result.data or []))
    
    # Count orders
    orders_today = orders_today_result.count or 0
    orders_this_week = orders_week_result.count or 0
    orders_this_month = orders_month_result.count or 0
    
    # Total users (all registered)
    total_users = total_users_result.count or 0
    
    # Pending orders (active/unfulfilled)
    pending_orders = pending_orders_result.count or 0
    
    # Count open tickets
    open_tickets = open_tickets_result.count or 0
    
    # Calculate total user balances (liabilities)
    total_user_balances = sum(float(u.get("balance", 0)) for u in (user_balances_result.data or []))
    
    # Calculate pending withdrawals
    pending_withdrawals = sum(float(w.get("amount", 0)) for w in (pending_withdrawals_result.data or []))
    
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
        "total_users": total_users,
        "pending_orders": pending_orders,
        "revenue_by_day": revenue_by_day,
        "open_tickets": open_tickets,
        "top_products": top_products,
        # Liabilities metrics
        "total_user_balances": total_user_balances,
        "pending_withdrawals": pending_withdrawals,
    }


@router.get("/metrics/business")
async def admin_get_business_metrics(
    days: int = 30,
    admin=Depends(verify_admin)
):
    """Get comprehensive business metrics from views"""
    db = get_database()
    
    # Get daily metrics
    daily = await db.client.table("business_metrics").select("*").limit(days).execute()
    
    # Get referral program metrics
    referral = await db.client.table("referral_program_metrics").select("*").single().execute()
    
    # Get product metrics
    products = await db.client.table("product_metrics").select("*").limit(10).execute()
    
    # Get retention cohorts
    retention = await db.client.table("retention_cohorts").select("*").limit(8).execute()
    
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


@router.get("/analytics/discount")
async def admin_get_discount_analytics(
    days: int = 30,
    admin=Depends(verify_admin)
):
    """Get discount channel analytics and migration funnel metrics."""
    db = get_database()
    
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    
    # 1. Migration stats from view
    migration_stats = await db.client.table("discount_migration_stats").select("*").execute()
    
    # 2. Discount orders stats
    discount_orders = await db.client.table("orders").select(
        "id, amount, status, created_at", count="exact"
    ).eq("source_channel", "discount").gte(
        "created_at", period_start.isoformat()
    ).execute()
    
    # 3. Insurance sales
    insurance_items = await db.client.table("order_items").select(
        "id, insurance_id", count="exact"
    ).not_.is_("insurance_id", "null").execute()
    
    # 4. Replacement stats
    replacements_pending = await db.client.table("insurance_replacements").select(
        "id", count="exact"
    ).eq("status", "pending").execute()
    
    replacements_approved = await db.client.table("insurance_replacements").select(
        "id", count="exact"
    ).in_("status", ["approved", "auto_approved"]).gte(
        "created_at", period_start.isoformat()
    ).execute()
    
    replacements_rejected = await db.client.table("insurance_replacements").select(
        "id", count="exact"
    ).eq("status", "rejected").gte(
        "created_at", period_start.isoformat()
    ).execute()
    
    # 5. Promo code stats by trigger
    promo_stats = await db.client.table("promo_codes").select(
        "source_trigger, current_uses"
    ).not_.is_("source_trigger", "null").execute()
    
    # Aggregate promo stats by trigger
    promo_by_trigger = {}
    for p in (promo_stats.data or []):
        trigger = p.get("source_trigger", "unknown")
        if trigger not in promo_by_trigger:
            promo_by_trigger[trigger] = {"count": 0, "used": 0}
        promo_by_trigger[trigger]["count"] += 1
        promo_by_trigger[trigger]["used"] += p.get("current_uses", 0)
    
    # 6. Top abusers
    # Get users with high abuse scores
    discount_users = await db.client.table("users").select(
        "telegram_id"
    ).eq("discount_tier_source", True).limit(100).execute()
    
    top_abusers = []
    for user in (discount_users.data or [])[:20]:  # Check first 20
        tid = user["telegram_id"]
        score_result = await db.client.rpc(
            "get_user_abuse_score",
            {"p_telegram_id": tid}
        ).execute()
        score = score_result.data if score_result.data else 0
        if score > 30:  # Only include if above threshold
            top_abusers.append({"telegram_id": tid, "abuse_score": score})
    
    top_abusers.sort(key=lambda x: x["abuse_score"], reverse=True)
    
    # Calculate totals
    discount_orders_data = discount_orders.data or []
    total_discount_revenue = sum(
        o.get("amount", 0) for o in discount_orders_data 
        if o.get("status") == "delivered"
    )
    total_discount_orders = len([o for o in discount_orders_data if o.get("status") == "delivered"])
    
    return {
        "period_days": days,
        "migration": migration_stats.data[0] if migration_stats.data else {},
        "discount_channel": {
            "total_orders": discount_orders.count if discount_orders.count else 0,
            "delivered_orders": total_discount_orders,
            "revenue": round(total_discount_revenue, 2),
            "avg_order_value": round(total_discount_revenue / max(total_discount_orders, 1), 2)
        },
        "insurance": {
            "items_with_insurance": insurance_items.count if insurance_items.count else 0,
            "insurance_rate": round(
                (insurance_items.count or 0) / max(discount_orders.count or 1, 1) * 100, 1
            )
        },
        "replacements": {
            "pending": replacements_pending.count if replacements_pending.count else 0,
            "approved": replacements_approved.count if replacements_approved.count else 0,
            "rejected": replacements_rejected.count if replacements_rejected.count else 0
        },
        "promo_codes": promo_by_trigger,
        "top_abusers": top_abusers[:10]
    }
