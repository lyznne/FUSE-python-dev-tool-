"""
Project Service - Core project management functionality
Handles project lifecycle, configuration, and framework detection
"""

import asyncio
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from python_dev_tool.core.config import Config
from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.exceptions import ProjectError
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.utils.file_utils import FileUtils
from python_dev_tool.utils.validation import ValidationUtils
from python_dev_tool.web.models.project import Project, ProjectStatus


class ProjectEventType(Enum):
    """Project event types for the event system."""

    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_STARTED = "project_started"
    PROJECT_STOPPED = "project_stopped"
    PROJECT_RELOADED = "project_reloaded"
    CONFIG_CHANGED = "config_changed"


@dataclass
class ProjectMetrics:
    """Project performance metrics."""

    startup_time: float
    memory_usage: int
    cpu_usage: float
    file_count: int
    last_modified: datetime
    hot_reload_count: int


class ProjectWatcher(FileSystemEventHandler):
    """File system watcher for project changes."""

    def __init__(self, project_service: "ProjectService", project_id: str):
        self.project_service = project_service
        self.project_id = project_id
        self.logger = logging.getLogger(f"{__name__}.ProjectWatcher")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Filter out unwanted files
        if self._should_ignore_file(event.src_path):
            return

        self.logger.info(f"File modified: {event.src_path}")
        asyncio.create_task(
            self.project_service.handle_file_change(self.project_id, event.src_path)
        )

    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored."""
        ignore_patterns = [
            "__pycache__",
            ".git",
            ".pyc",
            ".log",
            "node_modules",
            ".env",
            ".venv",
        ]
        return any(pattern in file_path for pattern in ignore_patterns)


class ProjectService:
    """Core project management service."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.projects: Dict[str, Project] = {}
        self.watchers: Dict[str, Observer] = {}
        self.metrics: Dict[str, ProjectMetrics] = {}
        self.config = None
        self.event_emitter = EventEmitter()
        self.framework_detector = FrameworkDetector()
        self.file_utils = FileUtils()
        self.validation_utils = ValidationUtils()

    @property
    def config(self):
        if self._config is None:
            self._config = Config()
        return self._config

    async def initialize(self):
        """Initialize the project service."""
        self.logger.info("Initializing ProjectService...")

        # Load existing projects
        await self._load_existing_projects()

        # Set up event handlers
        self._setup_event_handlers()

        self.logger.info("ProjectService initialized successfully")

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up ProjectService...")

        # Stop all watchers
        for observer in self.watchers.values():
            observer.stop()
            observer.join()

        # Save project states
        await self._save_project_states()

        self.logger.info("ProjectService cleanup completed")

    async def create_project(
        self,
        name: str,
        path: str,
        framework: Optional[str] = None,
        template: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> Project:
        """Create a new project."""
        try:
            # Validate inputs
            if not self.validation_utils.validate_project_name(name):
                raise ProjectError(f"Invalid project name: {name}")

            if not self.validation_utils.validate_path(path):
                raise ProjectError(f"Invalid project path: {path}")

            project_path = Path(path).resolve()

            # Check if project already exists
            if str(project_path) in [p.path for p in self.projects.values()]:
                raise ProjectError(f"Project already exists at path: {path}")

            # Detect framework if not provided
            if not framework:
                framework = await self.framework_detector.detect_framework(project_path)

            # Create project instance
            project = Project(
                id=self.file_utils.generate_id(),
                name=name,
                path=str(project_path),
                framework=framework,
                status=ProjectStatus.CREATED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                config=config or {},
            )

            # Initialize project structure if needed
            if template:
                await self._initialize_from_template(project, template)

            # Create project configuration
            await self._create_project_config(project)

            # Store project
            self.projects[project.id] = project

            # Start file watching
            await self._start_project_watcher(project)

            # Initialize metrics
            self.metrics[project.id] = ProjectMetrics(
                startup_time=0.0,
                memory_usage=0,
                cpu_usage=0.0,
                file_count=await self._count_project_files(project_path),
                last_modified=datetime.now(timezone.utc),
                hot_reload_count=0,
            )

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.PROJECT_CREATED.value, {"project": asdict(project)}
            )

            self.logger.info(f"Created project: {name} at {path}")
            return project

        except Exception as e:
            self.logger.error(f"Failed to create project {name}: {str(e)}")
            raise ProjectError(f"Failed to create project: {str(e)}")

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self.projects.get(project_id)

    async def get_all_projects(self) -> List[Project]:
        """Get all projects."""
        return list(self.projects.values())

    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Project:
        """Update project configuration."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        # Update project fields
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)

        project.updated_at = datetime.now(timezone.utc)

        # Update configuration file
        await self._update_project_config(project)

        # Emit event
        await self.event_emitter.emit(
            ProjectEventType.PROJECT_UPDATED.value,
            {"project": asdict(project), "updates": updates},
        )

        self.logger.info(f"Updated project: {project_id}")
        return project

    async def delete_project(self, project_id: str, remove_files: bool = False) -> bool:
        """Delete a project."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        try:
            # Stop file watcher
            await self._stop_project_watcher(project_id)

            # Remove files if requested
            if remove_files:
                project_path = Path(project.path)
                if project_path.exists():
                    shutil.rmtree(project_path)

            # Remove from memory
            del self.projects[project_id]

            # Remove metrics
            if project_id in self.metrics:
                del self.metrics[project_id]

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.PROJECT_DELETED.value,
                {"project_id": project_id, "removed_files": remove_files},
            )

            self.logger.info(f"Deleted project: {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete project {project_id}: {str(e)}")
            raise ProjectError(f"Failed to delete project: {str(e)}")

    async def start_project(self, project_id: str) -> bool:
        """Start a project."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        if project.status == ProjectStatus.RUNNING:
            return True

        try:
            start_time = datetime.now()

            # Update project status
            project.status = ProjectStatus.STARTING
            project.updated_at = datetime.now(timezone.utc)

            # Start project-specific processes
            await self._start_project_processes(project)

            # Update status to running
            project.status = ProjectStatus.RUNNING
            project.last_started = datetime.now(timezone.utc)

            # Update metrics
            if project_id in self.metrics:
                self.metrics[project_id].startup_time = (
                    datetime.now() - start_time
                ).total_seconds()

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.PROJECT_STARTED.value, {"project": asdict(project)}
            )

            self.logger.info(f"Started project: {project_id}")
            return True

        except Exception as e:
            project.status = ProjectStatus.ERROR
            project.error_message = str(e)
            self.logger.error(f"Failed to start project {project_id}: {str(e)}")
            raise ProjectError(f"Failed to start project: {str(e)}")

    async def stop_project(self, project_id: str) -> bool:
        """Stop a project."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        if project.status == ProjectStatus.STOPPED:
            return True

        try:
            # Update project status
            project.status = ProjectStatus.STOPPING
            project.updated_at = datetime.now(timezone.utc)

            # Stop project-specific processes
            await self._stop_project_processes(project)

            # Update status to stopped
            project.status = ProjectStatus.STOPPED
            project.last_stopped = datetime.now(timezone.utc)

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.PROJECT_STOPPED.value, {"project": asdict(project)}
            )

            self.logger.info(f"Stopped project: {project_id}")
            return True

        except Exception as e:
            project.status = ProjectStatus.ERROR
            project.error_message = str(e)
            self.logger.error(f"Failed to stop project {project_id}: {str(e)}")
            raise ProjectError(f"Failed to stop project: {str(e)}")

    async def reload_project(self, project_id: str) -> bool:
        """Reload a project (hot reload)."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        try:
            # Perform hot reload
            await self._perform_hot_reload(project)

            # Update metrics
            if project_id in self.metrics:
                self.metrics[project_id].hot_reload_count += 1

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.PROJECT_RELOADED.value, {"project": asdict(project)}
            )

            self.logger.info(f"Reloaded project: {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reload project {project_id}: {str(e)}")
            raise ProjectError(f"Failed to reload project: {str(e)}")

    async def get_project_metrics(self, project_id: str) -> Optional[ProjectMetrics]:
        """Get project metrics."""
        return self.metrics.get(project_id)

    async def get_project_config(self, project_id: str) -> Dict[str, Any]:
        """Get project configuration."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        config_path = Path(project.path) / ".fuse" / "config.toml"

        if not config_path.exists():
            return {}

        try:
            return toml.load(config_path)
        except Exception as e:
            self.logger.error(
                f"Failed to load config for project {project_id}: {str(e)}"
            )
            return {}

    async def update_project_config(
        self, project_id: str, config: Dict[str, Any]
    ) -> bool:
        """Update project configuration."""
        project = self.projects.get(project_id)
        if not project:
            raise ProjectError(f"Project not found: {project_id}")

        try:
            config_path = Path(project.path) / ".fuse" / "config.toml"
            config_path.parent.mkdir(exist_ok=True)

            with open(config_path, "w") as f:
                toml.dump(config, f)

            # Update project config
            project.config = config
            project.updated_at = datetime.now(timezone.utc)

            # Emit event
            await self.event_emitter.emit(
                ProjectEventType.CONFIG_CHANGED.value,
                {"project_id": project_id, "config": config},
            )

            self.logger.info(f"Updated config for project: {project_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to update config for project {project_id}: {str(e)}"
            )
            raise ProjectError(f"Failed to update project config: {str(e)}")

    async def handle_file_change(self, project_id: str, file_path: str):
        """Handle file system changes."""
        project = self.projects.get(project_id)
        if not project:
            return

        # Update metrics
        if project_id in self.metrics:
            self.metrics[project_id].last_modified = datetime.now(timezone.utc)

        # Trigger hot reload if project is running
        if project.status == ProjectStatus.RUNNING:
            await self.reload_project(project_id)

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the project service."""
        return {
            "status": "healthy",
            "projects_count": len(self.projects),
            "running_projects": len(
                [p for p in self.projects.values() if p.status == ProjectStatus.RUNNING]
            ),
            "watchers_count": len(self.watchers),
        }

    # Private methods

    async def _load_existing_projects(self):
        """Load existing projects from storage."""
        # Implementation would load from database or file system
        pass

    async def _save_project_states(self):
        """Save project states to storage."""
        # Implementation would save to database or file system
        pass

    def _setup_event_handlers(self):
        """Set up event handlers."""
        # Implementation would set up event listeners
        pass

    async def _initialize_from_template(self, project: Project, template: str):
        """Initialize project from template."""
        # Implementation would copy template files
        pass

    async def _create_project_config(self, project: Project):
        """Create project configuration file."""
        config_dir = Path(project.path) / ".fuse"
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / "config.toml"

        default_config = {
            "project": {
                "name": project.name,
                "framework": project.framework,
                "version": "1.0.0",
            },
            "server": {"host": "localhost", "port": 8000, "hot_reload": True},
            "deployment": {"platform": "local", "env": "development"},
        }

        with open(config_path, "w") as f:
            toml.dump(default_config, f)

    async def _update_project_config(self, project: Project):
        """Update project configuration file."""
        await self.update_project_config(project.id, project.config)

    async def _start_project_watcher(self, project: Project):
        """Start file system watcher for project."""
        if project.id in self.watchers:
            return

        event_handler = ProjectWatcher(self, project.id)
        observer = Observer()
        observer.schedule(event_handler, project.path, recursive=True)
        observer.start()

        self.watchers[project.id] = observer

    async def _stop_project_watcher(self, project_id: str):
        """Stop file system watcher for project."""
        if project_id in self.watchers:
            observer = self.watchers[project_id]
            observer.stop()
            observer.join()
            del self.watchers[project_id]

    async def _start_project_processes(self, project: Project):
        """Start project-specific processes."""
        # Implementation would start framework-specific processes
        pass

    async def _stop_project_processes(self, project: Project):
        """Stop project-specific processes."""
        # Implementation would stop framework-specific processes
        pass

    async def _perform_hot_reload(self, project: Project):
        """Perform hot reload for project."""
        # Implementation would perform framework-specific hot reload
        pass

    async def _count_project_files(self, project_path: Path) -> int:
        """Count files in project directory."""
        count = 0
        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            count += len(files)
        return count


async def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    service = ProjectService()
    await service.initialize()
    return service
