"""
FUSE - (python dev tool) - Core File Watcher
file_watcher.py - File System Monitoring and Hot Reload
"""

import asyncio
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from python_dev_tool.core.events import EventBus, EventType, EventEmitter


class ReloadType(Enum):
    """Types of reload strategies"""

    PROCESS_RESTART = "process_restart"
    SIGNAL_RELOAD = "signal_reload"
    HOT_RELOAD = "hot_reload"
    GRACEFUL_RESTART = "graceful_restart"


@dataclass
class FileChangeEvent:
    """File change event data"""

    path: str
    event_type: str  # created, modified, deleted, moved
    is_directory: bool
    timestamp: float
    relative_path: str = ""


class DebounceHandler(FileSystemEventHandler):
    """Debounced file system event handler"""

    def __init__(
        self, callback: Callable, ignore_patterns: List[str], debounce_ms: int = 500
    ):
        super().__init__()
        self.callback = callback
        self.ignore_patterns = [re.compile(pattern) for pattern in ignore_patterns]
        self.debounce_ms = debounce_ms
        self.pending_changes: Set[str] = set()
        self.debounce_timer: Optional[Timer] = None

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        for pattern in self.ignore_patterns:
            if pattern.search(path):
                return True
        return False

    def _handle_event(self, event: FileSystemEvent):
        """Handle file system event"""
        if self._should_ignore(event.src_path):
            return

        self.pending_changes.add(event.src_path)

        # Reset debounce timer
        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = Timer(self.debounce_ms / 1000.0, self._flush_changes)
        self.debounce_timer.start()

    def _flush_changes(self):
        """Flush pending changes to callback"""
        if self.pending_changes:
            changes = list(self.pending_changes)
            self.pending_changes.clear()
            self.callback(changes)

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_event(event)

    def on_created(self, event):
        self._handle_event(event)

    def on_deleted(self, event):
        self._handle_event(event)

    def on_moved(self, event):
        self._handle_event(event)


class FileWatcher(EventEmitter):
    """File system watcher with hot reload capabilities"""

    def __init__(self, event_bus: EventBus = None, debounce_ms: int = 500):
        super().__init__(event_bus)
        self.debounce_ms = debounce_ms
        self.observers: List[Observer] = []
        self.watch_configs: Dict[str, Dict[str, Any]] = {}
        self.is_running = False

    def add_watch(
        self,
        name: str,
        paths: List[str],
        ignore_patterns: List[str] = None,
        recursive: bool = True,
        callback: Callable = None,
    ):
        """Add a watch configuration"""
        if ignore_patterns is None:
            ignore_patterns = self._get_default_ignore_patterns()

        self.watch_configs[name] = {
            "paths": paths,
            "ignore_patterns": ignore_patterns,
            "recursive": recursive,
            "callback": callback,
        }

        if self.is_running:
            self._start_watch(name)

    def remove_watch(self, name: str):
        """Remove a watch configuration"""
        if name in self.watch_configs:
            self._stop_watch(name)
            del self.watch_configs[name]

    def start(self):
        """Start all watchers"""
        if self.is_running:
            return

        self.is_running = True

        for name in self.watch_configs:
            self._start_watch(name)

        asyncio.create_task(
            self.emit(
                EventType.FILE_CHANGED,
                {
                    "action": "watcher_started",
                    "watches": list(self.watch_configs.keys()),
                },
            )
        )

    def stop(self):
        """Stop all watchers"""
        if not self.is_running:
            return

        self.is_running = False

        for observer in self.observers:
            observer.stop()
            observer.join()

        self.observers.clear()

        asyncio.create_task(
            self.emit(EventType.FILE_CHANGED, {"action": "watcher_stopped"})
        )

    def _start_watch(self, name: str):
        """Start a specific watch"""
        config = self.watch_configs[name]

        def handle_changes(changed_files: List[str]):
            asyncio.create_task(self._handle_file_changes(name, changed_files))

            # Call custom callback if provided
            if config["callback"]:
                config["callback"](changed_files)

        for path in config["paths"]:
            if not os.path.exists(path):
                continue

            observer = Observer()
            event_handler = DebounceHandler(
                handle_changes, config["ignore_patterns"], self.debounce_ms
            )

            observer.schedule(event_handler, path, recursive=config["recursive"])
            observer.start()
            self.observers.append(observer)

    def _stop_watch(self, name: str):
        """Stop a specific watch"""
        # In a real implementation, we'd need to track which observers
        # belong to which watch config
        pass

    async def _handle_file_changes(self, watch_name: str, changed_files: List[str]):
        """Handle file changes"""
        await self.emit(
            EventType.FILE_CHANGED,
            {
                "watch_name": watch_name,
                "files": changed_files,
                "timestamp": time.time(),
            },
        )

    def _get_default_ignore_patterns(self) -> List[str]:
        """Get default ignore patterns"""
        return [
            r".*/__pycache__/.*",
            r".*\.pyc$",
            r".*\.pyo$",
            r".*\.pyd$",
            r".*\.git/.*",
            r".*\.svn/.*",
            r".*\.hg/.*",
            r".*\.DS_Store$",
            r".*\.pytest_cache/.*",
            r".*\.coverage.*",
            r".*\.tox/.*",
            r".*\.venv/.*",
            r".*node_modules/.*",
            r".*\.log$",
            r".*\.tmp$",
            r".*\.swp$",
            r".*~$",
        ]


