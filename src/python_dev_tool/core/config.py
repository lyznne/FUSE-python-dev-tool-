"""
FUSE - (python dev tool) - Core App
config.py - Config File
"""

# sys imports
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import toml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

from python_dev_tool.core.globals import (
    APP_HOST,
    APP_LOG_LEVEL,
    APP_PORT,
    APP_TIMEOUT,
    APP_UI_PORT,
    APP_WORKERS,
    FUSE_CONFIG_FILE,
    LOG_BACKUP_COUNT,
    LOG_FILE_ENABLED,
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_FILE_SIZE,
    PROJECT_NAME,
    SUPPORTED_FRAMEWORKS,
)

# local imports
from .exceptions import ConfigError


class ServerConfig(BaseModel):
    """Server configuration with enhanced validation."""

    host: str = APP_HOST
    port: int = APP_PORT
    auto_reload: bool = True
    show_logs: bool = True
    log_level: str = APP_LOG_LEVEL
    workers: int = APP_WORKERS
    timeout: int = APP_TIMEOUT

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host address."""
        if not v or not isinstance(v, str):
            raise ValueError("Host must be a non-empty string")

        # Basic validation for common host formats
        valid_hosts = ["0.0.0.0", "127.0.0.1", "localhost"]
        if (
            v not in valid_hosts
            and not v.replace(".", "")
            .replace(":", "")
            .replace("-", "")
            .replace("_", "")
            .isalnum()
        ):
            raise ValueError(f"Invalid host format: {v}")

        return v.strip()

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("Port must be an integer")

        if not (1024 <= v <= 65535):
            raise ValueError(f"Port must be between 1024 and 65535, got {v}")

        return v

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """Validate worker count."""
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("Workers must be an integer")

        if v < 1:
            raise ValueError("Workers must be at least 1")

        # Cap workers at reasonable limit
        return min(v, 32)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("Timeout must be an integer")

        if v < 1:
            raise ValueError("Timeout must be at least 1 second")

        return min(v, 3600)  # Cap at 1 hour

class DashboardConfig(BaseModel):
    """Dashboard configuration with enhanced validation."""

    enabled: bool = True
    host: str = APP_HOST
    port: int = APP_UI_PORT
    auto_open: bool = True
    theme: str = "dark"

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v):
        """Ensure port is a valid integer between 1024 and 65535."""
        # Handle tuple/list inputs
        if isinstance(v, (tuple, list)):
            v = v[0] if v else APP_UI_PORT

        try:
            port = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"Port must be an integer, got: {v!r}")

        if not (1024 <= port <= 65535):
            raise ValueError(f"Invalid port {port}. Must be between 1024 and 65535.")

        return port

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        """Validate theme selection."""
        valid_themes = ["dark", "light", "auto"]
        if value.lower() not in valid_themes:
            raise ValueError(f"Invalid theme '{value}'. Must be one of: {valid_themes}")
        return value.lower()

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host address."""
        if not v or not isinstance(v, str):
            raise ValueError("Host must be a non-empty string")
        return v.strip()


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: Optional[str] = None
    driver: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    @field_validator("pool_size", "max_overflow", "pool_timeout")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate positive integer values."""
        if not isinstance(v, int) or v < 1:
            raise ValueError("Value must be a positive integer")
        return v

class SecurityConfig(BaseModel):
    """Security configuration with enhanced validation."""

    secret_key: str = Field(default_factory=lambda: os.urandom(32).hex())
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"])
    allowed_origins: List[str] = Field(default=["*"])

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in valid_algorithms:
            raise ValueError(f"Invalid algorithm. Must be one of: {valid_algorithms}")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, v: int) -> int:
        """Validate token expiry time."""
        if not isinstance(v, int) or v < 1:
            raise ValueError("Token expiry must be a positive integer")
        return min(v, 10080)  # Cap at 1 week

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_allowed_origins(cls, v: Any) -> List[str]:
        """Convert and validate allowed origins."""
        if v is None:
            return ["*"]
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, (list, tuple)):
            return [item.strip() for item in v if isinstance(item, str)]
        raise ValueError("allowed_origins must be a string or a list of strings")

class DeploymentConfig(BaseModel):
    """Deployment configuration."""

    default_platform: str = ""
    auto_deploy: bool = False
    health_check_enabled: bool = True
    rollback_enabled: bool = True
    timeout: int = 300
    platforms: List[str] = Field(default=["docker", "railway", "render"])

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate deployment timeout."""
        if not isinstance(v, int) or v < 30:
            raise ValueError("Deployment timeout must be at least 30 seconds")
        return min(v, 3600)  # Cap at 1 hour

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: List[str]) -> List[str]:
        """Validate deployment platforms."""
        if not isinstance(v, list):
            raise ValueError("Platforms must be a list")

        valid_platforms = ["docker", "railway", "render", "heroku", "vercel", "netlify"]
        invalid_platforms = [p for p in v if p not in valid_platforms]

        if invalid_platforms:
            raise ValueError(
                f"Invalid platforms: {invalid_platforms}. Valid options: {valid_platforms}"
            )

        return v


