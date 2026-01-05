"""
Admin Accounting Router

P&L reports, expense tracking, and financial overview.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.services.database import get_database
from core.auth import verify_admin
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["admin-accounting"])


# =============================================================================
# Models
# =============================================================================

class AccountingSettings(BaseModel):
    reserve_marketing_pct: float = 5.0
    reserve_unforeseen_pct: float = 3.0
    reserve_tax_pct: float = 0.0
    default_acquiring_fee_pct: float = 5.0


class PaymentGatewayFee(BaseModel):
    gateway: str
    payment_method: Optional[str] = None
    fee_percent: float
    fee_fixed_amount: float = 0
    fee_currency: str = "RUB"
    display_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class ProductCostUpdate(BaseModel):
    product_id: str
    cost_price: float


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    currency: str = "USD"
    category: str  # cogs, operational, marketing, legal, hosting, other
    supplier_id: Optional[str] = None
    date: Optional[str] = None  # ISO date


# =============================================================================
# Financial Overview
# =============================================================================

@router.get("/accounting/overview")
async def get_financial_overview(admin=Depends(verify_admin)):
    """Get complete financial overview from database view."""
    db = get_database()
    
    # Get main overview
    result = await asyncio.to_thread(
        lambda: db.client.table("financial_overview").select("*").single().execute()
    )
    
    # Get reserve balance
    reserves_result = await asyncio.to_thread(
        lambda: db.client.table("reserve_balance").select("*").single().execute()
    )
    
    data = result.data or {}
    reserves = reserves_result.data or {}
    
    # Merge reserve data
    data["reserves_accumulated"] = float(reserves.get("total_accumulated", 0))
    data["reserves_used"] = float(reserves.get("total_used", 0))
    data["reserves_available"] = float(reserves.get("total_available", 0))
    
    return data


@router.get("/accounting/pl/daily")
async def get_daily_pl(
    days: int = Query(30, ge=1, le=365),
    comprehensive: bool = Query(False, description="Use comprehensive view with all costs"),
    admin=Depends(verify_admin)
):
    """Get daily P&L report."""
    db = get_database()
    
    view_name = "pl_comprehensive" if comprehensive else "pl_daily"
    
    result = await asyncio.to_thread(
        lambda: db.client.table(view_name)
        .select("*")
        .order("date", desc=True)
        .limit(days)
        .execute()
    )
    
    data = result.data or []
    
    # Calculate totals for the period
    totals = {
        "revenue": sum(float(d.get("revenue_net", d.get("revenue", 0))) for d in data),
        "revenue_gross": sum(float(d.get("revenue_gross", 0)) for d in data),
        "total_discounts": sum(float(d.get("total_discounts_given", 0)) for d in data),
        "cogs": sum(float(d.get("cogs", 0)) for d in data),
        "acquiring_fees": sum(float(d.get("acquiring_fees", 0)) for d in data),
        "referral_payouts": sum(float(d.get("referral_payouts", 0)) for d in data),
        "reserves": sum(float(d.get("reserves", 0)) for d in data),
        "review_cashbacks": sum(float(d.get("review_cashbacks", 0)) for d in data),
        "replacement_costs": sum(float(d.get("replacement_costs", 0)) for d in data),
        "insurance_revenue": sum(float(d.get("insurance_revenue", 0)) for d in data),
        "gross_profit": sum(float(d.get("gross_profit", 0)) for d in data),
        "net_profit": sum(float(d.get("net_profit", d.get("operating_profit", 0))) for d in data),
        "orders_count": sum(int(d.get("orders_count", 0)) for d in data),
    }
    
    # Calculate margins
    revenue = totals["revenue"]
    if revenue > 0:
        totals["gross_margin_pct"] = round((totals["gross_profit"] / revenue) * 100, 2)
        totals["net_margin_pct"] = round((totals["net_profit"] / revenue) * 100, 2)
    else:
        totals["gross_margin_pct"] = 0
        totals["net_margin_pct"] = 0
    
    return {
        "period_days": days,
        "comprehensive": comprehensive,
        "daily": data,
        "totals": totals
    }


@router.get("/accounting/pl/monthly")
async def get_monthly_pl(
    months: int = Query(12, ge=1, le=36),
    admin=Depends(verify_admin)
):
    """Get monthly P&L report."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("pl_monthly")
        .select("*")
        .order("month", desc=True)
        .limit(months)
        .execute()
    )
    
    data = result.data or []
    
    # Calculate totals
    totals = {
        "revenue": sum(float(d.get("revenue", 0)) for d in data),
        "cogs": sum(float(d.get("cogs", 0)) for d in data),
        "acquiring_fees": sum(float(d.get("acquiring_fees", 0)) for d in data),
        "referral_payouts": sum(float(d.get("referral_payouts", 0)) for d in data),
        "reserves": sum(float(d.get("reserves", 0)) for d in data),
        "other_expenses": sum(float(d.get("other_expenses", 0)) for d in data),
        "gross_profit": sum(float(d.get("gross_profit", 0)) for d in data),
        "operating_profit": sum(float(d.get("operating_profit", 0)) for d in data),
        "net_profit": sum(float(d.get("net_profit", 0)) for d in data),
        "orders_count": sum(int(d.get("orders_count", 0)) for d in data),
    }
    
    return {
        "period_months": months,
        "monthly": data,
        "totals": totals
    }


