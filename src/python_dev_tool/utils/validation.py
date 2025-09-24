"""
FUSE - (python dev tool) - Utils
validation.py - Validation functions
"""

import re
from pathlib import Path
from typing import Union, List
from python_dev_tool.core.exceptions import DevToolError


class ValidationUtils:
    """Validation utilities for various inputs."""

    @staticmethod
    def validate_project_name(name: str) -> bool:
        """Validate a project name."""
        try:
            ValidationUtils._validate_name(name)
            return True
        except DevToolError:
            return False

    @staticmethod
    def validate_path(path: Union[str, Path]) -> bool:
        """Validate a project path."""
        try:
            ValidationUtils._validate_project_path(path)
            return True
        except DevToolError:
            return False

    # Class versions of the existing standalone functions
    @staticmethod
    def _validate_project_path(
        project_path: Union[str, Path],
        must_exist: bool = True,
        must_be_dir: bool = True,
        check_empty: bool = False,
        allow_hidden: bool = False,
    ) -> Path:
        """
        Validate a project path for various conditions.

        Args:
            project_path: Path to validate (str or Path)
            must_exist: Whether the path must exist
            must_be_dir: Whether the path must be a directory
            check_empty: Whether to check if directory is empty
            allow_hidden: Whether to allow hidden directories

        Returns:
            Path: Validated absolute Path object

        Raises:
            DevToolError: If validation fails
        """
        try:
            path = (
                Path(project_path).expanduser().resolve()
            )  # Use resolve() instead of absolute()

            if must_exist and not path.exists():
                raise DevToolError(f"Project path does not exist: {path}")

            # Only check if it's a directory if the path exists OR if we're not requiring existence
            if must_be_dir:
                if must_exist:
                    # Path must exist and be a directory
                    if not path.is_dir():
                        raise DevToolError(f"Project path is not a directory: {path}")
                else:
                    # Path doesn't need to exist, but if it does, it must be a directory
                    if path.exists() and not path.is_dir():
                        raise DevToolError(
                            f"Project path exists but is not a directory: {path}"
                        )
                    # If path doesn't exist, check if it's a directory, so skip this check

            if check_empty and path.exists() and path.is_dir():
                if any(path.iterdir()):
                    raise DevToolError(f"Project directory is not empty: {path}")

            if not allow_hidden and path.name.startswith("."):
                raise DevToolError(f"Hidden directories are not allowed: {path}")

            return path

        except DevToolError:
            raise
        except Exception as e:
            raise DevToolError(f"Invalid project path '{project_path}': {e}")

    @staticmethod
    def _validate_name(name: str, max_length: int = 50) -> str:
        """
        Validate a project/application name.

        Args:
            name: Name to validate
            max_length: Maximum allowed length

        Returns:
            str: Validated name

        Raises:
            DevToolError: If validation fails
        """
        if not name:
            raise DevToolError("Name cannot be empty")

        if len(name) > max_length:
            raise DevToolError(f"Name too long (max {max_length} chars)")

        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            raise DevToolError(
                "Name can only contain letters, numbers, underscores and hyphens"
            )

        if not name[0].isalpha():
            raise DevToolError("Name must start with a letter")

        return name

    @staticmethod
    def validate_port(port: int) -> int:
        """
        Validate a network port number.

        Args:
            port: Port number to validate

        Returns:
            int: Validated port number

        Raises:
            DevToolError: If validation fails
        """
        if not 1 <= port <= 65535:
            raise DevToolError("Port must be between 1 and 65535")
        if port < 1024:
            raise DevToolError(
                f"Port {port} is a system port (requires root privileges). "
                "Choose a port >= 1024"
            )
        return port

    @staticmethod
    def validate_framework(framework: str) -> str:
        """
        Validate a framework name against supported frameworks.

        Args:
            framework: Framework name to validate

        Returns:
            str: Validated framework name (lowercase)

        Raises:
            DevToolError: If validation fails
        """
        supported = {
            "django",
            "flask",
            "fastapi",
            "streamlit",
            "tornado",
            "sanic",
            "pyramid",
            "bottle",
        }

        framework = framework.lower().strip()
        if framework not in supported:
            raise DevToolError(
                f"Unsupported framework: {framework}\n"
                f"Supported frameworks: {', '.join(sorted(supported))}"
            )
        return framework

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate a URL format.

        Args:
            url: URL to validate

        Returns:
            str: Validated URL

        Raises:
            DevToolError: If validation fails
        """
        url = url.strip()
        if not url:
            raise DevToolError("URL cannot be empty")

        if not re.match(
            r"^(https?|ftp)://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            url,
            re.IGNORECASE,
        ):
            raise DevToolError(f"Invalid URL format: {url}")

        return url

    @staticmethod
    def validate_positive_int(value: int, name: str = "value") -> int:
        """
        Validate that a value is a positive integer.

        Args:
            value: Value to validate
            name: Name of the value for error messages

        Returns:
            int: Validated positive integer

        Raises:
            DevToolError: If validation fails
        """
        if not isinstance(value, int) or value <= 0:
            raise DevToolError(f"{name} must be a positive integer")
        return value

    @staticmethod
    def validate_choice(value: str, choices: List[str], name: str = "value") -> str:
        """
        Validate that a value is in a list of allowed choices.

        Args:
            value: Value to validate
            choices: List of allowed values
            name: Name of the value for error messages

        Returns:
            str: Validated choice

        Raises:
            DevToolError: If validation fails
        """
        if value not in choices:
            raise DevToolError(
                f"Invalid {name}: {value}\nAllowed values: {', '.join(choices)}"
            )
        return value

    @staticmethod
    def validate_config_key(key: str) -> str:
        """
        Validate a configuration key format.

        Args:
            key: Configuration key to validate

        Returns:
            str: Validated key

        Raises:
            DevToolError: If validation fails
        """
        if not key:
            raise DevToolError("Configuration key cannot be empty")

        if not re.match(r"^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$", key):
            raise DevToolError(
                "Configuration key must use dot notation with alphanumeric characters "
                "(e.g., 'server.port')"
            )

        return key

    @staticmethod
    def validate_environment(env: str) -> str:
        """
        Validate an environment name.

        Args:
            env: Environment name to validate

        Returns:
            str: Validated environment name

        Raises:
            DevToolError: If validation fails
        """
        env = env.lower().strip()
        valid_envs = {"development", "testing", "staging", "production"}

        if env not in valid_envs:
            raise DevToolError(
                f"Invalid environment: {env}\n"
                f"Valid environments: {', '.join(sorted(valid_envs))}"
            )

        return env


def validate_project_path(*args, **kwargs) -> Path:
    return ValidationUtils._validate_project_path(*args, **kwargs)


def validate_name(*args, **kwargs) -> str:
    return ValidationUtils._validate_name(*args, **kwargs)


def validate_port(*args, **kwargs) -> int:
    return ValidationUtils.validate_port(*args, **kwargs)


def validate_framework(*args, **kwargs) -> str:
    return ValidationUtils.validate_framework(*args, **kwargs)


def validate_url(*args, **kwargs) -> str:
    return ValidationUtils.validate_url(*args, **kwargs)


def validate_positive_int(*args, **kwargs) -> int:
    return ValidationUtils.validate_positive_int(*args, **kwargs)


def validate_choice(*args, **kwargs) -> str:
    return ValidationUtils.validate_choice(*args, **kwargs)


def validate_config_key(*args, **kwargs) -> str:
    return ValidationUtils.validate_config_key(*args, **kwargs)


def validate_environment(*args, **kwargs) -> str:
    return ValidationUtils.validate_environment(*args, **kwargs)