class LoggingConfig(BaseModel):
    """Logging configuration with validation."""

    level: str = LOG_LEVEL
    format: str = LOG_FORMAT
    file_enabled: bool = LOG_FILE_ENABLED
    file_path: str = LOG_FILE_PATH
    max_file_size: int = LOG_MAX_FILE_SIZE
    backup_count: int = LOG_BACKUP_COUNT

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @field_validator("max_file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate max file size."""
        if not isinstance(v, int) or v < 1024:  # Minimum 1KB
            raise ValueError("Max file size must be at least 1024 bytes")
        return v

    @field_validator("backup_count")
    @classmethod
    def validate_backup_count(cls, v: int) -> int:
        """Validate backup count."""
        if not isinstance(v, int) or v < 0:
            raise ValueError("Backup count must be a non-negative integer")
        return min(v, 100)  # Cap at 100 backups

class DevToolConfig(BaseSettings):
    """Main configuration class of FUSE with enhanced validation."""

    # Project settings
    project_name: str = Field(
        default=PROJECT_NAME, description="Project name", min_length=1, max_length=100
    )
    project_root: Optional[Path] = Field(default=None, description="Project root path")
    framework: Literal[
        "django", "flask", "fastapi", "streamlit", "tornado", "sanic"
    ] = Field(default="flask", description="Framework name")
    python_version: str = Field(
        default="3.8+", description="Python version", pattern=r"^[0-9]+\.[0-9]+\+?$"
    )
    version: str = Field(
        default="1.0.0", description="Project version", pattern=r"^\d+\.\d+\.\d+$"
    )

    # Component settings
    server: ServerConfig = Field(default_factory=ServerConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Commands
    commands: Dict[str, str] = Field(
        default_factory=dict, description="Custom commands for the project"
    )

    # Environment variables
    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )

    # Plugin settings
    plugins: List[str] = Field(
        default_factory=list, description="List of enabled plugins"
    )

    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Enable testing mode")

    model_config = ConfigDict(
        env_prefix="FUSE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
        # Enable validation on assignment
        validate_assignment=True,
    )

    @field_validator("project_name", mode="before")
    @classmethod
    def validate_project_name(cls, v: Any) -> str:
        """Ensure project_name is always a string."""
        if isinstance(v, (tuple, list)):
            return str(v[0]) if v else PROJECT_NAME

        name = str(v).strip()
        if not name:
            raise ValueError("Project name cannot be empty")

        # Check for invalid characters
        invalid_chars = set(name) & set('\\/:*?"<>|')
        if invalid_chars:
            raise ValueError(
                f"Project name contains invalid characters: {invalid_chars}"
            )

        return name

    @field_validator("plugins", mode="before")
    @classmethod
    def validate_plugins(cls, v: Any) -> List[str]:
        """Convert plugins to list if needed."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, dict):
            return list(v.values())
        if isinstance(v, (tuple, set)):
            return list(v)
        return v

    @field_validator("framework")
    @classmethod
    def validate_framework(cls, v: str) -> str:
        """Validate framework selection."""
        if v is not None:
            framework_lower = v.lower()
            if framework_lower not in SUPPORTED_FRAMEWORKS:
                raise ValueError(
                    f"Invalid framework: {v}. Supported frameworks: {SUPPORTED_FRAMEWORKS}"
                )
            return framework_lower
        return "flask"  # Default fallback

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate command definitions."""
        if not isinstance(v, dict):
            raise ValueError("Commands must be a dictionary")

        # Validate command names and values
        validated_commands = {}
        for cmd_name, cmd_value in v.items():
            if not isinstance(cmd_name, str) or not cmd_name.strip():
                raise ValueError(f"Invalid command name: {cmd_name}")

            if not isinstance(cmd_value, str) or not cmd_value.strip():
                raise ValueError(f"Invalid command value for '{cmd_name}': {cmd_value}")

            validated_commands[cmd_name.strip()] = cmd_value.strip()

        return validated_commands

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate environment variables."""
        if not isinstance(v, dict):
            raise ValueError("Environment must be a dictionary")

        # Validate environment variable names and values
        validated_env = {}
        for env_name, env_value in v.items():
            if not isinstance(env_name, str) or not env_name.strip():
                raise ValueError(f"Invalid environment variable name: {env_name}")

            # Environment values can be empty, but must be strings
            if not isinstance(env_value, str):
                env_value = str(env_value)

            validated_env[env_name.strip()] = env_value

        return validated_env

    @model_validator(mode="after")
    def validate_port_conflicts(self) -> "DevToolConfig":
        """Ensure server and dashboard ports don't conflict."""
        if self.server.port == self.dashboard.port:
            raise ValueError(
                f"Server port ({self.server.port}) and dashboard port "
                f"({self.dashboard.port}) cannot be the same"
            )
        return self

class Config:
    """Optimized configuration manager with caching and thread safety."""

    _instances: Dict[str, "Config"] = {}
    _lock = threading.RLock()

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[DevToolConfig] = None
        self._config_mtime: Optional[float] = None
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> "Config":
        """Get singleton instance for a given config path."""
        path_key = str(config_path) if config_path else "default"

        with cls._lock:
            if path_key not in cls._instances:
                cls._instances[path_key] = cls(config_path)
            return cls._instances[path_key]

    @lru_cache(maxsize=1)
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in the project hierarchy (cached)."""
        current_dir = Path.cwd()

        # Configuration files in order of preference
        config_files = [
            ".fuse/config.toml",
            "fuse.toml",
            "pyproject.toml",
        ]

        for config_file in config_files:
            # Check current directory
            config_path = current_dir / config_file
            if config_path.exists():
                return config_path

            # Check parent directories
            for parent in current_dir.parents:
                parent_config = parent / config_file
                if parent_config.exists():
                    return parent_config

        return None

    def _unwrap_singleton_values(self, value: Any) -> Any:
        """Recursively unwrap singleton tuples/lists."""
        if isinstance(value, (tuple, list)) and len(value) == 1:
            return self._unwrap_singleton_values(value[0])
        elif isinstance(value, dict):
            return {k: self._unwrap_singleton_values(v) for k, v in value.items()}
        return value

    def _preprocess_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-process configuration data before validation."""
        processed = {}

        for key, value in config_data.items():
            if isinstance(value, dict):
                processed[key] = self._preprocess_config_data(value)
            else:
                processed[key] = self._unwrap_singleton_values(value)

            # Special handling for plugins dictionary format
            if key == "plugins" and isinstance(value, dict):
                processed[key] = list(value.values())

        return processed

    def _should_reload_config(self) -> bool:
        """Check if config file has been modified since last load."""
        if not self.config_path or not self.config_path.exists():
            return False

        current_mtime = self.config_path.stat().st_mtime
        return self._config_mtime != current_mtime

    def _load_config(self) -> None:
        """Load and validate configuration with error handling."""
        config_data = {}

        if self.config_path and self.config_path.exists():
            try:
                # Update modification time
                self._config_mtime = self.config_path.stat().st_mtime

                with open(self.config_path, "r", encoding="utf-8") as f:
                    raw_data = toml.load(f)

                # Handle pyproject.toml special case
                if self.config_path.name == "pyproject.toml":
                    config_data = raw_data.get("tool", {}).get("python_dev_tool", {})
                else:
                    config_data = raw_data

                # Pre-process the data
                config_data = self._preprocess_config_data(config_data)

            except toml.TomlDecodeError as e:
                raise ConfigError(f"Invalid TOML syntax in {self.config_path}: {e}")
            except Exception as e:
                raise ConfigError(f"Failed to load config from {self.config_path}: {e}")

        try:
            self._config = DevToolConfig(**config_data)
        except Exception as e:
            raise ConfigError(f"Invalid configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with auto-reload check."""
        if self._should_reload_config():
            self.reload()

        if self._config is None:
            return default

        try:
            # Support nested key access (e.g., "server.port")
            if "." in key:
                obj = self._config
                for part in key.split("."):
                    obj = getattr(obj, part, None)
                    if obj is None:
                        return default
                return obj
            else:
                return getattr(self._config, key, default)
        except AttributeError:
            return default

    def update(self, **kwargs: Any) -> None:
        """Update configuration values with validation."""
        with self._lock:
            if self._config is None:
                self._config = DevToolConfig(**kwargs)
            else:
                # Create new config with updated values
                current_data = self._config.model_dump()
                current_data.update(kwargs)
                self._config = DevToolConfig(**current_data)

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file with atomic write."""
        if self._config is None:
            raise ConfigError("No configuration to save")

        save_path = path or self.config_path
        if save_path is None:
            save_path = Path(FUSE_CONFIG_FILE)

        # Create directory if it doesn't exist
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Get configuration as dictionary
        config_dict = self._config.model_dump(exclude_unset=False)

        try:
            # Atomic write using temporary file
            temp_path = save_path.with_suffix(save_path.suffix + ".tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                toml.dump(config_dict, f)

            # Atomically replace the original file
            temp_path.replace(save_path)

            # Update modification time
            self._config_mtime = save_path.stat().st_mtime

        except Exception as e:
            # Clean up temporary file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise ConfigError(f"Failed to save configuration to {save_path}: {e}")

    @property
    def config(self) -> DevToolConfig:
        """Get configuration object with auto-reload."""
        if self._should_reload_config():
            self.reload()

        if self._config is None:
            self._config = DevToolConfig()
        return self._config

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def _apply_auto_detection(self, config: DevToolConfig) -> DeploymentConfig:
        """Apply auto-detection to fill in missing values."""
        # detector = ProjectDetector(self.project_path)

        # # Auto-detect framework if not set
        # if not config.framework:
        #     config.framework = detector.detect_framework()

        # # Auto-detect project name if not set
        # if not config.name:
        #     config.name = detector.detect_project_name()

        # # Auto-detect commands if not set
        # if not config.commands.dev:
        #     config.commands = detector.detect_commands(config.framework)

        # # Auto-detect virtual environment
        # if not config.virtual_env:
        #     config.virtual_env = detector.detect_virtual_env()

        return config

    @classmethod
    def load_from_path(cls, path: Path) -> "Config":
        """Load the configuration from a file path."""
        return cls.load_from_project(path)

    @classmethod
    def load_from_project(cls, project_path: Path) -> "Config":
        """Load the configuration from a project path."""
        config_file = project_path / ".fuse" / "config.toml"

        if not config_file.exists():
            raise ConfigError(f"Config file not found at: {config_file}")
        return cls(config_path=config_file)

    @classmethod
    def load_project_config(cls, project_path: Path) -> Dict[str, Any]:
        """Load the configuration from a project path."""
        config_file = project_path / ".fuse" / "config.toml"

        if not config_file.exists():
            raise ConfigError(f"Config file not found at: {config_file}")

    @classmethod
    def set_config_file(cls, config_path: Union[str, Path]) -> None:
        if isinstance(config_path, str):
            config_path = Path(config_path)

        if not isinstance(config_path, Path):
            raise TypeError(f"Expected a Path, got {type(config_path).__name__}")

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        cls._config_file = config_path
