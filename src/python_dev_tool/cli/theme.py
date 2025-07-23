"""
FUSE - (python dev tool) - Defines THEME
CLI - Terminal UI Theme
"""

from rich.theme import Theme

# Theme
DEV_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "red",
        "success": "green",
        "debug": "dim white",
        "framework": "bold magenta",
        "server": "bold blue",
        "command": "bold yellow",
        "path": "dim green",
        "status": "bold green",
        "progress": "bold cyan",
    }
)
