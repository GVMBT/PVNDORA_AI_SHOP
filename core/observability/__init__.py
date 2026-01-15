"""Observability Module.

Provides code analysis and performance monitoring:
- Digma integration (N+1 detection, chatty logic, dead code)
- OpenTelemetry tracing
- Performance metrics
"""

from .digma_setup import DIGMA_ENABLED, get_tracer, setup_digma

__all__ = ["DIGMA_ENABLED", "get_tracer", "setup_digma"]
