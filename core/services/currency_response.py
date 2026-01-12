"""
Unified Currency Response System

This module provides CurrencyFormatter for API responses.
All monetary values are stored in USD and converted for display.

Architecture:
- Database stores ALL amounts in USD
- API returns both USD amount and display amount
- Frontend uses USD for comparisons, display amount for UI
- Exchange rate is cached in Redis for 1 hour

IMPORTANT: Currency mappings and conversion logic is in core/services/currency.py
This module uses CurrencyService for all currency operations.

Usage:
    from core.services.currency_response import CurrencyFormatter

    formatter = await CurrencyFormatter.create(user_telegram_id, db, redis)
    
    # Format a single amount
    amount_response = formatter.format_amount(10.0)
    # Returns: {"usd": 10.0, "display": 794.0, "formatted": "794 ₽"}
    
    # Add currency metadata to response
    response = formatter.with_currency({
        "items": [...],
        "total_usd": 50.0,
    })
    # Adds: currency, exchange_rate, total (display)
"""

from decimal import Decimal
from typing import Dict, Any, Optional, Union, TypedDict
from dataclasses import dataclass

from core.services.money import to_decimal, to_float, round_money
# Import from single source of truth
from core.services.currency import (
    INTEGER_CURRENCIES, 
    get_currency_service
)
from core.logging import get_logger

logger = get_logger(__name__)


def round_referral_threshold(usd_threshold: float, target_currency: str, exchange_rate: float) -> float:
    """
    Round referral thresholds for display.
    
    Rules:
    - USD thresholds stay as-is (250, 1000)
    - RUB thresholds are rounded to nice values:
      * 250 USD → 20000 RUB (instead of ~19750-19780)
      * 1000 USD → 80000 RUB (instead of ~79000-79080)
    
    Args:
        usd_threshold: Threshold in USD (250 or 1000)
        target_currency: Target currency (RUB, USD, etc.)
        exchange_rate: Exchange rate for conversion
    
    Returns:
        Rounded threshold in target currency
    """
    if target_currency == "USD":
        return float(usd_threshold)
    
    if target_currency == "RUB":
        # Apply rounding rules for RUB
        if usd_threshold == 250:
            return 20000.0
        elif usd_threshold == 1000:
            return 80000.0
    
    # For other currencies, use normal conversion
    return round(usd_threshold * exchange_rate, 2)


class AmountResponse(TypedDict):
    """Typed dict for amount response."""
    usd: float
    display: float
    formatted: str


