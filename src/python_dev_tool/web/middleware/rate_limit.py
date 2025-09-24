"""
FUSE - (python dev tool) - Web App
Rate Limit Middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit middleware"""
    async def dispatch(self, request: Request, call_next):
        """Dispatch request to the next middleware or endpoint"""
        # TODO: Implement rate limit middleware
        return await call_next(request)
