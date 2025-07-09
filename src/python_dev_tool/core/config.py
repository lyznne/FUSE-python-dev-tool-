"""
FUSE - (python dev tool) - Core App
config.py - Config File
"""

# sys imports
from ctypes.macholib import framework
import os
import toml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# local imports
from .exceptions import ConfigError
from python_dev_tool.core.globals import (
    APP_HOST,
    APP_LOG_LEVEL,
    APP_PORT,
    APP_TIMEOUT,
    APP_UI_PORT,
    APP_WORKERS,
    FRAMEWORK,
    FUSE_CONFIG_FILE,
    LOG_BACKUP_COUNT,
    LOG_FILE_ENABLED,
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_FILE_SIZE,
    PROJECT_NAME,
    PROJECT_ROOT,
    PYTHON_VERSION,
    SUPPORTED_FRAMEWORKS,
)


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = APP_HOST
    port: int = APP_PORT
    auto_reload: bool = True
    show_logs: bool = True
    log_level: str = APP_LOG_LEVEL
    workers: int = APP_WORKERS
    timeout: int = APP_TIMEOUT


class DashboardConfig(BaseModel):
    """Dashboard configuration."""

    enabled: bool = True
    host: str = APP_HOST
    port: int = APP_UI_PORT
    auto_open: bool = True
    theme: str = "dark"

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value):
        """Validate theme."""
        if value not in ["dark", "light"]:
            raise ValueError("Invalid theme")
        return value


class DatabaseConfig(BaseModel):
    """Database configuration."""

    pass


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = Field(default_factory=lambda: os.urandom(32).hex())
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_host: List[str] = ["localhost", "127.0.0.1"]
    allowed_origin: List[str] = ["*"]
    # cors_origins: List[str] = ["http://localhost:3000"]


class DeploymentConfig(BaseModel):
    """Deployment configuration."""

    default_platform: str = ""
    auto_deploy: bool = False
    health_check_enabled: bool = True
    rollback_enabled: bool = True
    timeout: int = 300


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = LOG_LEVEL
    format: str = LOG_FORMAT
    file_enabled: bool = LOG_FILE_ENABLED
    file_path: str = LOG_FILE_PATH
    max_file_size: int = LOG_MAX_FILE_SIZE
    backup_count: int = LOG_BACKUP_COUNT


class DevToolConfig(BaseSettings):
    """Main configuration class of FUSE."""

    # project settings
    project_name: str = PROJECT_NAME
    project_root: Path = PROJECT_ROOT
    framework: Optional[str] = FRAMEWORK
    python_version: str = PYTHON_VERSION

    # Components settings
    server: ServerConfig = Field(default_factory=ServerConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Commands
    commands: Dict[str, str] = Field(default_factory=dict)

    # Environment variables
    environment: Dict[str, str] = Field(default_factory=dict)

    # Plugin settings
    plugins: List[str] = Field(default_factory=dict)

    # Development settings
    debug: bool = False
    testing: bool = False

    model_config = ConfigDict(
        env_prefix="FUSE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    @field_validator("framework")
    @classmethod
    def validate_framework(cls, v):
        """Validate framework."""

        if v is not None:
            supported_frameworks = SUPPORTED_FRAMEWORKS
            if v.lower() not in supported_frameworks:
                raise ValueError(f"Invalid framework: {v}")

        return v

    @field_validator("server")
    @classmethod
    def validate_server(cls, v):
        """Validate server settings."""
        if v.port < 1024 or v.port > 65535:
            raise ValueError("Invalid port number (must be between 1024 and 65535)")
        return v

    @field_validator("dashboard")
    @classmethod
    def validate_dashboard(cls, v):
        """Validate dashboard settings."""
        if v.port < 1024 or v.port > 65535:
            raise ValueError("Invalid port number (must be between 1024 and 65535)")
        return v


class Config: # class name ConfigManager
    """Configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.__find_config_file()
        self._config: Optional[DevToolConfig] = None
        self._load_config()

    def __find_config_file(self) -> Optional[Path]:
        """Find configuration in the project hierachy."""
        current_dir = Path.cwd()

        # look for config files in order of preference
        config_files = [
            ".devtool/config.toml",
            "devtool.toml",
            "pyproject.toml",
        ]

        for config_file in config_files:
            config_path = current_dir / config_file
            if config_path.exists():
                return config_path

            # look up the dir tree
            for parent in current_dir.parents:
                parent_config = parent / config_file
                if parent_config.exists():
                    return parent_config

        return None

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_data = {}

        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    if self.config_path.name == "pyproject.toml":
                        # Extract tool.python_dev_tool section
                        full_config = toml.load(f)
                        config_data = full_config.get("tool", {}).get(
                            "python_dev_tool", {}
                        )
                    else:
                        config_data = toml.load(f)
            except Exception as e:
                raise ConfigError(
                    f"Failed to load configuration from {self.config_path}: {e}"
                )

        # Load environment variables and create config
        try:
            self._config = DevToolConfig(**config_data)
        except Exception as e:
            raise ConfigError(f"Invalid configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        if self._config is None:
            return default

        try:
            return getattr(self._config, key, default)
        except AttributeError:
            return default

    def update(self, **kwargs: Any) -> None:
        """Update configuration values."""
        if self._config is None:
            self._config = DevToolConfig(**kwargs)
        else:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if self._config is None:
            return

        save_path = Path or self.config_path
        if save_path is None:
            save_path = Path(FUSE_CONFIG_FILE)

        # create dir if not exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        config_dict = self._config.dict()

        try:
            with open(save_path, "w") as f:
                toml.dump(config_dict, f)
        except Exception as e:
            raise ConfigError(f"Failed to save configuration to {save_path}: {e}")

    @property
    def config(self) -> DevToolConfig:
        """Get configuration object."""
        if self._config is None:
            self._load_config = DevToolConfig()
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