@dataclass
class CurrencyFormatter:
    """
    Unified currency formatter for API responses.
    
    Uses CurrencyService from core/services/currency.py for all operations.
    """
    currency: str
    exchange_rate: float
    
    @classmethod
    async def create(
        cls,
        user_telegram_id: Optional[int] = None,
        db = None,
        redis = None,
        preferred_currency: Optional[str] = None,
        language_code: Optional[str] = None,
        db_user = None  # OPTIMIZATION: Pass db_user directly to avoid duplicate DB query
    ) -> "CurrencyFormatter":
        """
        Factory method to create CurrencyFormatter for a user.
        
        Uses CurrencyService.get_user_currency() for currency determination.
        
        Args:
            user_telegram_id: Telegram user ID (used if db_user not provided)
            db: Database instance (used if db_user not provided)
            redis: Redis client
            preferred_currency: User's preferred currency (overrides db_user)
            language_code: User's language code (overrides db_user)
            db_user: User model object (OPTIMIZATION: pass directly to avoid duplicate query)
        """
        currency = "USD"
        exchange_rate = 1.0
        
        try:
            # Get user preferences from db_user if provided, otherwise from DB
            user_preferred = preferred_currency
            user_lang = language_code or "en"
            
            if db_user:
                # OPTIMIZATION: Use provided db_user (no DB query needed)
                if not preferred_currency:
                    user_preferred = getattr(db_user, 'preferred_currency', None)
                if not language_code:
                    user_lang = getattr(db_user, 'interface_language', None) or \
                               getattr(db_user, 'language_code', 'en') or 'en'
            elif user_telegram_id and db and not preferred_currency:
                # Fallback: Query DB if db_user not provided (backward compatibility)
                db_user_fetch = await db.get_user_by_telegram_id(user_telegram_id)
                if db_user_fetch:
                    user_preferred = getattr(db_user_fetch, 'preferred_currency', None)
                    user_lang = getattr(db_user_fetch, 'interface_language', None) or \
                               getattr(db_user_fetch, 'language_code', 'en') or 'en'
            
            # Use CurrencyService for currency determination (single source of truth)
            currency_service = get_currency_service(redis)
            currency = currency_service.get_user_currency(user_lang, user_preferred)
            
            # Log user identifier (telegram_id or db_user id)
            user_id_for_log = user_telegram_id or (getattr(db_user, 'telegram_id', None) if db_user else None)
            logger.info(f"CurrencyFormatter: user={user_id_for_log}, preferred={user_preferred}, currency={currency}")
            
            # Get exchange rate
            if currency != "USD":
                exchange_rate = await currency_service.get_exchange_rate(currency)
                logger.info(f"CurrencyFormatter: got exchange_rate={exchange_rate} for {currency}")
                
        except Exception as e:
            logger.error(f"Currency setup failed: {e}, using USD", exc_info=True)
            currency = "USD"
            exchange_rate = 1.0
        
        return cls(currency=currency, exchange_rate=exchange_rate)
    
    def convert(self, amount_usd: Union[float, Decimal, int, str]) -> float:
        """Convert USD amount to display currency."""
        if amount_usd is None:
            return 0.0
            
        decimal_amount = to_decimal(amount_usd)
        
        if self.currency == "USD":
            return to_float(decimal_amount)
        
        converted = decimal_amount * to_decimal(self.exchange_rate)
        
        # Round based on currency
        should_round_int = self.currency in INTEGER_CURRENCIES
        rounded = round_money(converted, to_int=should_round_int)
        
        return to_float(rounded)
    
    def format(self, amount: Union[float, Decimal, int]) -> str:
        """Format amount with currency symbol using CurrencyService."""
        if amount is None:
            amount = 0
        
        # Use CurrencyService.format_price for consistency
        currency_service = get_currency_service()
        return currency_service.format_price(amount, self.currency)
    
    def format_amount(self, amount_usd: Union[float, Decimal, int, str, None]) -> AmountResponse:
        """
        Format an amount for API response.
        
        Returns both USD value (for calculations) and display value (for UI).
        """
        if amount_usd is None:
            amount_usd = 0
            
        usd_value = to_float(to_decimal(amount_usd))
        display_value = self.convert(amount_usd)
        
        return {
            "usd": usd_value,
            "display": display_value,
            "formatted": self.format(display_value),
        }
    
    def with_currency(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add currency metadata to any response dict.
        
        Also converts any fields ending in '_usd' to display values.
        """
        result = {
            **response,
            "currency": self.currency,
            "exchange_rate": self.exchange_rate,
        }
        
        # Auto-convert _usd fields
        for key, value in response.items():
            if key.endswith("_usd") and isinstance(value, (int, float, Decimal)):
                display_key = key[:-4]  # Remove '_usd' suffix
                if display_key not in response:  # Don't overwrite existing
                    result[display_key] = self.convert(value)
        
        return result
    
    def format_price_response(
        self,
        price_usd: Union[float, Decimal],
        original_price_usd: Optional[Union[float, Decimal]] = None,
        discount_percent: int = 0
    ) -> Dict[str, Any]:
        """
        Format a complete price response for products/cart items.
        """
        response = {
            "price_usd": to_float(to_decimal(price_usd)),
            "price": self.convert(price_usd),
            "price_formatted": self.format(self.convert(price_usd)),
        }
        
        if original_price_usd is not None:
            response["original_price_usd"] = to_float(to_decimal(original_price_usd))
            response["original_price"] = self.convert(original_price_usd)
        
        if discount_percent:
            response["discount_percent"] = discount_percent
        
        return response


# Convenience function for simple cases
async def get_currency_formatter(
    user_telegram_id: Optional[int],
    db,
    redis = None,
    **kwargs
) -> CurrencyFormatter:
    """Get a CurrencyFormatter for a user."""
    return await CurrencyFormatter.create(user_telegram_id, db, redis, **kwargs)


def format_price_simple(
    amount: Union[float, Decimal, int],
    currency: str = "USD"
) -> str:
    """
    Simple price formatting without exchange rate.
    For use when you already have the converted amount.
    Delegates to CurrencyService.format_price for consistency.
    """
    currency_service = get_currency_service()
    return currency_service.format_price(amount, currency)

