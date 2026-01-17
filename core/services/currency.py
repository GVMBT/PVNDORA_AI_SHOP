"""Currency Service - Simplified for RUB-only.

All amounts are now in RUB. This service provides backwards-compatible
interface while always returning RUB values.

TODO(tech-debt):
- Remove unused parameters (target_currency, from_currency, to_currency)
  from method signatures after full migration verification
- Rename fields like "turnover_usd", "level_threshold_usd" to "_rub" in DB
- Remove LANGUAGE_TO_CURRENCY mapping (no longer needed)
"""

from decimal import Decimal
from typing import Any

from core.logging import get_logger
from core.services.money import round_money, to_decimal, to_float

logger = get_logger(__name__)

# =============================================================================
# SINGLE SOURCE OF TRUTH: RUB Only Configuration
# =============================================================================

# All currencies now map to RUB
LANGUAGE_TO_CURRENCY: dict[str, str] = {
    "ru": "RUB",
    "be": "RUB",
    "kk": "RUB",
    "en": "RUB",  # All languages now use RUB
}

# Currency symbol - only RUB
CURRENCY_SYMBOLS: dict[str, str] = {
    "RUB": "₽",
}

# All currencies displayed as integers (RUB)
INTEGER_CURRENCIES = {"RUB"}

# Fixed rate: RUB is base currency
FALLBACK_RATES: dict[str, float] = {
    "RUB": 1.0,
}


