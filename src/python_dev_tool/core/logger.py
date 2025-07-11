"""
FUSE - (python dev tool) - Core Logger
logger.py - Logger Infrastructure
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator, Any
from logging.handlers import RotatingFileHandler
import structlog
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init()


class LogLevel(Enum):
    """Log levels with color coding"""

    DEBUG = ("DEBUG", Fore.CYAN)
    INFO = ("INFO", Fore.GREEN)
    WARNING = ("WARNING", Fore.YELLOW)
    ERROR = ("ERROR", Fore.RED)
    CRITICAL = ("CRITICAL", Fore.MAGENTA)


@dataclass
class LogEntry:
    """Log entry data structure"""

    timestamp: datetime
    level: str
    message: str
    source: str
    project_id: str
    process_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    exception: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record):
        # Get color for log level
        level_color = self.COLORS.get(record.levelname, Fore.WHITE)

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # Format the message
        formatted = (
            f"{Fore.BLUE}[{timestamp}]{Style.RESET_ALL} "
            f"{level_color}[{record.levelname:8}]{Style.RESET_ALL} "
            f"{Fore.WHITE}[{record.name}]{Style.RESET_ALL} "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class LogBuffer:
    """Thread-safe circular buffer for log entries"""

    def __init__(self, max_size: int = 10000):
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self.subscribers = set()

    async def add_entry(self, entry: LogEntry):
        """Add log entry to buffer"""
        async with self.lock:
            self.buffer.append(entry)
            # Notify subscribers
            await self._notify_subscribers(entry)

    async def get_recent(self, count: int = 100) -> List[LogEntry]:
        """Get recent log entries"""
        async with self.lock:
            return list(self.buffer)[-count:]

    async def get_filtered(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        count: int = 100,
    ) -> List[LogEntry]:
        """Get filtered log entries"""
        async with self.lock:
            entries = list(self.buffer)

            # Apply filters
            if level:
                entries = [e for e in entries if e.level == level]
            if source:
                entries = [e for e in entries if e.source == source]
            if since:
                entries = [e for e in entries if e.timestamp >= since]

            return entries[-count:]

    def subscribe(self, callback):
        """Subscribe to new log entries"""
        self.subscribers.add(callback)

    def unsubscribe(self, callback):
        """Unsubscribe from log entries"""
        self.subscribers.discard(callback)

    async def _notify_subscribers(self, entry: LogEntry):
        """Notify all subscribers of new entry"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(entry)
                else:
                    callback(entry)
            except Exception as e:
                # Log error but don't propagate to avoid breaking the logger
                print(f"Error in log subscriber: {e}")