class ReloadStrategy:
    """Base reload strategy"""

    def __init__(self):
        self.watch_paths = ["**/*.py"]
        self.ignore_patterns = []
        self.debounce_ms = 500
        self.reload_type = ReloadType.PROCESS_RESTART
        self.signal_type = None

    def should_reload(self, changed_files: List[str]) -> bool:
        """Determine if reload is needed"""
        return any(f.endswith(".py") for f in changed_files)

    def get_reload_command(self, project_path: str) -> Optional[str]:
        """Get command to reload the application"""
        return None

    def prepare_reload(self, project_path: str) -> Dict[str, Any]:
        """Prepare for reload"""
        return {}


class DjangoReloadStrategy(ReloadStrategy):
    """Django-specific reload strategy"""

    def __init__(self):
        super().__init__()
        self.watch_paths = ["**/*.py", "**/templates/**/*.html", "**/static/**/*"]
        self.ignore_patterns.extend(["**/migrations/**/*.py"])
        self.reload_type = ReloadType.HOT_RELOAD

    def should_reload(self, changed_files: List[str]) -> bool:
        """Django-specific reload logic"""
        # Don't reload for migration files
        if any("migrations" in f for f in changed_files):
            return False

        # Reload for Python files, templates, or static files
        return any(f.endswith((".py", ".html", ".css", ".js")) for f in changed_files)

    def get_reload_command(self, project_path: str) -> Optional[str]:
        """Get Django reload command"""
        return "python manage.py runserver --noreload"


class FlaskReloadStrategy(ReloadStrategy):
    """Flask-specific reload strategy"""

    def __init__(self):
        super().__init__()
        self.watch_paths = ["**/*.py", "**/templates/**/*.html", "**/static/**/*"]
        self.reload_type = ReloadType.HOT_RELOAD

    def should_reload(self, changed_files: List[str]) -> bool:
        """Flask-specific reload logic"""
        return any(f.endswith((".py", ".html", ".css", ".js")) for f in changed_files)

    def get_reload_command(self, project_path: str) -> Optional[str]:
        """Get Flask reload command"""
        return "flask run --reload"


class FastAPIReloadStrategy(ReloadStrategy):
    """FastAPI-specific reload strategy"""

    def __init__(self):
        super().__init__()
        self.watch_paths = ["**/*.py"]
        self.reload_type = ReloadType.HOT_RELOAD

    def should_reload(self, changed_files: List[str]) -> bool:
        """FastAPI-specific reload logic"""
        return any(f.endswith(".py") for f in changed_files)

    def get_reload_command(self, project_path: str) -> Optional[str]:
        """Get FastAPI reload command"""
        return "uvicorn main:app --reload"