class CurrencyService:
    """Simplified currency service - RUB only.

    All methods return RUB values. Currency conversion is no longer performed.
    This provides backwards compatibility while simplifying the codebase.
    """

    def __init__(self, redis_client: Any = None) -> None:
        """Initialize currency service (redis no longer needed for rates)."""
        self.redis = redis_client
        self.language_to_currency = LANGUAGE_TO_CURRENCY

    def get_user_currency(
        self,
        language_code: str | None = None,
        preferred_currency: str | None = None,
    ) -> str:
        """Always returns RUB. Parameters ignored after RUB-only migration."""
        _ = language_code, preferred_currency  # Unused after RUB-only migration
        return "RUB"

    def get_exchange_rate(self, _target_currency: str) -> float:
        """Always returns 1.0 (RUB is base currency). Parameter ignored after RUB-only migration."""
        return 1.0

    def convert_price(
        self,
        price_rub: float | Decimal | str,
        _target_currency: str = "RUB",
        round_to_int: bool = True,
    ) -> float:
        """No conversion needed - returns the RUB price as-is.

        Args:
            price_rub: Price in RUB
            target_currency: Ignored (always RUB)
            round_to_int: If True, round to integer (default for RUB)

        Returns:
            Price as float (rounded to integer for RUB)

        """
        decimal_price = to_decimal(price_rub)
        if round_to_int:
            rounded = round_money(decimal_price, to_int=True)
        else:
            rounded = round_money(decimal_price)
        return to_float(rounded)

    def format_price(self, price: float | Decimal | str, currency: str = "RUB") -> str:
        _ = currency  # Unused after RUB-only migration
        """
        Format price with RUB symbol.

        Args:
            price: Price value (any numeric type)
            currency: Ignored (always RUB)

        Returns:
            Formatted price string like "1,234 ₽"
        """
        decimal_price = to_decimal(price)
        formatted = f"{int(round_money(decimal_price, to_int=True)):,}"
        return f"{formatted} ₽"

    # =========================================================================
    # Anchor Pricing Methods (simplified - always returns price directly)
    # =========================================================================

    def get_anchor_price(
        self,
        product: dict[str, Any] | Any,
        _target_currency: str = "RUB",
    ) -> Decimal:
        """Get product price in RUB (always the price field now).

        Args:
            product: Product dict or object with 'price'
            target_currency: Ignored (always RUB)

        Returns:
            Price in RUB as Decimal

        """
        if hasattr(product, "__getitem__"):
            base_price = product.get("price", 0)
        else:
            base_price = getattr(product, "price", 0)

        return to_decimal(base_price)

    def has_anchor_price(self, _product: dict[str, Any] | Any, currency: str) -> bool:
        """Always returns True for RUB (price is always set)."""
        return currency == "RUB"

    def get_anchor_threshold(
        self,
        settings: dict[str, Any] | Any,
        _target_currency: str,
        level: int,
    ) -> Decimal:
        """Get referral threshold for specified level in RUB.

        Args:
            settings: Referral settings with level thresholds
            target_currency: Ignored (always RUB)
            level: Level number (2 or 3)

        Returns:
            Threshold in RUB as Decimal

        """
        if level not in [2, 3]:
            msg = f"Level must be 2 or 3, got {level}"
            raise ValueError(msg)

        # Thresholds are now stored in RUB
        if hasattr(settings, "__getitem__"):
            threshold_key = f"level{level}_threshold_usd"  # Named _usd for backwards compat
            threshold = settings.get(threshold_key, 25000 if level == 2 else 100000)
        else:
            threshold_attr = f"level{level}_threshold_usd"
            threshold = getattr(settings, threshold_attr, 25000 if level == 2 else 100000)

        return to_decimal(threshold)

    def snapshot_rate(self, _currency: str) -> float:
        """Always returns 1.0 (no rate conversion needed). Parameter ignored after RUB-only migration."""
        return 1.0

    def get_balance_currency(self, language_code: str | None = None) -> str:
        """Always returns RUB. Parameter ignored after RUB-only migration."""
        _ = language_code  # Unused after RUB-only migration
        return "RUB"

    def convert_balance(
        self,
        _from_currency: str,
        _to_currency: str,
        amount: float | Decimal | str,
    ) -> Decimal:
        """No conversion needed - all balances are in RUB.
        Parameters from_currency and to_currency are ignored after RUB-only migration.

        Args:
            from_currency: Ignored
            to_currency: Ignored
            amount: Amount in RUB

        Returns:
            Same amount rounded as Decimal

        """
        decimal_amount = to_decimal(amount)
        return round_money(decimal_amount, to_int=True)

    def convert_to_base_currency(
        self,
        amount: float | Decimal | str,
        _from_currency: str = "RUB",
    ) -> Decimal:
        """No conversion - RUB is now base currency."""
        return round_money(to_decimal(amount), to_int=True)

    # =========================================================================
    # USDT Methods (for withdrawals)
    # =========================================================================

    async def get_usdt_rate(self) -> float:
        """Get current USDT/RUB exchange rate for withdrawals."""
        # For withdrawals, we need RUB to USDT rate
        # This should be fetched from exchange or set manually
        # Default: ~100 RUB per USDT (approximate)
        if self.redis:
            try:
                key = "currency:rate:USDT_RUB"
                result = await self.redis.get(key)
                if result:
                    return float(result)
            except Exception:
                pass

        # Fallback rate (should be updated periodically)
        # Updated Jan 2026: ~90-95 RUB per USDT (approximate current rate)
        return 90.0  # 1 USDT ≈ 90 RUB (approximate, should be fetched from API)

    async def calculate_withdrawal_usdt(
        self,
        amount_in_balance_currency: float | Decimal,
        balance_currency: str = "RUB",  # NOSONAR - kept for API compatibility
        network_fee: float | None = None,
    ) -> dict[str, Any]:
        """Calculate withdrawal payout in USDT from RUB balance.

        Formula: amount_to_pay = (amount_rub / usdt_rub_rate) - network_fee

        Args:
            amount_in_balance_currency: Amount in RUB
            balance_currency: Ignored (always RUB), kept for API compatibility
            network_fee: TRC20 network fee in USDT (default 1.5)

        Returns:
            Dict with calculation details

        """
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT

        amount_decimal = to_decimal(amount_in_balance_currency)

        # Get USDT/RUB rate (how many RUB per 1 USDT)
        usdt_rub_rate = await self.get_usdt_rate()

        # Calculate USDT equivalent
        amount_usdt_gross = to_float(amount_decimal) / usdt_rub_rate

        # Apply network fee
        amount_usdt_net = max(0, amount_usdt_gross - network_fee)

        # For backwards compatibility, calculate USD equivalent
        # Assuming USDT ≈ USD
        amount_usd = amount_usdt_gross

        return {
            "amount_usd": round(amount_usd, 2),
            "amount_usdt": round(amount_usdt_net, 2),
            "amount_usdt_gross": round(amount_usdt_gross, 2),
            "exchange_rate": 1.0,  # RUB is base, no conversion
            "usdt_rate": usdt_rub_rate,  # RUB per USDT
            "network_fee": network_fee,
        }

    async def calculate_min_withdrawal_amount(
        self,
        balance_currency: str = "RUB",  # NOSONAR - kept for API compatibility
        min_usdt_after_fees: float | None = None,
        network_fee: float | None = None,
        usdt_rate: float | None = None,
    ) -> dict[str, Any]:
        """Calculate minimum withdrawal amount in RUB.

        Formula: min_rub = (min_usdt_after_fees + network_fee) * usdt_rub_rate
        """
        if min_usdt_after_fees is None:
            min_usdt_after_fees = MIN_USDT_AFTER_FEES
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT

        # Get USDT rate if not provided
        if usdt_rate is None:
            usdt_rate = await self.get_usdt_rate()

        # Calculate minimum USDT needed (gross)
        min_usdt_gross = min_usdt_after_fees + network_fee

        # Calculate minimum RUB
        min_rub = min_usdt_gross * usdt_rate

        return {
            "min_amount": round(min_rub, 0),  # RUB is integer
            "min_usd": round(min_usdt_gross, 2),  # ~= USDT
            "min_usdt_gross": round(min_usdt_gross, 2),
            "min_usdt_after_fees": min_usdt_after_fees,
            "network_fee": network_fee,
            "exchange_rate": 1.0,
            "usdt_rate": usdt_rate,
        }

    async def calculate_max_withdrawal_amount(
        self,
        balance: float,
        _balance_currency: str = "RUB",
        network_fee: float | None = None,
        min_usdt_after_fees: float | None = None,
    ) -> dict[str, Any]:
        """Calculate maximum withdrawal amount from RUB balance."""
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT
        if min_usdt_after_fees is None:
            min_usdt_after_fees = MIN_USDT_AFTER_FEES

        withdrawal_calc = await self.calculate_withdrawal_usdt(
            amount_in_balance_currency=balance,
            balance_currency="RUB",
            network_fee=network_fee,
        )

        if withdrawal_calc["amount_usdt"] < min_usdt_after_fees:
            return {
                "max_amount": 0.0,
                "max_usdt_net": 0.0,
                "withdrawal_calc": withdrawal_calc,
                "can_withdraw": False,
            }

        return {
            "max_amount": balance,
            "max_usdt_net": withdrawal_calc["amount_usdt"],
            "withdrawal_calc": withdrawal_calc,
            "can_withdraw": True,
        }


# ==================== WITHDRAWAL CONSTANTS ====================
NETWORK_FEE_USDT = 1.5  # TRC20 network fee
MIN_USDT_AFTER_FEES = 8.5  # Minimum USDT user must receive after fees
MIN_WITHDRAWAL_USD = MIN_USDT_AFTER_FEES + NETWORK_FEE_USDT  # ~10 USDT total


# Global instance
_currency_service: CurrencyService | None = None


def get_currency_service(redis_client: Any = None) -> CurrencyService:
    """Get or create global currency service instance."""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService(redis_client)
    return _currency_service
