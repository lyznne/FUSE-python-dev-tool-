"""
FUSE - (python dev tool) - CLI Commands - Dev Command
CLI Commands - Dev Command
"""

# sys imports
import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# 3rd party imports
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# local imports
from python_dev_tool.core.config import Config, DevToolConfig
from python_dev_tool.core.events import EventBus
from python_dev_tool.core.exceptions import ConfigError, DevToolError
from python_dev_tool.core.file_watcher import FileWatcher
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.core.process_manager import ProcessManager
from python_dev_tool.core.template_manager import TemplateManager
from python_dev_tool.utils.network_utils import DomainUtils, NetworkUtils
from python_dev_tool.web.app import create_dev_ui_app


@dataclass
class DevOptions:
    """Options for development server."""

    project_path: Path
    port: int
    host: str
    ui_port: int
    open_browser: bool
    debug: bool = True
    reload: bool = True


class DevCommand:
    """Command for running development server."""

    def __init__(
        self,
        project_path: Path,
        port: Optional[int] = None,
        host: Optional[str] = None,
        debug: Optional[bool] = None,
        reload: Optional[bool] = None,
        ui_port: Optional[int] = None,
        open_browser: Optional[bool] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.project_path = project_path
        self.console = Console()
        self.process_manager = ProcessManager(event_bus or EventBus())
        self.template_manager = TemplateManager()
        self.framework_detector = FrameworkDetector()
        self.domain_utils = DomainUtils()

        # Initialize as None - will be set during config loading
        self.options: Optional[DevOptions] = None
        self.config_manager: Optional[Config] = None
        self.config: Optional[DevToolConfig] = None

        # Store CLI overrides
        self._cli_overrides = {
            "port": port,
            "host": host,
            "debug": debug,
            "reload": reload,
            "ui_port": ui_port,
            "open_browser": open_browser,
        }

        # Runtime state
        self.file_watcher = None
        self.dev_ui_process = None
        self.app_process = None
        self.running = False
        self.available_commands = {}

    async def run(self) -> None:
        """Run the development server."""
        try:
            # Step 1: Validate FUSE initialization and load config
            await self._validate_and_load_config()

            # Step 2: Initialize options with config + CLI overrides
            self._initialize_options()

            # Step 3: Setup signal handlers
            self._setup_signal_handlers()

            # Step 4: Validate and setup ports/domains
            await self._validate_and_setup_network()

            # Step 5: Start services
            await self._start_dev_ui()
            await self._start_application()

            # Step 6: Setup file watcher if reload is enabled
            if self.options.reload:
                await self._setup_file_watcher()

            # Step 7: Start background command analyzer
            await self._start_command_analyzer()

            # Step 8: Open browser if requested
            if self.options.open_browser:
                self._open_browser()

            # Step 9: Display status
            self._display_status()

            # Step 10: Keep running until interrupted
            self.running = True
            await self._run_forever()

        except Exception as e:
            raise DevToolError(f"Development server failed: {e}")
        finally:
            await self._cleanup()

    async def _validate_and_load_config(self) -> None:
        """Validate FUSE initialization and load configuration."""
        self.console.print("[cyan]🔍 Validating FUSE configuration...[/cyan]")

        if not self.project_path.exists():
            raise DevToolError(f"Project directory does not exist: {self.project_path}")

        # Check for FUSE configuration files
        fuse_config_paths = [
            self.project_path / ".fuse" / "config.toml",
            self.project_path / "fuse.toml",
        ]

        config_path = None
        for path in fuse_config_paths:
            if path.exists():
                config_path = path
                break

        if not config_path:
            # console error instead of raise
            self.console.print(
                "[red]❌ Project not initialized with FUSE. Run [yellow]'fuse init'[/yellow] first.[/red]"
            )
            raise SystemExit(1)

            # raise DevToolError(
            #     "Project not initialized with FUSE. Run 'fuse init' first.\n"
            #     "Expected configuration at: .fuse/config.toml or fuse.toml"
            # )

        # Load configuration
        try:
            self.config_manager = Config(config_path)
            self.config = self.config_manager.config

            # Load available commands from config
            self.available_commands = dict(self.config.commands)

            self.console.print(
                "[green]✓ FUSE configuration loaded successfully[/green]"
            )

        except ConfigError as e:
            raise DevToolError(f"Invalid FUSE configuration: {e}")
        except Exception as e:
            raise DevToolError(f"Failed to load FUSE configuration: {e}")

    def _initialize_options(self) -> None:
        """Initialize dev options with config values and CLI overrides."""
        if not self.config:
            raise DevToolError("Configuration not loaded")

        # Start with config defaults
        options_data = {
            "project_path": self.project_path,
            "port": self.config.server.port,
            "host": self.config.server.host,
            "debug": self.config.debug,
            "reload": self.config.server.auto_reload,
            "ui_port": self.config.dashboard.port,
            "open_browser": self.config.dashboard.auto_open,
        }

        # Apply CLI overrides where provided
        for key, value in self._cli_overrides.items():
            if value is not None:
                options_data[key] = value

        self.options = DevOptions(**options_data)

        self.console.print("[green]✓ Development options initialized[/green]")

    async def _validate_and_setup_network(self) -> None:
        """Validate ports and setup network configuration."""
        self.console.print("[cyan]🌐 Validating network configuration...[/cyan]")

        # Check main application port
        if not NetworkUtils.check_port_available(self.options.host, self.options.port):
            new_port = NetworkUtils.find_free_port(
                self.options.host, start_port=self.options.port
            )
            self.console.print(
                f"[yellow]Port {self.options.port} is busy, using {new_port}[/yellow]"
            )
            self.options.port = new_port

        # Check UI port - ensure it's different from app port
        ui_port_need_change = (
            not NetworkUtils.check_port_available(
                self.options.host, self.options.ui_port
            )
            or self.options.ui_port == self.options.port
        )

        if ui_port_need_change:
            # Start search from ui_port + 1 if it conflicts with app port
            start_port = max(self.options.ui_port, self.options.port + 1)
            new_ui_port = NetworkUtils.find_free_port(
                self.options.host, start_port=start_port
            )

            if self.options.ui_port == self.options.port:
                self.console.print(
                    f"[yellow]UI port {self.options.ui_port} conflicts with app port, using {new_ui_port}[/yellow]"
                )
            else:
                self.console.print(
                    f"[yellow]UI port {self.options.ui_port} is busy, using {new_ui_port}[/yellow]"
                )
            self.options.ui_port = new_ui_port

        # Verify ports are different
        if self.options.port == self.options.ui_port:
            # Emergency fallback
            self.options.ui_port = NetworkUtils.find_free_port(
                self.options.host, start_port=self.options.port + 1
            )
            self.console.print(
                f"[red]Emergency: Ports still conflicted, UI moved to {self.options.ui_port}[/red]"
            )

        # IMPORTANT: Setup domain URLs AFTER port validation
        self.domain_utils.configure(
            host=self.options.host,
            app_port=self.options.port,
            ui_port=self.options.ui_port,
        )

        self.console.print("[green]✓ Network configuration validated[/green]")
        self.console.print(
            f"[cyan]App will run on: {self.domain_utils.get_app_url()}[/cyan]"
        )
        self.console.print(
            f"[cyan]UI will run on: {self.domain_utils.get_ui_url()}[/cyan]"
        )

    async def _start_dev_ui(self) -> None:
        """Start the development UI server."""
        try:
            self.console.print("[blue]🚀 Starting development UI...[/blue]")

            # Validate UI port range
            if not (1024 <= self.options.ui_port <= 65535):
                self.options.ui_port = NetworkUtils.find_free_port(self.options.host)

            # Test app creation
            try:
                test_app = create_dev_ui_app(self.options.project_path)
            except Exception as e:
                raise DevToolError(f"Failed to create dev UI app: {e}")

            # Build UI command
            ui_command = [
                sys.executable,
                "-m",
                "uvicorn",
                "python_dev_tool.web.app:create_dev_ui_app_factory",  # Use the factory function
                "--host",
                self.options.host,
                "--port",
                str(self.options.ui_port),
                "--factory",  # This tells uvicorn to call the function
            ]

            # Add reload flag based on debug setting
            ui_command.append("--reload" if self.options.debug else "--no-reload")

            # Set environment variables
            env = os.environ.copy()
            env["DEVTOOL_PROJECT_PATH"] = str(self.options.project_path)

            # Start UI process
            self.console.print(f"[blue]Running UI: {' '.join(ui_command)}[/blue]")
            self.dev_ui_process = await asyncio.create_subprocess_exec(
                *ui_command,
                cwd=self.options.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            # Wait for startup
            await asyncio.sleep(3)
            self.console.print("[green]✓ Development UI started[/green]")
            if self.dev_ui_process.returncode is not None:
                # Process has already exited, read the output
                stdout, stderr = await self.dev_ui_process.communicate()
                output = stdout.decode() if stdout else ""
                error = stderr.decode() if stderr else ""

                self.console.print(f"[red]❌ Development UI failed to start[/red]")
                self.console.print(
                    f"[red]Exit code: {self.dev_ui_process.returncode}[/red]"
                )
                if output:
                    self.console.print(f"[red]Output: {output}[/red]")
                if error:
                    self.console.print(f"[red]Error: {error}[/red]")

                raise DevToolError(
                    f"Development UI process exited with code {self.dev_ui_process.returncode}"
                )

            # Test if the UI is accessible
            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    ui_url = self.domain_utils.get_ui_url()
                    async with session.get(f"{ui_url}/health", timeout=5) as response:
                        if response.status == 200:
                            self.console.print(
                                "[green]✓ Development UI started and is accessible[/green]"
                            )
                        else:
                            self.console.print(
                                f"[yellow]⚠️ Development UI started but health check returned {response.status}[/yellow]"
                            )
            except ImportError:
                # aiohttp not available, skip health check
                self.console.print("[green]✓ Development UI started[/green]")
            except Exception as e:
                self.console.print(
                    f"[yellow]⚠️ Development UI started but health check failed: {e}[/yellow]"
                )
                self.console.print("[yellow]Try accessing the UI manually[/yellow]")

        except Exception as e:
            raise DevToolError(f"Failed to start development UI: {e}")

    async def _start_application(self) -> None:
        """Start the main application using configuration."""
        try:
            self.console.print("[blue]🔥 Starting application server...[/blue]")

            # Get dev command from config
            dev_command = self.available_commands.get("dev")

            if not dev_command:
                # Fallback to framework detection
                detected_framework = self.framework_detector.detect_framework(
                    self.project_path
                )
                if detected_framework:
                    dev_command = self._get_fallback_command(detected_framework)

                if not dev_command:
                    raise DevToolError(
                        "No dev command found in configuration. "
                        "Please check your .fuse/config.toml file."
                    )

            self.console.print(f"[cyan]Using command: {dev_command}[/cyan]")

            # Replace placeholders with actual values from config
            dev_command = self._replace_command_placeholders(dev_command)
            self.console.print(f"[cyan]Executing: {dev_command}[/cyan]")

            # Start application process
            self.app_process = await asyncio.create_subprocess_shell(
                dev_command,
                cwd=self.options.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait and check startup
            await asyncio.sleep(2)
            if self.app_process.returncode is not None:
                stderr = await self.app_process.stderr.read()
                raise DevToolError(f"Application failed to start: {stderr.decode()}")

            # Get framework name for display
            framework_name = self._get_framework_display_name()
            self.console.print(f"[green]✓ {framework_name} application started[/green]")

        except Exception as e:
            raise DevToolError(f"Failed to start application: {e}")

    def _get_fallback_command(self, framework) -> Optional[str]:
        """Get fallback command based on detected framework."""
        framework_name = (
            framework.name.lower()
            if hasattr(framework, "name")
            else str(framework).lower()
        )

        fallback_commands = {
            "django": f"python manage.py runserver {self.options.host}:{self.options.port}",
            "flask": "python app.py",
            "fastapi": f"uvicorn main:app --reload --host {self.options.host} --port {self.options.port}",
            "streamlit": f"streamlit run app.py --server.address {self.options.host} --server.port {self.options.port}",
            "python": "python main.py",
        }

        return fallback_commands.get(framework_name)

    def _replace_command_placeholders(self, command: str) -> str:
        """Replace placeholders in command with actual values."""
        replacements = {
            "0.0.0.0": self.options.host,
            "0.0.0.1": self.options.host,
            "127.0.0.1": self.options.host,
            "localhost": self.options.host,
            "8000": str(self.options.port),
        }

        for placeholder, value in replacements.items():
            command = command.replace(placeholder, value)

        return command

    def _get_framework_display_name(self) -> str:
        """Get framework name for display purposes."""
        if hasattr(self.config, "project") and hasattr(
            self.config.project, "framework"
        ):
            return self.config.project.framework.title()
        elif self.config.framework:
            return self.config.framework.title()
        else:
            return "Application"

    async def _setup_file_watcher(self) -> None:
        """Setup file watcher for hot reload."""
        try:
            self.console.print("[blue]👁️ Setting up file watcher...[/blue]")

            # Initialize FileWatcher with event_bus and debounce_ms
            self.file_watcher = FileWatcher(
                event_bus=self.process_manager.event_bus,
                debounce_ms=500,
            )

            # use thread-safe callback
            def sync_file_change_handler(changed_files):
                """Thread safe file change handler."""
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # schedule the coroutine to run in the event loop
                        asyncio.run_coroutine_threadsafe(
                            self._handle_file_change(changed_files), loop
                        )
                    else:
                        self.console.print(
                            "[yellow]⚠️ Event loop not running, skipping file change[/yellow]"
                        )
                except Exception as e:
                    self.console.print(
                        f"[yellow]⚠️ Error handling file change: {e}[/yellow]"
                    )

            self.file_watcher.add_watch(
                name=self.config.project_name,
                paths=[str(self.options.project_path)],
                recursive=True,
                callback=sync_file_change_handler,
            )

            self.file_watcher.start()
            self.console.print("[green]✓ File watcher started[/green]")

        except Exception as e:
            raise DevToolError(f"Failed to setup file watcher: {e}")

    async def _start_command_analyzer(self) -> None:
        """Start background command analyzer."""
        try:
            self.console.print("[blue]🔍 Starting command analyzer...[/blue]")
            asyncio.create_task(self._analyze_commands_background())
            self.console.print("[green]✓ Command analyzer started[/green]")
        except Exception as e:
            self.console.print(
                f"[yellow]⚠️ Failed to start command analyzer: {e}[/yellow]"
            )

    async def _analyze_commands_background(self) -> None:
        """Background task to analyze and discover commands."""
        while self.running:
            try:
                # Discover new framework-specific commands
                new_commands = await self._discover_framework_commands()

                if new_commands:
                    self.available_commands.update(new_commands)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.console.print(f"[yellow]Command analysis error: {e}[/yellow]")
                await asyncio.sleep(60)

    async def _discover_framework_commands(self) -> Dict[str, str]:
        """Discover framework-specific commands."""
        discovered_commands = {}

        try:
            framework_name = self.config.framework.lower()

            # Django commands
            if framework_name == "django":
                manage_py = self.options.project_path / "manage.py"
                if manage_py.exists():
                    discovered_commands.update(
                        {
                            "migrate": "python manage.py migrate",
                            "makemigrations": "python manage.py makemigrations",
                            "createsuperuser": "python manage.py createsuperuser",
                            "collectstatic": "python manage.py collectstatic --noinput",
                            "shell": "python manage.py shell",
                            "dbshell": "python manage.py dbshell",
                        }
                    )

            # Flask commands
            elif framework_name == "flask":
                discovered_commands.update(
                    {
                        "shell": "flask shell",
                        "routes": "flask routes",
                        "run-debug": "flask run --debug",
                    }
                )

            # FastAPI commands
            elif framework_name == "fastapi":
                app_url = self.domain_utils.get_app_url()
                discovered_commands.update(
                    {
                        "docs": f"echo 'Visit {app_url}/docs for API documentation'",
                        "redoc": f"echo 'Visit {app_url}/redoc for ReDoc documentation'",
                    }
                )

        except Exception as e:
            self.console.print(f"[yellow]Error discovering commands: {e}[/yellow]")

        return discovered_commands

    async def _handle_file_change(self, changed_files) -> None:
        """Handle file change events for hot reload."""
        try:
            # Convert the list of file paths for the first file
            if changed_files:
                changed_file = (
                    Path(changed_files[0])
                    if isinstance(changed_files[0], str)
                    else changed_files[0]
                )
                self.console.print(f"[yellow]📁 File changed: {changed_file}[/yellow]")

                if self.app_process and self.app_process.returncode is None:
                    self.console.print("[blue]🔄 Restarting application...[/blue]")
                    try:
                        self.app_process.terminate()

                        # Wait for process to terminate with timeout
                        try:
                            await asyncio.wait_for(self.app_process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            self.console.print(
                                "[yellow]⚠️ Process didn't terminate gracefully, killing...[/yellow]"
                            )
                            self.app_process.kill()
                            await self.app_process.wait()

                        # Restart the application
                        await self._start_application()
                        self.console.print("[green]✓ Application restarted[/green]")

                    except Exception as e:
                        self.console.print(
                            f"[red]❌ Failed to restart application: {e}[/red]"
                        )
                else:
                    self.console.print(
                        "[yellow]⚠️ Application process not running, skipping restart[/yellow]"
                    )

        except Exception as e:
            self.console.print(f"[red]❌ Error handling file change: {e}[/red]")

    def _open_browser(self) -> None:
        """Open browser to development UI."""
        try:
            import webbrowser

            ui_url = self.domain_utils.get_ui_url()
            webbrowser.open(ui_url)
            self.console.print(f"[green]✓ Opened browser to {ui_url}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]Could not open browser: {e}[/yellow]")

    def _display_status(self) -> None:
        """Display comprehensive server status."""
        # Main status panel
        status_content = f"""[bold green]🔥 FUSE Development Server[/bold green]

            [cyan]Project:[/cyan] {getattr(self.config, "project_name", "Unknown")}
            [cyan]Framework:[/cyan] {self.config.framework.title()}
            [cyan]Version:[/cyan] {getattr(self.config, "version", "1.0.0")}

            [bold yellow]URLs:[/bold yellow]
            [cyan]Application:[/cyan] {self.domain_utils.get_app_url()}
            [cyan]Development UI:[/cyan] {self.domain_utils.get_ui_url()}
            """

        status_panel = Panel(
            status_content,
            title="🚀 Development Server Status",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(status_panel)

        # Services table with correct URLs
        services_table = Table(title="📊 Active Services", show_lines=True)
        services_table.add_column("Service", style="cyan")
        services_table.add_column("Status", style="green")
        services_table.add_column("URL", style="blue")
        services_table.add_column("Port", style="yellow")

        services_table.add_row(
            "🎯 Application Server",
            "Running",
            self.domain_utils.get_app_url(),
            str(self.options.port),
        )
        services_table.add_row(
            "🎛️ Development UI",
            "Running",
            self.domain_utils.get_ui_url(),
            str(self.options.ui_port),
        )
        services_table.add_row(
            "👁️ File Watcher", "Active" if self.options.reload else "Inactive", "-", "-"
        )
        services_table.add_row("🔍 Command Analyzer", "Active", "-", "-")

        self.console.print(services_table)

        # Available commands table
        if self.available_commands:
            commands_table = Table(title="⚡ Available Commands", show_lines=True)
            commands_table.add_column("Command", style="cyan")
            commands_table.add_column("Description", style="white")

            for cmd_name, cmd_value in self.available_commands.items():
                commands_table.add_row(cmd_name, cmd_value)

            self.console.print(commands_table)

        self.console.print(
            f"\n[bold green]🎯 Application: {self.domain_utils.get_app_url()}[/bold green]"
        )
        self.console.print(
            f"[bold blue]🎛️ Development UI: {self.domain_utils.get_ui_url()}[/bold blue]"
        )
        self.console.print(
            "\n[bold yellow]Press Ctrl+C to stop the server[/bold yellow]"
        )

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_shutdown_signal, sig)

    def _handle_shutdown_signal(self, sig) -> None:
        """Handle shutdown signals gracefully."""
        self.console.print(
            f"\n[yellow]Received shutdown signal {sig.name}, stopping...[/yellow]"
        )
        self.running = False

    async def _run_forever(self) -> None:
        """Main event loop."""
        while self.running:
            await asyncio.sleep(1)

    async def _cleanup(self) -> None:
        """Cleanup all resources."""
        self.console.print("[blue]🧹 Cleaning up resources...[/blue]")

        async def terminate_process(process):
            """Helper function to terminate a process gracefully."""
            if not process:
                return

            try:
                if process.returncode is None:  # Process is still running
                    process.terminate()
                    try:
                        # Wait for process to terminate with timeout
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        if process.returncode is None:  # Still running
                            process.kill()
                            await process.wait()
            except ProcessLookupError:
                pass  # Process already terminated
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Cleanup error: {e}[/yellow]")

        # Create list to hold cleanup tasks
        cleanup_tasks = []

        # Stop file watcher first
        if self.file_watcher and hasattr(self.file_watcher, "stop"):
            try:
                self.file_watcher.stop()
            except Exception as e:
                self.console.print(f"[yellow]⚠️ File watcher stop error: {e}[/yellow]")

        # Terminate processes
        if self.app_process:
            cleanup_tasks.append(terminate_process(self.app_process))

        if self.dev_ui_process:
            cleanup_tasks.append(terminate_process(self.dev_ui_process))

        # Run cleanup tasks concurrently with timeout
        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=10.0
                )
            except asyncio.TimeoutError:
                self.console.print(
                    "[yellow]⚠️ Cleanup took too long, some resources may not have been released properly[/yellow]"
                )
            except Exception as e:
                self.console.print(
                    f"[yellow]⚠️ Cleanup encountered an error: {e}[/yellow]"
                )

        self.console.print("[green]✓ Cleanup complete[/green]")

    # Public API methods
    def get_available_commands(self) -> Dict[str, str]:
        """Get all available commands for external access."""
        return self.available_commands.copy()

    async def execute_command(self, command_name: str) -> Dict[str, Any]:
        """Execute a specific command and return result."""
        if command_name not in self.available_commands:
            return {
                "success": False,
                "error": f"Command '{command_name}' not found",
                "output": "",
            }

        try:
            command = self.available_commands[command_name]
            result = self.template_manager.run_command(
                command,
                cwd=self.options.project_path,
                silent=False,
            )

            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "return_code": result.return_code,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "return_code": 1,
            }
