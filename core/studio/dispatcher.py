"""Studio Dispatcher - Entry point for AI generation.

Provides unified interface for all AI providers.
Handles adapter selection and price calculation.
"""

from typing import Any

from core.logging import get_logger
from core.studio.adapters.base import (
    AdapterCapabilities,
    AdapterError,
    BaseAdapter,
    GenerationRequest,
    GenerationResult,
)

logger = get_logger(__name__)

# Registry of available adapters
# Key: model_id (matches studio_model_prices.id)
# Value: Adapter class
_ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register_adapter(adapter_class: type[BaseAdapter]) -> type[BaseAdapter]:
    """Decorator to register an adapter class."""
    _ADAPTER_REGISTRY[adapter_class.model_id] = adapter_class
    return adapter_class


def _load_adapters() -> None:
    """Lazy-load all adapter classes."""
    if _ADAPTER_REGISTRY:
        return  # Already loaded

    # Import adapters to trigger registration
    try:
        from core.studio.adapters.veo import VeoAdapter, VeoFastAdapter
        _ADAPTER_REGISTRY["veo-3.1"] = VeoAdapter
        _ADAPTER_REGISTRY["veo-fast"] = VeoFastAdapter
    except ImportError as e:
        logger.warning(f"Failed to load Veo adapters: {e}")

    # TODO: Add more adapters as they're implemented
    # from core.studio.adapters.kling import KlingAdapter
    # from core.studio.adapters.suno import SunoAdapter
    # from core.studio.adapters.elevenlabs import ElevenLabsAdapter

    logger.info(f"Loaded {len(_ADAPTER_REGISTRY)} studio adapters: {list(_ADAPTER_REGISTRY.keys())}")


def get_adapter(model_id: str) -> BaseAdapter:
    """Get adapter instance for a model.

    Args:
        model_id: Model identifier (e.g., 'veo-3.1', 'kling-1.6')

    Returns:
        Adapter instance

    Raises:
        AdapterError: If model not found or adapter unavailable
    """
    _load_adapters()

    adapter_class = _ADAPTER_REGISTRY.get(model_id)
    if not adapter_class:
        available = list(_ADAPTER_REGISTRY.keys())
        raise AdapterError(
            f"Unknown model: {model_id}. Available: {available}",
            code="MODEL_NOT_FOUND",
        )

    return adapter_class()


def get_available_models() -> list[dict[str, Any]]:
    """Get list of available models with their capabilities.

    Returns:
        List of model info dicts
    """
    _load_adapters()

    models = []
    for model_id, adapter_class in _ADAPTER_REGISTRY.items():
        try:
            adapter = adapter_class()
            capabilities = adapter.get_capabilities()
            models.append({
                "id": model_id,
                "name": adapter.display_name,
                "type": adapter.generation_type.value,
                "capabilities": capabilities.to_dict(),
            })
        except Exception as e:
            logger.warning(f"Failed to get capabilities for {model_id}: {e}")

    return models


def get_model_capabilities(model_id: str) -> AdapterCapabilities:
    """Get capabilities for a specific model.

    Args:
        model_id: Model identifier

    Returns:
        AdapterCapabilities for the model
    """
    adapter = get_adapter(model_id)
    return adapter.get_capabilities()


async def generate(model_id: str, request: GenerationRequest) -> GenerationResult:
    """Start generation with specified model.

    This is the main entry point for starting AI generations.

    Args:
        model_id: Model to use (e.g., 'veo-3.1')
        request: Generation request

    Returns:
        GenerationResult with job_id for tracking

    Raises:
        AdapterError: If generation fails to start
    """
    adapter = get_adapter(model_id)

    logger.info(
        f"Starting generation: model={model_id}, type={request.type}, "
        f"prompt={request.prompt[:50]}..."
    )

    try:
        result = await adapter.generate(request)
        logger.info(f"Generation started: job_id={result.job_id}, status={result.status}")
        return result
    except AdapterError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generation: {e}", exc_info=True)
        raise AdapterError(f"Generation failed: {e}", retryable=True, raw_error=e)


async def check_status(model_id: str, job_id: str) -> GenerationResult:
    """Check status of a generation job.

    Args:
        model_id: Model that was used
        job_id: Job ID from generate()

    Returns:
        GenerationResult with current status
    """
    adapter = get_adapter(model_id)
    return await adapter.check_status(job_id)


async def cancel_generation(model_id: str, job_id: str) -> bool:
    """Cancel a running generation.

    Args:
        model_id: Model that was used
        job_id: Job ID from generate()

    Returns:
        True if cancelled successfully
    """
    adapter = get_adapter(model_id)
    return await adapter.cancel(job_id)


# ============================================================
# Price Calculation
# ============================================================

async def calculate_price(
    model_id: str,
    config: dict[str, Any],
    db: Any = None,
) -> int:
    """Calculate generation price in RUB.

    Args:
        model_id: Model to use
        config: Generation config (resolution, duration, etc.)
        db: Database instance (optional, will get if not provided)

    Returns:
        Price in RUB (integer)
    """
    if db is None:
        from core.services.database import get_database
        db = get_database()

    # Use SQL function for price calculation
    try:
        result = await db.client.rpc(
            "calculate_studio_generation_price",
            {"p_model_id": model_id, "p_config": config},
        ).execute()

        if result.data is not None:
            return int(result.data)
    except Exception as e:
        logger.warning(f"RPC price calculation failed, using fallback: {e}")

    # Fallback: Get base price from table
    try:
        model_result = (
            await db.client.table("studio_model_prices")
            .select("base_price, price_multipliers")
            .eq("id", model_id)
            .eq("is_active", True)
            .single()
            .execute()
        )

        if not model_result.data:
            raise AdapterError(f"Model not found or inactive: {model_id}")

        base_price = float(model_result.data["base_price"])
        multipliers = model_result.data.get("price_multipliers") or {}

        # Apply multipliers
        for key, value in config.items():
            if key in multipliers and value in multipliers[key]:
                base_price *= float(multipliers[key][value])

        return round(base_price)

    except Exception as e:
        logger.exception(f"Failed to calculate price for {model_id}")
        raise AdapterError(f"Price calculation failed: {e}")
