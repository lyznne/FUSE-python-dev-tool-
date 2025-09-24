"""
FUSE - (python dev tool) - Web App
Security Middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for Fuse"""
    async def dispatch(self, request: Request, call_next):
        """Dispatch request to the next middleware or endpoint"""
        # TODO: Implement security middleware
        return await call_next(request)
