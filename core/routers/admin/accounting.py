"""
Admin Accounting Router

P&L reports, expense tracking, and financial overview.
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.auth import verify_admin
from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)
router = APIRouter(tags=["admin-accounting"])

# Constants (avoid string duplication)
SELECT_BALANCE_FIELDS = "balance, balance_currency"
SELECT_WITHDRAWAL_FIELDS = "amount_debited, balance_currency"

# =============================================================================
# Helper Functions (reduce cognitive complexity)
# =============================================================================


def parse_date_range(
    from_date: str | None, to_date: str | None, period: str | None
) -> tuple[datetime | None, datetime]:
    """Parse date range from query parameters (reduces cognitive complexity)."""
    now = datetime.now(UTC)
    start_date: datetime | None = None
    end_date: datetime = now

    if from_date:
        try:
            start_date = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            if not start_date.tzinfo:
                start_date = start_date.replace(tzinfo=UTC)
        except ValueError:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=UTC)

    if to_date:
        try:
            end_date = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            if not end_date.tzinfo:
                end_date = end_date.replace(tzinfo=UTC)
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            end_date = datetime.strptime(to_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=UTC
            )

    if not start_date and period:
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start_date = now - timedelta(days=30)

    return start_date, end_date


def extract_order_data(order: dict[str, Any]) -> tuple[str, float | None, float, dict[str, Any] | None]:
    """Extract currency, amounts, and expenses from order (reduces cognitive complexity)."""
    currency_raw = order.get("fiat_currency")
    currency = str(currency_raw) if currency_raw else "USD"
    fiat_amount_raw = order.get("fiat_amount")
    fiat_amount = float(fiat_amount_raw) if isinstance(fiat_amount_raw, (int, float)) else None
    amount_raw = order.get("amount", 0)
    amount_usd = float(amount_raw) if isinstance(amount_raw, (int, float)) else 0.0

    expenses_raw = order.get("order_expenses")
    expenses: dict[str, Any] | None = None
    if expenses_raw:
        if isinstance(expenses_raw, list):
            expenses = (
                cast(dict[str, Any], expenses_raw[0])
                if expenses_raw and isinstance(expenses_raw[0], dict)
                else None
            )
        elif isinstance(expenses_raw, dict):
            expenses = cast(dict[str, Any], expenses_raw)

    return currency, fiat_amount, amount_usd, expenses


def calculate_revenue_amounts(
    amount_usd: float,
    real_amount: float,
    expenses: dict[str, Any] | None,
    currency: str,
) -> tuple[float, float, float]:
    """Calculate gross revenue, promo discount in fiat currency (reduces cognitive complexity)."""
    promo_discount_raw = expenses.get("promo_discount_amount", 0) if expenses else 0
    promo_discount_usd = (
        float(promo_discount_raw) if isinstance(promo_discount_raw, (int, float)) else 0.0
    )

    revenue_gross_usd = amount_usd + promo_discount_usd

    if promo_discount_usd > 0:
        if amount_usd > 0:
            gross_ratio = revenue_gross_usd / amount_usd
            fiat_gross = real_amount * gross_ratio
        else:
            fiat_gross = revenue_gross_usd
        fiat_promo_discount = fiat_gross - real_amount
    else:
        fiat_gross = real_amount
        fiat_promo_discount = 0.0

    return fiat_gross, fiat_promo_discount, revenue_gross_usd


def extract_expenses(expenses: dict[str, Any]) -> dict[str, float]:
    """Extract expense amounts from order_expenses (reduces cognitive complexity)."""
    return {
        "cogs": float(expenses.get("cogs_amount", 0))
        if isinstance(expenses.get("cogs_amount"), (int, float))
        else 0.0,
        "acquiring": float(expenses.get("acquiring_fee_amount", 0))
        if isinstance(expenses.get("acquiring_fee_amount"), (int, float))
        else 0.0,
        "referral": float(expenses.get("referral_payout_amount", 0))
        if isinstance(expenses.get("referral_payout_amount"), (int, float))
        else 0.0,
        "reserve": float(expenses.get("reserve_amount", 0))
        if isinstance(expenses.get("reserve_amount"), (int, float))
        else 0.0,
        "review": float(expenses.get("review_cashback_amount", 0))
        if isinstance(expenses.get("review_cashback_amount"), (int, float))
        else 0.0,
        "replacement": float(expenses.get("insurance_replacement_cost", 0))
        if isinstance(expenses.get("insurance_replacement_cost"), (int, float))
        else 0.0,
    }


def round_currency_value(value: float, currency: str) -> float:
    """Round currency value based on currency type (reduces cognitive complexity)."""
    if currency in ("RUB", "UAH", "TRY", "INR", "JPY", "KRW"):
        return round(value)
    return round(value, 2)


# Helper: Calculate profit metrics (reduces cognitive complexity)
def _calculate_profit_metrics(
    total_revenue_usd: float,
    total_cogs: float,
    total_acquiring_fees: float,
    total_referral_payouts: float,
    total_reserves: float,
    total_review_cashbacks: float,
    total_replacement_costs: float,
    total_other_expenses: float,
    total_insurance_revenue: float,
) -> dict[str, float]:
    """Calculate profit metrics from revenue and expenses."""
    gross_profit_usd = total_revenue_usd - total_cogs
    operating_expenses_usd = (
        total_acquiring_fees
        + total_referral_payouts
        + total_reserves
        + total_review_cashbacks
        + total_replacement_costs
    )
    operating_profit_usd = gross_profit_usd - operating_expenses_usd
    net_profit_usd = operating_profit_usd - total_other_expenses + total_insurance_revenue

    return {
        "gross_profit": gross_profit_usd,
        "operating_profit": operating_profit_usd,
        "net_profit": net_profit_usd,
    }


# Helper: Calculate liability totals (reduces cognitive complexity)
def _calculate_liability_totals(liabilities_by_currency: dict) -> dict[str, float]:
    """Calculate total user balances and pending withdrawals."""
    return {
        "total_user_balances": sum(
            (
                float(data.get("user_balances", 0))
                if isinstance(data.get("user_balances"), (int, float))
                else 0.0
            )
            for data in liabilities_by_currency.values()
            if isinstance(data, dict)
        ),
        "pending_withdrawals": sum(
            (
                float(data.get("pending_withdrawals", 0))
                if isinstance(data.get("pending_withdrawals"), (int, float))
                else 0.0
            )
            for data in liabilities_by_currency.values()
            if isinstance(data, dict)
        ),
    }


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
    payment_method: str | None = None
    fee_percent: float
    fee_fixed_amount: float = 0
    fee_currency: str = "RUB"
    display_name: str | None = None
    notes: str | None = None
    is_active: bool = True


class ProductCostUpdate(BaseModel):
    product_id: str
    cost_price: float


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    currency: str = "USD"
    category: str  # cogs, operational, marketing, legal, hosting, other
    supplier_id: str | None = None
    date: str | None = None  # ISO date


# Helper: Process orders for financial overview (reduces cognitive complexity)
async def _process_orders_for_overview(
    orders: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """Process orders and calculate revenue by currency and expense totals."""
    revenue_by_currency: dict = {}
    expense_totals = {
        "revenue_usd": 0.0,
        "revenue_gross_usd": 0.0,
        "cogs": 0.0,
        "acquiring_fees": 0.0,
        "referral_payouts": 0.0,
        "reserves": 0.0,
        "review_cashbacks": 0.0,
        "replacement_costs": 0.0,
    }

    for raw_order in orders:
        if not isinstance(raw_order, dict):
            continue
        order = cast(dict[str, Any], raw_order)

        currency, fiat_amount, amount_usd, expenses = extract_order_data(order)
        real_amount = float(fiat_amount) if fiat_amount is not None else amount_usd
        fiat_gross, fiat_promo_discount, revenue_gross_usd = calculate_revenue_amounts(
            amount_usd, real_amount, expenses, currency
        )

        # Initialize currency bucket
        if currency not in revenue_by_currency:
            revenue_by_currency[currency] = {
                "orders_count": 0,
                "revenue": 0.0,
                "revenue_gross": 0.0,
                "discounts_given": 0.0,
            }

        revenue_by_currency[currency]["orders_count"] += 1
        revenue_by_currency[currency]["revenue"] += real_amount
        revenue_by_currency[currency]["revenue_gross"] += fiat_gross
        revenue_by_currency[currency]["discounts_given"] += fiat_promo_discount

        # USD totals for expense calculations
        expense_totals["revenue_usd"] += amount_usd
        expense_totals["revenue_gross_usd"] += revenue_gross_usd

        # Expenses (from order_expenses, always in USD)
        if expenses and isinstance(expenses, dict):
            exp = extract_expenses(expenses)
            expense_totals["cogs"] += exp["cogs"]
            expense_totals["acquiring_fees"] += exp["acquiring"]
            expense_totals["referral_payouts"] += exp["referral"]
            expense_totals["reserves"] += exp["reserve"]
            expense_totals["review_cashbacks"] += exp["review"]
            expense_totals["replacement_costs"] += exp["replacement"]

    # Round currency values
    for currency_key in revenue_by_currency:
        for key in revenue_by_currency[currency_key]:
            if key != "orders_count":
                revenue_by_currency[currency_key][key] = round_currency_value(
                    revenue_by_currency[currency_key][key], currency_key
                )

    return revenue_by_currency, expense_totals


# Helper: Get other expenses and insurance revenue (reduces cognitive complexity)
async def _get_other_expenses_and_insurance(
    db: Any, start_date: datetime | None, end_date: datetime
) -> tuple[float, dict[str, float], float]:
    """Get other expenses, expenses by category, and insurance revenue."""
    # Other Expenses
    expenses_query = db.client.table("expenses").select("amount_usd, category")
    if start_date:
        expenses_query = expenses_query.gte("date", start_date.date().isoformat())
    if end_date:
        expenses_query = expenses_query.lte("date", end_date.date().isoformat())

    other_expenses_result = await expenses_query.execute()
    total_other_expenses = 0.0
    expenses_by_category: dict[str, float] = {}
    for raw_e in other_expenses_result.data or []:
        if isinstance(raw_e, dict):
            e = cast(dict[str, Any], raw_e)
            amount_raw = e.get("amount_usd", 0)
            total_other_expenses += (
                float(amount_raw) if isinstance(amount_raw, (int, float)) else 0.0
            )

            cat_raw = e.get("category", "other")
            cat = str(cat_raw) if cat_raw else "other"
            amount = float(amount_raw) if isinstance(amount_raw, (int, float)) else 0.0
            expenses_by_category[cat] = expenses_by_category.get(cat, 0.0) + amount

    # Insurance Revenue
    insurance_query = db.client.table("insurance_revenue").select("price")
    if start_date:
        insurance_query = insurance_query.gte("created_at", start_date.isoformat())
    if end_date:
        insurance_query = insurance_query.lte("created_at", end_date.isoformat())

    insurance_result = await insurance_query.execute()
    total_insurance_revenue = 0.0
    for raw_i in insurance_result.data or []:
        if isinstance(raw_i, dict):
            i = cast(dict[str, Any], raw_i)
            price_raw = i.get("price", 0)
            total_insurance_revenue += (
                float(price_raw) if isinstance(price_raw, (int, float)) else 0.0
            )

    return total_other_expenses, expenses_by_category, total_insurance_revenue


# =============================================================================
# Financial Overview (Multi-Currency with Date Filtering)
# =============================================================================


@router.get("/accounting/overview")
async def get_financial_overview(
    period: str | None = Query(None, description="Period: today, month, all"),
    from_date: str | None = Query(None, alias="from", description="Start date (ISO format)"),
    to_date: str | None = Query(None, alias="to", description="End date (ISO format)"),
    display_currency: str = Query(
        "USD", description="DEPRECATED - kept for backward compatibility"
    ),
    admin=Depends(verify_admin),
):
    """
    Get financial overview with REAL currency amounts (no conversion).

    Returns separate totals for each currency (USD, RUB, etc.) showing
    what was actually paid, not converted values.

    COGS and other supplier costs remain in USD (since suppliers are paid in $).

    Args:
        period: Filter by period (today, month, all). Ignored if from/to provided.
        from_date: Start date filter (ISO format: 2026-01-01)
        to_date: End date filter (ISO format: 2026-01-31)
    """
    db = get_database()

    # Determine date range
    start_date, end_date = parse_date_range(from_date, to_date, period)

    # Build orders query with date filtering
    orders_query = (
        db.client.table("orders")
        .select(
            "id, amount, original_price, fiat_amount, fiat_currency, exchange_rate_snapshot, "
            "created_at, order_expenses(cogs_amount, acquiring_fee_amount, referral_payout_amount, "
            "reserve_amount, review_cashback_amount, insurance_replacement_cost, promo_discount_amount)"
        )
        .eq("status", "delivered")
    )

    if start_date:
        orders_query = orders_query.gte("created_at", start_date.isoformat())
    if end_date:
        orders_query = orders_query.lte("created_at", end_date.isoformat())

    orders_result = await orders_query.execute()
    orders = orders_result.data or []

    # Process orders and calculate revenue/expenses
    revenue_by_currency, expense_totals = await _process_orders_for_overview(orders)
    total_revenue_usd = expense_totals["revenue_usd"]
    total_revenue_gross_usd = expense_totals["revenue_gross_usd"]
    total_cogs = expense_totals["cogs"]
    total_acquiring_fees = expense_totals["acquiring_fees"]
    total_referral_payouts = expense_totals["referral_payouts"]
    total_reserves = expense_totals["reserves"]
    total_review_cashbacks = expense_totals["review_cashbacks"]
    total_replacement_costs = expense_totals["replacement_costs"]

    # Get other expenses and insurance revenue
    total_other_expenses, expenses_by_category, total_insurance_revenue = (
        await _get_other_expenses_and_insurance(db, start_date, end_date)
    )

    # ==========================================================================
    # Liabilities by Currency (REAL amounts)
    # ==========================================================================
    liabilities_by_currency: dict = {}

    # Process user balances and pending withdrawals using helpers
    await _process_user_balances(db, liabilities_by_currency)
    await _process_pending_withdrawals(db, liabilities_by_currency)
    _round_liability_values(liabilities_by_currency)

    # ==========================================================================
    # Reserves
    # ==========================================================================
    try:
        reserves_result = await db.client.table("reserve_balance").select("*").single().execute()
        reserves_raw = reserves_result.data
        reserves = cast(dict[str, Any], reserves_raw) if isinstance(reserves_raw, dict) else {}
    except Exception:
        reserves: dict[str, Any] = {}

    # ==========================================================================
    # Calculate Profit (in USD for now, since COGS is in USD)
    # ==========================================================================
    profit_data = _calculate_profit_metrics(
        total_revenue_usd,
        total_cogs,
        total_acquiring_fees,
        total_referral_payouts,
        total_reserves,
        total_review_cashbacks,
        total_replacement_costs,
        total_other_expenses,
        total_insurance_revenue,
    )
    gross_profit_usd = profit_data["gross_profit"]
    operating_profit_usd = profit_data["operating_profit"]
    net_profit_usd = profit_data["net_profit"]

    # ==========================================================================
    # Build Response
    # ==========================================================================
    return {
        # Filter info
        "period": period or ("custom" if from_date or to_date else "all"),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat(),
        # Orders summary
        "total_orders": len(orders),
        # =====================================================================
        # REVENUE BY CURRENCY (Real amounts, no conversion!)
        # =====================================================================
        "revenue_by_currency": revenue_by_currency,
        # Legacy totals in USD (for backward compatibility)
        "total_revenue": round(total_revenue_usd, 2),  # Чистая выручка (после промокодов)
        "total_revenue_gross": round(
            total_revenue_gross_usd, 2
        ),  # Валовая выручка (наша цена БЕЗ промокодов)
        "total_discounts_given": round(
            total_revenue_gross_usd - total_revenue_usd, 2
        ),  # Скидки через промокоды
        # =====================================================================
        # EXPENSES (Always in USD - suppliers are paid in $)
        # =====================================================================
        "expenses_usd": {
            "cogs": round(total_cogs, 2),
            "acquiring_fees": round(total_acquiring_fees, 2),
            "referral_payouts": round(total_referral_payouts, 2),
            "reserves": round(total_reserves, 2),
            "review_cashbacks": round(total_review_cashbacks, 2),
            "replacement_costs": round(total_replacement_costs, 2),
            "other_expenses": round(total_other_expenses, 2),
            "other_by_category": {k: round(v, 2) for k, v in expenses_by_category.items()},
        },
        # Legacy expense fields (for backward compatibility)
        "total_cogs": round(total_cogs, 2),
        "total_acquiring_fees": round(total_acquiring_fees, 2),
        "total_referral_payouts": round(total_referral_payouts, 2),
        "total_reserves": round(total_reserves, 2),
        "total_review_cashbacks": round(total_review_cashbacks, 2),
        "total_replacement_costs": round(total_replacement_costs, 2),
        "total_other_expenses": round(total_other_expenses, 2),
        # Insurance revenue (in USD)
        "total_insurance_revenue": round(total_insurance_revenue, 2),
        # =====================================================================
        # LIABILITIES BY CURRENCY (Real amounts!)
        # =====================================================================
        "liabilities_by_currency": liabilities_by_currency,
        # Legacy liabilities (sum converted to USD for compatibility)
        **_calculate_liability_totals(liabilities_by_currency),
        # =====================================================================
        # PROFIT (In USD, since COGS is in $)
        # =====================================================================
        "profit_usd": {
            "gross_profit": round(gross_profit_usd, 2),
            "operating_profit": round(operating_profit_usd, 2),
            "net_profit": round(net_profit_usd, 2),
            "gross_margin_pct": round(
                (gross_profit_usd / total_revenue_usd * 100) if total_revenue_usd > 0 else 0, 2
            ),
            "net_margin_pct": round(
                (net_profit_usd / total_revenue_usd * 100) if total_revenue_usd > 0 else 0, 2
            ),
        },
        # Legacy profit field
        "net_profit": round(net_profit_usd, 2),
        # Reserves (in USD)
        "reserves_accumulated": (
            float(reserves.get("total_accumulated", 0))
            if isinstance(reserves.get("total_accumulated"), (int, float))
            else 0.0
        ),
        "reserves_used": (
            float(reserves.get("total_used", 0))
            if isinstance(reserves.get("total_used"), (int, float))
            else 0.0
        ),
        "reserves_available": (
            float(reserves.get("total_available", 0))
            if isinstance(reserves.get("total_available"), (int, float))
            else 0.0
        ),
        # Deprecated field kept for backward compatibility
        "currency_breakdown": revenue_by_currency,
        "display_currency": "MULTI",  # Indicates new multi-currency mode
    }


# Helper: Initialize daily data entry (reduces cognitive complexity)
def _init_daily_entry(order_date: str) -> dict[str, Any]:
    """Initialize daily data entry structure."""
    return {
        "date": order_date,
        "orders_count": 0,
        "revenue_by_currency": {},
        "revenue_usd": 0.0,
        "cogs": 0.0,
        "acquiring_fees": 0.0,
        "referral_payouts": 0.0,
        "reserves": 0.0,
        "review_cashbacks": 0.0,
        "replacement_costs": 0.0,
    }


# Helper: Process order expenses into daily entry (reduces cognitive complexity)
def _add_order_expenses_to_day(day: dict[str, Any], expenses: dict[str, Any]) -> None:
    """Add order expenses to daily entry."""
    day["cogs"] += float(expenses.get("cogs_amount", 0) or 0)
    day["acquiring_fees"] += float(expenses.get("acquiring_fee_amount", 0) or 0)
    day["referral_payouts"] += float(expenses.get("referral_payout_amount", 0) or 0)
    day["reserves"] += float(expenses.get("reserve_amount", 0) or 0)
    day["review_cashbacks"] += float(expenses.get("review_cashback_amount", 0) or 0)
    day["replacement_costs"] += float(expenses.get("insurance_replacement_cost", 0) or 0)


# Helper: Process order into daily data (reduces cognitive complexity)
def _process_order_for_daily(
    order: dict[str, Any], daily_data: dict[str, dict[str, Any]]
) -> None:
    """Process a single order and add it to daily data."""
    created_at_raw = order.get("created_at", "")
    created_at_str = str(created_at_raw) if created_at_raw else ""
    order_date = created_at_str[:10] if len(created_at_str) >= 10 else ""

    if order_date not in daily_data:
        daily_data[order_date] = _init_daily_entry(order_date)

    day = daily_data[order_date]
    day["orders_count"] += 1

    # Extract order data
    currency, fiat_amount, amount_usd, expenses = extract_order_data(order)
    real_amount = float(fiat_amount) if fiat_amount is not None else amount_usd

    # Add expenses
    if expenses:
        _add_order_expenses_to_day(day, expenses)

    # Add revenue
    if currency not in day["revenue_by_currency"]:
        day["revenue_by_currency"][currency] = {"revenue": 0.0, "orders_count": 0}
    day["revenue_by_currency"][currency]["revenue"] += real_amount
    day["revenue_by_currency"][currency]["orders_count"] += 1
    day["revenue_usd"] += amount_usd


# Helper: Get insurance revenue by date (reduces cognitive complexity)
async def _get_insurance_by_date(
    db: Any, start_date: datetime
) -> dict[str, float]:
    """Get insurance revenue grouped by date."""
    insurance_by_date: dict[str, float] = {}
    insurance_result = (
        await db.client.table("insurance_revenue")
        .select("price, created_at")
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    for raw_ins in insurance_result.data or []:
        if not isinstance(raw_ins, dict):
            continue
        ins = cast(dict[str, Any], raw_ins)
        created_at_raw = ins.get("created_at", "")
        created_at_str = str(created_at_raw) if created_at_raw else ""
        ins_date = created_at_str[:10] if len(created_at_str) >= 10 else ""
        price_raw = ins.get("price", 0)
        price = float(price_raw) if isinstance(price_raw, (int, float)) else 0.0
        insurance_by_date[ins_date] = insurance_by_date.get(ins_date, 0.0) + price

    return insurance_by_date


# Helper: Calculate profits for daily entries (reduces cognitive complexity)
def _calculate_daily_profits(
    daily_data: dict[str, dict[str, Any]], insurance_by_date: dict[str, float], comprehensive: bool
) -> None:
    """Calculate profit metrics for each day."""
    for date, day in daily_data.items():
        revenue_usd = day["revenue_usd"]
        cogs = day["cogs"]

        day["gross_profit_usd"] = round(revenue_usd - cogs, 2)

        operating_expenses = (
            day["acquiring_fees"]
            + day["referral_payouts"]
            + day["reserves"]
            + day["review_cashbacks"]
            + day["replacement_costs"]
        )
        day["operating_profit_usd"] = round(day["gross_profit_usd"] - operating_expenses, 2)

        if comprehensive:
            day["insurance_revenue"] = round(insurance_by_date.get(date, 0), 2)
            day["net_profit_usd"] = round(day["operating_profit_usd"] + day["insurance_revenue"], 2)
        else:
            day["net_profit_usd"] = day["operating_profit_usd"]

        # Round all fields
        day["cogs"] = round(cogs, 2)
        day["acquiring_fees"] = round(day["acquiring_fees"], 2)
        day["referral_payouts"] = round(day["referral_payouts"], 2)
        day["reserves"] = round(day["reserves"], 2)
        day["review_cashbacks"] = round(day["review_cashbacks"], 2)
        day["replacement_costs"] = round(day["replacement_costs"], 2)
        day["revenue_usd"] = round(revenue_usd, 2)

        # Round currency revenues
        for curr_data in day["revenue_by_currency"].values():
            if isinstance(curr_data.get("revenue"), float):
                curr_data["revenue"] = round(curr_data["revenue"], 2)


@router.get("/accounting/pl/daily")
async def get_daily_pl(
    days: int = Query(30, ge=1, le=365),
    comprehensive: bool = Query(False, description="Include all cost categories"),
    admin=Depends(verify_admin),
):
    """
    Get daily P&L report with REAL currency breakdown (no conversion).

    Returns:
        - Daily data with revenue_by_currency for each day
        - Expenses always in USD (COGS, acquiring, etc.)
        - Totals aggregated across all days
    """
    db = get_database()

    start_date = datetime.now(UTC) - timedelta(days=days)

    # Fetch orders with expenses and currency info
    orders_result = (
        await db.client.table("orders")
        .select(
            "id, amount, original_price, fiat_amount, fiat_currency, created_at, "
            "order_expenses(cogs_amount, acquiring_fee_amount, referral_payout_amount, "
            "reserve_amount, review_cashback_amount, insurance_replacement_cost)"
        )
        .eq("status", "delivered")
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    orders = orders_result.data or []

    # Group by date
    daily_data: dict = {}

    for raw_order in orders:
        if not isinstance(raw_order, dict):
            continue
        order = cast(dict[str, Any], raw_order)
        _process_order_for_daily(order, daily_data)

    # Get insurance revenue if comprehensive
    insurance_by_date = await _get_insurance_by_date(db, start_date) if comprehensive else {}

    # Calculate profits for each day
    _calculate_daily_profits(daily_data, insurance_by_date, comprehensive)

    # Sort by date descending
    daily_list = sorted(daily_data.values(), key=lambda x: x["date"], reverse=True)

    # Calculate totals
    totals_revenue_by_currency: dict = {}
    for day in daily_list:
        for currency, curr_data in day["revenue_by_currency"].items():
            if currency not in totals_revenue_by_currency:
                totals_revenue_by_currency[currency] = {"revenue": 0.0, "orders_count": 0}
            totals_revenue_by_currency[currency]["revenue"] += curr_data["revenue"]
            totals_revenue_by_currency[currency]["orders_count"] += curr_data["orders_count"]

    # Round totals
    for curr_data in totals_revenue_by_currency.values():
        curr_data["revenue"] = round(curr_data["revenue"], 2)

    totals = {
        "revenue_by_currency": totals_revenue_by_currency,
        "revenue_usd": round(sum(d["revenue_usd"] for d in daily_list), 2),
        "orders_count": sum(d["orders_count"] for d in daily_list),
        "cogs": round(sum(d["cogs"] for d in daily_list), 2),
        "acquiring_fees": round(sum(d["acquiring_fees"] for d in daily_list), 2),
        "referral_payouts": round(sum(d["referral_payouts"] for d in daily_list), 2),
        "reserves": round(sum(d["reserves"] for d in daily_list), 2),
        "review_cashbacks": round(sum(d["review_cashbacks"] for d in daily_list), 2),
        "replacement_costs": round(sum(d["replacement_costs"] for d in daily_list), 2),
        "gross_profit_usd": round(sum(d["gross_profit_usd"] for d in daily_list), 2),
        "operating_profit_usd": round(sum(d["operating_profit_usd"] for d in daily_list), 2),
        "net_profit_usd": round(sum(d["net_profit_usd"] for d in daily_list), 2),
    }

    if comprehensive:
        totals["insurance_revenue"] = round(
            sum(d.get("insurance_revenue", 0) for d in daily_list), 2
        )

    # Calculate margins
    if totals["revenue_usd"] > 0:
        totals["gross_margin_pct"] = round(
            (totals["gross_profit_usd"] / totals["revenue_usd"]) * 100, 2
        )
        totals["net_margin_pct"] = round(
            (totals["net_profit_usd"] / totals["revenue_usd"]) * 100, 2
        )
    else:
        totals["gross_margin_pct"] = 0
        totals["net_margin_pct"] = 0

    return {
        "period_days": days,
        "comprehensive": comprehensive,
        "start_date": start_date.isoformat()[:10],
        "end_date": datetime.now(UTC).isoformat()[:10],
        "daily": daily_list,
        "totals": totals,
        # Deprecated - kept for backward compatibility
        "display_currency": "MULTI",
    }


@router.get("/accounting/pl/monthly")
async def get_monthly_pl(months: int = Query(12, ge=1, le=36), admin=Depends(verify_admin)):
    """
    Get monthly P&L report with REAL currency breakdown (no conversion).

    Returns revenue by currency for each month, expenses in USD.
    """
    db = get_database()

    # Calculate start date
    now = datetime.now(UTC)
    start_date = now - timedelta(days=months * 31)  # Approximate

    # Fetch orders with expenses and currency info
    orders_result = (
        await db.client.table("orders")
        .select(
            "id, amount, original_price, fiat_amount, fiat_currency, created_at, "
            "order_expenses(cogs_amount, acquiring_fee_amount, referral_payout_amount, "
            "reserve_amount, review_cashback_amount, insurance_replacement_cost)"
        )
        .eq("status", "delivered")
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    orders = orders_result.data or []

    # Fetch other expenses
    expenses_result = (
        await db.client.table("expenses")
        .select("amount_usd, date")
        .gte("date", start_date.date().isoformat())
        .execute()
    )

    other_expenses_by_month: dict = {}
    for exp in expenses_result.data or []:
        exp_date = exp.get("date", "")[:7]  # YYYY-MM
        other_expenses_by_month[exp_date] = other_expenses_by_month.get(exp_date, 0) + float(
            exp.get("amount_usd", 0)
        )

    # Fetch insurance revenue
    insurance_result = (
        await db.client.table("insurance_revenue")
        .select("price, created_at")
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    insurance_by_month: dict = {}
    for ins in insurance_result.data or []:
        ins_date = ins.get("created_at", "")[:7]  # YYYY-MM
        insurance_by_month[ins_date] = insurance_by_month.get(ins_date, 0) + float(
            ins.get("price", 0)
        )

    # Group by month
    monthly_data: dict = {}

    for order in orders:
        order_month = order.get("created_at", "")[:7]  # YYYY-MM

        if order_month not in monthly_data:
            monthly_data[order_month] = {
                "month": order_month,
                "orders_count": 0,
                "revenue_by_currency": {},
                "revenue_usd": 0.0,
                "cogs": 0.0,
                "acquiring_fees": 0.0,
                "referral_payouts": 0.0,
                "reserves": 0.0,
                "review_cashbacks": 0.0,
                "replacement_costs": 0.0,
            }

        month = monthly_data[order_month]
        month["orders_count"] += 1

        # Revenue by currency
        currency = order.get("fiat_currency") or "USD"
        fiat_amount = order.get("fiat_amount")
        amount_usd = float(order.get("amount", 0))

        real_amount = float(fiat_amount) if fiat_amount is not None else amount_usd

        if currency not in month["revenue_by_currency"]:
            month["revenue_by_currency"][currency] = {"revenue": 0.0, "orders_count": 0}
        month["revenue_by_currency"][currency]["revenue"] += real_amount
        month["revenue_by_currency"][currency]["orders_count"] += 1
        month["revenue_usd"] += amount_usd

        # Expenses (USD)
        expenses = order.get("order_expenses")
        if expenses:
            if isinstance(expenses, list):
                expenses = expenses[0] if expenses else {}
            month["cogs"] += float(expenses.get("cogs_amount", 0))
            month["acquiring_fees"] += float(expenses.get("acquiring_fee_amount", 0))
            month["referral_payouts"] += float(expenses.get("referral_payout_amount", 0))
            month["reserves"] += float(expenses.get("reserve_amount", 0))
            month["review_cashbacks"] += float(expenses.get("review_cashback_amount", 0))
            month["replacement_costs"] += float(expenses.get("insurance_replacement_cost", 0))

    # Calculate profits for each month
    for month_key, month in monthly_data.items():
        month["other_expenses"] = round(other_expenses_by_month.get(month_key, 0), 2)
        month["insurance_revenue"] = round(insurance_by_month.get(month_key, 0), 2)

        revenue_usd = month["revenue_usd"]
        cogs = month["cogs"]

        month["gross_profit_usd"] = round(revenue_usd - cogs, 2)

        operating_expenses = (
            month["acquiring_fees"]
            + month["referral_payouts"]
            + month["reserves"]
            + month["review_cashbacks"]
            + month["replacement_costs"]
        )
        month["operating_profit_usd"] = round(month["gross_profit_usd"] - operating_expenses, 2)
        month["net_profit_usd"] = round(
            month["operating_profit_usd"] - month["other_expenses"] + month["insurance_revenue"], 2
        )

        # Round fields
        month["revenue_usd"] = round(revenue_usd, 2)
        month["cogs"] = round(cogs, 2)
        month["acquiring_fees"] = round(month["acquiring_fees"], 2)
        month["referral_payouts"] = round(month["referral_payouts"], 2)
        month["reserves"] = round(month["reserves"], 2)
        month["review_cashbacks"] = round(month["review_cashbacks"], 2)
        month["replacement_costs"] = round(month["replacement_costs"], 2)

        # Round currency revenues
        for curr_data in month["revenue_by_currency"].values():
            curr_data["revenue"] = round(curr_data["revenue"], 2)

    # Sort by month descending and limit
    monthly_list = sorted(monthly_data.values(), key=lambda x: x["month"], reverse=True)[:months]

    # Calculate totals
    totals_revenue_by_currency: dict = {}
    for month in monthly_list:
        for currency, curr_data in month["revenue_by_currency"].items():
            if currency not in totals_revenue_by_currency:
                totals_revenue_by_currency[currency] = {"revenue": 0.0, "orders_count": 0}
            totals_revenue_by_currency[currency]["revenue"] += curr_data["revenue"]
            totals_revenue_by_currency[currency]["orders_count"] += curr_data["orders_count"]

    for curr_data in totals_revenue_by_currency.values():
        curr_data["revenue"] = round(curr_data["revenue"], 2)

    totals = {
        "revenue_by_currency": totals_revenue_by_currency,
        "revenue_usd": round(sum(m["revenue_usd"] for m in monthly_list), 2),
        "orders_count": sum(m["orders_count"] for m in monthly_list),
        "cogs": round(sum(m["cogs"] for m in monthly_list), 2),
        "acquiring_fees": round(sum(m["acquiring_fees"] for m in monthly_list), 2),
        "referral_payouts": round(sum(m["referral_payouts"] for m in monthly_list), 2),
        "reserves": round(sum(m["reserves"] for m in monthly_list), 2),
        "review_cashbacks": round(sum(m["review_cashbacks"] for m in monthly_list), 2),
        "replacement_costs": round(sum(m["replacement_costs"] for m in monthly_list), 2),
        "other_expenses": round(sum(m["other_expenses"] for m in monthly_list), 2),
        "insurance_revenue": round(sum(m["insurance_revenue"] for m in monthly_list), 2),
        "gross_profit_usd": round(sum(m["gross_profit_usd"] for m in monthly_list), 2),
        "operating_profit_usd": round(sum(m["operating_profit_usd"] for m in monthly_list), 2),
        "net_profit_usd": round(sum(m["net_profit_usd"] for m in monthly_list), 2),
    }

    # Calculate margins
    if totals["revenue_usd"] > 0:
        totals["gross_margin_pct"] = round(
            (totals["gross_profit_usd"] / totals["revenue_usd"]) * 100, 2
        )
        totals["net_margin_pct"] = round(
            (totals["net_profit_usd"] / totals["revenue_usd"]) * 100, 2
        )
    else:
        totals["gross_margin_pct"] = 0
        totals["net_margin_pct"] = 0

    return {
        "period_months": months,
        "monthly": monthly_list,
        "totals": totals,
        # Deprecated
        "display_currency": "MULTI",
    }


# =============================================================================
# Product Profitability
# =============================================================================


@router.get("/accounting/products")
async def get_product_profitability(admin=Depends(verify_admin)):
    """Get product profitability analysis."""
    db = get_database()

    result = await db.client.table("product_profitability").select("*").execute()

    return {"products": result.data or []}


@router.put("/accounting/products/cost")
async def update_product_cost(update: ProductCostUpdate, admin=Depends(verify_admin)):
    """Update product cost price."""
    db = get_database()

    result = (
        await db.client.table("products")
        .update({"cost_price": update.cost_price})
        .eq("id", update.product_id)
        .execute()
    )

    if not result.data:
        return {"success": False, "error": "Product not found"}

    return {"success": True, "product": result.data[0]}


@router.put("/accounting/products/cost/bulk")
async def update_product_costs_bulk(updates: list[ProductCostUpdate], admin=Depends(verify_admin)):
    """Bulk update product cost prices."""
    db = get_database()

    results = []
    for update in updates:
        result = (
            await db.client.table("products")
            .update({"cost_price": update.cost_price})
            .eq("id", update.product_id)
            .execute()
        )
        results.append({"product_id": update.product_id, "success": bool(result.data)})

    return {"results": results}


# =============================================================================
# Payment Gateway Fees
# =============================================================================


@router.get("/accounting/gateway-fees")
async def get_gateway_fees(admin=Depends(verify_admin)):
    """Get all payment gateway fee configurations."""
    db = get_database()

    result = await db.client.table("payment_gateway_fees").select("*").order("gateway").execute()

    return {"fees": result.data or []}


@router.put("/accounting/gateway-fees")
async def update_gateway_fee(fee: PaymentGatewayFee, admin=Depends(verify_admin)):
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
        "updated_at": datetime.now(UTC).isoformat(),
    }

    result = (
        await db.client.table("payment_gateway_fees")
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

    result = await db.client.table("accounting_settings").select("*").single().execute()

    return result.data or {
        "reserve_marketing_pct": 5.0,
        "reserve_unforeseen_pct": 3.0,
        "reserve_tax_pct": 0.0,
        "default_acquiring_fee_pct": 5.0,
    }


@router.put("/accounting/settings")
async def update_accounting_settings(settings: AccountingSettings, admin=Depends(verify_admin)):
    """Update accounting settings."""
    db = get_database()

    data = {
        "reserve_marketing_pct": settings.reserve_marketing_pct,
        "reserve_unforeseen_pct": settings.reserve_unforeseen_pct,
        "reserve_tax_pct": settings.reserve_tax_pct,
        "default_acquiring_fee_pct": settings.default_acquiring_fee_pct,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    await db.client.table("accounting_settings").update(data).eq(
        "id", "00000000-0000-0000-0000-000000000001"
    ).execute()

    return {"success": True, "settings": data}


# =============================================================================
# Liabilities (Multi-Currency)
# =============================================================================


# Helper to initialize currency entry (reduces cognitive complexity)
def _init_currency_entry() -> dict:
    """Initialize currency entry in liabilities dict."""
    return {
        "user_balances": 0.0,
        "users_count": 0,
        "pending_withdrawals": 0.0,
        "withdrawals_count": 0,
    }


# Helper to process user balances (reduces cognitive complexity)
async def _process_user_balances(db, liabilities_by_currency: dict):
    """Process user balances by currency."""
    try:
        balances_result = (
            await db.client.table("users")
            .select(SELECT_BALANCE_FIELDS)
            .gt("balance", 0)
            .execute()
        )

        for user in balances_result.data or []:
            currency = user.get("balance_currency") or "USD"
            balance = float(user.get("balance", 0))

            if currency not in liabilities_by_currency:
                liabilities_by_currency[currency] = _init_currency_entry()

            liabilities_by_currency[currency]["user_balances"] += balance
            liabilities_by_currency[currency]["users_count"] += 1
    except Exception as e:
        logger.warning("Failed to get user balances: %s", e)


# Helper to process pending withdrawals (reduces cognitive complexity)
async def _process_pending_withdrawals(db, liabilities_by_currency: dict):
    """Process pending withdrawals by currency."""
    try:
        withdrawals_result = (
            await db.client.table("withdrawal_requests")
            .select(SELECT_WITHDRAWAL_FIELDS)
            .eq("status", "pending")
            .execute()
        )

        for w in withdrawals_result.data or []:
            currency = w.get("balance_currency") or "USD"
            amount = float(w.get("amount_debited", 0))

            if currency not in liabilities_by_currency:
                liabilities_by_currency[currency] = _init_currency_entry()

            liabilities_by_currency[currency]["pending_withdrawals"] += amount
            liabilities_by_currency[currency]["withdrawals_count"] += 1
    except Exception as e:
        logger.warning("Failed to get pending withdrawals: %s", e)


# Helper to round currency values (reduces cognitive complexity)
def _round_liability_values(liabilities_by_currency: dict):
    """Round liability values based on currency type."""
    INTEGER_CURRENCIES = ("RUB", "UAH", "TRY", "INR", "JPY", "KRW")

    for currency in liabilities_by_currency:
        data = liabilities_by_currency[currency]
        if currency in INTEGER_CURRENCIES:
            data["user_balances"] = round(data["user_balances"])
            data["pending_withdrawals"] = round(data["pending_withdrawals"])
        else:
            data["user_balances"] = round(data["user_balances"], 2)
            data["pending_withdrawals"] = round(data["pending_withdrawals"], 2)
        data["total"] = data["user_balances"] + data["pending_withdrawals"]


@router.get("/accounting/liabilities")
async def get_liabilities(admin=Depends(verify_admin)):
    """
    Get current liabilities with REAL currency breakdown (no conversion).

    Returns user balances and pending withdrawals per currency.
    """
    db = get_database()

    liabilities_by_currency: dict = {}

    await _process_user_balances(db, liabilities_by_currency)
    await _process_pending_withdrawals(db, liabilities_by_currency)
    _round_liability_values(liabilities_by_currency)

    total_user_balances = sum(d.get("user_balances", 0) for d in liabilities_by_currency.values())
    total_pending = sum(d.get("pending_withdrawals", 0) for d in liabilities_by_currency.values())

    return {
        "liabilities_by_currency": liabilities_by_currency,
        "total_user_balances": total_user_balances,
        "pending_withdrawals": total_pending,
        "total_liabilities": total_user_balances + total_pending,
        "currencies_count": len(liabilities_by_currency),
    }


# =============================================================================
# Order Expenses Detail
# =============================================================================


@router.get("/accounting/orders/{order_id}/expenses")
async def get_order_expenses(order_id: str, admin=Depends(verify_admin)):
    """Get detailed expense breakdown for a specific order."""
    db = get_database()

    result = (
        await db.client.table("order_expenses")
        .select("*")
        .eq("order_id", order_id)
        .single()
        .execute()
    )

    if not result.data:
        return {"error": "No expenses found for this order"}

    return result.data


@router.post("/accounting/orders/{order_id}/recalculate")
async def recalculate_order_expenses(order_id: str, admin=Depends(verify_admin)):
    """Recalculate expenses for a specific order."""
    db = get_database()

    await db.client.rpc("calculate_order_expenses", {"p_order_id": order_id}).execute()

    # Fetch updated expenses
    expenses = (
        await db.client.table("order_expenses")
        .select("*")
        .eq("order_id", order_id)
        .single()
        .execute()
    )

    return {"success": True, "expenses": expenses.data}


@router.post("/accounting/recalculate-all")
async def recalculate_all_expenses(admin=Depends(verify_admin)):
    """Recalculate expenses for all delivered orders."""
    db = get_database()

    # Get all delivered orders
    orders = await db.client.table("orders").select("id").eq("status", "delivered").execute()

    count = 0
    for order in orders.data or []:
        await db.client.rpc("calculate_order_expenses", {"p_order_id": order["id"]}).execute()
        count += 1

    return {"success": True, "orders_processed": count}


# =============================================================================
# Expenses Management
# =============================================================================


@router.get("/accounting/expenses")
async def get_expenses(
    days: int = Query(30, ge=1, le=365), category: str | None = None, admin=Depends(verify_admin)
):
    """Get direct expenses (non-COGS)."""
    db = get_database()

    start_date = datetime.now(UTC) - timedelta(days=days)

    query = db.client.table("expenses").select("*").gte("date", start_date.isoformat())

    if category:
        query = query.eq("category", category)

    result = await query.order("date", desc=True).execute()

    data = result.data or []

    # Aggregate by category
    by_category = {}
    for exp in data:
        cat = exp.get("category", "other")
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += float(exp.get("amount_usd", 0))

    return {"expenses": data, "by_category": by_category, "total": sum(by_category.values())}


@router.post("/accounting/expenses")
async def create_expense(expense: ExpenseCreate, admin=Depends(verify_admin)):
    """Create a new expense entry."""
    db = get_database()

    # Convert to USD if needed
    amount_usd = expense.amount
    if expense.currency != "USD":
        # Get exchange rate
        rate_result = (
            await db.client.table("exchange_rates")
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
        "date": expense.date or datetime.now(UTC).date().isoformat(),
    }

    result = await db.client.table("expenses").insert(data).execute()

    return {"success": True, "expense": result.data[0] if result.data else data}


# =============================================================================
# Summary Report
# =============================================================================


@router.get("/accounting/report")
async def get_accounting_report(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    admin=Depends(verify_admin),
):
    """
    Get comprehensive accounting report for a period.
    Includes ALL costs: COGS, Acquiring, Referrals, Reserves, Review Cashbacks, Replacements.
    """
    db = get_database()

    # Determine date range
    now = datetime.now(UTC)
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=365)

    # Get orders with expenses and currency snapshot fields
    orders_result = (
        await db.client.table("orders")
        .select(
            "id, amount, original_price, discount_percent, created_at, fiat_currency, fiat_amount, exchange_rate_snapshot, order_expenses(*)"
        )
        .eq("status", "delivered")
        .gte("created_at", start_date.isoformat())
        .execute()
    )

    orders = orders_result.data or []

    # Group orders by currency for breakdown
    orders_by_currency = {}
    for order in orders:
        # Use fiat_currency if available, otherwise default to "USD"
        currency = order.get("fiat_currency") or "USD"
        if currency not in orders_by_currency:
            orders_by_currency[currency] = {
                "orders": [],
                "revenue_usd": 0.0,
                "revenue_gross_usd": 0.0,
                "revenue_fiat": 0.0,  # Real amount in payment currency
                "orders_count": 0,
            }
        orders_by_currency[currency]["orders"].append(order)
        orders_by_currency[currency]["revenue_usd"] += float(order.get("amount", 0))

        # Calculate gross using ONLY promo_discount (ignore MSRP)
        expenses = order.get("order_expenses")
        promo_discount_usd = 0.0
        if expenses:
            if isinstance(expenses, list):
                expenses = expenses[0] if expenses else {}
            promo_discount_usd = float(expenses.get("promo_discount_amount", 0))

        orders_by_currency[currency]["revenue_gross_usd"] += (
            float(order.get("amount", 0)) + promo_discount_usd
        )

        fiat_amount = order.get("fiat_amount")
        if fiat_amount is not None:
            orders_by_currency[currency]["revenue_fiat"] += float(fiat_amount)
        else:
            # Fallback: if no fiat_amount, assume it's USD (equal to amount)
            orders_by_currency[currency]["revenue_fiat"] += float(order.get("amount", 0))
        orders_by_currency[currency]["orders_count"] += 1

    # Build currency_breakdown for response
    currency_breakdown = {}
    for currency, data in orders_by_currency.items():
        currency_breakdown[currency] = {
            "orders_count": data["orders_count"],
            "revenue_usd": round(data["revenue_usd"], 2),
            "revenue_fiat": round(data["revenue_fiat"], 2),
            "revenue_gross_usd": round(data["revenue_gross_usd"], 2),
        }

    # Calculate totals
    revenue = sum(float(o.get("amount", 0)) for o in orders)

    # Calculate revenue_gross from breakdowns
    revenue_gross = sum(data["revenue_gross_usd"] for data in orders_by_currency.values())
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
    insurance_result = (
        await db.client.table("insurance_revenue")
        .select("price")
        .gte("created_at", start_date.isoformat())
        .execute()
    )
    insurance_revenue = sum(float(i.get("price", 0)) for i in (insurance_result.data or []))

    # Get other expenses
    other_expenses_result = (
        await db.client.table("expenses")
        .select("amount_usd, category")
        .gte("date", start_date.date().isoformat())
        .execute()
    )

    other_expenses = sum(float(e.get("amount_usd", 0)) for e in (other_expenses_result.data or []))

    # Expenses by category
    expenses_by_category = {}
    for e in other_expenses_result.data or []:
        cat = e.get("category", "other")
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + float(e.get("amount_usd", 0))

    # Calculate profits
    gross_profit = revenue - cogs
    operating_expenses_total = (
        acquiring + referrals + reserves + review_cashbacks + replacement_costs
    )
    operating_profit = gross_profit - operating_expenses_total
    net_profit = operating_profit - other_expenses + insurance_revenue

    # Get liabilities by currency (multi-currency!)
    liabilities_by_currency: dict = {}

    # User balances
    try:
        balances_result = (
            await db.client.table("users")
            .select(SELECT_BALANCE_FIELDS)
            .gt("balance", 0)
            .execute()
        )

        for user in balances_result.data or []:
            curr = user.get("balance_currency") or "USD"
            balance = float(user.get("balance", 0))

            if curr not in liabilities_by_currency:
                liabilities_by_currency[curr] = {
                    "user_balances": 0.0,
                    "pending_withdrawals": 0.0,
                }
            liabilities_by_currency[curr]["user_balances"] += balance
    except Exception as e:
        logger.warning("Failed to get user balances for report: %s", e)

    # Pending withdrawals
    try:
        withdrawals_result = (
            await db.client.table("withdrawal_requests")
            .select(SELECT_WITHDRAWAL_FIELDS)
            .eq("status", "pending")
            .execute()
        )

        for w in withdrawals_result.data or []:
            curr = w.get("balance_currency") or "USD"
            amount = float(w.get("amount_debited", 0))

            if curr not in liabilities_by_currency:
                liabilities_by_currency[curr] = {
                    "user_balances": 0.0,
                    "pending_withdrawals": 0.0,
                }
            liabilities_by_currency[curr]["pending_withdrawals"] += amount
    except Exception as e:
        logger.warning("Failed to get withdrawals for report: %s", e)

    # Calculate totals per currency
    for curr_data in liabilities_by_currency.values():
        curr_data["user_balances"] = round(curr_data["user_balances"], 2)
        curr_data["pending_withdrawals"] = round(curr_data["pending_withdrawals"], 2)
        curr_data["total"] = curr_data["user_balances"] + curr_data["pending_withdrawals"]

    # Legacy totals
    total_user_balances = sum(d["user_balances"] for d in liabilities_by_currency.values())
    total_pending_withdrawals = sum(
        d["pending_withdrawals"] for d in liabilities_by_currency.values()
    )

    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
        "orders_count": len(orders),
        # Currency breakdown (revenue)
        "currency_breakdown": currency_breakdown,
        # Income Statement (expenses in USD)
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
                "total": round(operating_expenses_total, 2),
            },
            "operating_profit": round(operating_profit, 2),
            "operating_margin_pct": round(
                (operating_profit / revenue * 100) if revenue > 0 else 0, 2
            ),
            "other_expenses": round(other_expenses, 2),
            "other_expenses_by_category": {k: round(v, 2) for k, v in expenses_by_category.items()},
            "net_profit": round(net_profit, 2),
            "net_margin_pct": round((net_profit / revenue * 100) if revenue > 0 else 0, 2),
        },
        # Balance Sheet Items - MULTI-CURRENCY!
        "liabilities": {
            # NEW: breakdown by currency
            "by_currency": liabilities_by_currency,
            # Legacy fields (sum, not converted)
            "user_balances": total_user_balances,
            "pending_withdrawals": total_pending_withdrawals,
            "total": total_user_balances + total_pending_withdrawals,
        },
        # Key Metrics
        "metrics": {
            "avg_order_value": round(revenue / len(orders), 2) if orders else 0,
            "cogs_per_order": round(cogs / len(orders), 2) if orders else 0,
            "acquiring_pct": round((acquiring / revenue * 100) if revenue > 0 else 0, 2),
            "referral_pct": round((referrals / revenue * 100) if revenue > 0 else 0, 2),
            "cashback_pct": round((review_cashbacks / revenue * 100) if revenue > 0 else 0, 2),
            "discount_rate_pct": round(
                (total_discounts / revenue_gross * 100) if revenue_gross > 0 else 0, 2
            ),
        },
    }
