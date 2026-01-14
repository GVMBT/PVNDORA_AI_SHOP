"""
Security Headers Middleware for FastAPI

Implements security best practices:
- Content-Security-Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements security headers recommended by OWASP and security scanners:
    - CSP: Prevents XSS attacks
    - HSTS: Forces HTTPS connections
    - X-Frame-Options: Prevents clickjacking
    - And more...
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Content-Security-Policy
        # Allow Telegram WebApp, Vercel, and common CDNs
        # 'unsafe-inline' and 'unsafe-eval' needed for Telegram Mini Apps
        # Note: CSP policy may be tightened when Telegram Mini App requirements allow
        # See: https://core.telegram.org/bots/webapps#initializing-mini-apps
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org https://cdn.vercel-insights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.telegram.org https://pvndora.app https://*.vercel.app; "
            "frame-src 'self' https://telegram.org; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests;"
        )
        response.headers["Content-Security-Policy"] = csp

        # HTTP Strict Transport Security (HSTS)
        # Max-age: 31536000 = 1 year in seconds
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # X-Frame-Options (legacy, CSP frame-ancestors takes precedence)
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Remove server information leaks
        # Note: Vercel sets Server header, but we can try to hide other headers
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
