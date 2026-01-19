"""Studio module - AI content generation.

This module provides:
- Adapters for different AI providers (Veo, Kling, Suno, etc.)
- Price calculation
- Generation management
"""

from core.studio.adapters.base import (
    BaseAdapter,
    GenerationRequest,
    GenerationResult,
)
from core.studio.dispatcher import get_adapter, generate

__all__ = [
    "BaseAdapter",
    "GenerationRequest",
    "GenerationResult",
    "get_adapter",
    "generate",
]
