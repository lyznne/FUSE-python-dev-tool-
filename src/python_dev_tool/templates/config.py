"""
FUSE - Python Dev Tool
Config Templates
"""

import toml
from pathlib import Path


class FrameworkConfig:
    """Loads framework-specific configuration from template files."""

    BASE_DIR = Path(__file__).parent / "config"

    @classmethod
    def get_framework_config(cls, framework: str) -> dict:
        """
        Loads a framework-specific TOML config.

        Args:
            framework (str): The framework name (e.g. "django", "flask", "fastapi")

        Returns:
            dict: Parsed configuration dictionary
        """
        file_map = {
            "django": "django.toml",
            "flask": "flask.toml",
            "fastapi": "fastapi.toml",
        }

        filename = file_map.get(framework.lower(), "default.toml")
        file_path = cls.BASE_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(f"No config found for framework: {framework}")

        return toml.load(file_path)
