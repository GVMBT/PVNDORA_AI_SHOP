"""
Money Utilities - Safe Decimal operations for monetary values.

Avoids float precision issues by using Decimal throughout.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union

# Default precision for money operations (2 decimal places)
MONEY_PRECISION = Decimal("0.01")

# Precision for integer currencies (RUB, UAH, etc.)
INTEGER_PRECISION = Decimal("1")


def to_decimal(value: Union[str, int, float, Decimal, None]) -> Decimal:
    """
    Convert any value to Decimal safely.
    
    Args:
        value: Value to convert (str, int, float, Decimal, or None)
        
    Returns:
        Decimal representation of the value, or Decimal("0") if None/invalid
    """
    if value is None:
        return Decimal("0")
    
    if isinstance(value, Decimal):
        return value
    
    try:
        # Convert via string to avoid float precision issues
        if isinstance(value, float):
            # Use string representation to preserve precision
            return Decimal(str(value))
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def to_kopecks(value: Union[str, int, float, Decimal]) -> int:
    """
    Convert decimal amount to minor units (kopecks/cents).
    
    Used for payment APIs that expect integer minor units.
    
    Args:
        value: Amount in major units (e.g., 100.50 RUB)
        
    Returns:
        Amount in minor units (e.g., 10050 kopecks)
    """
    decimal_value = to_decimal(value)
    return int((decimal_value * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_kopecks(kopecks: int) -> Decimal:
    """
    Convert minor units (kopecks/cents) to decimal amount.
    
    Args:
        kopecks: Amount in minor units (e.g., 10050)
        
    Returns:
        Amount in major units as Decimal (e.g., 100.50)
    """
    return Decimal(kopecks) / Decimal(100)


def round_money(value: Union[str, int, float, Decimal], to_int: bool = False) -> Decimal:
    """
    Round monetary value to appropriate precision.
    
    Args:
        value: Value to round
        to_int: If True, round to integer (for RUB, UAH, etc.)
        
    Returns:
        Rounded Decimal value
    """
    decimal_value = to_decimal(value)
    precision = INTEGER_PRECISION if to_int else MONEY_PRECISION
    return decimal_value.quantize(precision, rounding=ROUND_HALF_UP)


def format_money(value: Union[str, int, float, Decimal], currency: str = "USD") -> str:
    """
    Format monetary value with currency symbol.
    
    Args:
        value: Value to format
        currency: Currency code (USD, RUB, EUR, etc.)
        
    Returns:
        Formatted string with currency symbol
    """
    decimal_value = to_decimal(value)
    
    # Use currency symbols from single source of truth
    from core.services.currency import CURRENCY_SYMBOLS, INTEGER_CURRENCIES
    
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    
    # Integer currencies
    if currency in INTEGER_CURRENCIES:
        formatted = f"{int(round_money(decimal_value, to_int=True)):,}"
    else:
        formatted = f"{round_money(decimal_value):,.2f}"
    
    # Symbol placement
    if currency in ("USD", "EUR", "GBP"):
        return f"{symbol}{formatted}"
    return f"{formatted} {symbol}"


def to_float(value: Union[str, int, float, Decimal]) -> float:
    """
    Convert Decimal to float for JSON serialization or external APIs.
    
    Use only at API boundaries, not for internal calculations.
    
    Args:
        value: Decimal or other numeric value
        
    Returns:
        Float representation
    """
    return float(to_decimal(value))


def add(a: Union[str, int, float, Decimal], b: Union[str, int, float, Decimal]) -> Decimal:
    """Safe addition of monetary values."""
    return to_decimal(a) + to_decimal(b)


def subtract(a: Union[str, int, float, Decimal], b: Union[str, int, float, Decimal]) -> Decimal:
    """Safe subtraction of monetary values."""
    return to_decimal(a) - to_decimal(b)


def multiply(value: Union[str, int, float, Decimal], factor: Union[str, int, float, Decimal]) -> Decimal:
    """Safe multiplication of monetary value by a factor."""
    return to_decimal(value) * to_decimal(factor)


def divide(value: Union[str, int, float, Decimal], divisor: Union[str, int, float, Decimal]) -> Decimal:
    """Safe division of monetary value."""
    d = to_decimal(divisor)
    if d == 0:
        return Decimal("0")
    return to_decimal(value) / d


def percent(value: Union[str, int, float, Decimal], percent_value: Union[str, int, float, Decimal]) -> Decimal:
    """Calculate percentage of a monetary value."""
    return multiply(value, divide(percent_value, 100))


def compare(a: Union[str, int, float, Decimal], b: Union[str, int, float, Decimal]) -> int:
    """
    Compare two monetary values.
    
    Returns:
        -1 if a < b, 0 if a == b, 1 if a > b
    """
    diff = to_decimal(a) - to_decimal(b)
    if diff < 0:
        return -1
    elif diff > 0:
        return 1
    return 0

