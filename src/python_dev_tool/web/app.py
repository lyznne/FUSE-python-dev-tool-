"""
FUSE - (python dev tool) - Web App
app.py - Web App with proper factory pattern
"""

# sys imports
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# 3rd party imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from python_dev_tool.core.config import Config

# local imports
from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.logger import DevToolLogger, setup_logging
from python_dev_tool.web.api import (
    commands,
    files,
    logs,
    processes,
    projects,
    websocket,
)
from python_dev_tool.web.middleware.auth import AuthMiddleware
from python_dev_tool.web.middleware.cors import setup_cors
from python_dev_tool.web.middleware.rate_limit import RateLimitMiddleware
from python_dev_tool.web.middleware.security import SecurityMiddleware
from python_dev_tool.web.services.log_service import LogService
from python_dev_tool.web.services.process_service import ProcessService

# configure Logging
logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
setup_logging("default")
logger =  DevToolLogger()

# Global variables - will be initialized in factory
project_service = None
process_service = None
log_service = None
app_config = None
app_logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    global project_service, process_service, log_service

    # startup
    logger.info("Starting Python Dev Tool Web server...")

    # Initialize services if they exist
    if project_service:
        await project_service.initialize()
    if process_service:
        await process_service.initialize()
    if log_service:
        await log_service.initialize()

    yield

    # shutdown
    logger.info("Shutting down Python Dev Tool Web server...")
    if project_service:
        await project_service.cleanup()
    if process_service:
        await process_service.cleanup()
    if log_service:
        await log_service.cleanup()


def create_dev_ui_app_factory():
    """Factory function for uvicorn --factory flag."""
    # Get project path from environment variable
    project_path_str = os.getenv("DEVTOOL_PROJECT_PATH")
    if not project_path_str:
        project_path = Path.cwd()
    else:
        project_path = Path(project_path_str)

    return create_dev_ui_app(project_path)


def create_dev_ui_app(project_path: Path) -> FastAPI:
    """Create the development UI app."""
    global project_service, process_service, log_service, app_config, app_logger

    try:
        config = Config.load_from_project(project_path)
    except Exception as e:
        logger.warning(f"Could not load project config: {e}, using defaults")
        config = Config()

    # Initialize logger
    app_logger = DevToolLogger(project_path)

    # Ensure logs directory exists
    log_dir = config.logging.dir if hasattr(config, "logging") else ".fuse/logs"
    (project_path / log_dir).mkdir(parents=True, exist_ok=True)

    # Initialize services
    log_service = LogService(config=config)
    process_service = ProcessService(config=config, logger=app_logger)

    # Store config globally
    app_config = config

    event_emitter = EventEmitter()
    app_state = {"project_path": project_path, "config": config, "logger": app_logger}

    # create app
    app = create_web_app(app_state, config, event_emitter, app_logger)

    return app


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

    # Store app state
    app.state.project_path = app_state.get("project_path")
    app.state.config = config
    app.state.logger = logger

    # set up CORS
    setup_cors(app)

    # add middleware
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(processes.router, prefix="/api/v1/processes", tags=["processes"])
    app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
    app.include_router(commands.router, prefix="/api/v1/commands", tags=["commands"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

    # mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Add a simple root endpoint
    @app.get("/")
    async def root():
        """Root endpoint to verify the server is working."""
        return {
            "message": "FUSE Development UI is running",
            "status": "healthy",
            "version": "0.0.1",
            "project_path": str(app.state.project_path)
            if hasattr(app.state, "project_path")
            else None,
        }

    # health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        services_status = {}

        # Only check services if they're initialized
        if project_service:
            try:
                services_status[
                    "project_service"
                ] = await project_service.health_check()
            except:
                services_status["project_service"] = "error"

        if process_service:
            try:
                services_status[
                    "process_service"
                ] = await process_service.health_check()
            except:
                services_status["process_service"] = "error"

        if log_service:
            try:
                services_status["log_service"] = await log_service.health_check()
            except:
                services_status["log_service"] = "error"

        return {
            "status": "healthy",
            "message": "Python Dev Tool is running (🚀 FUSE)",
            "version": "0.0.1",
            "services": services_status,
        }

    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return {
            "status": "error",
            "error": {
                "status_code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
                "path": request.url.path,
            },
        }

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", extra={"show_exc_info": True})
        return {
            "status": "error",
            "error": {
                "status_code": 500,
                "message": str(exc),
                "type": "Internal Server Error",
                "path": request.url.path,
            },
        }

    return app


# Export the factory function for uvicorn
def create_app():
    """Alternative factory function name."""
    return create_dev_ui_app_factory()
