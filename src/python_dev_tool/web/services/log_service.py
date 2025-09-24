"""
Log Service - Comprehensive logging, monitoring, and analytics
Handles log collection, processing, storage, and real-time streaming
"""

import json
import logging
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import aiofiles

from python_dev_tool.core.config import Config
from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.exceptions import LogError
from python_dev_tool.utils.async_utils import AsyncUtils
from python_dev_tool.utils.string_utils import StringUtils
from python_dev_tool.web.models.log import LogEntry, LogLevel, LogSource


class LogEventType(Enum):
    """Log event types."""

    LOG_ENTRY_CREATED = "log_entry_created"
    ERROR_DETECTED = "error_detected"
    WARNING_DETECTED = "warning_detected"
    PATTERN_MATCHED = "pattern_matched"
    LOG_ROTATION = "log_rotation"
    LOG_EXPORT = "log_export"


@dataclass
class LogFilter:
    """Log filtering configuration."""

    levels: Optional[List[LogLevel]] = None
    sources: Optional[List[LogSource]] = None
    project_ids: Optional[List[str]] = None
    process_ids: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search_query: Optional[str] = None
    regex_pattern: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class LogStats:
    """Log statistics."""

    total_entries: int
    error_count: int
    warning_count: int
    info_count: int
    debug_count: int
    entries_per_hour: Dict[str, int]
    top_sources: Dict[str, int]
    avg_message_length: float
    last_error_time: Optional[datetime] = None


@dataclass
class LogPattern:
    """Log pattern for monitoring."""

    name: str
    pattern: str
    level: LogLevel
    action: str
    enabled: bool = True
    match_count: int = 0
    last_match: Optional[datetime] = None


