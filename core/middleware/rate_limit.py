"""Rate Limiting Middleware for FastAPI.

Provides rate limiting using Upstash Redis.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Upstash Redis.

    Limits requests per IP address per endpoint.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 30,
        redis_client: Any = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.redis_client = redis_client
        self._cache: dict[str, list[float]] = {}  # Fallback in-memory cache

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        # Only rate limit auth endpoints
        if not request.url.path.startswith("/api/auth"):
            return await call_next(request)  # type: ignore[no-any-return]

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            # Use first IP from X-Forwarded-For (original client)
            client_ip = forwarded_for.split(",")[0].strip()

        # Create rate limit key
        key = f"rate_limit:{client_ip}:{request.url.path}"

        # Check rate limit
        if await self._is_rate_limited(key):
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"},
            )

        # Record request
        await self._record_request(key)

        return await call_next(request)  # type: ignore[no-any-return]

    async def _is_rate_limited(self, key: str) -> bool:
        """Check if key is rate limited."""
        if self.redis_client:
            try:
                # Use Redis for distributed rate limiting
                current = await self.redis_client.get(key)
                if current:
                    count = int(current)
                    return count >= self.requests_per_minute
                return False
            except Exception as e:
                logger.warning(f"Redis rate limit check failed: {e}, falling back to in-memory")
                # Fallback to in-memory

        # In-memory fallback
        now = time.time()
        if key not in self._cache:
            return False

        # Clean old entries (older than 1 minute)
        self._cache[key] = [t for t in self._cache[key] if now - t < 60]

        return len(self._cache[key]) >= self.requests_per_minute

    async def _record_request(self, key: str) -> None:
        """Record a request for rate limiting."""
        now = time.time()

        if self.redis_client:
            try:
                # Use Redis with expiration
                # Check if key exists to determine if we need to set expiration
                current = await self.redis_client.get(key)
                if current is None:
                    # First request - set with expiration
                    await self.redis_client.setex(key, 60, "1")
                else:
                    # Increment existing counter
                    # Upstash REST API doesn't support INCR directly, so we read-increment-write
                    count = int(current) + 1
                    await self.redis_client.setex(key, 60, str(count))
                return
            except Exception as e:
                logger.warning(f"Redis rate limit record failed: {e}, falling back to in-memory")
                # Fallback to in-memory

        # In-memory fallback
        if key not in self._cache:
            self._cache[key] = []

        self._cache[key].append(now)

        # Clean old entries
        self._cache[key] = [t for t in self._cache[key] if now - t < 60]
