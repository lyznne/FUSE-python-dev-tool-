"""
FUSE - (python dev tool) - Core Process Manager
process_manager.py - Process Manager (Process lifecycle management)
"""

# sys imports
import asyncio
import datetime
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import psutil

# 3rd party imports
# local imports
from python_dev_tool.core.events import EventBus


class ProcessStatus(Enum):
    """Process status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """Process information."""

    pid: Optional[int] = None
    name: str = ""
    command: str = ""
    status: ProcessStatus = ProcessStatus.UNKNOWN
    started_at: Optional[datetime.datetime] = None
    stopped_at: Optional[datetime.datetime] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    port: Optional[int] = None


class ProcessManager:
    """Process manager."""

    def __init__(self, event_bus: EventBus):
        self.processes: Dict[int, ProcessInfo] = {}
        self.event_bus = event_bus
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_process(
        self,
        name: str,
        command: str,
        env: Dict[str, str],
        cwd: str,
        port: int,
    ) -> ProcessInfo:
        """Start a new process with monitoring."""

        try:
            # start process
            process = await asyncio.create_subprocess_exec(
                *command.split(),
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            # create process info
            process_info = ProcessInfo(
                pid=process.pid,
                name=name,
                command=command,
                status=ProcessStatus.STARTING,
                started_at=datetime.datetime.now(),
                port=self._extract_port(command),
                cpu_percent=0.0,
                memory_mb=0.0,
            )

            self.processes[name] = process_info

            # start monitoring
            if not self._monitor_task:
                self._monitor_task = asyncio.create_task(self._monitor_processes())

            # start log streaming
            asyncio.create_task(self._stream_logs(name, process))

            self.event_bus.publish(
                "process started",
                {
                    "name": name,
                    "pid": process_info.pid,
                    "command": command,
                    "port": process_info.port,
                },
            )

            return process_info
        except Exception as e:
            self.event_bus.publish(
                "process error",
                {
                    "name": name,
                    "command": command,
                    "error": str(e),
                },
            )
            raise

    async def stop_process(self, name: str, pid: int) -> bool:
        """Stop a running process."""
        if name not in self.processes:
            return False

        process_info = self.processes[name]
        if process_info.status != ProcessStatus.RUNNING:
            return False

        try:
            # get psutil process
            process = psutil.Process(process_info.pid)

            # gracefully stop process
            process.terminate()

            # wait for termination
            try:
                process.wait(timeout=10)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait()

            # update status
            process_info.status = ProcessStatus.STOPPED
            process_info.stopped_at = datetime.datetime.now()

            self.event_bus.publish(
                "process stopped",
                {
                    "name": name,
                    "pid": process_info.pid,
                },
            )
            return True
        except Exception as e:
            self.event_bus.publish(
                "process.error",
                {
                    "name": name,
                    # 'pid': process_info.pid,
                    "error": str(e),
                },
            )

    async def _monitor_processes(self) -> None:
        """Monitor processes and update status."""
        while True:
            for name, process_info in self.processes.items():
                if process_info.pid and process_info.status == ProcessStatus.RUNNING:
                    try:
                        process = psutil.Process(process_info.pid)

                        # update metrics
                        process_info.cpu_percent = process.cpu_percent()
                        process_info.memory_mb = process.memory_info().rss / 1024 / 1024

                        # check if process is still alive
                        if not process.is_running():
                            process_info.status = ProcessStatus.CRASHED
                            self.event_bus.publish(
                                "process.craashed",
                                {
                                    "name": name,
                                    "pid": process_info.pid,
                                },
                            )

                    except psutil.NoSuchProcess:
                        process_info.status = ProcessStatus.CRASHED
                        self.event_bus.publish(
                            "process.craashed",
                            {
                                "name": name,
                                "pid": process_info.pid,
                            },
                        )

            await asyncio.sleep(1)

    def _extract_port(self, command: str) -> Optional[int]:
        """Extract port from command string."""

        # commmand patterns
        patterns = [
            r"--port[=\s](\d+)",
            r"-p[=\s](\d+)",
            r":(\d+)",
            r"runserver[=\s].*:(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                return int(match.group(1))

        return None

    def get_project_processes(self, project_path: Path) -> List[Dict[str, str]]:
        """
        Scan running processes and return those related to the given project.
        """
        project_path_str = str(project_path.resolve())
        matching_procs = []

        for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
            try:
                cwd = proc.info.get("cwd")
                cmdline = proc.info.get("cmdline") or []

                if cwd and cwd.startswith(project_path_str):
                    matching_procs.append(
                        {
                            "name": proc.info.get("name", "unknown"),
                            "status": proc.status(),
                            "pid": str(proc.pid),
                            "cmd": " ".join(cmdline),
                        }
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return matching_procs
