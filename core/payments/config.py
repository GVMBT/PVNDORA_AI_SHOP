"""Payment gateway configuration and validation."""
import os
import logging
from typing import Dict, Optional, Tuple

from fastapi import HTTPException

from .constants import PaymentGateway, normalize_gateway

logger = logging.getLogger(__name__)


# Gateway configuration requirements
GATEWAY_ENV_REQUIREMENTS: Dict[str, Tuple[str, ...]] = {
    PaymentGateway.RUKASSA.value: ("RUKASSA_SHOP_ID", "RUKASSA_TOKEN"),
    PaymentGateway.CRYSTALPAY.value: ("CRYSTALPAY_LOGIN", "CRYSTALPAY_SECRET", "CRYSTALPAY_SALT"),
    PaymentGateway.FREEKASSA.value: ("FREEKASSA_MERCHANT_ID", "FREEKASSA_SECRET_WORD_1", "FREEKASSA_SECRET_WORD_2"),
    # For 1Plat we require both shop/merchant id and secret key
    PaymentGateway.ONEPLAT.value: ("ONEPLAT_SECRET_KEY", "ONEPLAT_SHOP_ID|ONEPLAT_MERCHANT_ID"),
}

# Human-readable gateway names for error messages
GATEWAY_NAMES: Dict[str, str] = {
    PaymentGateway.RUKASSA.value: "Rukassa",
    PaymentGateway.CRYSTALPAY.value: "CrystalPay",
    PaymentGateway.FREEKASSA.value: "Freekassa",
    PaymentGateway.ONEPLAT.value: "1Plat",
}


def get_gateway_config(gateway: str) -> Dict[str, Optional[str]]:
    """
    Get all environment variables for a gateway.
    
    Returns dict with env var names as keys and their values (or None if not set).
    """
    gateway = normalize_gateway(gateway)
    
    if gateway == PaymentGateway.RUKASSA.value:
        return {
            "shop_id": os.environ.get("RUKASSA_SHOP_ID"),
            "token": os.environ.get("RUKASSA_TOKEN"),
        }
    elif gateway == PaymentGateway.CRYSTALPAY.value:
        return {
            "login": os.environ.get("CRYSTALPAY_LOGIN"),
            "secret": os.environ.get("CRYSTALPAY_SECRET"),
            "salt": os.environ.get("CRYSTALPAY_SALT"),
        }
    elif gateway == PaymentGateway.FREEKASSA.value:
        return {
            "merchant_id": os.environ.get("FREEKASSA_MERCHANT_ID"),
            "secret_word_1": os.environ.get("FREEKASSA_SECRET_WORD_1"),
            "secret_word_2": os.environ.get("FREEKASSA_SECRET_WORD_2"),
        }
    elif gateway == PaymentGateway.ONEPLAT.value:
        return {
            "shop_id": os.environ.get("ONEPLAT_SHOP_ID") or os.environ.get("ONEPLAT_MERCHANT_ID"),
            "secret_key": os.environ.get("ONEPLAT_SECRET_KEY"),
        }
    return {}


def validate_gateway_config(gateway: str) -> str:
    """
    Validate payment gateway environment configuration.
    
    Args:
        gateway: Gateway name (will be normalized)
        
    Returns:
        Normalized gateway name
        
    Raises:
        HTTPException: If gateway is not configured
    """
    gateway = normalize_gateway(gateway)
    config = get_gateway_config(gateway)
    name = GATEWAY_NAMES.get(gateway, gateway)
    
    # Check if all required values are present
    missing = []
    for key, value in config.items():
        # Special case: shop_id may come from two env vars
        if key == "shop_id":
            if not value:
                missing.append("ONEPLAT_SHOP_ID|ONEPLAT_MERCHANT_ID")
            continue
        if not value:
            missing.append(key)
    
    if missing:
        env_vars = GATEWAY_ENV_REQUIREMENTS.get(gateway, ())
        logger.error(f"Payment gateway {name} not configured. Missing: {missing}")
        raise HTTPException(
            status_code=500,
            detail=f"{name} не настроен. Настройте: {', '.join(env_vars)}"
        )
    
    return gateway


def is_gateway_configured(gateway: str) -> bool:
    """Check if a gateway is properly configured without raising exceptions."""
    gateway = normalize_gateway(gateway)
    config = get_gateway_config(gateway)
    return all(value for value in config.values())


def get_default_gateway() -> str:
    """Get the default payment gateway from environment."""
    default = os.environ.get("DEFAULT_PAYMENT_GATEWAY", PaymentGateway.RUKASSA.value)
    return normalize_gateway(default)