# =============================================================================
# Product Profitability
# =============================================================================

@router.get("/accounting/products")
async def get_product_profitability(admin=Depends(verify_admin)):
    """Get product profitability analysis."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("product_profitability")
        .select("*")
        .execute()
    )
    
    return {
        "products": result.data or []
    }


@router.put("/accounting/products/cost")
async def update_product_cost(
    update: ProductCostUpdate,
    admin=Depends(verify_admin)
):
    """Update product cost price."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("products")
        .update({"cost_price": update.cost_price})
        .eq("id", update.product_id)
        .execute()
    )
    
    if not result.data:
        return {"success": False, "error": "Product not found"}
    
    return {"success": True, "product": result.data[0]}


@router.put("/accounting/products/cost/bulk")
async def update_product_costs_bulk(
    updates: List[ProductCostUpdate],
    admin=Depends(verify_admin)
):
    """Bulk update product cost prices."""
    db = get_database()
    
    results = []
    for update in updates:
        result = await asyncio.to_thread(
            lambda u=update: db.client.table("products")
            .update({"cost_price": u.cost_price})
            .eq("id", u.product_id)
            .execute()
        )
        results.append({
            "product_id": update.product_id,
            "success": bool(result.data)
        })
    
    return {"results": results}


# =============================================================================
# Payment Gateway Fees
# =============================================================================

@router.get("/accounting/gateway-fees")
async def get_gateway_fees(admin=Depends(verify_admin)):
    """Get all payment gateway fee configurations."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("payment_gateway_fees")
        .select("*")
        .order("gateway")
        .execute()
    )
    
    return {
        "fees": result.data or []
    }


@router.put("/accounting/gateway-fees")
async def update_gateway_fee(
    fee: PaymentGatewayFee,
    admin=Depends(verify_admin)
):
    """Update or create payment gateway fee configuration."""
    db = get_database()
    
    data = {
        "gateway": fee.gateway,
        "payment_method": fee.payment_method,
        "fee_percent": fee.fee_percent,
        "fee_fixed_amount": fee.fee_fixed_amount,
        "fee_currency": fee.fee_currency,
        "display_name": fee.display_name,
        "notes": fee.notes,
        "is_active": fee.is_active,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await asyncio.to_thread(
        lambda: db.client.table("payment_gateway_fees")
        .upsert(data, on_conflict="gateway,payment_method")
        .execute()
    )
    
    return {"success": True, "fee": result.data[0] if result.data else data}


# =============================================================================
# Accounting Settings (Reserves)
# =============================================================================

@router.get("/accounting/settings")
async def get_accounting_settings(admin=Depends(verify_admin)):
    """Get accounting settings (reserve percentages, default fees)."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("accounting_settings")
        .select("*")
        .single()
        .execute()
    )
    
    return result.data or {
        "reserve_marketing_pct": 5.0,
        "reserve_unforeseen_pct": 3.0,
        "reserve_tax_pct": 0.0,
        "default_acquiring_fee_pct": 5.0
    }


@router.put("/accounting/settings")
async def update_accounting_settings(
    settings: AccountingSettings,
    admin=Depends(verify_admin)
):
    """Update accounting settings."""
    db = get_database()
    
    data = {
        "reserve_marketing_pct": settings.reserve_marketing_pct,
        "reserve_unforeseen_pct": settings.reserve_unforeseen_pct,
        "reserve_tax_pct": settings.reserve_tax_pct,
        "default_acquiring_fee_pct": settings.default_acquiring_fee_pct,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    result = await asyncio.to_thread(
        lambda: db.client.table("accounting_settings")
        .update(data)
        .eq("id", "00000000-0000-0000-0000-000000000001")
        .execute()
    )
    
    return {"success": True, "settings": data}


# =============================================================================
# Liabilities
# =============================================================================

@router.get("/accounting/liabilities")
async def get_liabilities(admin=Depends(verify_admin)):
    """Get current liabilities (user balances, pending withdrawals)."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("liabilities_summary")
        .select("*")
        .single()
        .execute()
    )
    
    return result.data or {
        "total_user_balances": 0,
        "pending_withdrawals": 0,
        "total_liabilities": 0
    }


# =============================================================================
# Order Expenses Detail
# =============================================================================

@router.get("/accounting/orders/{order_id}/expenses")
async def get_order_expenses(
    order_id: str,
    admin=Depends(verify_admin)
):
    """Get detailed expense breakdown for a specific order."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.table("order_expenses")
        .select("*")
        .eq("order_id", order_id)
        .single()
        .execute()
    )
    
    if not result.data:
        return {"error": "No expenses found for this order"}
    
    return result.data


