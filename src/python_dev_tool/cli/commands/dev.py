"""
FUSE - (python dev tool) - CLI Commands - Dev Command
CLI Commands - Dev Command
"""

# sys imports
import sys
import os
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# 3rd party imports
from rich.console import Console
from rich.table import Table

# local imports
from python_dev_tool.core.events import EventBus
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.globals import APP_HOST, APP_OPEN_BROWSER, APP_PORT, APP_UI_PORT
from python_dev_tool.core.process_manager import ProcessManager
from python_dev_tool.core.file_watcher import FileWatcher
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.web.app import   create_dev_ui_app
from python_dev_tool.utils.network_utils import NetworkUtils

@dataclass
class DevOptions:
    """Options for development server."""

    project_path: Path
    port: int = APP_PORT
    host: str = APP_HOST
    debug: bool = True
    reload: bool = True
    ui_port: int = APP_UI_PORT
    open_browser: bool = APP_OPEN_BROWSER


class DevCommand:
    """Command for running development server."""

    def __init__(
        self,
        project_path: Path,
        port: int = APP_PORT,
        host: str = APP_HOST,
        debug: bool = True,
        reload: bool = True,
        ui_port: int = APP_UI_PORT,
        open_browser: bool = APP_OPEN_BROWSER,
        event_bus: Optional[EventBus] = None,
    ):

        def _unwrap(value, fallback=None):
            """Unwraps a value or returns a fallback."""
            if isinstance(value, (tuple,list)):
                return value[0] if value else fallback
            return value

        self.options = DevOptions(
            project_path=project_path,
            port=_unwrap(port, APP_PORT),
            host=_unwrap(host, APP_HOST),
            debug=debug,
            reload=reload,
            ui_port=_unwrap(ui_port, APP_UI_PORT),
            open_browser=_unwrap(open_browser, APP_OPEN_BROWSER),
        )
        self.console = Console()
        self.process_manager = ProcessManager(event_bus or EventBus())
        self.file_watcher = None
        self.dev_ui_process = None
        self.app_process = None
        self.running = False

    async def run(self) -> None:
        """Run the development server."""
        try:
            # Validate project
            await self._validate_project()

            # Setup signal handlers
            self._setup_signal_handlers()

            # Start services
            await self._start_dev_ui()
            await self._start_application()

            # Setup file watcher if reload is enabled
            if self.options.reload:
                await self._setup_file_watcher()

            # Open browser if requested
            if self.options.open_browser:
                self._open_browser()

            # Display status
            self._display_status()

            # Keep running until interrupted
            self.running = True
            await self._run_forever()

        except Exception as e:
            raise DevToolError(f"Development server failed: {e}")
        finally:
            await self._cleanup()

    async def _validate_project(self) -> None:
        """Validate project structure."""
        if not self.options.project_path.exists():
            raise DevToolError(f"Project directory does not exist: {self.options.project_path}")

        config_path = self.options.project_path / ".devtool" / "config.toml"
        if not config_path.exists():
            raise DevToolError(
                "Project not initialized. Run 'fuse init' first."
            )

        # Check if ports are available
        if not NetworkUtils.check_port_available(self.options.host, self.options.port):
            new_port = NetworkUtils.find_free_port(self.options.host, start_port=self.options.port)
            self.console.print(f"[yellow]Port {self.options.port} is busy, using {new_port}[/yellow]")
            self.options.port = new_port

        if not NetworkUtils.check_port_available(
            self.options.host, self.options.ui_port
        ):
            new_ui_port = NetworkUtils.find_free_port(
                self.options.host, start_port=self.options.ui_port
            )
            self.console.print(f"[yellow]UI port {self.options.ui_port} is busy, using {new_ui_port}[/yellow]")
            self.options.ui_port = new_ui_port

    # async def _start_dev_ui(self) -> None:
    #     """Start the development UI server."""
    #     try:
    #         self.console.print("[blue]Starting development UI...[/blue]")

    #         def _unwrap(value, fallback=None):
    #             """Unwraps a value or returns a fallback."""
    #             if isinstance(value, (tuple,list)):
    #                 return value[0] if value else fallback
    #             return value

    #         # Ensure UI port is an integer and within valid range
    #         try:
    #             self.options.ui_port = int(_unwrap(self.options.ui_port, APP_UI_PORT))
    #         except Exception as e:
    #             raise DevToolError(f"Invalid UI port: {self.options.ui_port} ({e})")


    #         if self.options.ui_port < 1024 or self.options.ui_port > 65535:
    #             self.options.ui_port = NetworkUtils.find_free_port(self.options.host)

    #         # Create FastAPI app for dev UI
    #         create_dev_ui_app(self.options.project_path)

    #         # Start UI server in separate process
    #         ui_command = [
    #             sys.executable, "-m", "uvicorn",
    #             "python_dev_tool.web.app:create_dev_ui_app",
    #             "--host", self.options.host,
    #             "--port", str(self.options.ui_port),
    #             "--reload" if self.options.debug else "--no-reload",
    #             "--app-dir", str(self.options.project_path),
    #         ]

    #         self.dev_ui_process = await asyncio.create_subprocess_exec(
    #             *ui_command,
    #             cwd=self.options.project_path,
    #             stdout=asyncio.subprocess.PIPE,
    #             stderr=asyncio.subprocess.STDOUT,
    #         )

    #         # Wait for UI to start
    #         await asyncio.sleep(2)

    #         self.console.print("[green]✓ Development UI started[/green]")

    #     except Exception as e:
    #         raise DevToolError(f"Failed to start development UI: {e}")


    async def _start_dev_ui(self) -> None:
        """Start the development UI server."""
        try:
            self.console.print("[blue]Starting development UI...[/blue]")

            def _unwrap(value, fallback=None):
                """Unwraps a value or returns a fallback."""
                if isinstance(value, (tuple, list)):
                    return value[0] if value else fallback
                return value

            # Ensure UI port is an integer and within valid range
            try:
                self.options.ui_port = int(_unwrap(self.options.ui_port, APP_UI_PORT))
            except Exception as e:
                raise DevToolError(f"Invalid UI port: {self.options.ui_port} ({e})")

            if self.options.ui_port < 1024 or self.options.ui_port > 65535:
                self.options.ui_port = NetworkUtils.find_free_port(self.options.host)

            # Test that the app can be created (don't store it, just validate)
            try:
                test_app = create_dev_ui_app(self.options.project_path)
                # If we get here, the app creation works
            except Exception as e:
                raise DevToolError(f"Failed to create dev UI app: {e}")

            # Start UI server in separate process using the factory function
            ui_command = [
                sys.executable,
                "-m",
                "uvicorn",
                "python_dev_tool.web.app:create_dev_ui_app",
                "--host",
                self.options.host,
                "--port",
                str(self.options.ui_port),
                "--reload" if self.options.debug else "--no-reload",
                "--factory",  # Important: tells uvicorn to call the function
            ]

            # Set environment variable for project path
            env = os.environ.copy()
            env["DEVTOOL_PROJECT_PATH"] = str(self.options.project_path)

            self.dev_ui_process = await asyncio.create_subprocess_exec(
                *ui_command,
                cwd=self.options.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            # Wait for UI to start
            await asyncio.sleep(2)

            self.console.print("[green]✓ Development UI started[/green]")

        except Exception as e:
            raise DevToolError(f"Failed to start development UI: {e}")


    async def _start_application(self) -> None:
        """Start the main application."""
        try:
            self.console.print("[blue]Starting application server...[/blue]")

            # Detect framework and get run command
            detector = FrameworkDetector(self.options.project_path)
            framework_info = detector.detect_framework()

            if not framework_info:
                raise DevToolError("Could not detect framework")

            # Get run command from framework info
            run_command = framework_info.commands.get("run")
            if not run_command:
                raise DevToolError(f"No run command defined for {framework_info.name}")

            # Start application process
            self.app_process = await asyncio.create_subprocess_shell(
                run_command,
                cwd=self.options.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait briefly to check if process started successfully
            await asyncio.sleep(1)
            if self.app_process.returncode is not None:
                stderr = await self.app_process.stderr.read()
                raise DevToolError(f"Application failed to start: {stderr.decode()}")

            self.console.print(
                f"[green]✓ {framework_info.name} application started[/green]"
            )

        except Exception as e:
            raise DevToolError(f"Failed to start application: {e}")

    async def _setup_file_watcher(self) -> None:
        """Setup file watcher for hot reload."""
        try:
            self.console.print("[blue]Setting up file watcher...[/blue]")

            # Get watched directories from framework detection
            detector = FrameworkDetector(self.options.project_path)
            framework_info = detector.detect_framework()

            if not framework_info:
                raise DevToolError("Could not detect framework for file watching")

            # Create file watcher
            self.file_watcher = FileWatcher(
                paths=[self.options.project_path],
                callback=self._handle_file_change,
                ignore_patterns=["*.pyc", "__pycache__", "*.swp"],
            )

            await self.file_watcher.start()
            self.console.print("[green]✓ File watcher started[/green]")

        except Exception as e:
            raise DevToolError(f"Failed to setup file watcher: {e}")

    async def _handle_file_change(self, changed_file: Path) -> None:
        """Handle file change events."""
        self.console.print(f"[yellow]File changed: {changed_file}[/yellow]")

        # Restart application process
        if self.app_process:
            self.console.print("[blue]Restarting application...[/blue]")
            self.app_process.terminate()
            await self.app_process.wait()
            await self._start_application()

    def _open_browser(self) -> None:
        """Open browser to development UI."""
        try:
            import webbrowser

            url = f"http://{self.options.host}:{self.options.ui_port}"
            webbrowser.open(url)
            self.console.print(f"[green]✓ Opened browser to {url}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]Could not open browser: {e}[/yellow]")

    def _display_status(self) -> None:
        """Display server status information."""
        status_table = Table(title="Development Server Status", show_lines=True)
        status_table.add_column("Service", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("URL")

        status_table.add_row(
            "Application Server",
            "Running",
            f"http://{self.options.host}:{self.options.port}",
        )
        status_table.add_row(
            "Development UI",
            "Running",
            f"http://{self.options.host}:{self.options.ui_port}",
        )
        status_table.add_row(
            "File Watcher", "Active" if self.options.reload else "Inactive", "-"
        )

        self.console.print(status_table)
        self.console.print("\n[bold]Press Ctrl+C to stop the server[/bold]")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        import signal

        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_shutdown_signal, sig)

    def _handle_shutdown_signal(self, sig) -> None:
        """Handle shutdown signals."""
        self.console.print(
            f"\n[yellow]Received shutdown signal {sig.name}, stopping...[/yellow]"
        )
        self.running = False

    async def _run_forever(self) -> None:
        """Main run loop."""
        while self.running:
            await asyncio.sleep(1)

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        self.console.print("[blue]Cleaning up resources...[/blue]")

        # Stop file watcher
        if self.file_watcher:
            await self.file_watcher.stop()

        # Stop application process
        if self.app_process:
            self.app_process.terminate()
            await self.app_process.wait()

        # Stop dev UI process
        if self.dev_ui_process:
            self.dev_ui_process.terminate()
            await self.dev_ui_process.wait()

        self.console.print("[green]✓ Cleanup complete[/green]")
