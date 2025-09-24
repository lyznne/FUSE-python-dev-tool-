"""
FUSE - (python dev tool) - Web App
Auth Middleware
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for FUSE"""
    async def dispatch(self, request: Request, call_next):
        """Dispatch request to the next middleware or endpoint"""
        # TODO: Implement authentication middleware
        response = await call_next(request)
        return response