@router.post("/accounting/orders/{order_id}/recalculate")
async def recalculate_order_expenses(
    order_id: str,
    admin=Depends(verify_admin)
):
    """Recalculate expenses for a specific order."""
    db = get_database()
    
    result = await asyncio.to_thread(
        lambda: db.client.rpc(
            "calculate_order_expenses",
            {"p_order_id": order_id}
        ).execute()
    )
    
    # Fetch updated expenses
    expenses = await asyncio.to_thread(
        lambda: db.client.table("order_expenses")
        .select("*")
        .eq("order_id", order_id)
        .single()
        .execute()
    )
    
    return {
        "success": True,
        "expenses": expenses.data
    }


@router.post("/accounting/recalculate-all")
async def recalculate_all_expenses(admin=Depends(verify_admin)):
    """Recalculate expenses for all delivered orders."""
    db = get_database()
    
    # Get all delivered orders
    orders = await asyncio.to_thread(
        lambda: db.client.table("orders")
        .select("id")
        .eq("status", "delivered")
        .execute()
    )
    
    count = 0
    for order in (orders.data or []):
        await asyncio.to_thread(
            lambda oid=order["id"]: db.client.rpc(
                "calculate_order_expenses",
                {"p_order_id": oid}
            ).execute()
        )
        count += 1
    
    return {
        "success": True,
        "orders_processed": count
    }


# =============================================================================
# Expenses Management
# =============================================================================

@router.get("/accounting/expenses")
async def get_expenses(
    days: int = Query(30, ge=1, le=365),
    category: Optional[str] = None,
    admin=Depends(verify_admin)
):
    """Get direct expenses (non-COGS)."""
    db = get_database()
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = db.client.table("expenses").select("*").gte("date", start_date.isoformat())
    
    if category:
        query = query.eq("category", category)
    
    result = await asyncio.to_thread(
        lambda: query.order("date", desc=True).execute()
    )
    
    data = result.data or []
    
    # Aggregate by category
    by_category = {}
    for exp in data:
        cat = exp.get("category", "other")
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += float(exp.get("amount_usd", 0))
    
    return {
        "expenses": data,
        "by_category": by_category,
        "total": sum(by_category.values())
    }


@router.post("/accounting/expenses")
async def create_expense(
    expense: ExpenseCreate,
    admin=Depends(verify_admin)
):
    """Create a new expense entry."""
    db = get_database()
    
    # Convert to USD if needed
    amount_usd = expense.amount
    if expense.currency != "USD":
        # Get exchange rate
        rate_result = await asyncio.to_thread(
            lambda: db.client.table("exchange_rates")
            .select("rate")
            .eq("currency", expense.currency)
            .single()
            .execute()
        )
        if rate_result.data:
            rate = float(rate_result.data["rate"])
            amount_usd = expense.amount / rate
    
    data = {
        "description": expense.description,
        "amount": expense.amount,
        "currency": expense.currency,
        "amount_usd": round(amount_usd, 2),
        "category": expense.category,
        "supplier_id": expense.supplier_id,
        "date": expense.date or datetime.now(timezone.utc).date().isoformat(),
    }
    
    result = await asyncio.to_thread(
        lambda: db.client.table("expenses").insert(data).execute()
    )
    
    return {"success": True, "expense": result.data[0] if result.data else data}


# =============================================================================
# Summary Report
# =============================================================================

