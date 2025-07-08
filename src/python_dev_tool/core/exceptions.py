"""
FUSE - (python dev tool) - Core App
exceptions.py - Exceptions
"""


# 3rd party imports
from typing import Any, Dict, Optional

class DevToolError(Exception):
    """Base exception for all FUSE errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ConfigError(DevToolError):
    """Raised when there's a configuration error."""
    pass

class ProcessError(DevToolError):
    """Raised when there's a process management error."""

    def __init__(self, message: str,  process_id: Optional[str] = None, exit_code: Optional[int] = None):
        super().__init__(message)
        self.process_id = process_id
        self.exit_code = exit_code

class FrameworkError(DevToolError):
    """Raised when there's an error with the detected framework  or Intergration error."""

    def __init__(self, message: str, framework: Optional[str] = None):
        super().__init__(message)
        self.framework = framework

class DeploymentError(DevToolError):
    """Raised when there's an error with deployment."""

    def __init__(self, message: str, platform: Optional[str] = None):
        super().__init__(message)
        self.platform = platform

class SecurityError(DevToolError):
    """Raised when there's an error with security-related operations."""
    pass

class NetworkError(DevToolError):
    """Raised when there's an error with network-related operations."""

    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None):
        super().__init__(message)
        self.host = host
        self.port = port


# ---
