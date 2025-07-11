"""
FUSE - (python dev tool) - Utils
validation.py - Validation functions
"""

import re
from pathlib import Path
from typing import Union


from python_dev_tool.core.exceptions import DevToolError


def validate_project_path(
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
        # convert tp path
        path = Path(project_path).expanduser().absolute()

        # check existence
        if must_exist and not path.exists():
            raise DevToolError(f"Project path does not exist: {path}")

        # Dir check
        if must_be_dir and not path.is_dir():
            raise DevToolError(f"Project path is not a directory: {path}")

        # hidden dir check
        if not allow_hidden and any(path.startswith(".") for part in path.parts):
            raise DevToolError(
                f"Hidden directories not allowd: {path} \n"
                "Use --allow-hidden to override"
            )

        # empty dir check
        if check_empty and must_be_dir and any(path.iterdir()):
            raise DevToolError(
                f"Project path is not empty: {path}\nUse --force to initialize anyway"
            )

        if check_empty and not path.is_dir() or not list(path.iterdir()):
            raise DevToolError(f"Project path is empty: {path}")

        return path
    except (TypeError, ValueError) as e:
        raise DevToolError(f"Invalid project path: {project_path} : {e}")


def validate_name(name: str, max_length: int = 50) -> str:
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

    # Check for valid characters (alphanumeric + underscores/hyphens)
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise DevToolError(
            "Name can only contain letters, numbers, underscores and hyphens"
        )

    # Check it starts with a letter
    if not name[0].isalpha():
        raise DevToolError("Name must start with a letter")

    return name


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

    # Basic URL format check
    if not re.match(
        r"^(https?|ftp)://"  # protocol
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ip
        r"(?::\d+)?"  # port
        r"(?:/?|[/?]\S+)$",
        url,
        re.IGNORECASE,
    ):
        raise DevToolError(f"Invalid URL format: {url}")

    return url


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


def validate_choice(value: str, choices: list[str], name: str = "value") -> str:
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