@router.get("/accounting/report")
async def get_accounting_report(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    admin=Depends(verify_admin)
):
    """
    Get comprehensive accounting report for a period.
    Includes ALL costs: COGS, Acquiring, Referrals, Reserves, Review Cashbacks, Replacements.
    """
    db = get_database()
    
    # Determine date range
    now = datetime.now(timezone.utc)
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=365)
    
    # Get orders with expenses
    orders_result = await asyncio.to_thread(
        lambda: db.client.table("orders")
        .select("id, amount, original_price, discount_percent, created_at, order_expenses(*)")
        .eq("status", "delivered")
        .gte("created_at", start_date.isoformat())
        .execute()
    )
    
    orders = orders_result.data or []
    
    # Calculate totals
    revenue = sum(float(o.get("amount", 0)) for o in orders)
    revenue_gross = sum(float(o.get("original_price", o.get("amount", 0))) for o in orders)
    total_discounts = revenue_gross - revenue
    
    cogs = 0
    acquiring = 0
    referrals = 0
    reserves = 0
    review_cashbacks = 0
    replacement_costs = 0
    
    for order in orders:
        expenses = order.get("order_expenses")
        if expenses:
            if isinstance(expenses, list):
                expenses = expenses[0] if expenses else {}
            cogs += float(expenses.get("cogs_amount", 0))
            acquiring += float(expenses.get("acquiring_fee_amount", 0))
            referrals += float(expenses.get("referral_payout_amount", 0))
            reserves += float(expenses.get("reserve_amount", 0))
            review_cashbacks += float(expenses.get("review_cashback_amount", 0))
            replacement_costs += float(expenses.get("insurance_replacement_cost", 0))
    
    # Get insurance revenue
    insurance_result = await asyncio.to_thread(
        lambda: db.client.table("insurance_revenue")
        .select("price")
        .gte("created_at", start_date.isoformat())
        .execute()
    )
    insurance_revenue = sum(float(i.get("price", 0)) for i in (insurance_result.data or []))
    
    # Get other expenses
    other_expenses_result = await asyncio.to_thread(
        lambda: db.client.table("expenses")
        .select("amount_usd, category")
        .gte("date", start_date.date().isoformat())
        .execute()
    )
    
    other_expenses = sum(float(e.get("amount_usd", 0)) for e in (other_expenses_result.data or []))
    
    # Expenses by category
    expenses_by_category = {}
    for e in (other_expenses_result.data or []):
        cat = e.get("category", "other")
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + float(e.get("amount_usd", 0))
    
    # Calculate profits
    gross_profit = revenue - cogs
    operating_expenses_total = acquiring + referrals + reserves + review_cashbacks + replacement_costs
    operating_profit = gross_profit - operating_expenses_total
    net_profit = operating_profit - other_expenses + insurance_revenue
    
    # Get liabilities
    liabilities_result = await asyncio.to_thread(
        lambda: db.client.table("liabilities_summary")
        .select("*")
        .single()
        .execute()
    )
    liabilities = liabilities_result.data or {}
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "orders_count": len(orders),
        
        # Income Statement
        "income_statement": {
            "revenue_gross": round(revenue_gross, 2),
            "discounts_given": round(total_discounts, 2),
            "revenue_net": round(revenue, 2),
            "insurance_revenue": round(insurance_revenue, 2),
            
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round((gross_profit / revenue * 100) if revenue > 0 else 0, 2),
            
            "operating_expenses": {
                "acquiring_fees": round(acquiring, 2),
                "referral_payouts": round(referrals, 2),
                "reserves": round(reserves, 2),
                "review_cashbacks": round(review_cashbacks, 2),
                "replacement_costs": round(replacement_costs, 2),
                "total": round(operating_expenses_total, 2)
            },
            
            "operating_profit": round(operating_profit, 2),
            "operating_margin_pct": round((operating_profit / revenue * 100) if revenue > 0 else 0, 2),
            
            "other_expenses": round(other_expenses, 2),
            "other_expenses_by_category": {k: round(v, 2) for k, v in expenses_by_category.items()},
            
            "net_profit": round(net_profit, 2),
            "net_margin_pct": round((net_profit / revenue * 100) if revenue > 0 else 0, 2),
        },
        
        # Balance Sheet Items
        "liabilities": {
            "user_balances": float(liabilities.get("total_user_balances", 0)),
            "pending_withdrawals": float(liabilities.get("pending_withdrawals", 0)),
            "total": float(liabilities.get("total_liabilities", 0))
        },
        
        # Key Metrics
        "metrics": {
            "avg_order_value": round(revenue / len(orders), 2) if orders else 0,
            "cogs_per_order": round(cogs / len(orders), 2) if orders else 0,
            "acquiring_pct": round((acquiring / revenue * 100) if revenue > 0 else 0, 2),
            "referral_pct": round((referrals / revenue * 100) if revenue > 0 else 0, 2),
            "cashback_pct": round((review_cashbacks / revenue * 100) if revenue > 0 else 0, 2),
            "discount_rate_pct": round((total_discounts / revenue_gross * 100) if revenue_gross > 0 else 0, 2),
        }
    }
