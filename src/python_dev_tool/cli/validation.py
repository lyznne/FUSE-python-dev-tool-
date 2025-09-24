"""
FUSE - (python dev tool) - CLI Validators
CLI - Validators
"""

import keyword
import os
import re
from pathlib import Path
from typing import List

from python_dev_tool.core.exceptions import DevToolError


class ProjectValidator:
    """Validator for project initialization and configuration."""

    # Valid project name pattern (Python package naming convention)
    PROJECT_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*")

    # Reserved Python keywords and built-in names
    RESERVED_NAMES = set(
        keyword.kwlist
        + [
            "python",
            "pip",
            "setuptools",
            "wheel",
            "django",
            "flask",
            "fastapi",
            "streamlit",
            "tornado",
            "sanic",
            "test",
            "tests",
            "src",
            "lib",
            "bin",
            "etc",
            "var",
            "tmp",
            "home",
            "root",
        ]
    )

    # Blocked directory names
    BLOCKED_DIRECTORIES = {
        "con",
        "prn",
        "aux",
        "nul",  # Windows reserved
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }

    def validate_project_name(self, name: str) -> bool:
        """Validate project name according to Python conventions."""
        if not name:
            raise DevToolError("Project name cannot be empty")

        if not self.PROJECT_NAME_PATTERN.match(name):
            raise DevToolError(
                f"Invalid project name: '{name}'\n"
                "Project names must start with a letter or underscore, "
                "followed by letters, numbers, or underscores only."
            )

        if name.lower() in self.RESERVED_NAMES:
            raise DevToolError(
                f"Project name '{name}' is reserved. Please choose a different name."
            )

        if name.lower() in self.BLOCKED_DIRECTORIES:
            raise DevToolError(f"Project name '{name}' is not allowed on this system.")

        if len(name) > 50:
            raise DevToolError("Project name must be 50 characters or less")

        return True

    def validate_project_path(self, path: Path) -> bool:
        """Validate project path."""
        try:
            # Convert to absolute path
            abs_path = path.resolve()

            # Check if path is too long (Windows has 260 char limit)
            if len(str(abs_path)) > 240:
                raise DevToolError(
                    f"Project path is too long: {abs_path}\n"
                    "Please choose a shorter path."
                )

            # Check for invalid characters in path
            invalid_chars = '<>:"|?*'
            if any(char in str(abs_path) for char in invalid_chars):
                raise DevToolError(
                    f"Project path contains invalid characters: {abs_path}\n"
                    f"Avoid these characters: {invalid_chars}"
                )

            # Check if we can create/access the directory
            if path.exists():
                if not path.is_dir():
                    raise DevToolError(f"Path exists but is not a directory: {path}")

                # Check write permissions
                if not os.access(path, os.W_OK):
                    raise DevToolError(f"No write permission for directory: {path}")
            else:
                # Check if parent directory exists and is writable
                parent = path.parent
                if not parent.exists():
                    # Try to create parent directories
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        raise DevToolError(
                            f"Cannot create parent directories: {parent}"
                        )

                if not os.access(parent, os.W_OK):
                    raise DevToolError(
                        f"No write permission for parent directory: {parent}"
                    )

            return True

        except OSError as e:
            raise DevToolError(f"Invalid project path: {e}")

    def validate_framework(
        self, framework: str, supported_frameworks: List[str]
    ) -> bool:
        """Validate framework selection."""
        if framework not in supported_frameworks:
            raise DevToolError(
                f"Unsupported framework: '{framework}'\n"
                f"Supported frameworks: {', '.join(supported_frameworks)}"
            )
        return True

    def check_directory_conflicts(self, path: Path) -> List[str]:
        """Check for potential conflicts in project directory."""
        conflicts = []

        if not path.exists():
            return conflicts

        # Check for existing Python files that might conflict
        python_files = list(path.glob("*.py"))
        if python_files:
            conflicts.append(f"Found {len(python_files)} Python files")

        # Check for existing frameworks
        framework_indicators = {
            "Django": ["manage.py", "settings.py"],
            "Flask": ["app.py", "wsgi.py"],
            "FastAPI": ["main.py", "api.py"],
            "Streamlit": ["streamlit_app.py"],
        }

        for framework, indicators in framework_indicators.items():
            if any((path / indicator).exists() for indicator in indicators):
                conflicts.append(f"Detected existing {framework} project")

        # Check for virtual environments
        venv_dirs = [".venv", "venv", "env", "ENV"]
        existing_venvs = [venv for venv in venv_dirs if (path / venv).exists()]
        if existing_venvs:
            conflicts.append(f"Found virtual environments: {', '.join(existing_venvs)}")

        # Check for package managers
        package_files = ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"]
        existing_packages = [pkg for pkg in package_files if (path / pkg).exists()]
        if existing_packages:
            conflicts.append(f"Found package files: {', '.join(existing_packages)}")

        return conflicts


def validate_project_path(path: Path) -> None:
    """Standalone function to validate project path."""
    validator = ProjectValidator()
    validator.validate_project_path(path)


def validate_project_name(name: str) -> None:
    """Standalone function to validate project name."""
    validator = ProjectValidator()
    validator.validate_project_name(name)


def validate_framework(framework: str, supported_frameworks: List[str]) -> None:
    """Standalone function to validate framework."""
    validator = ProjectValidator()
    validator.validate_framework(framework, supported_frameworks)
