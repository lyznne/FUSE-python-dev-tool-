"""
FUSE - (python dev tool) - Web App
Log Models
"""

from enum import Enum
from pydantic import BaseModel


class LogEntry(BaseModel):
    """Log entry model for managing logs in the web application."""
    timestamp: str
    message: str

class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogSource(str, Enum):
    """Log sources."""
    APPLICATION = "application"
    DJANGO = "django"
    FLASK = "flask"
    FASTAPI = "fastapi"
    STREAMLITE = "streamlit"
    TORNADO = "tornado"
    SANIC = "sanic"
    PYRAMID = "pyramid"
    BOTTLE = "bottle"
    PYTHON = "python"
