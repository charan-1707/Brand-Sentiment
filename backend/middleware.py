"""Production middlewares: security headers + per-IP rate limiting."""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = \
            "camera=(), microphone=(), geolocation=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window limiter (per client IP)."""

    def __init__(self, app, max_requests: int = 300, window_seconds: int = 60,
                 exempt_paths: tuple = ("/api/health", "/api/ready")):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.exempt = exempt_paths
        self._hits: dict = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path in self.exempt:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[ip]
        while window and now - window[0] > self.window:
            window.popleft()
        if len(window) >= self.max_requests:
            return JSONResponse(
                {"detail": "Rate limit exceeded, please slow down."},
                status_code=429)
        window.append(now)
        return await call_next(request)
