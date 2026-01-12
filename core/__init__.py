"""
PVNDORA Core Module

This package contains the core infrastructure components:
- db: Database clients (Supabase + Redis)
- queue: QStash message queue
- cart: Redis cart manager
- ai: Gemini AI integration
- rag: Vector search pipeline
- models: Pydantic schemas

Note: Imports are lazy to avoid circular dependency issues
and ensure clean module loading in serverless environments.

IMPORTANT: Database is async-first. Use:
    from core.services.database import get_database, init_database

For Redis:
    from core.db import get_redis
"""

# Lazy imports to avoid issues at module load time
# pylint: disable=undefined-all-variable
__all__ = [
    "close_database",
    "get_database",
    "get_qstash",
    "get_redis",
    "init_database",
    "publish_to_worker",
]
# pylint: enable=undefined-all-variable


def __getattr__(name):
    """Lazy attribute access for clean serverless loading."""
    if name == "get_database":
        from core.services.database import get_database

        return get_database
    if name == "init_database":
        from core.services.database import init_database

        return init_database
    if name == "close_database":
        from core.services.database import close_database

        return close_database
    if name == "get_redis":
        from core.db import get_redis

        return get_redis
    if name == "get_qstash":
        from core.queue import get_qstash

        return get_qstash
    if name == "publish_to_worker":
        from core.queue import publish_to_worker

        return publish_to_worker
    raise AttributeError(f"module 'core' has no attribute '{name}'")
