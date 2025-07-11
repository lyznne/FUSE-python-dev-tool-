"""
FUSE - (python dev tool) - Web App
app.py - Web App
"""

# sys imports
from contextlib import asynccontextmanager
import logging
from pathlib import Path

# 3rd party imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles


# local imports
from python_dev_tool.web.api import projects, processes, logs, commands, files, websocket
from python_dev_tool.web.middleware.cors import setup_cors
from python_dev_tool.web.middleware.auth import AuthMiddleware
from python_dev_tool.web.middleware.rate_limit import RateLimitMiddleware
from python_dev_tool.web.middleware.security import SecurityMiddleware
from python_dev_tool.web.services.project_service import ProjectService
from python_dev_tool.web.services.process_service import ProcessService
from python_dev_tool.web.services.log_service import LogService


# configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
project_service = ProjectService()
process_service = ProcessService()
log_service = LogService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # startup
    logger.info("Starting Python Dev Tool Web server...")
    await project_service.initialize()
    await process_service.initialize()
    await log_service.initialize()

    yield

    # shutdown
    logger.info("Shutting down Python Dev Tool Web server...")
    await project_service.cleanup()
    await process_service.cleanup()
    await log_service.cleanup()


def create_web_app(
    app_state: dict,
    config: dict,
    event_emitter: any,
    logger: any,
) -> FastAPI:
    """Create the web app & configure FastAPI application."""

    # create app
    app = FastAPI(
        title="Python Dev Tool - FUSE ",
        description="🚀 Python Development Tool - Supercharge your Python development workflow",
        version="0.0.1",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # set up CORS
    setup_cors(app)

    # add middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # add api routes
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(processes.router, prefix="/api/v1/processes", tags=["processes"])
    app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
    app.include_router(commands.router, prefix="/api/v1/commands", tags=["commands"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

    #   mount static files
    static_dir  =  Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "message": "Python Dev Tool is running (🚀 FUSE)",
            "version": "0.0.1",
            "services": {
                "project_service": await project_service.health_check(),
                "process_service": await process_service.health_check(),
                "log_service": await log_service.health_check(),
            }
        }

    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        # return exc.json()
        return {
            "status": "error",
            "error": {
                "status_code": exc.status_code,
                "message": exc.detail,
                "type": exc.type,
                "path": request.url.path,
            }
        }

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return {
            "status": "error",
            "error": {
                "status_code": 500,
                "message": str(exc),
                "type": "general | Internal Server Error",
                "path": request.url.path,
            }
        }

    return app


# Create the app instance
# app = create_app()

# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
