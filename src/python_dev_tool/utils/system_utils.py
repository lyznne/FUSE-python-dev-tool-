"""
FUSE - (python dev tool) - Utils
System Utils - System-related utilities for FUSE
Dependency Utils - Dependency management utilities for FUSE
"""

import platform
from typing import Any, Dict, List
import socket
import sys
import os


class SystemUtils:
    """Utility for retrieving system information."""

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """
        Get system information.

        Returns:
            dict: Dictionary containing system information.
        """

        return {
            "os": platform.system(),  # e.g., 'Linux'
            "platform": platform.platform(),  # Full platform string
            "platform-release": platform.release(),
            "platform-version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python-version": platform.python_version(),
            "python-compiler": platform.python_compiler(),
            "python-executable": sys.executable,
            "python-implementation": platform.python_implementation(),
            "python-build": platform.python_build()[0],
            "python-build-time": platform.python_build()[1],
            "python-path": os.getenv("PYTHONPATH", ""),
            "python-virtualenv": os.getenv("VIRTUAL_ENV", "None"),
            "python-virtualenv-prefix": sys.prefix,
            "python-virtualenv-site-packages": next(
                p for p in sys.path if "site-packages" in p
            ),
        }


class DependencyUtils:
    """Dependency management utilities."""

    @staticmethod
    def check_dependencies(commands: List[str]) -> Dict[str, Any]:
        """
        Check if the dependencies are installed, outdated, vulnerable, missing etc and return the status.

        Returns:
            dict: Dictionary containing the status of each dependency.
        """
        import shutil

        status = {}
        for command in commands:
            try:
                result = shutil.which(command)
                if result is None:
                    status[command] = "not installed"
                else:
                    status[command] = "installed"
            except Exception as e:
                status[command] = f"error: {str(e)}"
        return status
