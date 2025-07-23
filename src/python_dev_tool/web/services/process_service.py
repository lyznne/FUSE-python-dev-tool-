"""
Process Service - Process management and lifecycle control
Handles process creation, monitoring, and termination
"""

import asyncio
import logging
import os
import subprocess
import psutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.exceptions import ProcessError
from python_dev_tool.web.models.process import Process, ProcessStatus, ProcessType
from python_dev_tool.utils.async_utils import AsyncUtils
from python_dev_tool.utils.network_utils import NetworkUtils


class ProcessEventType(Enum):
    """Process event types."""
    PROCESS_CREATED = "process_created"
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    PROCESS_CRASHED = "process_crashed"
    PROCESS_RESTARTED = "process_restarted"
    OUTPUT_RECEIVED = "output_received"
    ERROR_RECEIVED = "error_received"


@dataclass
class ProcessMetrics:
    """Process performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_mb: int
    pid: int
    threads: int
    uptime: float
    restart_count: int
    last_restart: Optional[datetime] = None


@dataclass
class ProcessCommand:
    """Process command configuration."""
    command: str
    args: List[str]
    cwd: str
    env: Dict[str, str]
    shell: bool = False


class ProcessMonitor:
    """Monitor process health and performance."""

    def __init__(self, process_service: 'ProcessService'):
        self.process_service = process_service
        self.logger = logging.getLogger(f"{__name__}.ProcessMonitor")
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def start_monitoring(self, process_id: str):
        """Start monitoring a process."""
        if process_id in self.monitoring_tasks:
            return

        task = asyncio.create_task(self._monitor_process(process_id))
        self.monitoring_tasks[process_id] = task

    async def stop_monitoring(self, process_id: str):
        """Stop monitoring a process."""
        if process_id in self.monitoring_tasks:
            task = self.monitoring_tasks[process_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.monitoring_tasks[process_id]

    async def _monitor_process(self, process_id: str):
        """Monitor process continuously."""
        while True:
            try:
                process = await self.process_service.get_process(process_id)
                if not process or process.status != ProcessStatus.RUNNING:
                    break

                # Get process metrics
                metrics = await self._get_process_metrics(process)
                if metrics:
                    # Update metrics
                    self.process_service.metrics[process_id] = metrics

                    # Check for crashes
                    if not await self._is_process_alive(process):
                        await self.process_service._handle_process_crash(process_id)
                        break

                await asyncio.sleep(1)  # Monitor every second

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring process {process_id}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _get_process_metrics(self, process: Process) -> Optional[ProcessMetrics]:
        """Get process performance metrics."""
        try:
            if not process.pid:
                return None

            psutil_process = psutil.Process(process.pid)

            # Get CPU and memory usage
            cpu_percent = psutil_process.cpu_percent()
            memory_info = psutil_process.memory_info()
            memory_percent = psutil_process.memory_percent()

            # Get process info
            create_time = psutil_process.create_time()
            uptime = datetime.now().timestamp() - create_time

            return ProcessMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_info.rss // 1024 // 1024,  # Convert to MB
                pid=process.pid,
                threads=psutil_process.num_threads(),
                uptime=uptime,
                restart_count=process.restart_count or 0,
                last_restart=process.last_restart
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    async def _is_process_alive(self, process: Process) -> bool:
        """Check if process is alive."""
        try:
            if not process.pid:
                return False
            psutil_process = psutil.Process(process.pid)
            return psutil_process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False


class ProcessService:
    """Core process management service."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processes: Dict[str, Process] = {}
        self.subprocesses: Dict[str, subprocess.Popen] = {}
        self.metrics: Dict[str, ProcessMetrics] = {}
        self.event_emitter = EventEmitter()
        self.monitor = ProcessMonitor(self)
        self.network_utils = NetworkUtils()
        self.async_utils = AsyncUtils()

    async def initialize(self):
        """Initialize the process service."""
        self.logger.info("Initializing ProcessService...")

        # Clean up any orphaned processes
        await self._cleanup_orphaned_processes()

        self.logger.info("ProcessService initialized successfully")

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up ProcessService...")

        # Stop all monitoring tasks
        for task in self.monitor.monitoring_tasks.values():
            task.cancel()

        # Terminate all processes
        for process_id in list(self.processes.keys()):
            await self.terminate_process(process_id)

        self.logger.info("ProcessService cleanup completed")

    async def create_process(
        self,
        name: str,
        command: ProcessCommand,
        process_type: ProcessType = ProcessType.SERVER,
        auto_restart: bool = True,
        max_restarts: int = 3,
        project_id: Optional[str] = None
    ) -> Process:
        """Create a new process."""
        try:
            # Generate process ID
            process_id = self.async_utils.generate_id()

            # Find available port if needed
            port = None
            if process_type in [ProcessType.SERVER, ProcessType.WEB]:
                port = await self.network_utils.find_available_port()

            # Create process instance
            process = Process(
                id=process_id,
                name=name,
                command=command.command,
                args=command.args,
                cwd=command.cwd,
                env=command.env,
                process_type=process_type,
                status=ProcessStatus.CREATED,
                auto_restart=auto_restart,
                max_restarts=max_restarts,
                port=port,
                project_id=project_id,
                created_at=datetime.now(timezone.utc)
            )

            # Store process
            self.processes[process_id] = process

            # Emit event
            await self.event_emitter.emit(
                ProcessEventType.PROCESS_CREATED.value,
                {"process": asdict(process)}
            )

            self.logger.info(f"Created process: {name} ({process_id})")
            return process

        except Exception as e:
            self.logger.error(f"Failed to create process {name}: {str(e)}")
            raise ProcessError(f"Failed to create process: {str(e)}")

    async def start_process(self, process_id: str) -> bool:
        """Start a process."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        if process.status == ProcessStatus.RUNNING:
            return True

        try:
            # Update status
            process.status = ProcessStatus.STARTING
            process.updated_at = datetime.now(timezone.utc)

            # Build command
            cmd = [process.command] + process.args

            # Set up environment
            env = os.environ.copy()
            env.update(process.env)

            # Add port to environment if available
            if process.port:
                env['PORT'] = str(process.port)

            # Start subprocess
            subprocess_proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=process.cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )

            # Store subprocess
            self.subprocesses[process_id] = subprocess_proc

            # Update process info
            process.status = ProcessStatus.STOPPED
            process.stopped_at = datetime.now(timezone.utc)
            process.pid = None

            # Emit event
            await self.event_emitter.emit(
                ProcessEventType.PROCESS_STOPPED.value,
                {"process": asdict(process)}
            )

            self.logger.info(f"Stopped process: {process.name} ({process_id})")
            return True

        except Exception as e:
            process.status = ProcessStatus.ERROR
            process.error_message = str(e)
            self.logger.error(f"Failed to stop process {process_id}: {str(e)}")
            raise ProcessError(f"Failed to stop process: {str(e)}")

    async def restart_process(self, process_id: str) -> bool:
        """Restart a process."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        try:
            # Stop process if running
            if process.status == ProcessStatus.RUNNING:
                await self.stop_process(process_id)

            # Increment restart count
            process.restart_count = (process.restart_count or 0) + 1
            process.last_restart = datetime.now(timezone.utc)

            # Check restart limits
            if process.restart_count > process.max_restarts:
                process.status = ProcessStatus.FAILED
                process.error_message = "Maximum restart attempts exceeded"
                return False

            # Start process
            await self.start_process(process_id)

            # Emit event
            await self.event_emitter.emit(
                ProcessEventType.PROCESS_RESTARTED.value,
                {"process": asdict(process)}
            )

            self.logger.info(f"Restarted process: {process.name} ({process_id})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restart process {process_id}: {str(e)}")
            raise ProcessError(f"Failed to restart process: {str(e)}")

    async def terminate_process(self, process_id: str) -> bool:
        """Terminate a process permanently."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        try:
            # Stop process
            await self.stop_process(process_id, force=True)

            # Remove from processes
            del self.processes[process_id]

            # Clean up metrics
            if process_id in self.metrics:
                del self.metrics[process_id]

            self.logger.info(f"Terminated process: {process.name} ({process_id})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to terminate process {process_id}: {str(e)}")
            raise ProcessError(f"Failed to terminate process: {str(e)}")

    async def get_process(self, process_id: str) -> Optional[Process]:
        """Get process by ID."""
        return self.processes.get(process_id)

    async def get_all_processes(self) -> List[Process]:
        """Get all processes."""
        return list(self.processes.values())

    async def get_processes_by_source(self, project_id: str) -> List[Process]:
        """Get processes for a specific project."""
        return [
            process for process in self.processes.values()
            if process.project_id == project_id
        ]

    async def get_process_metrics(self, process_id: str) -> Optional[ProcessMetrics]:
        """Get process metrics."""
        return self.metrics.get(process_id)

    async def get_process_output(
        self,
        process_id: str,
        lines: int = 100,
        stream: str = "both"
    ) -> Dict[str, List[str]]:
        """Get process output."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        # This would typically read from log files or in-memory buffers
        # For now, return empty structure
        return {
            "stdout": [],
            "stderr": []
        }

    async def send_input(self, process_id: str, input_data: str) -> bool:
        """Send input to a process."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        if process.status != ProcessStatus.RUNNING:
            raise ProcessError(f"Process is not running: {process_id}")

        try:
            subprocess_proc = self.subprocesses.get(process_id)
            if subprocess_proc and subprocess_proc.stdin:
                subprocess_proc.stdin.write(input_data.encode())
                await subprocess_proc.stdin.drain()
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to send input to process {process_id}: {str(e)}")
            raise ProcessError(f"Failed to send input: {str(e)}")

    async def kill_process_tree(self, process_id: str) -> bool:
        """Kill process and all its children."""
        process = self.processes.get(process_id)
        if not process or not process.pid:
            return False

        try:
            # Get process tree
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)

            # Kill children first
            for child in children:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Kill parent
            parent.kill()

            # Wait for processes to die
            gone, still_alive = psutil.wait_procs(children + [parent], timeout=3)

            # Force kill any remaining processes
            for proc in still_alive:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Failed to kill process tree {process_id}: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the process service."""
        running_processes = [
            p for p in self.processes.values()
            if p.status == ProcessStatus.RUNNING
        ]

        return {
            "status": "healthy",
            "processes_count": len(self.processes),
            "running_processes": len(running_processes),
            "monitoring_tasks": len(self.monitor.monitoring_tasks),
            "subprocesses": len(self.subprocesses)
        }

    # Private methods
    async def _handle_process_output(self, process_id: str):
        """Handle process output streams."""
        subprocess_proc = self.subprocesses.get(process_id)
        if not subprocess_proc:
            return

        # Handle stdout
        asyncio.create_task(self._read_stream(
            process_id, subprocess_proc.stdout, "stdout"
        ))

        # Handle stderr
        asyncio.create_task(self._read_stream(
            process_id, subprocess_proc.stderr, "stderr"
        ))

    async def _read_stream(self, process_id: str, stream, stream_type: str):
        """Read from a process stream."""
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break

                line_str = line.decode('utf-8', errors='replace').strip()

                # Emit output event
                event_type = (
                    ProcessEventType.OUTPUT_RECEIVED.value
                    if stream_type == "stdout"
                    else ProcessEventType.ERROR_RECEIVED.value
                )

                await self.event_emitter.emit(event_type, {
                    "process_id": process_id,
                    "output": line_str,
                    "stream": stream_type,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        except Exception as e:
            self.logger.error(f"Error reading {stream_type} for process {process_id}: {str(e)}")

    async def _handle_process_crash(self, process_id: str):
        """Handle process crash."""
        process = self.processes.get(process_id)
        if not process:
            return

        # Update process status
        process.status = ProcessStatus.CRASHED
        process.updated_at = datetime.now(timezone.utc)

        # Emit crash event
        await self.event_emitter.emit(
            ProcessEventType.PROCESS_CRASHED.value,
            {"process": asdict(process)}
        )

        self.logger.warning(f"Process crashed: {process.name} ({process_id})")

        # Auto-restart if enabled
        if process.auto_restart and (process.restart_count or 0) < process.max_restarts:
            await asyncio.sleep(1)  # Brief delay before restart
            await self.restart_process(process_id)

    async def _cleanup_orphaned_processes(self):
        """Clean up any orphaned processes from previous sessions."""
        # This would typically check for processes that were left running and clean them up
        pass

    async def stop_process(self, process_id: str, force: bool = False) -> bool:
        """Stop a process."""
        process = self.processes.get(process_id)
        if not process:
            raise ProcessError(f"Process not found: {process_id}")

        if process.status == ProcessStatus.STOPPED:
            return True

        try:
            # Update status
            process.status = ProcessStatus.STOPPING
            process.updated_at = datetime.now(timezone.utc)

            # Stop monitoring
            await self.monitor.stop_monitoring(process_id)

            # Terminate subprocess
            if process_id in self.subprocesses:
                subprocess_proc = self.subprocesses[process_id]

                if force:
                    # Force kill
                    subprocess_proc.kill()
                else:
                    # Graceful shutdown
                    subprocess_proc.terminate()

                    # Wait for graceful shutdown
                    try:
                        await asyncio.wait_for(subprocess_proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Force kill if graceful shutdown fails
                        subprocess_proc.kill()
                        await subprocess_proc.wait()

                del self.subprocesses[process_id]

            # Update process info
            process.status = ProcessStatus.STOPPED
            process.stopped_at = datetime.now(timezone.utc)
            process.pid = None

            # Emit event
            await self.event_emitter.emit(
                ProcessEventType.PROCESS_STOPPED.value,
                {"process": asdict(process)}
            )

            self.logger.info(f"Stopped process: {process.name} ({process_id})")
            return True

        except Exception as e:
            process.status = ProcessStatus.ERROR
            process.error_message = str(e)
            self.logger.error(f"Failed to stop process {process_id}: {str(e)}")
            raise ProcessError(f"Failed to stop process: {str(e)}")


def get_process_service() -> ProcessService:
    """Get the singleton instance of ProcessService."""
    if not hasattr(get_process_service, "_instance"):
        get_process_service._instance = ProcessService()
    return get_process_service._instance
