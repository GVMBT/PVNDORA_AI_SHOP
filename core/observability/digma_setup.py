"""Digma Observability Setup.

Автоматически отслеживает:
- Все DB запросы (Supabase через HTTP)
- Все HTTP запросы
- Производительность endpoints
- N+1 queries (автоматически)
- Chatty logic (автоматически)
- Dead code (автоматически)

Требования:
1. Зарегистрироваться на https://digma.ai (free tier доступен)
2. Получить DIGMA_COLLECTOR_URL и DIGMA_API_KEY
3. Установить зависимости: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx opentelemetry-exporter-otlp
"""

import os

from core.logging import get_logger

logger = get_logger(__name__)

# Digma configuration
DIGMA_COLLECTOR_URL = os.environ.get("DIGMA_COLLECTOR_URL", "")
DIGMA_API_KEY = os.environ.get("DIGMA_API_KEY", "")
DIGMA_ENABLED = bool(DIGMA_COLLECTOR_URL and DIGMA_API_KEY)

# Try to import OpenTelemetry (optional dependency)
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning(
        "OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx opentelemetry-exporter-otlp",
    )


def setup_digma(app) -> None:
    """Настраивает Digma для автоматического отслеживания.

    Отслеживает:
    - Все FastAPI endpoints
    - Все HTTP запросы (включая Supabase)
    - Производительность
    - N+1 queries (автоматически обнаруживает)
    - Chatty logic (автоматически обнаруживает)

    Args:
        app: FastAPI application instance

    """
    if not DIGMA_ENABLED:
        logger.info(
            "Digma disabled: Set DIGMA_COLLECTOR_URL and DIGMA_API_KEY environment variables to enable",
        )
        return

    if not OPENTELEMETRY_AVAILABLE:
        logger.error(
            "Digma enabled but OpenTelemetry not installed. Install required packages first.",
        )
        return

    try:
        # Create Resource with service information
        resource = Resource.create(
            {
                "service.name": "pvndora-api",
                "service.version": "1.0.0",
                "deployment.environment": os.environ.get("VERCEL_ENV", "development"),
                "service.namespace": "pvndora",
            },
        )

        # Настроить TracerProvider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Настроить OTLP экспортер для Digma
        # Digma использует HTTP endpoint для OTLP
        otlp_exporter = OTLPSpanExporter(
            endpoint=DIGMA_COLLECTOR_URL,
            headers={
                "Authorization": f"Bearer {DIGMA_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        # Добавить BatchSpanProcessor для эффективной отправки
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

        # Инструментировать FastAPI (автоматически отслеживает все endpoints)
        FastAPIInstrumentor.instrument_app(app)

        # Инструментировать HTTPX (для Supabase запросов через HTTP)
        # Это критично - Supabase использует httpx для HTTP запросов
        HTTPXClientInstrumentor().instrument()

        logger.info(
            f"[Digma] Observability enabled. Collector: {DIGMA_COLLECTOR_URL[:50]}...",
        )
        logger.info(
            "[Digma] Tracking: FastAPI endpoints, HTTP requests (Supabase), DB queries, performance",
        )

    except Exception as e:
        logger.error(f"[Digma] Failed to setup observability: {e}", exc_info=True)
        logger.warning("[Digma] Continuing without observability")


def get_tracer(name: str):
    """Получить tracer для ручного создания spans (опционально).

    Args:
        name: Имя tracer (обычно __name__ модуля)

    Returns:
        Tracer instance или NoOpTracer если Digma отключен

    """
    if not DIGMA_ENABLED or not OPENTELEMETRY_AVAILABLE:
        # Return dummy tracer that does nothing
        class NoOpTracer:
            def start_as_current_span(self, *args, **kwargs):
                return self

            def __enter__(self):
                return self

            def __exit__(self, *args):
                # No-op: No cleanup needed for no-op tracer
                pass

        return NoOpTracer()

    return trace.get_tracer(name)
