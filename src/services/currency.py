"""
Currency Conversion Service

Handles currency conversion based on user language and caches exchange rates.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Union
import os
from datetime import datetime, timedelta

from src.services.money import to_decimal, to_float, round_money

# Language to Currency mapping
LANGUAGE_TO_CURRENCY: Dict[str, str] = {
    "ru": "RUB",      # Русский → Рубли
    "uk": "UAH",      # Украинский → Гривны
    "en": "USD",      # Английский → Доллары
    "de": "EUR",      # Немецкий → Евро
    "fr": "EUR",      # Французский → Евро
    "es": "EUR",      # Испанский → Евро
    "tr": "TRY",      # Турецкий → Лиры
    "ar": "AED",      # Арабский → Дирхамы
    "hi": "INR",      # Хинди → Рупии
    "be": "RUB",      # Белорусский → Рубли
    "kk": "RUB",      # Казахский → Рубли
}

# Default exchange rates (fallback if API unavailable)
# Rates are relative to USD (1 USD = X currency)
DEFAULT_RATES: Dict[str, float] = {
    "USD": 1.0,
    "RUB": 90.0,      # 1 USD = 90 RUB
    "EUR": 0.92,      # 1 USD = 0.92 EUR
    "UAH": 38.0,      # 1 USD = 38 UAH
    "TRY": 32.0,      # 1 USD = 32 TRY
    "AED": 3.67,      # 1 USD = 3.67 AED
    "INR": 83.0,      # 1 USD = 83 INR
}


class CurrencyService:
    """Service for currency conversion and rate management."""
    
    def __init__(self, redis_client=None):
        """
        Initialize currency service.
        
        Args:
            redis_client: Optional Redis client for caching rates
        """
        self.redis = redis_client
        self.language_to_currency = LANGUAGE_TO_CURRENCY
        self.default_rates = DEFAULT_RATES
    
    def get_user_currency(self, language_code: Optional[str]) -> str:
        """
        Get currency code for user's language.
        
        Args:
            language_code: User's language code (e.g., "ru", "en")
            
        Returns:
            Currency code (e.g., "RUB", "USD")
        """
        if not language_code:
            return "USD"
        
        # Normalize language code (e.g., "ru-RU" -> "ru")
        lang = language_code.split("-")[0].lower()
        return self.language_to_currency.get(lang, "USD")
    
    async def get_exchange_rate(self, target_currency: str) -> float:
        """
        Get exchange rate for target currency (relative to USD).
        
        Args:
            target_currency: Target currency code
            
        Returns:
            Exchange rate (1 USD = X target_currency)
        """
        if target_currency == "USD":
            return 1.0
        
        # Try to get from cache first
        if self.redis:
            try:
                cached_rate = await self._get_cached_rate(target_currency)
                if cached_rate:
                    return float(cached_rate)
            except Exception as e:
                print(f"Warning: Failed to get cached rate: {e}")
        
        # Try to fetch from external API
        try:
            rate = await self._fetch_exchange_rate(target_currency)
            if rate:
                # Cache the rate for 1 hour
                if self.redis:
                    await self._cache_rate(target_currency, rate)
                return rate
        except Exception as e:
            print(f"Warning: Failed to fetch exchange rate: {e}")
        
        # Fallback to default rates
        return self.default_rates.get(target_currency, 1.0)
    
    async def _get_cached_rate(self, currency: str) -> Optional[str]:
        """Get cached exchange rate from Redis."""
        if not self.redis:
            return None
        
        try:
            # AsyncRedis from upstash-redis
            key = f"currency:rate:{currency}"
            result = await self.redis.get(key)
            return result if result else None
        except Exception as e:
            print(f"Warning: Failed to get cached rate: {e}")
            return None
    
    async def _cache_rate(self, currency: str, rate: float):
        """Cache exchange rate in Redis with 1 hour TTL."""
        if not self.redis:
            return
        
        try:
            key = f"currency:rate:{currency}"
            # AsyncRedis setex method
            await self.redis.setex(key, 3600, str(rate))
        except Exception as e:
            print(f"Warning: Failed to cache rate: {e}")
    
    async def _fetch_exchange_rate(self, target_currency: str) -> Optional[float]:
        """
        Fetch exchange rate from external API.
        
        Currently uses free API: exchangerate-api.com
        Can be replaced with paid API for better reliability.
        """
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Free API: https://api.exchangerate-api.com/v4/latest/USD
                response = await client.get(
                    "https://api.exchangerate-api.com/v4/latest/USD"
                )
                response.raise_for_status()
                data = response.json()
                rates = data.get("rates", {})
                return rates.get(target_currency)
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
            return None
    
    async def convert_price(
        self, 
        price_usd: Union[float, Decimal, str, int], 
        target_currency: str,
        round_to_int: bool = False
    ) -> float:
        """
        Convert price from USD to target currency.
        
        Args:
            price_usd: Price in USD (any numeric type)
            target_currency: Target currency code
            round_to_int: If True, round to integer (for RUB, UAH, etc.)
            
        Returns:
            Converted price as float (for JSON serialization)
        """
        decimal_price = to_decimal(price_usd)
        
        if target_currency == "USD":
            return to_float(decimal_price)
        
        rate = await self.get_exchange_rate(target_currency)
        converted = decimal_price * to_decimal(rate)
        
        # Round based on currency using Decimal quantize
        should_round_int = round_to_int or target_currency in ["RUB", "UAH", "TRY", "INR"]
        rounded = round_money(converted, to_int=should_round_int)
        return to_float(rounded)
    
    def format_price(self, price: Union[float, Decimal, str, int], currency: str) -> str:
        """
        Format price with currency symbol.
        
        Args:
            price: Price value (any numeric type)
            currency: Currency code
            
        Returns:
            Formatted price string
        """
        decimal_price = to_decimal(price)
        
        symbols = {
            "USD": "$",
            "RUB": "₽",
            "EUR": "€",
            "UAH": "₴",
            "TRY": "₺",
            "INR": "₹",
            "AED": "د.إ",
        }
        
        symbol = symbols.get(currency, currency)
        
        # Format number
        if currency in ["RUB", "UAH", "TRY", "INR"]:
            formatted = f"{int(round_money(decimal_price, to_int=True)):,}"
        else:
            formatted = f"{to_float(round_money(decimal_price)):,.2f}"
        
        # Place symbol based on currency
        if currency in ["USD", "EUR", "GBP"]:
            return f"{symbol}{formatted}"
        else:
            return f"{formatted} {symbol}"


# Global instance (will be initialized with Redis if available)
_currency_service: Optional[CurrencyService] = None


def get_currency_service(redis_client=None) -> CurrencyService:
    """Get or create global currency service instance."""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService(redis_client)
    return _currency_service

