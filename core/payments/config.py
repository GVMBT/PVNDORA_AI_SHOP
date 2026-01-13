"""Payment gateway configuration and validation."""

import logging
import os

from fastapi import HTTPException

from .constants import PaymentGateway, normalize_gateway

logger = logging.getLogger(__name__)


# Gateway configuration requirements
GATEWAY_ENV_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    PaymentGateway.CRYSTALPAY.value: ("CRYSTALPAY_LOGIN", "CRYSTALPAY_SECRET", "CRYSTALPAY_SALT"),
}

# Human-readable gateway names for error messages
GATEWAY_NAMES: dict[str, str] = {
    PaymentGateway.CRYSTALPAY.value: "CrystalPay",
}


def get_gateway_config(_gateway: str) -> dict[str, str | None]:
    """
    Get all environment variables for a gateway.

    Returns dict with env var names as keys and their values (or None if not set).
    """
    # All gateways map to CrystalPay now
    return {
        "login": os.environ.get("CRYSTALPAY_LOGIN"),
        "secret": os.environ.get("CRYSTALPAY_SECRET"),
        "salt": os.environ.get("CRYSTALPAY_SALT"),
    }


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
        if not value:
            missing.append(key)

    if missing:
        env_vars = GATEWAY_ENV_REQUIREMENTS.get(gateway, ())
        logger.error(f"Payment gateway {name} not configured. Missing: {missing}")
        raise HTTPException(
            status_code=500, detail=f"{name} не настроен. Настройте: {', '.join(env_vars)}"
        )

    return gateway


def is_gateway_configured(gateway: str) -> bool:
    """Check if a gateway is properly configured without raising exceptions."""
    config = get_gateway_config(gateway)
    return all(value for value in config.values())


def get_default_gateway() -> str:
    """Get the default payment gateway from environment."""
    return PaymentGateway.CRYSTALPAY.value
