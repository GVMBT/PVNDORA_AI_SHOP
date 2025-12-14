"""
Currency Conversion Service

Handles currency conversion based on user language and caches exchange rates.
"""
from decimal import Decimal
from typing import Dict, Optional, Union

from core.services.money import to_decimal, to_float, round_money
from core.logging import get_logger

logger = get_logger(__name__)

# Language to Currency mapping
# Simplified logic: Russian → RUB, all others → USD
LANGUAGE_TO_CURRENCY: Dict[str, str] = {
    "ru": "RUB",      # Русский → Рубли
    "be": "RUB",      # Белорусский → Рубли
    "kk": "RUB",      # Казахский → Рубли
    # All other languages default to USD
    "uk": "USD",      # Украинский → USD
    "en": "USD",      # Английский → USD
    "de": "USD",      # Немецкий → USD
    "fr": "USD",      # Французский → USD
    "es": "USD",      # Испанский → USD
    "tr": "USD",      # Турецкий → USD
    "ar": "USD",      # Арабский → USD
    "hi": "USD",      # Хинди → USD
}

# Note: Exchange rates are fetched from exchangerate-api.com
# No hardcoded fallback rates - always use real-time data


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
    
    def get_user_currency(self, language_code: Optional[str] = None, preferred_currency: Optional[str] = None) -> str:
        """
        Get currency code for user.
        
        Priority:
        1. preferred_currency (if set by user)
        2. language_code mapping (if provided)
        3. Default to USD
        
        Args:
            language_code: User's language code (e.g., "ru", "en")
            preferred_currency: User's preferred currency from DB (e.g., "RUB", "USD")
            
        Returns:
            Currency code (e.g., "RUB", "USD")
        """
        # Use preferred currency if set
        if preferred_currency:
            return preferred_currency.upper()
        
        # Fallback to language-based currency
        # Simplified logic: Russian (ru/be/kk) → RUB, all others → USD
        if language_code:
            # Normalize language code (e.g., "ru-RU" -> "ru")
            lang = language_code.split("-")[0].lower()
            # Check if it's a Russian language variant
            if lang in ["ru", "be", "kk"]:
                return "RUB"
            # All other languages default to USD
            return "USD"
        
        return "USD"
    
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
                logger.warning(f"Failed to get cached rate: {e}")
        
        # Try to fetch from external API
        try:
            rate = await self._fetch_exchange_rate(target_currency)
            if rate:
                # Cache the rate for 1 hour
                if self.redis:
                    await self._cache_rate(target_currency, rate)
                return rate
        except Exception as e:
            logger.warning(f"Failed to fetch exchange rate for {target_currency}: {e}")
        
        # No fallback - if API unavailable, log error and return 1.0 (USD equivalent)
        # This will show prices in USD if conversion fails
        logger.error(f"Could not get exchange rate for {target_currency}, using 1.0 (USD)")
        return 1.0
    
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
            logger.warning(f"Failed to get cached rate: {e}")
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
            logger.warning(f"Failed to cache rate: {e}")
    
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
            logger.error(f"Error fetching exchange rate: {e}")
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

