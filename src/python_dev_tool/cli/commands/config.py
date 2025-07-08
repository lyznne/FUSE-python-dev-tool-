"""
FUSE - (python dev tool) - CLI Commands - Config Command
CLI - Config Command
"""
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.config import Config


@dataclass
class ConfigOptions:
    """Options for config command."""

    action: str
    key: Optional[str]
    value: Optional[str]
    global_config: bool
    project_path: Path


class ConfigCommand:
    """Command for managing configuration."""

    def __init__(
        self,
        action: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        global_config: bool = False,
        project_path: Path = Path("."),
    ):
        self.options = ConfigOptions(
            action=action,
            key=key,
            value=value,
            global_config=global_config,
            project_path=project_path,
        )
        self.console = Console()

    def run(self) -> Dict[str, Any]:
        """Run the config command."""
        try:
            action = self.options.action.lower()

            if action == "show":
                return self._show_config()
            elif action == "get":
                return self._get_config()
            elif action == "set":
                return self._set_config()
            elif action == "reset":
                return self._reset_config()
            else:
                raise DevToolError(f"Unknown config action: {action}")

        except Exception as e:
            raise DevToolError(f"Config operation failed: {e}")

    def _show_config(self) -> Dict[str, Any]:
        """Show all configuration."""
        config = (
            Config.load_global()
            if self.options.global_config
            else Config.load_local(self.options.project_path)
        )

        config_items = []
        for key, value in config.items():
            config_items.append(
                {
                    "key": key,
                    "value": str(value),
                    "source": "global" if self.options.global_config else "local",
                }
            )

        return {
            "config": config_items,
            "scope": "global" if self.options.global_config else "local",
        }

    def _get_config(self) -> Dict[str, Any]:
        """Get a specific config value."""
        if not self.options.key:
            raise DevToolError("No key specified for get operation")

        config = (
            Config.load_global()
            if self.options.global_config
            else Config.load_local(self.options.project_path)
        )
        value = config.get(self.options.key)

        return {
            "key": self.options.key,
            "value": value,
            "found": value is not None,
            "scope": "global" if self.options.global_config else "local",
        }

    def _set_config(self) -> Dict[str, Any]:
        """Set a config value."""
        if not self.options.key or not self.options.value:
            raise DevToolError("Both key and value must be specified for set operation")

        config = (
            Config.load_global()
            if self.options.global_config
            else Config.load_local(self.options.project_path)
        )
        config[self.options.key] = self.options.value

        if self.options.global_config:
            config.save_global()
        else:
            config.save_local(self.options.project_path)

        return {
            "key": self.options.key,
            "value": self.options.value,
            "scope": "global" if self.options.global_config else "local",
        }

    def _reset_config(self) -> Dict[str, Any]:
        """Reset config to defaults."""
        config = Config()

        if self.options.global_config:
            config.save_global()
        else:
            config.save_local(self.options.project_path)

        return {
            "reset": True,
            "scope": "global" if self.options.global_config else "local",
        }
