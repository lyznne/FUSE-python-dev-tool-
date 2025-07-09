"""
FUSE - (python dev tool) - Defines PROJECT
A comprehensive development tool for Python projects.

This package provides a live development server, web dashboard, and one-click deployment capabilitties  for Python Web applications.
"""

__version__ = "0.0.1"
__author__ = "lyznne"
__email__ = "emuthiani26@gmail.com"
__license__ = "AGPL-3.0"


from .core.app import DevToolApp
from .core.config import Config, DevToolConfig
from .core.exceptions import DevToolError, ConfigError, ProcessError, FrameworkError



__all__ = [
    "__version__",
    "DevToolApp",
    "Config",
    "DevToolConfig",
    "DevToolError",
    "ConfigError",
    "ProcessError",
    "FrameworkError",
]
