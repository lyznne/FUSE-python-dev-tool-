"""
Health Monitoring Module
Monitors system and application health status
"""

import asyncio
import psutil
import time
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import os
import traceback

from python_dev_tool.core.events import EventEmitter
from python_dev_tool.core.logger import DevToolLogger

# Internal imports


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'response_time': self.response_time,
            'metadata': self.metadata
        }


class BaseHealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str, timeout: float = 30.0):
        self.name = name
        self.timeout = timeout
        self.last_result: Optional[HealthCheckResult] = None
        self.failure_count = 0
        self.success_count = 0

    async def check(self) -> HealthCheckResult:
        """Perform the health check"""
        start_time = time.time()

        try:
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout
            )
            response_time = (time.time() - start_time) * 1000  # ms

            result.response_time = response_time
            result.timestamp = datetime.now()

            if result.status == HealthStatus.HEALTHY:
                self.success_count += 1
                self.failure_count = 0
            else:
                self.failure_count += 1

            self.last_result = result
            return result

        except asyncio.TimeoutError:
            self.failure_count += 1
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check timed out after {self.timeout}s",
                response_time=(time.time() - start_time) * 1000
            )
            self.last_result = result
            return result

        except Exception as e:
            self.failure_count += 1
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                response_time=(time.time() - start_time) * 1000,
                metadata={'error': str(e), 'traceback': traceback.format_exc()}
            )
            self.last_result = result
            return result

    async def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement the actual health check"""
        raise NotImplementedError()


class SystemHealthCheck(BaseHealthCheck):
    """System-level health checks"""

    def __init__(self, name: str = "system", timeout: float = 10.0):
        super().__init__(name, timeout)
        self.cpu_threshold = 90.0  # %
        self.memory_threshold = 90.0  # %
        self.disk_threshold = 90.0  # %
        self.load_threshold = 10.0  # load average

    async def _perform_check(self) -> HealthCheckResult:
        """Check system health"""
        issues = []
        warnings = []
        metadata = {}

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metadata['cpu_percent'] = cpu_percent
        if cpu_percent > self.cpu_threshold:
            issues.append(f"High CPU usage: {cpu_percent:.1f}%")
        elif cpu_percent > self.cpu_threshold * 0.8:
            warnings.append(f"Elevated CPU usage: {cpu_percent:.1f}%")

        # Memory usage
        memory = psutil.virtual_memory()
        metadata['memory_percent'] = memory.percent
        if memory.percent > self.memory_threshold:
            issues.append(f"High memory usage: {memory.percent:.1f}%")
        elif memory.percent > self.memory_threshold * 0.8:
            warnings.append(f"Elevated memory usage: {memory.percent:.1f}%")

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        metadata['disk_percent'] = disk_percent
        if disk_percent > self.disk_threshold:
            issues.append(f"High disk usage: {disk_percent:.1f}%")
        elif disk_percent > self.disk_threshold * 0.8:
            warnings.append(f"Elevated disk usage: {disk_percent:.1f}%")

        # Load average (Unix-like systems)
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()[0]
            metadata['load_avg'] = load_avg
            if load_avg > self.load_threshold:
                issues.append(f"High load average: {load_avg:.2f}")
            elif load_avg > self.load_threshold * 0.8:
                warnings.append(f"Elevated load average: {load_avg:.2f}")

        # Determine overall status
        if issues:
            status = HealthStatus.CRITICAL
            message = f"System health issues: {'; '.join(issues)}"
        elif warnings:
            status = HealthStatus.WARNING
            message = f"System health warnings: {'; '.join(warnings)}"
        else:
            status = HealthStatus.HEALTHY
            message = "System is healthy"

        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            metadata=metadata
        )


class ProcessHealthCheck(BaseHealthCheck):
    """Process-level health checks"""

    def __init__(self, name: str = "process", timeout: float = 5.0):
        super().__init__(name, timeout)
        self.process = psutil.Process()
        self.memory_threshold = 500 * 1024 * 1024  # 500MB
        self.thread_threshold = 100

    async def _perform_check(self) -> HealthCheckResult:
        """Check process health"""
        issues = []
        warnings = []
        metadata = {}

        try:
            with self.process.oneshot():
                # Memory usage
                memory_info = self.process.memory_info()
                metadata['memory_rss'] = memory_info.rss
                metadata['memory_vms'] = memory_info.vms

                if memory_info.rss > self.memory_threshold:
                    issues.append(f"High memory usage: {memory_info.rss / (1024*1024):.1f}MB")
                elif memory_info.rss > self.memory_threshold * 0.8:
                    warnings.append(f"Elevated memory usage: {memory_info.rss / (1024*1024):.1f}MB")

                # Thread count
                num_threads = self.process.num_threads()
                metadata['num_threads'] = num_threads
                if num_threads > self.thread_threshold:
                    issues.append(f"High thread count: {num_threads}")
                elif num_threads > self.thread_threshold * 0.8:
                    warnings.append(f"Elevated thread count: {num_threads}")

                # CPU usage
                cpu_percent = self.process.cpu_percent()
                metadata['cpu_percent'] = cpu_percent

                # File descriptors (Unix-like systems)
                if hasattr(self.process, 'num_fds'):
                    num_fds = self.process.num_fds()
                    metadata['num_fds'] = num_fds
                    if num_fds > 1000:
                        issues.append(f"High file descriptor count: {num_fds}")
                    elif num_fds > 800:
                        warnings.append(f"Elevated file descriptor count: {num_fds}")

                # Process status
                status = self.process.status()
                metadata['status'] = status
                if status in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                    issues.append(f"Process in bad state: {status}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            issues.append("Process not found")
            status = HealthStatus.CRITICAL
            message = "Process not found"  # noqa: F841
            metadata['error'] = "Process not found"
            self.failure_count += 1


class HealthChecker:
    """Health checker for the development tool all in one"""

    def __init__(self, logger: Optional[DevToolLogger] = None, event_emitter: Optional[EventEmitter] = None):
        self.logger = logger
        self.event_emitter = event_emitter
        self.health_checks: Dict[str, BaseHealthCheck] = {}
        self.running = False
        self.last_check_time = None
        self.check_interval = 30.0  # seconds
        self.last_check_result = None

    async def start(self) -> None:
        """Start the health checker"""
        if self.running:
            return

        self.running = True
        self.last_check_time = datetime.now()
        self.check_task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop the health checker"""
        self.running = False

        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass

    async def _check_loop(self) -> None:
        """Main health check loop"""
        while self.running:
            try:
                await self.check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval)

    async def check(self) -> None:
        """Perform health checks"""

        # Check system health

        # Check process health


        # Check framework health
