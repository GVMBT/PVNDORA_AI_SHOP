"""AI Provider Adapters.

Each adapter translates unified GenerationRequest into provider-specific API calls.
"""

from core.studio.adapters.base import (
    BaseAdapter,
    GenerationRequest,
    GenerationResult,
    AdapterCapabilities,
    CustomOption,
)

__all__ = [
    "BaseAdapter",
    "GenerationRequest",
    "GenerationResult",
    "AdapterCapabilities",
    "CustomOption",
]