class StreamlitReloadStrategy(ReloadStrategy):
    """Streamlit-specific reload strategy"""

    def __init__(self):
        super().__init__()
        self.watch_paths = ["**/*.py"]
        self.reload_type = ReloadType.SIGNAL_RELOAD
        self.signal_type = "SIGUSR1"

    def should_reload(self, changed_files: List[str]) -> bool:
        """Streamlit-specific reload logic"""
        return any(f.endswith(".py") for f in changed_files)

    def get_reload_command(self, project_path: str) -> Optional[str]:
        """Get Streamlit reload command"""
        return "streamlit run app.py"


class GenericReloadStrategy(ReloadStrategy):
    """Generic reload strategy for unknown frameworks"""

    def __init__(self):
        super().__init__()
        self.reload_type = ReloadType.PROCESS_RESTART


class HotReloader(EventEmitter):
    """Hot reloader that manages file watching and application reloading"""

    def __init__(self, event_bus: EventBus = None):
        super().__init__(event_bus)
        self.file_watcher = FileWatcher(event_bus)
        self.reload_strategies: Dict[str, ReloadStrategy] = {
            "django": DjangoReloadStrategy(),
            "flask": FlaskReloadStrategy(),
            "fastapi": FastAPIReloadStrategy(),
            "streamlit": StreamlitReloadStrategy(),
            "generic": GenericReloadStrategy(),
        }
        self.active_projects: Dict[str, Dict[str, Any]] = {}

        # Subscribe to file change events
        self.subscribe(EventType.FILE_CHANGED, self._handle_file_change)

    async def setup_project_watching(
        self,
        project_id: str,
        project_path: str,
        framework: str,
        custom_patterns: List[str] = None,
    ):
        """Setup file watching for a project"""
        strategy = self._get_reload_strategy(framework)

        # Resolve watch paths
        watch_paths = []
        for pattern in strategy.watch_paths:
            if pattern.startswith("**/"):
                watch_paths.append(os.path.join(project_path, pattern[3:]))
            else:
                watch_paths.append(os.path.join(project_path, pattern))

        # Add custom patterns if provided
        if custom_patterns:
            watch_paths.extend(custom_patterns)

        # Filter to existing paths
        existing_paths = [p for p in watch_paths if os.path.exists(p)]

        self.active_projects[project_id] = {
            "path": project_path,
            "framework": framework,
            "strategy": strategy,
            "last_reload": time.time(),
        }

        # Setup file watching
        self.file_watcher.add_watch(
            name=project_id,
            paths=existing_paths,
            ignore_patterns=strategy.ignore_patterns,
            callback=lambda files: self._project_files_changed(project_id, files),
        )

        await self.emit(
            EventType.FRAMEWORK_DETECTED,
            {
                "project_id": project_id,
                "framework": framework,
                "watch_paths": existing_paths,
            },
        )

    def stop_project_watching(self, project_id: str):
        """Stop watching a project"""
        if project_id in self.active_projects:
            self.file_watcher.remove_watch(project_id)
            del self.active_projects[project_id]

    def start(self):
        """Start the hot reloader"""
        self.file_watcher.start()

    def stop(self):
        """Stop the hot reloader"""
        self.file_watcher.stop()

    def _get_reload_strategy(self, framework: str) -> ReloadStrategy:
        """Get reload strategy for framework"""
        return self.reload_strategies.get(framework, self.reload_strategies["generic"])

    def _project_files_changed(self, project_id: str, changed_files: List[str]):
        """Handle project file changes"""
        if project_id not in self.active_projects:
            return

        project_info = self.active_projects[project_id]
        strategy = project_info["strategy"]

        # Check if reload is needed
        if strategy.should_reload(changed_files):
            # Prevent rapid reloads
            now = time.time()
            if now - project_info["last_reload"] < 2:  # 2 second cooldown
                return

            project_info["last_reload"] = now

            # Emit reload event
            asyncio.create_task(
                self.emit(
                    EventType.SERVER_RELOAD,
                    {
                        "project_id": project_id,
                        "framework": project_info["framework"],
                        "changed_files": changed_files,
                        "reload_type": strategy.reload_type.value,
                    },
                )
            )

    async def _handle_file_change(self, event):
        """Handle file change events"""
        # This is called for all file changes, additional processing can be done here
        pass

    def get_project_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project information"""
        return self.active_projects.get(project_id)

    def list_active_projects(self) -> List[str]:
        """List active project IDs"""
        return list(self.active_projects.keys())
