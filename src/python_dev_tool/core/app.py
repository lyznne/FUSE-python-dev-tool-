"""
FUSE - (python dev tool) - Core App
app.py - Core App
"""

# sys imports
import asyncio
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import webbrowser
import threading
import time
import traceback

# 3rd party imports
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text

# local imports
from python_dev_tool.core.config import Config
from python_dev_tool.core.process_manager import ProcessManager
from python_dev_tool.core.file_watcher import FileWatcher
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.core.server import DevelopmentServer
from python_dev_tool.core.logger import DevToolLogger
from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.exceptions import FrameworkNotFoundError
from python_dev_tool.web.app import create_web_app
from python_dev_tool.monitoring.metrics import MetricsCollector
from python_dev_tool.monitoring.health import HealthCheck


@dataclass
class AppState:
    """Application state container"""

    running: bool = False
    started_at: Optional[datetime] = None
    project_path: Optional[Path] = None
    framework: Optional[str] = None
    server_port: Optional[int] = None
    ui_port: Optional[int] = None
    processes: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    performance: Dict[str, Any] = field(default_factory=dict)


class DevToolApp:
    """
    Main application class that orchestrates all components.

    This class manages:
    - Development server lifecycle
    - Web UI dashboard
    - File watching and hot reload
    - Process management
    - Metrics collection
    - Event handling
    - Command execution
    - Performance monitoring
    """

    def __init__(
        self,
        project_path: Path,
        config: Optional[Config] = None,
        console: Optional[Console] = None,
    ):
        """
        Initialize the development tool application.

        Args:
            project_path: Path to the project directory
            config: Configuration object (optional)
            console: Rich console for output (optional)
        """
        self.project_path = project_path.resolve()
        self.config = config or Config.load_from_path(project_path)
        self.console = console or Console()
        self.state = AppState(project_path=self.project_path)

        # Initialize core components
        self.logger = DevToolLogger(self.console)
        self.event_emitter = EventEmitter()
        self.framework_detector = FrameworkDetector(self.project_path)
        self.process_manager = ProcessManager(self.event_emitter, self.logger)
        self.file_watcher = FileWatcher(self.project_path, self.event_emitter)
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthCheck()

        # Development server and web app
        self.dev_server: Optional[DevelopmentServer] = None
        self.web_app: Optional[Any] = None

        # Internal state
        self._shutdown_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._live_display: Optional[Live] = None
        self._ui_server = None

        # Setup event handlers
        self._setup_event_handlers()

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_event_handlers(self):
        """Setup event handlers for various application events."""

        @self.event_emitter.on("file_changed")
        def on_file_changed(event: Dict[str, Any]) -> None:
            """Handle file change events."""
            self.logger.info(f"File changed: {event['path']}")
            self.state.logs.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": f"File changed: {event['path']}",
                    "type": "file_change",
                }
            )

            # Trigger hot reload if enabled
            if self.config.get("hot_reload", True):
                asyncio.create_task(self._trigger_hot_reload())

        @self.event_emitter.on("process_started")
        def on_process_started(event: Dict[str, Any]) -> None:
            """Handle process start events."""
            process_name = event["name"]
            self.logger.success(f"Process started: {process_name}")
            self.state.processes[process_name] = {
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "pid": event.get("pid"),
                "command": event.get("command"),
            }

        @self.event_emitter.on("process_stopped")
        def on_process_stopped(event: Dict[str, Any]) -> None:
            """Handle process stop events."""
            process_name = event["name"]
            self.logger.warning(f"Process stopped: {process_name}")
            if process_name in self.state.processes:
                self.state.processes[process_name]["status"] = "stopped"
                self.state.processes[process_name]["stopped_at"] = (
                    datetime.now().isoformat()
                )

        @self.event_emitter.on("error")
        def on_error(event: Dict[str, Any]) -> None:
            """Handle error events."""
            self.logger.error(f"Error: {event['message']}")
            self.state.errors.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "message": event["message"],
                    "type": event.get("type", "general"),
                    "traceback": event.get("traceback"),
                    "file": event.get("file"),
                    "line": event.get("line"),
                }
            )

        @self.event_emitter.on("command_executed")
        def on_command_executed(event: Dict[str, Any]) -> None:
            """Handle command execution events."""
            command = event["command"]
            self.logger.info(f"Command executed: {command}")
            self.state.commands.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "command": command,
                    "output": event.get("output"),
                    "exit_code": event.get("exit_code"),
                }
            )

        @self.event_emitter.on("metrics_updated")
        def on_metrics_updated(event: Dict[str, Any]) -> None:
            """Handle metrics update events."""
            self.state.metrics.update(event["metrics"])
            self.state.performance.update(event.get("performance", {}))

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            if self._shutdown_event:
                self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self) -> None:
        """Initialize the application and detect framework."""
        self.logger.info("Initializing development tool...")

        # Detect framework
        try:
            framework_info = await self.framework_detector.detect()
            self.state.framework = framework_info["name"]
            self.logger.success(f"Detected framework: {framework_info['name']}")

            # Update config with framework-specific settings
            self.config.update_framework_settings(framework_info)

            # Set framework-specific commands
            self._set_framework_commands(framework_info)

        except FrameworkNotFoundError:
            self.logger.warning(
                "No framework detected, using generic Python configuration"
            )
            self.state.framework = "python"
            self._set_generic_commands()

        # Initialize development server
        self.dev_server = DevelopmentServer(
            project_path=self.project_path,
            config=self.config,
            framework=self.state.framework,
            event_emitter=self.event_emitter,
            logger=self.logger,
        )

        # Initialize web application
        self.web_app = create_web_app(
            app_state=self.state,
            config=self.config,
            event_emitter=self.event_emitter,
            logger=self.logger,
        )

        # Start metrics collection
        await self.metrics_collector.start()

        # Start health checking
        await self.health_checker.start()

        self.logger.success("Application initialized successfully")

    def _set_framework_commands(self, framework_info: Dict[str, Any]) -> None:
        """Set framework-specific commands based on detected framework."""
        framework_name = framework_info["name"].lower()

        commands = {
            "django": [
                "python manage.py runserver",
                "python manage.py migrate",
                "python manage.py makemigrations",
                "python manage.py collectstatic",
                "python manage.py shell",
                "python manage.py test",
                "python manage.py createsuperuser",
            ],
            "flask": [
                "flask run",
                "flask shell",
                "flask db init",
                "flask db migrate",
                "flask db upgrade",
                "python -m flask run --debug",
            ],
            "fastapi": [
                "uvicorn main:app --reload",
                "uvicorn main:app --host 0.0.0.0 --port 8000",
                "python -m uvicorn main:app --reload --debug",
            ],
            "streamlit": [
                "streamlit run app.py",
                "streamlit run app.py --server.port 8501",
                "streamlit config show",
            ],
        }

        self.state.commands = commands.get(framework_name, self._get_generic_commands())

    def _set_generic_commands(self) -> None:
        """Set generic Python commands."""
        self.state.commands = self._get_generic_commands()

    def _get_generic_commands(self) -> List[str]:
        """Get generic Python commands."""
        return [
            "python -m http.server 8000",
            "python app.py",
            "python main.py",
            "python -m pytest",
            "python -m pip install -r requirements.txt",
            "python -m pip freeze > requirements.txt",
        ]

    async def start(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        ui_port: int = 8001,
        debug: bool = True,
        reload: bool = True,
        open_browser: bool = True,
    ) -> None:
        """
        Start the development server and web UI.

        Args:
            host: Host to bind servers to
            port: Port for the development server
            ui_port: Port for the web UI
            debug: Enable debug mode
            reload: Enable hot reload
            open_browser: Open browser automatically
        """
        self.state.running = True
        self.state.started_at = datetime.now()
        self.state.server_port = port
        self.state.ui_port = ui_port

        self.logger.info("Starting development environment...")

        # Start file watcher if reload is enabled
        if reload:
            await self.file_watcher.start()

        # Start development server
        dev_server_task = asyncio.create_task(
            self.dev_server.start(host=host, port=port, debug=debug)
        )
        self._tasks.append(dev_server_task)

        # Start web UI
        web_ui_task = asyncio.create_task(self._start_web_ui(host=host, port=ui_port))
        self._tasks.append(web_ui_task)

        # Start metrics collection task
        metrics_task = asyncio.create_task(self._collect_metrics())
        self._tasks.append(metrics_task)

        # Start live display
        if not self.console.quiet:
            self._start_live_display()

        # Open browser if requested
        if open_browser:
            self._open_browser(host, port, ui_port)

        # Log startup information
        self.logger.success("Development environment started successfully!")
        self.logger.info(f"Application: http://{host}:{port}")
        self.logger.info(f"Debug UI: http://{host}:{ui_port}")
        self.logger.info("Press Ctrl+C to stop")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cleanup
        await self._cleanup()

    async def _start_web_ui(self, host: str, port: int) -> None:
        """Start the web UI server."""
        try:
            import uvicorn

            config = uvicorn.Config(
                self.web_app,
                host=host,
                port=port,
                log_level="info",
                reload=False,
                access_log=False,
            )

            server = uvicorn.Server(config)
            self._ui_server = server
            await server.serve()

        except Exception as e:
            self.logger.error(f"Failed to start web UI: {e}")
            self.event_emitter.emit(
                "error",
                {
                    "message": f"Web UI startup failed: {e}",
                    "type": "web_ui_error",
                    "traceback": traceback.format_exc(),
                },
            )

    async def _collect_metrics(self) -> None:
        """Collect performance metrics periodically."""
        while self.state.running:
            try:
                metrics = await self.metrics_collector.collect()
                self.event_emitter.emit("metrics_updated", {"metrics": metrics})
                await asyncio.sleep(5)  # Collect metrics every 5 seconds
            except Exception as e:
                self.logger.error(f"Metrics collection failed: {e}")
                await asyncio.sleep(10)  # Wait longer on error

    def _start_live_display(self) -> None:
        """Start the live display for real-time monitoring."""

        def create_layout():
            layout = Layout()

            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
                Layout(name="footer", size=3),
            )

            layout["main"].split_row(
                Layout(name="left"),
                Layout(name="right"),
            )

            layout["left"].split_column(
                Layout(name="processes", ratio=1),
                Layout(name="logs", ratio=2),
            )

            layout["right"].split_column(
                Layout(name="metrics", ratio=1),
                Layout(name="commands", ratio=1),
            )

            return layout

        def update_display():
            layout = create_layout()

            # Header
            header = Panel(
                f"🚀 Python Dev Tool - {self.state.framework.upper()} - {self.project_path.name}",
                style="bold blue",
            )
            layout["header"].update(header)

            # Processes
            process_table = Table(title="Running Processes", show_header=True)
            process_table.add_column("Name", style="cyan")
            process_table.add_column("Status", style="green")
            process_table.add_column("PID", style="yellow")

            for name, info in self.state.processes.items():
                process_table.add_row(
                    name,
                    info["status"],
                    str(info.get("pid", "N/A")),
                )

            layout["processes"].update(Panel(process_table, title="Processes"))

            # Logs
            log_text = Text()
            for log in self.state.logs[-10:]:  # Show last 10 logs
                timestamp = log.get("timestamp", "")[:19]  # Remove microseconds
                level = log.get("level", "INFO")
                message = log.get("message", "")

                color = {
                    "INFO": "blue",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "SUCCESS": "green",
                }.get(level, "white")

                log_text.append(f"[{timestamp}] ", style="dim")
                log_text.append(f"[{level}] ", style=f"bold {color}")
                log_text.append(f"{message}\n", style=color)

            layout["logs"].update(Panel(log_text, title="Recent Logs"))

            # Metrics
            metrics_table = Table(title="Performance Metrics", show_header=True)
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", style="green")

            for key, value in self.state.metrics.items():
                metrics_table.add_row(key, str(value))

            layout["metrics"].update(Panel(metrics_table, title="Metrics"))

            # Commands
            command_text = Text()
            for i, cmd in enumerate(self.state.commands[:5], 1):
                command_text.append(f"{i}. {cmd}\n", style="cyan")

            layout["commands"].update(Panel(command_text, title="Available Commands"))

            # Footer
            footer = Panel(
                f"Server: http://127.0.0.1:{self.state.server_port} | "
                f"UI: http://127.0.0.1:{self.state.ui_port} | "
                f"Uptime: {self._get_uptime()}",
                style="dim",
            )
            layout["footer"].update(footer)

            return layout

        # Run live display in a separate thread
        def run_live_display():
            try:
                with Live(
                    update_display(), refresh_per_second=1, console=self.console
                ) as live:
                    while self.state.running:
                        live.update(update_display())
                        time.sleep(1)
            except KeyboardInterrupt:
                pass

        display_thread = threading.Thread(target=run_live_display, daemon=True)
        display_thread.start()

    def _get_uptime(self) -> str:
        """Get formatted uptime string."""
        if not self.state.started_at:
            return "0s"

        uptime = datetime.now() - self.state.started_at
        total_seconds = int(uptime.total_seconds())

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def _open_browser(self, host: str, port: int, ui_port: int) -> None:
        """Open browser tabs for application and UI."""

        def open_urls():
            time.sleep(2)  # Wait for servers to start
            try:
                webbrowser.open(f"http://{host}:{port}")
                time.sleep(1)
                webbrowser.open(f"http://{host}:{ui_port}")
            except Exception as e:
                self.logger.warning(f"Failed to open browser: {e}")

        browser_thread = threading.Thread(target=open_urls, daemon=True)
        browser_thread.start()

    async def _trigger_hot_reload(self) -> None:
        """Trigger hot reload of the development server."""
        try:
            if self.dev_server:
                await self.dev_server.reload()
                self.logger.info("Hot reload triggered")
        except Exception as e:
            self.logger.error(f"Hot reload failed: {e}")

    async def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        self.logger.info("Shutting down development environment...")

        self.state.running = False

        # Stop file watcher
        if hasattr(self.file_watcher, "stop"):
            await self.file_watcher.stop()

        # Stop development server
        if self.dev_server:
            await self.dev_server.stop()

        # Stop UI server
        if self._ui_server:
            self._ui_server.should_exit = True

        # Stop metrics collection
        if hasattr(self.metrics_collector, "stop"):
            await self.metrics_collector.stop()

        # Stop health checker
        if hasattr(self.health_checker, "stop"):
            await self.health_checker.stop()

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self.logger.success("Development environment stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current application status."""
        return {
            "project_name": self.project_path.name,
            "framework": self.state.framework,
            "running": self.state.running,
            "started_at": self.state.started_at.isoformat()
            if self.state.started_at
            else None,
            "uptime": self._get_uptime(),
            "server_port": self.state.server_port,
            "ui_port": self.state.ui_port,
            "processes": self.state.processes,
            "metrics": self.state.metrics,
            "recent_logs": self.state.logs[-10:],
            "errors": self.state.errors,
            "commands": self.state.commands,
            "config_file": str(self.config.config_file)
            if hasattr(self.config, "config_file")
            else None,
        }

    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a command and return result."""
        try:
            result = await self.process_manager.execute_command(command)

            self.event_emitter.emit(
                "command_executed",
                {
                    "command": command,
                    "output": result.get("output"),
                    "exit_code": result.get("exit_code"),
                },
            )

            return result

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            self.event_emitter.emit(
                "error",
                {
                    "message": f"Command execution failed: {e}",
                    "type": "command_error",
                    "command": command,
                    "traceback": traceback.format_exc(),
                },
            )
            return {
                "success": False,
                "error": str(e),
                "exit_code": 1,
            }

    async def stop(self) -> None:
        """Stop the development environment."""
        self._shutdown_event.set()
        await self._cleanup()
