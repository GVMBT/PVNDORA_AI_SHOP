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
"""

# Lazy imports to avoid issues at module load time
__all__ = [
    "get_supabase",
    "get_supabase_sync", 
    "get_redis",
    "get_qstash",
    "publish_to_worker",
]


def __getattr__(name):
    """Lazy attribute access for clean serverless loading."""
    if name == "get_supabase":
        from core.db import get_supabase
        return get_supabase
    elif name == "get_supabase_sync":
        from core.db import get_supabase_sync
        return get_supabase_sync
    elif name == "get_redis":
        from core.db import get_redis
        return get_redis
    elif name == "get_qstash":
        from core.queue import get_qstash
        return get_qstash
    elif name == "publish_to_worker":
        from core.queue import publish_to_worker
        return publish_to_worker
    raise AttributeError(f"module 'core' has no attribute '{name}'")

