"""
Runtime Query Monitor Middleware

Отслеживает все Supabase запросы в runtime и обнаруживает:
- N+1 queries (повторяющиеся запросы)
- Chatty logic (слишком много запросов в одном HTTP запросе)

Usage:
    from core.middleware.query_monitor import QueryMonitorMiddleware
    app.add_middleware(QueryMonitorMiddleware)

NOTE: This middleware is integrated but requires manual instrumentation via log_query().
For now, prefer static analysis with scripts/detect_nplusone.py which provides
better detection without runtime overhead.

TODO: Consider integration with supabase-py's logging or removal if static analysis
is sufficient.
"""

import time
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import get_logger

logger = get_logger(__name__)


class QueryMonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware для мониторинга DB запросов в runtime.

    Обнаруживает:
    - N+1 queries (одинаковые запросы повторяются много раз)
    - Chatty logic (слишком много запросов в одном HTTP запросе)
    """

    def __init__(self, app, threshold_nplusone: int = 5, threshold_chatty: int = 20):
        """
        Args:
            app: FastAPI application
            threshold_nplusone: Минимальное количество повторений для N+1 (default: 5)
            threshold_chatty: Максимальное количество запросов для Chatty Logic (default: 20)
        """
        super().__init__(app)
        self.threshold_nplusone = threshold_nplusone
        self.threshold_chatty = threshold_chatty
        # Храним запросы по request_id
        self.request_queries: Dict[str, List[dict]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """Обрабатывает HTTP запрос и отслеживает DB запросы."""
        # Генерируем уникальный ID для запроса
        request_id = str(uuid.uuid4())
        request.state.query_monitor_id = request_id
        request.state.query_start_time = time.time()

        # Очищаем старые данные (если есть)
        if request_id in self.request_queries:
            self.request_queries[request_id].clear()

        try:
            response = await call_next(request)
        finally:
            # Анализируем запросы после обработки
            await self._analyze_queries(request_id, request)

        return response

    async def _analyze_queries(self, request_id: str, request: Request):
        """Анализирует запросы на наличие проблем."""
        queries = self.request_queries.get(request_id, [])

        if not queries:
            return

        # Проверка Chatty Logic (слишком много запросов)
        if len(queries) >= self.threshold_chatty:
            duration = time.time() - request.state.query_start_time
            logger.warning(
                f"[QueryMonitor] Chatty Logic detected in {request.url.path} "
                f"(Request ID: {request_id[:8]}): {len(queries)} queries in {duration:.2f}s"
            )
            logger.warning(
                f"[QueryMonitor] Consider using batch operations. "
                f"Queries: {self._summarize_queries(queries)}"
            )

        # Проверка N+1 (повторяющиеся запросы)
        nplusone_issues = self._detect_nplusone(queries)
        if nplusone_issues:
            for issue in nplusone_issues:
                logger.warning(
                    f"[QueryMonitor] N+1 Query detected in {request.url.path} "
                    f"(Request ID: {request_id[:8]}): {issue['table']} queried {issue['count']} times"
                )
                logger.warning(
                    f"[QueryMonitor] Pattern: {issue['pattern']}. "
                    f"Suggestion: Use batch query with .in_() filter"
                )

        # Очищаем данные после анализа
        if request_id in self.request_queries:
            del self.request_queries[request_id]

    def _detect_nplusone(self, queries: List[dict]) -> List[dict]:
        """Обнаруживает N+1 паттерны."""
        # Группируем запросы по таблице и фильтрам
        query_groups = defaultdict(list)
        for q in queries:
            # Создаем ключ из таблицы и основных фильтров
            key = self._get_query_key(q)
            query_groups[key].append(q)

        # Находим группы с большим количеством повторений
        issues = []
        for key, group_queries in query_groups.items():
            if len(group_queries) >= self.threshold_nplusone:
                # Берем первый запрос для примера
                example = group_queries[0]
                issues.append(
                    {
                        "table": example.get("table", "unknown"),
                        "count": len(group_queries),
                        "pattern": key,
                        "example": example.get("query", ""),
                    }
                )

        return issues

    def _get_query_key(self, query: dict) -> str:
        """Создает ключ для группировки похожих запросов."""
        table = query.get("table", "unknown")
        operation = query.get("operation", "unknown")
        # Используем основные фильтры для группировки
        filters = query.get("filters", {})
        # Сортируем фильтры для консистентности
        filter_key = "_".join(sorted(f"{k}={v}" for k, v in filters.items() if k != "id"))
        return f"{table}_{operation}_{filter_key}"

    def _summarize_queries(self, queries: List[dict]) -> str:
        """Создает краткое описание запросов."""
        table_counts = defaultdict(int)
        for q in queries:
            table = q.get("table", "unknown")
            table_counts[table] += 1

        summary = ", ".join(f"{table}: {count}" for table, count in sorted(table_counts.items()))
        return f"Tables: {summary}"

    def log_query(
        self, request_id: str, table: str, operation: str, filters: dict | None = None, query: str = ""
    ):
        """
        Логирует DB запрос (вызывается из Database класса).

        Args:
            request_id: ID HTTP запроса (из request.state.query_monitor_id)
            table: Название таблицы
            operation: Тип операции (select, insert, update, delete, rpc)
            filters: Фильтры запроса
            query: Полный текст запроса (опционально)
        """
        if not request_id:
            return

        self.request_queries[request_id].append(
            {
                "table": table,
                "operation": operation,
                "filters": filters or {},
                "query": query,
                "timestamp": time.time(),
            }
        )


# Глобальный экземпляр (создается при инициализации middleware)
_query_monitor: QueryMonitorMiddleware | None = None


def get_query_monitor() -> QueryMonitorMiddleware | None:
    """Получить глобальный экземпляр QueryMonitor."""
    return _query_monitor


def set_query_monitor(monitor: QueryMonitorMiddleware):
    """Установить глобальный экземпляр QueryMonitor."""
    global _query_monitor
    _query_monitor = monitor
