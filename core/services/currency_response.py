"""
Unified Currency Response System

This module provides a single source of truth for currency handling.
All monetary values are stored in USD and converted for display.

Architecture:
- Database stores ALL amounts in USD
- API returns both USD amount and display amount
- Frontend uses USD for comparisons, display amount for UI
- Exchange rate is cached in Redis for 1 hour

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
from core.logging import get_logger

logger = get_logger(__name__)


# Currency symbols mapping
CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "RUB": "₽",
    "EUR": "€",
    "UAH": "₴",
    "TRY": "₺",
    "INR": "₹",
    "AED": "د.إ",
    "GBP": "£",
    "CNY": "¥",
    "JPY": "¥",
    "KRW": "₩",
    "BRL": "R$",
}

# Currencies that should be displayed as integers (no decimals)
INTEGER_CURRENCIES = {"RUB", "UAH", "TRY", "INR", "JPY", "KRW"}

# Language to default currency mapping
LANGUAGE_TO_CURRENCY: Dict[str, str] = {
    "ru": "RUB",
    "be": "RUB",
    "kk": "RUB",
    "uk": "UAH",
    "tr": "TRY",
    "hi": "INR",
    "ar": "AED",
    # All others default to USD
}


class AmountResponse(TypedDict):
    """Typed dict for amount response."""
    usd: float
    display: float
    formatted: str


@dataclass
class CurrencyFormatter:
    """
    Unified currency formatter for API responses.
    
    This is the ONLY place where currency conversion logic should exist.
    All API endpoints should use this for consistent currency handling.
    """
    currency: str
    exchange_rate: float
    
    @classmethod
    async def create(
        cls,
        user_telegram_id: Optional[int],
        db,
        redis = None,
        preferred_currency: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> "CurrencyFormatter":
        """
        Factory method to create CurrencyFormatter for a user.
        
        Priority for currency:
        1. preferred_currency param (explicit override)
        2. User's preferred_currency from DB
        3. Language-based default
        4. USD fallback
        """
        from core.services.currency import get_currency_service
        
        currency = "USD"
        exchange_rate = 1.0
        
        try:
            # Get user preferences from DB if telegram_id provided
            user_preferred = preferred_currency
            user_lang = language_code or "en"
            
            if user_telegram_id and not preferred_currency:
                db_user = await db.get_user_by_telegram_id(user_telegram_id)
                if db_user:
                    user_preferred = getattr(db_user, 'preferred_currency', None)
                    user_lang = getattr(db_user, 'interface_language', None) or \
                               getattr(db_user, 'language_code', 'en') or 'en'
            
            # Determine currency
            if user_preferred:
                currency = user_preferred.upper()
            else:
                # Language-based fallback
                lang = user_lang.split("-")[0].lower() if user_lang else "en"
                currency = LANGUAGE_TO_CURRENCY.get(lang, "USD")
            
            # Get exchange rate
            if currency != "USD" and redis:
                currency_service = get_currency_service(redis)
                exchange_rate = await currency_service.get_exchange_rate(currency)
                
        except Exception as e:
            logger.warning(f"Currency setup failed: {e}, using USD")
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
        """Format amount with currency symbol."""
        if amount is None:
            amount = 0
            
        decimal_amount = to_decimal(amount)
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency)
        
        # Format number
        if self.currency in INTEGER_CURRENCIES:
            formatted = f"{int(round_money(decimal_amount, to_int=True)):,}"
        else:
            formatted = f"{to_float(round_money(decimal_amount)):,.2f}"
        
        # Place symbol based on currency convention
        if self.currency in ["USD", "EUR", "GBP", "CNY", "JPY"]:
            return f"{symbol}{formatted}"
        else:
            return f"{formatted} {symbol}"
    
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
    """
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    
    if currency in INTEGER_CURRENCIES:
        formatted = f"{int(to_decimal(amount)):,}"
    else:
        formatted = f"{to_float(to_decimal(amount)):,.2f}"
    
    if currency in ["USD", "EUR", "GBP", "CNY", "JPY"]:
        return f"{symbol}{formatted}"
    else:
        return f"{formatted} {symbol}"