class LogProcessor:
    """Process and enrich log entries."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LogProcessor")
        self.string_utils = StringUtils()

        # Common error patterns
        self.error_patterns = [
            r"(?i)error|exception|traceback|failed|failure",
            r"(?i)connection\s+(refused|timeout|error)",
            r"(?i)permission\s+denied",
            r"(?i)file\s+not\s+found",
            r"(?i)syntax\s+error",
            r"(?i)import\s+error",
            r"(?i)module\s+not\s+found",
            r"(?i)database\s+error",
            r"(?i)authentication\s+failed",
            r"(?i)access\s+denied",
        ]

        # Warning patterns
        self.warning_patterns = [
            r"(?i)warn|warning|deprecated",
            r"(?i)timeout|slow|performance",
            r"(?i)retry|retrying",
            r"(?i)fallback|default",
            r"(?i)missing\s+configuration",
        ]

    async def process_log_entry(self, entry: LogEntry) -> LogEntry:
        """Process and enrich a log entry."""
        # Detect log level if not set
        if entry.level == LogLevel.UNKNOWN:
            entry.level = self._detect_log_level(entry.message)

        # Extract structured data
        entry.structured_data = self._extract_structured_data(entry.message)

        # Add tags
        entry.tags = self._extract_tags(entry.message)

        # Detect stack traces
        if self._is_stack_trace(entry.message):
            entry.tags.append("stack_trace")

        # Parse Django/Flask specific formats
        if entry.source == LogSource.DJANGO:
            entry = self._parse_django_log(entry)
        elif entry.source == LogSource.FLASK:
            entry = self._parse_flask_log(entry)

        return entry

    def _detect_log_level(self, message: str) -> LogLevel:
        """Detect log level from message content."""
        message_lower = message.lower()

        # Check for explicit level indicators
        if any(
            word in message_lower
            for word in ["error", "exception", "traceback", "failed"]
        ):
            return LogLevel.ERROR
        elif any(word in message_lower for word in ["warn", "warning", "deprecated"]):
            return LogLevel.WARNING
        elif any(word in message_lower for word in ["info", "information"]):
            return LogLevel.INFO
        elif any(word in message_lower for word in ["debug", "trace"]):
            return LogLevel.DEBUG

        return LogLevel.INFO

    def _extract_structured_data(self, message: str) -> Dict[str, Any]:
        """Extract structured data from log message."""
        structured = {}

        # Extract JSON if present
        try:
            json_match = re.search(r"\{[^}]+\}", message)
            if json_match:
                structured["json"] = json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Extract key-value pairs
        kv_pattern = r"(\w+)=([^\s]+)"
        for match in re.finditer(kv_pattern, message):
            key, value = match.groups()
            structured[key] = value

        # Extract URLs
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, message)
        if urls:
            structured["urls"] = urls

        # Extract IP addresses
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, message)
        if ips:
            structured["ips"] = ips

        return structured

    def _extract_tags(self, message: str) -> List[str]:
        """Extract tags from log message."""
        tags = []

        # Check for common patterns
        for pattern in self.error_patterns:
            if re.search(pattern, message):
                tags.append("error_pattern")
                break

        for pattern in self.warning_patterns:
            if re.search(pattern, message):
                tags.append("warning_pattern")
                break

        # Extract hashtags
        hashtag_pattern = r"#\w+"
        hashtags = re.findall(hashtag_pattern, message)
        tags.extend(hashtags)

        return tags

    def _is_stack_trace(self, message: str) -> bool:
        """Check if message contains a stack trace."""
        stack_indicators = [
            "Traceback (most recent call last)",
            'File "',
            "line ",
            "at ",
            "caused by",
            "stack trace",
        ]
        return any(indicator in message for indicator in stack_indicators)

    def _parse_django_log(self, entry: LogEntry) -> LogEntry:
        """Parse Django-specific log format."""
        # Django request logs
        django_request_pattern = (
            r'\[(\d{2}\/\w{3}\/\d{4} \d{2}:\d{2}:\d{2})\] "([A-Z]+) ([^"]+)"'
        )
        match = re.search(django_request_pattern, entry.message)

        if match:
            timestamp_str, method, path = match.groups()
            entry.structured_data.update(
                {"http_method": method, "path": path, "request_log": True}
            )
            entry.tags.append("http_request")

        return entry

    def _parse_flask_log(self, entry: LogEntry) -> LogEntry:
        """Parse Flask-specific log format."""
        # Flask request logs
        flask_pattern = (
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[([^\]]+)\] "([A-Z]+) ([^"]+)"'
        )
        match = re.search(flask_pattern, entry.message)

        if match:
            ip, timestamp_str, method, path = match.groups()
            entry.structured_data.update(
                {
                    "client_ip": ip,
                    "http_method": method,
                    "path": path,
                    "request_log": True,
                }
            )
            entry.tags.append("http_request")

        return entry


class LogStorage:
    """Handle log storage and retrieval."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.LogStorage")

        # In-memory buffers for recent logs
        self.recent_logs: deque = deque(maxlen=1000)
        self.logs_by_project: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.logs_by_process: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

    async def store_log_entry(self, entry: LogEntry):
        """Store a log entry."""
        # Add to in-memory buffers
        self.recent_logs.append(entry)

        if entry.project_id:
            self.logs_by_project[entry.project_id].append(entry)

        if entry.process_id:
            self.logs_by_process[entry.process_id].append(entry)

        # Write to file
        await self._write_to_file(entry)

    async def get_logs(
        self, filter_config: LogFilter, limit: int = 100, offset: int = 0
    ) -> List[LogEntry]:
        """Retrieve logs with filtering."""
        # For now, use in-memory logs
        # XXX :TODO - load from state.db and fallback to log file 
        # In production, this would query the file system or database
        logs = list(self.recent_logs)

        # Apply filters
        if filter_config.levels:
            logs = [log for log in logs if log.level in filter_config.levels]

        if filter_config.sources:
            logs = [log for log in logs if log.source in filter_config.sources]

        if filter_config.project_ids:
            logs = [log for log in logs if log.project_id in filter_config.project_ids]

        if filter_config.process_ids:
            logs = [log for log in logs if log.process_id in filter_config.process_ids]

        if filter_config.start_time:
            logs = [log for log in logs if log.timestamp >= filter_config.start_time]

        if filter_config.end_time:
            logs = [log for log in logs if log.timestamp <= filter_config.end_time]

        if filter_config.search_query:
            query = filter_config.search_query.lower()
            logs = [log for log in logs if query in log.message.lower()]

        if filter_config.regex_pattern:
            pattern = re.compile(filter_config.regex_pattern)
            logs = [log for log in logs if pattern.search(log.message)]

        if filter_config.tags:
            logs = [
                log
                for log in logs
                if any(tag in log.tags for tag in filter_config.tags)
            ]

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        return logs[offset : offset + limit]

    async def _write_to_file(self, entry: LogEntry):
        """Write log entry to file."""
        try:
            # Create date-based file structure
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            # XXX: TODO update to log file in confi
            log_file = self.storage_path / f"{date_str}.log"

            # Format log entry
            log_line = self._format_log_entry(entry)

            # Write to file
            async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                await f.write(log_line + "\n")

        except Exception as e:
            self.logger.error(f"Failed to write log to file: {str(e)}")

    def _format_log_entry(self, entry: LogEntry) -> str:
        """Format log entry for file storage."""
        return json.dumps(
            {
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "source": entry.source.value,
                "message": entry.message,
                "project_id": entry.project_id,
                "process_id": entry.process_id,
                "tags": entry.tags,
                "structured_data": entry.structured_data,
                "stack_trace": entry.stack_trace,
            }
        )