class LogManager:
    """Centralized log management system"""

    def __init__(self, project_id: str, log_level: str = "INFO"):
        self.project_id = project_id
        self.log_level = getattr(logging, log_level.upper())

        # Create logs directory
        self.log_dir = Path(f".fuse/logs/{project_id}")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Log files
        self.log_file = self.log_dir / "app.log"
        self.error_log_file = self.log_dir / "error.log"

        # Initialize buffer
        self.buffer = LogBuffer()

        # Setup structured logging
        self._setup_structured_logging()

        # Setup standard logging
        self._setup_standard_logging()

        # Logger instances
        self.loggers: Dict[str, logging.Logger] = {}
        self.main_logger = self.get_logger("main")

    def _setup_structured_logging(self):
        """Setup structured logging with structlog"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._structlog_processor,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _setup_standard_logging(self):
        """Setup standard Python logging"""
        # Create formatters
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_formatter = ColoredFormatter()

        # Setup file handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(self.log_level)

        # Setup error file handler
        error_handler = RotatingFileHandler(
            self.error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        error_handler.setFormatter(file_formatter)
        error_handler.setLevel(logging.ERROR)

        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(self.log_level)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)

    def _structlog_processor(self, logger, method_name, event_dict):
        """Custom structlog processor to add entries to buffer"""
        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=event_dict.get("level", "INFO").upper(),
            message=event_dict.get("event", ""),
            source=event_dict.get("logger", "unknown"),
            project_id=self.project_id,
            process_id=event_dict.get("process_id"),
            metadata=event_dict.get("metadata", {}),
            exception=event_dict.get("exception"),
        )

        # Add to buffer asynchronously
        asyncio.create_task(self.buffer.add_entry(entry))

        return event_dict

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create logger for given name"""
        if name not in self.loggers:
            logger = logging.getLogger(f"fuse.{self.project_id}.{name}")
            self.loggers[name] = logger
        return self.loggers[name]

    def get_structured_logger(self, name: str):
        """Get structured logger"""
        return structlog.get_logger(f"fuse.{self.project_id}.{name}")

    async def get_logs(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        count: int = 100,
    ) -> List[LogEntry]:
        """Get recent logs with filtering"""
        return await self.buffer.get_filtered(level, source, since, count)

    async def stream_logs(self) -> AsyncGenerator[LogEntry, None]:
        """Stream logs in real-time"""
        queue = asyncio.Queue()

        async def subscriber(entry: LogEntry):
            await queue.put(entry)

        self.buffer.subscribe(subscriber)

        try:
            while True:
                entry = await queue.get()
                yield entry
        finally:
            self.buffer.unsubscribe(subscriber)

    async def clear_logs(self):
        """Clear log buffer"""
        async with self.buffer.lock:
            self.buffer.buffer.clear()

    def log_process_start(self, process_id: str, command: str):
        """Log process start"""
        self.main_logger.info(
            f"Process started: {command}",
            extra={"process_id": process_id, "command": command},
        )

    def log_process_stop(self, process_id: str, exit_code: int):
        """Log process stop"""
        level = logging.INFO if exit_code == 0 else logging.ERROR
        self.main_logger.log(
            level,
            f"Process stopped with exit code: {exit_code}",
            extra={"process_id": process_id, "exit_code": exit_code},
        )

    def log_file_change(self, file_path: str, change_type: str):
        """Log file change"""
        self.main_logger.info(
            f"File {change_type}: {file_path}",
            extra={"file_path": file_path, "change_type": change_type},
        )

    def log_deployment_start(self, platform: str, deployment_id: str):
        """Log deployment start"""
        self.main_logger.info(
            f"Deployment started to {platform}",
            extra={"platform": platform, "deployment_id": deployment_id},
        )

    def log_deployment_complete(self, platform: str, deployment_id: str, success: bool):
        """Log deployment completion"""
        level = logging.INFO if success else logging.ERROR
        status = "successful" if success else "failed"
        self.main_logger.log(
            level,
            f"Deployment {status} to {platform}",
            extra={
                "platform": platform,
                "deployment_id": deployment_id,
                "success": success,
            },
        )

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error with context"""
        self.main_logger.error(
            f"Error: {str(error)}", exc_info=True, extra={"context": context or {}}
        )

    def close(self):
        """Close all handlers and cleanup"""
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)


# Global log manager instance
_log_managers: Dict[str, LogManager] = {}


def get_log_manager(project_id: str, log_level: str = "INFO") -> LogManager:
    """Get or create log manager for project"""
    if project_id not in _log_managers:
        _log_managers[project_id] = LogManager(project_id, log_level)
    return _log_managers[project_id]


def setup_logging(project_id: str, log_level: str = "INFO") -> LogManager:
    """Setup logging for project"""
    return get_log_manager(project_id, log_level)


# Convenience functions
def get_logger(project_id: str, name: str) -> logging.Logger:
    """Get logger for project and name"""
    return get_log_manager(project_id).get_logger(name)


def get_structured_logger(project_id: str, name: str):
    """Get structured logger for project and name"""
    return get_log_manager(project_id).get_structured_logger(name)


async def get_project_logs(project_id: str, **kwargs) -> List[LogEntry]:
    """Get logs for project"""
    return await get_log_manager(project_id).get_logs(**kwargs)


async def stream_project_logs(project_id: str) -> AsyncGenerator[LogEntry, None]:
    """Stream logs for project"""
    async for entry in get_log_manager(project_id).stream_logs():
        yield entry


class DevToolLogger:
    """Simplified logger interface for the dev tool"""

    def __init__(self, project_id: str = "default", name: str = "main"):
        self.manager = get_log_manager(project_id)
        self.logger = self.manager.get_structured_logger(name)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(message, **kwargs)



