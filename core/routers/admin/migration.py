"""
Admin Migration Analytics API

Provides statistics on discount bot users migrating to PVNDORA.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.security.admin_auth import verify_admin_user
from core.services.database import get_database

router = APIRouter(prefix="/migration", tags=["admin"])


# ============================================
# Models
# ============================================

class MigrationStats(BaseModel):
    """Overall migration statistics."""
    # User counts
    total_discount_users: int = 0
    total_pvndora_users: int = 0
    migrated_users: int = 0  # Users with orders in both channels
    migration_rate: float = 0.0  # migrated / discount_users %
    
    # Order counts
    discount_orders: int = 0
    pvndora_orders_from_discount: int = 0  # Orders in PVNDORA by discount users
    
    # Revenue
    discount_revenue: float = 0.0
    pvndora_revenue_from_migrated: float = 0.0
    
    # Promo codes
    promos_generated: int = 0
    promos_used: int = 0
    promo_conversion_rate: float = 0.0


class MigrationTrend(BaseModel):
    """Migration trend data point."""
    date: str
    new_discount_users: int = 0
    migrated_users: int = 0
    discount_orders: int = 0
    pvndora_orders: int = 0


class MigrationDashboard(BaseModel):
    """Complete migration dashboard."""
    stats: MigrationStats
    trend: list[MigrationTrend] = []
    top_migrating_products: list[dict] = []


# ============================================
# Endpoints
# ============================================

@router.get("/stats", response_model=MigrationStats)
async def get_migration_stats(
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    _admin: dict = Depends(verify_admin_user)
):
    """Get migration statistics for the specified period."""
    db = get_database()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()
    
    # 1. Count discount users (users who have made discount orders)
    discount_users_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "user_telegram_id", count="exact"
        ).eq("source_channel", "discount").execute()
    )
    # Get unique users
    discount_users_data = discount_users_result.data or []
    discount_user_ids = set(u["user_telegram_id"] for u in discount_users_data)
    total_discount_users = len(discount_user_ids)
    
    # 2. Count PVNDORA users
    pvndora_users_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "user_telegram_id"
        ).neq("source_channel", "discount").execute()
    )
    pvndora_users_data = pvndora_users_result.data or []
    pvndora_user_ids = set(u["user_telegram_id"] for u in pvndora_users_data)
    total_pvndora_users = len(pvndora_user_ids)
    
    # 3. Count migrated users (intersection)
    migrated_user_ids = discount_user_ids & pvndora_user_ids
    migrated_users = len(migrated_user_ids)
    migration_rate = (migrated_users / total_discount_users * 100) if total_discount_users > 0 else 0.0
    
    # 4. Count orders in period
    discount_orders_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "id", count="exact"
        ).eq("source_channel", "discount").gte(
            "created_at", cutoff_str
        ).execute()
    )
    discount_orders = discount_orders_result.count or 0
    
    # 5. PVNDORA orders from discount users
    pvndora_orders_from_discount = 0
    if migrated_user_ids:
        for user_id in list(migrated_user_ids)[:100]:  # Limit to avoid timeout
            orders_result = await asyncio.to_thread(
                lambda uid=user_id: db.client.table("orders").select(
                    "id", count="exact"
                ).eq("user_telegram_id", uid).neq(
                    "source_channel", "discount"
                ).gte("created_at", cutoff_str).execute()
            )
            pvndora_orders_from_discount += orders_result.count or 0
    
    # 6. Revenue calculations
    discount_revenue_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "total_amount"
        ).eq("source_channel", "discount").eq(
            "status", "delivered"
        ).gte("created_at", cutoff_str).execute()
    )
    discount_revenue = sum(
        o.get("total_amount", 0) or 0 
        for o in (discount_revenue_result.data or [])
    )
    
    # 7. Promo stats
    promos_result = await asyncio.to_thread(
        lambda: db.client.table("promo_codes").select(
            "id, is_used"
        ).gte("created_at", cutoff_str).execute()
    )
    promos_data = promos_result.data or []
    promos_generated = len(promos_data)
    promos_used = sum(1 for p in promos_data if p.get("is_used"))
    promo_conversion = (promos_used / promos_generated * 100) if promos_generated > 0 else 0.0
    
    return MigrationStats(
        total_discount_users=total_discount_users,
        total_pvndora_users=total_pvndora_users,
        migrated_users=migrated_users,
        migration_rate=round(migration_rate, 2),
        discount_orders=discount_orders,
        pvndora_orders_from_discount=pvndora_orders_from_discount,
        discount_revenue=round(discount_revenue, 2),
        promo_conversion_rate=round(promo_conversion, 2),
        promos_generated=promos_generated,
        promos_used=promos_used
    )


@router.get("/trend", response_model=list[MigrationTrend])
async def get_migration_trend(
    days: int = Query(14, ge=1, le=90, description="Period in days"),
    _admin: dict = Depends(verify_admin_user)
):
    """Get daily migration trend data."""
    db = get_database()
    trend = []
    
    for i in range(days, -1, -1):
        date = datetime.now(timezone.utc) - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Discount orders on this day
        discount_result = await asyncio.to_thread(
            lambda ds=date_start, de=date_end: db.client.table("orders").select(
                "id", count="exact"
            ).eq("source_channel", "discount").gte(
                "created_at", ds.isoformat()
            ).lte("created_at", de.isoformat()).execute()
        )
        
        # PVNDORA orders on this day
        pvndora_result = await asyncio.to_thread(
            lambda ds=date_start, de=date_end: db.client.table("orders").select(
                "id", count="exact"
            ).neq("source_channel", "discount").gte(
                "created_at", ds.isoformat()
            ).lte("created_at", de.isoformat()).execute()
        )
        
        trend.append(MigrationTrend(
            date=date_start.strftime("%Y-%m-%d"),
            discount_orders=discount_result.count or 0,
            pvndora_orders=pvndora_result.count or 0
        ))
    
    return trend


@router.get("/top-products")
async def get_top_migrating_products(
    limit: int = Query(10, ge=1, le=50),
    _admin: dict = Depends(verify_admin_user)
):
    """Get products that most attract discount users to PVNDORA."""
    db = get_database()
    
    # Get all discount orders to find user IDs
    discount_orders_result = await asyncio.to_thread(
        lambda: db.client.table("orders").select(
            "user_telegram_id"
        ).eq("source_channel", "discount").execute()
    )
    discount_user_ids = set(
        o["user_telegram_id"] for o in (discount_orders_result.data or [])
    )
    
    if not discount_user_ids:
        return []
    
    # Get PVNDORA orders from these users
    product_counts = {}
    for user_id in list(discount_user_ids)[:50]:  # Sample
        orders_result = await asyncio.to_thread(
            lambda uid=user_id: db.client.table("orders").select(
                "product_id"
            ).eq("user_telegram_id", uid).neq(
                "source_channel", "discount"
            ).execute()
        )
        
        for order in (orders_result.data or []):
            pid = order.get("product_id")
            if pid:
                product_counts[pid] = product_counts.get(pid, 0) + 1
    
    # Get product details
    top_products = []
    sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    for product_id, count in sorted_products:
        product_result = await asyncio.to_thread(
            lambda pid=product_id: db.client.table("products").select(
                "name, category"
            ).eq("id", pid).single().execute()
        )
        
        if product_result.data:
            top_products.append({
                "product_id": product_id,
                "name": product_result.data.get("name", "Unknown"),
                "category": product_result.data.get("category", "Unknown"),
                "migration_orders": count
            })
    
    return top_products
