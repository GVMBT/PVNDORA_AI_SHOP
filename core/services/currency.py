"""
Currency Conversion Service

Handles currency conversion based on user language and caches exchange rates.
Supports anchor pricing (fixed prices per currency) and rate snapshots for orders.
"""

from datetime import UTC
from decimal import Decimal
from typing import Any

from core.logging import get_logger
from core.services.money import round_money, to_decimal, to_float

logger = get_logger(__name__)

# =============================================================================
# SINGLE SOURCE OF TRUTH: Currency Configuration
# =============================================================================

# Language to Currency mapping
# Russian-speaking regions → RUB, all others → USD for simplicity
LANGUAGE_TO_CURRENCY: dict[str, str] = {
    "ru": "RUB",  # Русский → Рубли
    "be": "RUB",  # Белорусский → Рубли
    "kk": "RUB",  # Казахский → Рубли
    # All other languages default to USD for simplicity
    # (users can override via preferred_currency in profile)
}

# Currency symbols mapping
CURRENCY_SYMBOLS: dict[str, str] = {
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

# Note: Exchange rates are fetched from exchangerate-api.com
# Fallback rates used when API is unavailable (updated periodically)
# IMPORTANT: Keep these reasonably accurate - they're only used as last resort
FALLBACK_RATES: dict[str, float] = {
    "RUB": 80.0,  # ~80 RUB per 1 USD
    "EUR": 0.92,  # ~0.92 EUR per 1 USD
    "UAH": 41.0,  # ~41 UAH per 1 USD
    "TRY": 34.0,  # ~34 TRY per 1 USD
    "INR": 84.0,  # ~84 INR per 1 USD
    "AED": 3.67,  # ~3.67 AED per 1 USD (fixed rate)
    "GBP": 0.79,  # ~0.79 GBP per 1 USD
    "CNY": 7.25,  # ~7.25 CNY per 1 USD
    "JPY": 154.0,  # ~154 JPY per 1 USD
    "KRW": 1400.0,  # ~1400 KRW per 1 USD
    "BRL": 6.1,  # ~6.1 BRL per 1 USD
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

    def get_user_currency(
        self, language_code: str | None = None, preferred_currency: str | None = None
    ) -> str:
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

        Priority:
        1. Redis cache (fast, 1 hour TTL)
        2. Supabase exchange_rates table (authoritative source)
        3. External API (fallback, updates Supabase)
        4. Hardcoded fallback (last resort)

        Args:
            target_currency: Target currency code

        Returns:
            Exchange rate (1 USD = X target_currency)
        """
        if target_currency == "USD":
            return 1.0

        # 1. Try Redis cache first (fast path)
        if self.redis:
            try:
                cached_rate = await self._get_cached_rate(target_currency)
                if cached_rate:
                    return float(cached_rate)
            except Exception as e:
                logger.debug(f"Redis cache miss for {target_currency}: {e}")

        # 2. Try Supabase exchange_rates table (source of truth)
        try:
            rate = await self._get_rate_from_db(target_currency)
            if rate:
                logger.info(f"Got rate from DB: {target_currency}={rate}")
                # Cache in Redis for faster subsequent access
                if self.redis:
                    await self._cache_rate(target_currency, rate)
                return rate
            logger.debug(f"No rate in DB for {target_currency}")
        except Exception as e:
            logger.warning(f"Failed to get rate from DB for {target_currency}: {e}")

        # 3. Try to fetch from external API (and update DB)
        try:
            logger.info(f"Fetching rate from API for {target_currency}...")
            rate = await self._fetch_exchange_rate(target_currency)
            if rate:
                logger.info(f"Got rate from API: {target_currency}={rate}")
                if self.redis:
                    await self._cache_rate(target_currency, rate)
                # Also update DB for persistence
                await self._update_rate_in_db(target_currency, rate)
                return rate
            logger.warning(f"API returned no rate for {target_currency}")
        except Exception as e:
            logger.error(f"Failed to fetch exchange rate for {target_currency}: {e}", exc_info=True)

        # 4. Last resort: hardcoded fallback
        fallback_rate = FALLBACK_RATES.get(target_currency)
        if fallback_rate:
            logger.warning(f"Using fallback rate for {target_currency}: {fallback_rate}")
            return fallback_rate

        logger.error(f"No rate available for {target_currency}, using 1.0")
        return 1.0

    async def _get_rate_from_db(self, currency: str) -> float | None:
        """Get exchange rate from Supabase exchange_rates table."""
        try:
            from core.services.database import get_database

            db = get_database()
            result = (
                await db.client.table("exchange_rates")
                .select("rate")
                .eq("currency", currency)
                .single()
                .execute()
            )

            if result.data and isinstance(result.data, dict) and result.data.get("rate"):
                return float(result.data["rate"])
            return None
        except Exception as e:
            logger.debug(f"DB rate lookup failed for {currency}: {e}")
            return None

    async def _update_rate_in_db(self, currency: str, rate: float):
        """Update exchange rate in Supabase."""
        try:
            from datetime import datetime

            from core.services.database import get_database

            db = get_database()
            await (
                db.client.table("exchange_rates")
                .upsert(
                    {
                        "currency": currency,
                        "rate": rate,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"Failed to update rate in DB for {currency}: {e}")

    async def _get_cached_rate(self, currency: str) -> str | None:
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

    async def _fetch_exchange_rate(self, target_currency: str) -> float | None:
        """
        Fetch exchange rate from external API.

        Currently uses free API: exchangerate-api.com
        Can be replaced with paid API for better reliability.
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Free API: https://api.exchangerate-api.com/v4/latest/USD
                response = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
                response.raise_for_status()
                data = response.json()
                rates = data.get("rates", {})
                rate_value = rates.get(target_currency)
                return float(rate_value) if rate_value is not None else None
        except Exception:
            logger.exception("Error fetching exchange rate")
            return None

    async def convert_price(
        self,
        price_usd: float | Decimal | str,
        target_currency: str,
        round_to_int: bool = False,
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

    def format_price(self, price: float | Decimal | str, currency: str) -> str:
        """
        Format price with currency symbol.

        Args:
            price: Price value (any numeric type)
            currency: Currency code

        Returns:
            Formatted price string
        """
        decimal_price = to_decimal(price)
        symbol = CURRENCY_SYMBOLS.get(currency, currency)

        # Format number
        if currency in INTEGER_CURRENCIES:
            formatted = f"{int(round_money(decimal_price, to_int=True)):,}"
        else:
            formatted = f"{to_float(round_money(decimal_price)):,.2f}"

        # Place symbol based on currency convention
        if currency in ["USD", "EUR", "GBP", "CNY", "JPY"]:
            return f"{symbol}{formatted}"
        return f"{formatted} {symbol}"

    # =========================================================================
    # Anchor Pricing Methods (NEW)
    # =========================================================================

    async def get_anchor_price(
        self, product: dict[str, Any] | Any, target_currency: str
    ) -> Decimal:
        """
        Get product price in target currency using anchor prices.

        Priority:
        1. Fixed anchor price from product.prices[currency] (if set)
        2. Fallback: convert from USD price

        Args:
            product: Product dict or object with 'price' and optional 'prices' (JSONB)
            target_currency: Target currency code (RUB, USD, etc.)

        Returns:
            Price in target currency as Decimal
        """
        # Handle both dict and object
        if hasattr(product, "__getitem__"):
            prices = product.get("prices") or {}
            base_price = product.get("price", 0)
        else:
            prices = getattr(product, "prices", None) or {}
            base_price = getattr(product, "price", 0)

        # Check for anchor price in target currency
        if prices and target_currency in prices:
            anchor_price = prices[target_currency]
            if anchor_price is not None:
                logger.debug(f"Using anchor price for {target_currency}: {anchor_price}")
                return to_decimal(anchor_price)

        # Fallback: convert from USD
        if target_currency == "USD":
            return to_decimal(base_price)

        converted = await self.convert_price(base_price, target_currency)
        return to_decimal(converted)

    def has_anchor_price(self, product: dict[str, Any] | Any, currency: str) -> bool:
        """
        Check if product has a fixed anchor price for given currency.

        Args:
            product: Product dict or object
            currency: Currency code to check

        Returns:
            True if anchor price exists, False otherwise
        """
        if hasattr(product, "__getitem__"):
            prices = product.get("prices") or {}
        else:
            prices = getattr(product, "prices", None) or {}

        return bool(prices and currency in prices and prices[currency] is not None)

    def _extract_settings_data(
        self, settings: dict[str, Any] | Any, level: int
    ) -> tuple[dict, float]:
        """Extract thresholds_by_currency and base_threshold_usd from settings (reduces cognitive complexity)."""
        if hasattr(settings, "__getitem__"):
            thresholds_by_currency = settings.get("thresholds_by_currency") or {}
            threshold_usd_key = f"level{level}_threshold_usd"
            base_threshold_usd = settings.get(threshold_usd_key, 250 if level == 2 else 1000)
        else:
            thresholds_by_currency = getattr(settings, "thresholds_by_currency", None) or {}
            threshold_usd_attr = f"level{level}_threshold_usd"
            base_threshold_usd = getattr(settings, threshold_usd_attr, 250 if level == 2 else 1000)
        return thresholds_by_currency, base_threshold_usd

    def _get_anchor_threshold_from_settings(
        self, thresholds_by_currency: dict, target_currency: str, level: int
    ) -> Decimal | None:
        """Get anchor threshold from settings if available (reduces cognitive complexity)."""
        if not thresholds_by_currency or target_currency not in thresholds_by_currency:
            return None

        currency_thresholds = thresholds_by_currency[target_currency]
        if not isinstance(currency_thresholds, dict):
            return None

        level_key = f"level{level}"
        if level_key not in currency_thresholds:
            return None

        anchor_threshold = currency_thresholds[level_key]
        if anchor_threshold is None:
            return None

        logger.debug(
            "Using anchor threshold for %s level%s: %s", target_currency, level, anchor_threshold
        )
        return to_decimal(anchor_threshold)

    async def get_anchor_threshold(
        self,
        settings: dict[str, Any] | Any,
        target_currency: str,
        level: int,  # 2 or 3
    ) -> Decimal:
        """
        Get referral threshold for specified level and currency using anchor thresholds.

        Priority:
        1. Fixed anchor threshold from settings.thresholds_by_currency[currency][level] (if set)
        2. Fallback: convert from USD threshold

        Args:
            settings: Referral settings dict or object with 'thresholds_by_currency' and 'level2_threshold_usd', 'level3_threshold_usd'
            target_currency: Target currency code (RUB, USD, etc.)
            level: Level number (2 or 3)

        Returns:
            Threshold in target currency as Decimal
        """
        if level not in [2, 3]:
            raise ValueError(f"Level must be 2 or 3, got {level}")

        thresholds_by_currency, base_threshold_usd = self._extract_settings_data(settings, level)

        anchor_threshold = self._get_anchor_threshold_from_settings(
            thresholds_by_currency, target_currency, level
        )
        if anchor_threshold is not None:
            return anchor_threshold

        if target_currency == "USD":
            return to_decimal(base_threshold_usd)

        converted = await self.convert_price(base_threshold_usd, target_currency)
        return to_decimal(converted)

    async def snapshot_rate(self, currency: str) -> float:
        """
        Get current exchange rate for snapshotting in orders.

        This rate should be stored with the order for accurate
        historical accounting.

        Args:
            currency: Currency code

        Returns:
            Exchange rate (1 USD = X currency)
        """
        if currency == "USD":
            return 1.0
        return await self.get_exchange_rate(currency)

    def get_balance_currency(self, language_code: str | None = None) -> str:
        """
        Determine balance currency for a user based on Telegram language.

        Used for NEW users to set their balance_currency on registration.
        Balance is stored in the user's local currency (RUB for Russian-speaking,
        USD for others).

        Args:
            language_code: User's Telegram language code (ru, en, de, etc.)

        Returns:
            Currency code: RUB for ru/be/kk, USD for others
        """
        if language_code:
            lang = language_code.split("-")[0].lower()
            if lang in ["ru", "be", "kk"]:
                return "RUB"
        return "USD"

    async def convert_balance(
        self,
        from_currency: str,
        to_currency: str,
        amount: float | Decimal | str,
    ) -> Decimal:
        """
        Convert balance between currencies (RUB ↔ USD only).

        This method is specifically for balance conversions where we only
        support RUB and USD. Use convert_price() for product price conversions.

        Args:
            from_currency: Source currency (RUB or USD)
            to_currency: Target currency (RUB or USD)
            amount: Amount to convert

        Returns:
            Converted amount as Decimal, properly rounded

        Raises:
            ValueError: If currency is not RUB or USD

        Example:
            >>> await currency_service.convert_balance("USD", "RUB", 10.0)
            Decimal('900')  # At rate 90

            >>> await currency_service.convert_balance("RUB", "USD", 900.0)
            Decimal('10.00')  # At rate 90
        """
        # Validate currencies (only RUB and USD supported for balance)
        valid_currencies = {"USD", "RUB"}
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency not in valid_currencies:
            raise ValueError(f"Invalid from_currency: {from_currency}. Must be USD or RUB")
        if to_currency not in valid_currencies:
            raise ValueError(f"Invalid to_currency: {to_currency}. Must be USD or RUB")

        decimal_amount = to_decimal(amount)

        # Same currency - no conversion needed
        if from_currency == to_currency:
            return round_money(decimal_amount, to_int=(to_currency == "RUB"))

        # Get RUB rate (1 USD = X RUB)
        rub_rate = await self.get_exchange_rate("RUB")

        if from_currency == "USD" and to_currency == "RUB":
            # USD → RUB: multiply by rate
            result = decimal_amount * to_decimal(rub_rate)
            return round_money(result, to_int=True)  # RUB is integer

        if from_currency == "RUB" and to_currency == "USD":
            # RUB → USD: divide by rate
            if rub_rate == 0:
                rub_rate = FALLBACK_RATES.get("RUB", 80.0)
            result = decimal_amount / to_decimal(rub_rate)
            return round_money(result, to_int=False)  # USD has decimals

        # Should never reach here due to validation above
        return round_money(decimal_amount)

    async def convert_to_base_currency(
        self, amount: float | Decimal | str, from_currency: str
    ) -> Decimal:
        """
        Convert amount from any currency to USD (base currency).

        Args:
            amount: Amount in source currency
            from_currency: Source currency code

        Returns:
            Amount in USD as Decimal
        """
        if from_currency == "USD":
            return to_decimal(amount)

        rate = await self.get_exchange_rate(from_currency)
        if rate == 0:
            rate = 1.0

        # amount / rate = USD
        return round_money(to_decimal(amount) / to_decimal(rate))

    # =========================================================================
    # USDT Methods (for withdrawals)
    # =========================================================================

    async def get_usdt_rate(self) -> float:
        """
        Get current USDT/USD exchange rate.

        USDT is a stablecoin pegged to USD, so rate is typically ~1.0
        but can vary slightly (0.99-1.01).

        Returns:
            USDT rate (1 USDT = X USD)
        """
        # Try to get from cache/DB first
        if self.redis:
            try:
                cached = await self._get_cached_rate("USDT")
                if cached:
                    return float(cached)
            except Exception:
                pass

        # USDT is a stablecoin, typically 1:1 with USD
        # For production, you might want to fetch from CoinGecko/Binance API
        # For now, use 1.0 as default (stable assumption)
        return 1.0

    async def calculate_withdrawal_usdt(
        self,
        amount_in_balance_currency: float | Decimal,
        balance_currency: str,
        network_fee: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate withdrawal payout in USDT.

        Formula: amount_to_pay = (amount / exchange_rate / usdt_rate) - network_fee

        Args:
            amount_in_balance_currency: Amount in user's balance currency (e.g., 5000 RUB)
            balance_currency: User's balance currency (RUB, USD, etc.)
            network_fee: TRC20 network fee in USDT (default 1.5)

        Returns:
            Dict with:
                - amount_usd: Equivalent in USD
                - amount_usdt: Final USDT payout after fees
                - exchange_rate: Currency to USD rate used
                - usdt_rate: USDT/USD rate used
                - network_fee: Network fee applied
        """
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT

        amount_decimal = to_decimal(amount_in_balance_currency)

        # Get exchange rate (1 USD = X balance_currency)
        if balance_currency == "USD":
            exchange_rate = 1.0
        else:
            exchange_rate = await self.get_exchange_rate(balance_currency)

        # Get USDT rate (typically 1.0)
        usdt_rate = await self.get_usdt_rate()

        # Calculate USD equivalent
        amount_usd = to_float(amount_decimal / to_decimal(exchange_rate))

        # Calculate USDT amount (before fees)
        amount_usdt_gross = amount_usd / usdt_rate

        # Apply network fee
        amount_usdt_net = max(0, amount_usdt_gross - network_fee)

        return {
            "amount_usd": round(amount_usd, 2),
            "amount_usdt": round(amount_usdt_net, 2),
            "amount_usdt_gross": round(amount_usdt_gross, 2),
            "exchange_rate": exchange_rate,
            "usdt_rate": usdt_rate,
            "network_fee": network_fee,
        }

    async def calculate_min_withdrawal_amount(
        self,
        balance_currency: str,
        min_usdt_after_fees: float | None = None,
        network_fee: float | None = None,
        usdt_rate: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate minimum withdrawal amount in user's balance currency.

        Formula: min_amount = (min_usdt_after_fees + network_fee) / usdt_rate * exchange_rate

        Args:
            balance_currency: User's balance currency (RUB, USD, etc.)
            min_usdt_after_fees: Minimum USDT user must receive after fees (defaults to MIN_USDT_AFTER_FEES constant)
            network_fee: TRC20 network fee in USDT (defaults to NETWORK_FEE_USDT constant)
            usdt_rate: USDT/USD rate (if None, fetched from service)

        Returns:
            Dict with:
                - min_amount: Minimum amount in balance_currency
                - min_usd: Minimum amount in USD
                - min_usdt_gross: Minimum USDT before fees
                - exchange_rate: Currency to USD rate used
        """
        if min_usdt_after_fees is None:
            min_usdt_after_fees = MIN_USDT_AFTER_FEES
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT

        # Get USDT rate if not provided
        if usdt_rate is None:
            usdt_rate = await self.get_usdt_rate()

        # Calculate minimum USD: (8.5 + 1.5) * 1.0 = 10.0 USD
        min_usdt_gross = min_usdt_after_fees + network_fee
        min_usd = min_usdt_gross * usdt_rate

        # Get exchange rate (1 USD = X balance_currency)
        if balance_currency == "USD":
            exchange_rate = 1.0
        else:
            exchange_rate = await self.get_exchange_rate(balance_currency)

        # Calculate minimum in user's currency
        min_amount = min_usd * exchange_rate

        return {
            "min_amount": round(min_amount, 2),
            "min_usd": round(min_usd, 2),
            "min_usdt_gross": round(min_usdt_gross, 2),
            "min_usdt_after_fees": min_usdt_after_fees,
            "network_fee": network_fee,
            "exchange_rate": exchange_rate,
            "usdt_rate": usdt_rate,
        }

    async def calculate_max_withdrawal_amount(
        self,
        balance: float,
        balance_currency: str,
        network_fee: float | None = None,
        min_usdt_after_fees: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate maximum withdrawal amount user can withdraw from their balance.
        Ensures that after fees, user gets at least min_usdt_after_fees.

        Returns:
            Dict with:
                - max_amount: Maximum amount in balance_currency
                - max_usdt_net: Maximum USDT user will receive after fees
                - withdrawal_calc: Full calculation result
        """
        if network_fee is None:
            network_fee = NETWORK_FEE_USDT
        if min_usdt_after_fees is None:
            min_usdt_after_fees = MIN_USDT_AFTER_FEES

        # Calculate what user would get if they withdraw their full balance
        withdrawal_calc = await self.calculate_withdrawal_usdt(
            amount_in_balance_currency=balance,
            balance_currency=balance_currency,
            network_fee=network_fee,
        )

        # If after fees user gets less than minimum, return 0
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
# Centralized withdrawal configuration (single source of truth)
NETWORK_FEE_USDT = 1.5  # TRC20 network fee
MIN_USDT_AFTER_FEES = (
    8.5  # Minimum USDT user must receive after fees (exchange requirement: 10 USD total)
)
MIN_WITHDRAWAL_USD = MIN_USDT_AFTER_FEES + NETWORK_FEE_USDT  # 10.0 USD total (8.5 + 1.5)


# Global instance (will be initialized with Redis if available)
_currency_service: CurrencyService | None = None


def get_currency_service(redis_client=None) -> CurrencyService:
    """Get or create global currency service instance."""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService(redis_client)
    return _currency_service