class LogService:
    """Core log management service."""

    def __init__(self, config: Optional[Config] = None):
        self.logger = logging.getLogger(__name__)
        try:
            self.config = config or Config()
            self._validate_config()
            self.storage_path = self._resolve_logs_path()
            self._ensure_logs_dir()

            # Initialize components
            self.storage = LogStorage(self.storage_path)
            self.processor = LogProcessor()
            self.event_emitter = EventEmitter()
            self.async_utils = AsyncUtils()

            # Pattern monitoring
            self.patterns: Dict[str, LogPattern] = {}

            # Statistics - Initialize here instead of in _get_logs_dir
            self.stats = LogStats(
                total_entries=0,
                error_count=0,
                warning_count=0,
                info_count=0,
                debug_count=0,
                entries_per_hour={},
                top_sources={},
                avg_message_length=0.0,
            )

            # Real-time subscribers
            self.subscribers: Dict[str, Callable] = {}

        except Exception as e:
            self.logger.error(f"Failed to initialize LogService: {str(e)}")
            raise LogError(f"Failed to initialize LogService: {str(e)}")

    def _validate_config(self):
        """Validate config."""
        if not hasattr(self.config, "logging"):
            # Create default logging config if missing
            from types import SimpleNamespace

            self.config.logging = SimpleNamespace()
            self.config.logging.dir = ".fuse/logs"
            self.config.logging.level = "INFO"
            self.config.logging.format = "default"

    def _resolve_logs_path(self) -> Path:
        """Resolve the absolute path to logs directory."""
        log_dir = getattr(self.config.logging, "dir", ".fuse/logs")

        if Path(log_dir).is_absolute():
            return Path(log_dir)

        # Get project root - handle different ways it might be stored
        project_root = None
        if hasattr(self.config, "project_root") and self.config.project_root:
            project_root = Path(self.config.project_root)
        elif hasattr(self.config, "project_path") and self.config.project_path:
            project_root = Path(self.config.project_path)
        else:
            project_root = Path.cwd()

        return project_root / log_dir

    def _ensure_logs_dir(self) -> None:
        """Ensure logs directory exists."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create logs directory: {str(e)}")
            raise

    async def initialize(self):
        """Initialize the log service."""
        self.logger.info("Initializing LogService...")

        # Load existing patterns
        await self._load_patterns()

        # Set up default patterns
        await self._setup_default_patterns()

        self.logger.info("LogService initialized successfully")

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up LogService...")

        # Save patterns
        await self._save_patterns()

        # Rotate logs if needed
        await self._rotate_logs()

        self.logger.info("LogService cleanup completed")

    async def _load_patterns(self):
        """Load patterns from storage."""
        try:
            patterns_file = self.storage_path / "patterns.json"
            if patterns_file.exists():
                async with aiofiles.open(patterns_file, "r") as f:
                    content = await f.read()
                    patterns_data = json.loads(content)

                    for name, data in patterns_data.items():
                        self.patterns[name] = LogPattern(**data)
        except Exception as e:
            self.logger.warning(f"Failed to load patterns: {e}")

    async def _save_patterns(self):
        """Save patterns to storage."""
        try:
            patterns_file = self.storage_path / "patterns.json"
            patterns_data = {
                name: asdict(pattern) for name, pattern in self.patterns.items()
            }

            async with aiofiles.open(patterns_file, "w") as f:
                await f.write(json.dumps(patterns_data, indent=2))
        except Exception as e:
            self.logger.warning(f"Failed to save patterns: {e}")

    async def _setup_default_patterns(self):
        """Set up default monitoring patterns."""
        default_patterns = [
            LogPattern(
                name="error_detection",
                pattern=r"(?i)error|exception|failed|failure",
                level=LogLevel.ERROR,
                action="alert",
            ),
            LogPattern(
                name="warning_detection",
                pattern=r"(?i)warn|warning|deprecated",
                level=LogLevel.WARNING,
                action="log",
            ),
        ]

        for pattern in default_patterns:
            if pattern.name not in self.patterns:
                self.patterns[pattern.name] = pattern

    async def _rotate_logs(self):
        """Rotate old log files."""
        try:
            # Simple rotation - remove files older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)

            for log_file in self.storage_path.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.logger.info(f"Rotated old log file: {log_file}")
        except Exception as e:
            self.logger.warning(f"Failed to rotate logs: {e}")

    async def _update_stats(self, entry: LogEntry):
        """Update log statistics."""
        self.stats.total_entries += 1

        if entry.level == LogLevel.ERROR:
            self.stats.error_count += 1
            self.stats.last_error_time = entry.timestamp
        elif entry.level == LogLevel.WARNING:
            self.stats.warning_count += 1
        elif entry.level == LogLevel.INFO:
            self.stats.info_count += 1
        elif entry.level == LogLevel.DEBUG:
            self.stats.debug_count += 1

        # Update hourly stats
        hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
        self.stats.entries_per_hour[hour_key] = (
            self.stats.entries_per_hour.get(hour_key, 0) + 1
        )

        # Update source stats
        source_name = entry.source.value
        self.stats.top_sources[source_name] = (
            self.stats.top_sources.get(source_name, 0) + 1
        )

        # Update average message length
        total_length = self.stats.avg_message_length * (
            self.stats.total_entries - 1
        ) + len(entry.message)
        self.stats.avg_message_length = total_length / self.stats.total_entries

    async def _check_patterns(self, entry: LogEntry):
        """Check entry against monitoring patterns."""
        for pattern in self.patterns.values():
            if not pattern.enabled:
                continue

            try:
                if re.search(pattern.pattern, entry.message):
                    pattern.match_count += 1
                    pattern.last_match = entry.timestamp

                    await self.event_emitter.emit(
                        LogEventType.PATTERN_MATCHED.value,
                        {
                            "pattern": pattern.name,
                            "entry": asdict(entry),
                            "action": pattern.action,
                        },
                    )
            except re.error as e:
                self.logger.warning(f"Invalid regex pattern '{pattern.name}': {e}")

    async def _notify_subscribers(self, entry: LogEntry):
        """Notify real-time subscribers."""
        for subscriber_id, subscriber_info in self.subscribers.items():
            try:
                callback = subscriber_info["callback"]
                filter_config = subscriber_info.get("filter")

                # Apply filter if specified
                if filter_config:
                    # Simple filter check - in production would be more comprehensive
                    if filter_config.levels and entry.level not in filter_config.levels:
                        continue
                    if (
                        filter_config.sources
                        and entry.source not in filter_config.sources
                    ):
                        continue

                # Call the callback
                if callable(callback):
                    await callback(entry)

            except Exception as e:
                self.logger.warning(f"Failed to notify subscriber {subscriber_id}: {e}")

    async def add_log_entry(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        source: LogSource = LogSource.APPLICATION,
        project_id: Optional[str] = None,
        process_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """Add a new log entry."""
        try:
            # Create log entry
            entry = LogEntry(
                id=self.async_utils.generate_id(),
                timestamp=datetime.now(timezone.utc),
                level=level,
                source=source,
                message=message,
                project_id=project_id,
                process_id=process_id,
                stack_trace=stack_trace,
                tags=[],
                structured_data=extra_data or {},
            )

            # Process the entry
            entry = await self.processor.process_log_entry(entry)

            # Store the entry
            await self.storage.store_log_entry(entry)

            # Update statistics
            await self._update_stats(entry)

            # Check patterns
            await self._check_patterns(entry)

            # Notify subscribers
            await self._notify_subscribers(entry)

            # Emit event
            await self.event_emitter.emit(
                LogEventType.LOG_ENTRY_CREATED.value, {"entry": asdict(entry)}
            )

            return entry

        except Exception as e:
            self.logger.error(f"Failed to add log entry: {str(e)}")
            raise LogError(f"Failed to add log entry: {str(e)}")

    async def get_logs(
        self,
        filter_config: Optional[LogFilter] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LogEntry]:
        """Get logs with filtering."""
        if not filter_config:
            filter_config = LogFilter()

        return await self.storage.get_logs(filter_config, limit, offset)

    async def get_log_stats(
        self, project_id: Optional[str] = None, time_range: Optional[timedelta] = None
    ) -> LogStats:
        """Get log statistics."""
        # For now, return global stats
        # In production, would calculate based on filters
        return self.stats

    async def search_logs(
        self, query: str, limit: int = 100, use_regex: bool = False
    ) -> List[LogEntry]:
        """Search logs by query."""
        filter_config = LogFilter()

        if use_regex:
            filter_config.regex_pattern = query
        else:
            filter_config.search_query = query

        return await self.storage.get_logs(filter_config, limit)

    async def export_logs(
        self,
        filter_config: LogFilter,
        format: str = "json",
        output_path: Optional[Path] = None,
    ) -> Path:
        """Export logs to file."""
        try:
            # Get logs
            logs = await self.storage.get_logs(filter_config, limit=10000)

            # Generate output path
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.storage_path / f"export_{timestamp}.{format}"

            # Export based on format
            if format == "json":
                await self._export_json(logs, output_path)
            elif format == "csv":
                await self._export_csv(logs, output_path)
            elif format == "txt":
                await self._export_txt(logs, output_path)
            else:
                raise LogError(f"Unsupported export format: {format}")

            # Emit event
            await self.event_emitter.emit(
                LogEventType.LOG_EXPORT.value,
                {"path": str(output_path), "format": format, "count": len(logs)},
            )

            self.logger.info(f"Exported {len(logs)} logs to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to export logs: {str(e)}")
            raise LogError(f"Failed to export logs: {str(e)}")

    async def _export_json(self, logs: List[LogEntry], output_path: Path):
        """Export logs as JSON."""
        data = [asdict(log) for log in logs]
        async with aiofiles.open(output_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

    async def _export_csv(self, logs: List[LogEntry], output_path: Path):
        """Export logs as CSV."""
        # Basic CSV export - would use proper CSV library in production
        header = "timestamp,level,source,message,project_id,process_id\n"
        async with aiofiles.open(output_path, "w") as f:
            await f.write(header)
            for log in logs:
                line = (
                    f"{log.timestamp},{log.level.value},{log.source.value},"
                    f'"{log.message}",{log.project_id or ""},{log.process_id or ""}\n'
                )
                await f.write(line)

    async def _export_txt(self, logs: List[LogEntry], output_path: Path):
        """Export logs as plain text."""
        async with aiofiles.open(output_path, "w") as f:
            for log in logs:
                line = f"[{log.timestamp}] {log.level.value} - {log.message}\n"
                await f.write(line)

    async def add_pattern(self, pattern: LogPattern) -> bool:
        """Add a log monitoring pattern."""
        try:
            self.patterns[pattern.name] = pattern
            await self._save_patterns()

            self.logger.info(f"Added log pattern: {pattern.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add pattern: {str(e)}")
            raise LogError(f"Failed to add pattern: {str(e)}")

    async def remove_pattern(self, pattern_name: str) -> bool:
        """Remove a log monitoring pattern."""
        if pattern_name in self.patterns:
            del self.patterns[pattern_name]
            await self._save_patterns()

            self.logger.info(f"Removed log pattern: {pattern_name}")
            return True

        return False

    async def subscribe_to_logs(
        self,
        subscriber_id: str,
        callback: Callable[[LogEntry], None],
        filter_config: Optional[LogFilter] = None,
    ) -> bool:
        """Subscribe to real-time log updates."""
        self.subscribers[subscriber_id] = {
            "callback": callback,
            "filter": filter_config,
        }

        self.logger.info(f"Added log subscriber: {subscriber_id}")
        return True

    async def unsubscribe_from_logs(self, subscriber_id: str) -> bool:
        """Unsubscribe from real-time log updates."""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            self.logger.info(f"Removed log subscriber: {subscriber_id}")
            return True

        return False

    async def stream_logs(
        self, filter_config: Optional[LogFilter] = None
    ) -> AsyncGenerator[LogEntry, None]:
        """Stream logs in real-time."""
        # Placeholder implementation
        # In production, would implement proper streaming
        while True:
            # Yield recent logs
            recent_logs = list(self.storage.recent_logs)
            for log in recent_logs:
                yield log

            # Wait before next batch
            import asyncio

            await asyncio.sleep(1)


def get_log_service() -> LogService:
    """Get the singleton instance of LogService."""
    if not hasattr(get_log_service, "_instance"):
        get_log_service._instance = LogService()
    return get_log_service._instance
