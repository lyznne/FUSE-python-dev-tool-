"""
FUSE - (python dev tool) - Web App
CORS Middleware
"""
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*"
        ],
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )
