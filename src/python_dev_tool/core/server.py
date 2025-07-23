"""
FUSE - (python dev tool) - Core Development Server
server.py - Development Server with Framework Integration
"""
# sys imports
import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import socket
import signal

# local imports
from python_dev_tool.core.events import EventBus, EventType, EventEmitter
from python_dev_tool.core.exceptions import ServerError
from python_dev_tool.core.file_watcher import HotReloader
from python_dev_tool.core.process_manager import ProcessManager


class ServerState(Enum):
    """Server states"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    RELOADING = "reloading"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServerConfig:
    """Server configuration"""

    host: str = "127.0.0.1"
    port: int = 8000
    auto_reload: bool = True
    debug: bool = True
    workers: int = 1
    timeout: int = 30
    env_vars: Dict[str, str] = None
    custom_command: Optional[str] = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


@dataclass
class ServerInfo:
    """Server information"""

    server_id: str
    project_path: str
    framework: str
    config: ServerConfig
    state: ServerState
    pid: Optional[int] = None
    url: Optional[str] = None
    start_time: Optional[float] = None
    last_reload: Optional[float] = None
    error_message: Optional[str] = None


class FrameworkServer:
    """Base class for framework-specific servers"""

    def __init__(self, project_path: str, config: ServerConfig):
        self.project_path = project_path
        self.config = config
        self.process: Optional[subprocess.Popen] = None

    def get_command(self) -> List[str]:
        """Get the command to start the server"""
        raise NotImplementedError

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for the server"""
        env = os.environ.copy()
        env.update(self.config.env_vars)
        return env

    def get_url(self) -> str:
        """Get the server URL"""
        return f"http://{self.config.host}:{self.config.port}"

    def is_ready(self) -> bool:
        """Check if server is ready to accept connections"""
        return self._check_port_open(self.config.host, self.config.port)

    def _check_port_open(self, host: str, port: int) -> bool:
        """Check if port is open"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    def cleanup(self):
        """Cleanup resources"""
        pass


class DjangoServer(FrameworkServer):
    """Django development server"""

    def get_command(self) -> List[str]:
        """Get Django runserver command"""
        if self.config.custom_command:
            return self.config.custom_command.split()

        cmd = [
            sys.executable,
            "manage.py",
            "runserver",
            f"{self.config.host}:{self.config.port}",
        ]

        if not self.config.auto_reload:
            cmd.append("--noreload")

        return cmd

    def get_env_vars(self) -> Dict[str, str]:
        """Get Django environment variables"""
        env = super().get_env_vars()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": env.get("DJANGO_SETTINGS_MODULE", "settings"),
                "PYTHONPATH": self.project_path,
            }
        )
        return env


class FlaskServer(FrameworkServer):
    """Flask development server"""

    def get_command(self) -> List[str]:
        """Get Flask command"""
        if self.config.custom_command:
            return self.config.custom_command.split()

        return [
            sys.executable,
            "-m",
            "flask",
            "run",
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
        ]

    def get_env_vars(self) -> Dict[str, str]:
        """Get Flask environment variables"""
        env = super().get_env_vars()
        env.update(
            {
                "FLASK_ENV": "development" if self.config.debug else "production",
                "FLASK_DEBUG": "1" if self.config.debug else "0",
                "FLASK_RUN_HOST": self.config.host,
                "FLASK_RUN_PORT": str(self.config.port),
            }
        )

        # Try to find Flask app
        app_file = self._find_app_file()
        if app_file:
            env["FLASK_APP"] = app_file

        return env

    def _find_app_file(self) -> Optional[str]:
        """Find Flask app file"""
        possible_files = ["app.py", "main.py", "application.py", "run.py"]
        for file in possible_files:
            if os.path.exists(os.path.join(self.project_path, file)):
                return file
        return None


class FastAPIServer(FrameworkServer):
    """FastAPI development server"""

    def get_command(self) -> List[str]:
        """Get FastAPI/Uvicorn command"""
        if self.config.custom_command:
            return self.config.custom_command.split()

        app_module = self._find_app_module()

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            app_module,
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
        ]

        if self.config.auto_reload:
            cmd.append("--reload")

        if self.config.workers > 1:
            cmd.extend(["--workers", str(self.config.workers)])

        return cmd

    def _find_app_module(self) -> str:
        """Find FastAPI app module"""
        possible_modules = [
            "main:app",
            "app:app",
            "application:app",
            "api:app",
            "server:app",
        ]

        for module in possible_modules:
            file_path = module.split(":")[0] + ".py"
            if os.path.exists(os.path.join(self.project_path, file_path)):
                return module

        return "main:app"  # Default fallback


class StreamlitServer(FrameworkServer):
    """Streamlit development server"""

    def get_command(self) -> List[str]:
        """Get Streamlit command"""
        if self.config.custom_command:
            return self.config.custom_command.split()

        app_file = self._find_app_file()

        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_file,
            "--server.address",
            self.config.host,
            "--server.port",
            str(self.config.port),
        ]

        if not self.config.auto_reload:
            cmd.extend(["--server.fileWatcherType", "none"])

        return cmd

    def _find_app_file(self) -> str:
        """Find Streamlit app file"""
        possible_files = ["app.py", "main.py", "streamlit_app.py"]
        for file in possible_files:
            if os.path.exists(os.path.join(self.project_path, file)):
                return file
        return "app.py"  # Default fallback


class GenericServer(FrameworkServer):
    """Generic Python server"""

    def get_command(self) -> List[str]:
        """Get generic Python command"""
        if self.config.custom_command:
            return self.config.custom_command.split()

        # Try to find main script
        main_file = self._find_main_file()
        return [sys.executable, main_file]

    def _find_main_file(self) -> str:
        """Find main Python file"""
        possible_files = ["main.py", "app.py", "server.py", "run.py"]
        for file in possible_files:
            if os.path.exists(os.path.join(self.project_path, file)):
                return file
        return "main.py"  # Default fallback


class DevelopmentServer(EventEmitter):
    """Development server manager"""

    def __init__(
        self,
        project_path: str,
        framework: str,
        config: ServerConfig,
        event_bus: EventBus = None,
        process_manager: ProcessManager = None,
        hot_reloader: HotReloader = None,
    ):
        super().__init__(event_bus)
        self.project_path = project_path
        self.framework = framework
        self.config = config
        self.process_manager = process_manager
        self.hot_reloader = hot_reloader

        self.server_id = f"{framework}_{int(time.time())}"
        self.state = ServerState.STOPPED
        self.framework_server = self._create_framework_server()
        self.process: Optional[subprocess.Popen] = None
        self.monitor_task: Optional[asyncio.Task] = None

        # Subscribe to reload events
        if hot_reloader:
            self.subscribe(EventType.SERVER_RELOAD, self._handle_reload_event)

    def _create_framework_server(self) -> FrameworkServer:
        """Create framework-specific server"""
        servers = {
            "django": DjangoServer,
            "flask": FlaskServer,
            "fastapi": FastAPIServer,
            "streamlit": StreamlitServer,
        }

        server_class = servers.get(self.framework, GenericServer)
        return server_class(self.project_path, self.config)

    async def start(self) -> bool:
        """Start the development server"""
        if self.state != ServerState.STOPPED:
            return False

        try:
            self.state = ServerState.STARTING
            await self.emit(
                EventType.SERVER_STARTED,
                {"server_id": self.server_id, "state": self.state.value},
            )

            # Get command and environment
            command = self.framework_server.get_command()
            env = self.framework_server.get_env_vars()

            # Start process
            self.process = subprocess.Popen(
                command,
                cwd=self.project_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Start monitoring
            self.monitor_task = asyncio.create_task(self._monitor_process())

            # Wait for server to be ready
            await self._wait_for_ready()

            self.state = ServerState.RUNNING
            await self.emit(
                EventType.SERVER_STARTED,
                {
                    "server_id": self.server_id,
                    "state": self.state.value,
                    "url": self.framework_server.get_url(),
                    "pid": self.process.pid,
                },
            )

            # Setup hot reloading
            if self.hot_reloader and self.config.auto_reload:
                await self.hot_reloader.setup_project_watching(
                    self.server_id, self.project_path, self.framework
                )

            return True

        except Exception as e:
            self.state = ServerState.ERROR
            await self.emit(
                EventType.SERVER_STOPPED,
                {
                    "server_id": self.server_id,
                    "state": self.state.value,
                    "error": str(e),
                },
            )
            return False

    async def stop(self) -> bool:
        """Stop the development server"""
        if self.state == ServerState.STOPPED:
            return True

        try:
            self.state = ServerState.STOPPING
            await self.emit(
                EventType.SERVER_STOPPED,
                {"server_id": self.server_id, "state": self.state.value},
            )

            # Stop hot reloading
            if self.hot_reloader:
                self.hot_reloader.stop_project_watching(self.server_id)

            # Terminate process
            if self.process:
                self.process.terminate()

                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process_exit()), timeout=10
                    )
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    self.process.kill()

                self.process = None

            # Cancel monitoring
            if self.monitor_task:
                self.monitor_task.cancel()
                self.monitor_task = None

            self.state = ServerState.STOPPED
            await self.emit(
                EventType.SERVER_STOPPED,
                {"server_id": self.server_id, "state": self.state.value},
            )

            return True

        except Exception as e:
            self.state = ServerState.ERROR
            await self.emit(
                EventType.SERVER_STOPPED,
                {
                    "server_id": self.server_id,
                    "state": self.state.value,
                    "error": str(e),
                },
            )
            return False

    async def restart(self) -> bool:
        """Restart the development server"""
        await self.stop()
        return await self.start()

    async def reload(self) -> bool:
        """Reload the development server"""
        if self.state != ServerState.RUNNING:
            return False

        self.state = ServerState.RELOADING
        await self.emit(
            EventType.SERVER_RELOAD,
            {"server_id": self.server_id, "state": self.state.value},
        )

        # For now, just restart the server
        # For frameworks that support in-process reloading
        if self.framework in ("flask", "django", "fastapi"):
            try:
                # Send reload signal to the process
                if self.process and self.process.poll() is None:
                    if sys.platform == "win32":
                        # Windows doesn't support SIGUSR1
                        return await self.restart()
                    else:
                        self.process.send_signal(signal.SIGUSR1)
                        self.state = ServerState.RUNNING
                        await self.emit(
                            EventType.SERVER_RELOADED,
                            {"server_id": self.server_id, "state": self.state.value},
                        )
                        return True
            except Exception as e:
                return await self.restart()

        # Fall back to full restart for other frameworks
        return await self.restart()

    async def _handle_reload_event(self, data: dict) -> None:
        """Handle file change events for hot reloading"""
        if self.state == ServerState.RUNNING and self.config.auto_reload:
            await self.reload()

    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for server to become ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.framework_server.is_ready():
                return
            await asyncio.sleep(0.5)

        if self.process and self.process.poll() is not None:
            output = self.process.stdout.read() if self.process.stdout else ""
            raise ServerError(f"Server failed to start:\n{output}")
        raise ServerError("Server failed to become ready")

    async def _wait_for_process_exit(self) -> None:
        """Wait for process to exit"""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)

    async def _monitor_process(self) -> None:
        """Monitor the server process for crashes"""
        try:
            while True:
                if self.process is None:
                    break

                # Check if process died
                if self.process.poll() is not None:
                    output = self.process.stdout.read() if self.process.stdout else ""
                    self.state = ServerState.ERROR
                    await self.emit(
                        EventType.SERVER_STOPPED,
                        {
                            "server_id": self.server_id,
                            "state": self.state.value,
                            "error": f"Process crashed with return code {self.process.returncode}\n{output}",
                        },
                    )
                    break

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.state = ServerState.ERROR
            await self.emit(
                EventType.SERVER_STOPPED,
                {
                    "server_id": self.server_id,
                    "state": self.state.value,
                    "error": str(e),
                },
            )

    def get_server_info(self) -> ServerInfo:
        """Get current server information"""
        return ServerInfo(
            server_id=self.server_id,
            project_path=self.project_path,
            framework=self.framework,
            config=self.config,
            state=self.state,
            pid=self.process.pid if self.process else None,
            url=self.framework_server.get_url()
            if self.state == ServerState.RUNNING
            else None,
            start_time=getattr(self.process, "start_time", None)
            if self.process
            else None,
            last_reload=getattr(self, "_last_reload_time", None),
            error_message=getattr(self, "_last_error", None),
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class ServerManager:
    """Manages multiple development servers"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus or EventBus()
        self.servers: Dict[str, DevelopmentServer] = {}
        self.process_manager = ProcessManager()
        self.hot_reloader = HotReloader(event_bus)

    async def start_server(
        self, project_path: str, framework: str, config: Optional[ServerConfig] = None
    ) -> str:
        """Start a new development server"""
        config = config or ServerConfig()
        server = DevelopmentServer(
            project_path=project_path,
            framework=framework,
            config=config,
            event_bus=self.event_bus,
            process_manager=self.process_manager,
            hot_reloader=self.hot_reloader,
        )

        server_id = server.server_id
        self.servers[server_id] = server

        if not await server.start():
            del self.servers[server_id]
            raise ServerError("Failed to start server")

        return server_id

    async def stop_server(self, server_id: str) -> bool:
        """Stop a running server"""
        server = self.servers.get(server_id)
        if not server:
            return False

        result = await server.stop()
        if result:
            del self.servers[server_id]

        return result

    async def restart_server(self, server_id: str) -> bool:
        """Restart a server"""
        server = self.servers.get(server_id)
        if not server:
            return False

        return await server.restart()

    async def reload_server(self, server_id: str) -> bool:
        """Reload a server"""
        server = self.servers.get(server_id)
        if not server:
            return False

        return await server.reload()

    def get_server_info(self, server_id: str) -> Optional[ServerInfo]:
        """Get server information"""
        server = self.servers.get(server_id)
        return server.get_server_info() if server else None

    def list_servers(self) -> List[ServerInfo]:
        """List all running servers"""
        return [server.get_server_info() for server in self.servers.values()]

    async def stop_all(self) -> None:
        """Stop all running servers"""
        for server_id in list(self.servers.keys()):
            await self.stop_server(server_id)
