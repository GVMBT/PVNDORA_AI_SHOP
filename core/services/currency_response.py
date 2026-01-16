"""Unified Currency Response System - RUB Only.

This module provides CurrencyFormatter for API responses.
All monetary values are stored and displayed in RUB.

Architecture:
- Database stores ALL amounts in RUB
- API returns amounts in RUB
- No currency conversion needed

Usage:
    from core.services.currency_response import CurrencyFormatter

    formatter = CurrencyFormatter.create(user_telegram_id, db, redis)

    # Format a single amount
    amount_response = formatter.format_amount(1000)
    # Returns: {"usd": 1000, "display": 1000, "formatted": "1 000 ₽"}

    # Add currency metadata to response
    response = formatter.with_currency({
        "items": [...],
        "total": 5000,
    })
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypedDict

from core.logging import get_logger
from core.services.currency import get_currency_service
from core.services.money import round_money, to_decimal, to_float

logger = get_logger(__name__)


def round_referral_threshold(
    threshold: float,
    _target_currency: str = "RUB",
    _exchange_rate: float = 1.0,
) -> float:
    """Return referral threshold in RUB.
    All thresholds are now stored in RUB directly.
    """
    return float(threshold)


class AmountResponse(TypedDict):
    """Typed dict for amount response."""

    usd: float  # Named 'usd' for backwards compatibility, actually RUB
    display: float
    formatted: str


@dataclass
class CurrencyFormatter:
    """Unified currency formatter for API responses.

    Simplified for RUB-only system.
    """

    currency: str = "RUB"
    exchange_rate: float = 1.0

    @classmethod
    def create(
        cls,
        user_telegram_id: int | None = None,  # Kept for backward compatibility
        db: Any = None,  # Kept for backward compatibility
        redis: Any = None,  # Kept for backward compatibility
        preferred_currency: str | None = None,  # Kept for backward compatibility
        language_code: str | None = None,  # Kept for backward compatibility
        db_user: Any = None,  # Kept for backward compatibility
        **kwargs: Any,  # Accept any additional kwargs for backward compatibility
    ) -> "CurrencyFormatter":
        """Factory method to create CurrencyFormatter.

        After RUB-only migration: Always returns RUB formatter (no conversion needed).
        All parameters are kept for backward compatibility but ignored.
        """
        _ = (
            user_telegram_id,
            db,
            redis,
            preferred_currency,
            language_code,
            db_user,
            kwargs,
        )  # Unused after RUB-only migration
        return cls(currency="RUB", exchange_rate=1.0)

    def convert(self, amount: float | Decimal | str | None) -> float:
        """No conversion needed - returns amount as-is (rounded)."""
        if amount is None:
            return 0.0
        decimal_amount = to_decimal(amount)
        rounded = round_money(decimal_amount, to_int=True)
        return to_float(rounded)

    def format(self, amount: float | Decimal | None) -> str:
        """Format amount with RUB symbol."""
        if amount is None:
            amount = 0
        currency_service = get_currency_service()
        return currency_service.format_price(amount, "RUB")

    def format_balance(self, amount: float | Decimal | None, currency: str = "RUB") -> str:
        """Format a balance amount with RUB symbol.

        Args:
            amount: The amount to format (in RUB)
            currency: Ignored (always RUB)

        Returns:
            Formatted string like "1 000 ₽"

        """
        if amount is None:
            amount = 0
        currency_service = get_currency_service()
        return currency_service.format_price(amount, "RUB")

    def format_amount(self, amount: float | Decimal | str | None) -> AmountResponse:
        """Format an amount for API response.

        Returns dict with amount in RUB.
        Note: 'usd' key is kept for backwards compatibility but contains RUB value.
        """
        if amount is None:
            amount = 0

        rub_value = self.convert(amount)

        return {
            "usd": rub_value,  # Backwards compatibility - actually RUB
            "display": rub_value,
            "formatted": self.format(rub_value),
        }

    def with_currency(self, response: dict[str, Any]) -> dict[str, Any]:
        """Add currency metadata to any response dict."""
        result = {
            **response,
            "currency": "RUB",
            "exchange_rate": 1.0,
        }

        # Convert _usd fields to display values (same value for RUB)
        for key, value in response.items():
            if key.endswith("_usd") and isinstance(value, (int, float, Decimal)):
                display_key = key[:-4]  # Remove '_usd' suffix
                if display_key not in response:
                    result[display_key] = self.convert(value)

        return result

    def format_price_response(
        self,
        price: float | Decimal,
        original_price: float | Decimal | None = None,
        discount_percent: int = 0,
    ) -> dict[str, Any]:
        """Format a complete price response for products/cart items."""
        price_rub = self.convert(price)
        response = {
            "price_usd": price_rub,  # Backwards compat - actually RUB
            "price": price_rub,
            "price_formatted": self.format(price_rub),
        }

        if original_price is not None:
            original_rub = self.convert(original_price)
            response["original_price_usd"] = original_rub  # Backwards compat
            response["original_price"] = original_rub

        if discount_percent:
            response["discount_percent"] = discount_percent

        return response


# Convenience function
def get_currency_formatter(
    user_telegram_id: int | None = None,
    db: Any = None,
    redis: Any = None,
    **kwargs: Any,
) -> CurrencyFormatter:
    """Get a CurrencyFormatter (always RUB)."""
    return CurrencyFormatter.create(user_telegram_id, db, redis, **kwargs)


def format_price_simple(amount: float | Decimal, _currency: str = "RUB") -> str:
    """Simple price formatting in RUB."""
    currency_service = get_currency_service()
    return currency_service.format_price(amount, "RUB")
