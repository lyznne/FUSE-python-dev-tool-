"""
Health Monitoring Module
Monitors system and application health status

Health monitoring and checks for Python Dev Tool.

This module provides comprehensive health monitoring including:
- System health checks (CPU, memory, disk, network)
- Application health checks (services, dependencies, endpoints)
- Framework-specific health checks
- Custom health checks with configurable thresholds
- Health status aggregation and reporting
- Integration with alerting systems
"""

import asyncio
import psutil
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import requests
import socket
import logging



logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    @property
    def is_warning(self) -> bool:
        return self.status == HealthStatus.WARNING

    @property
    def is_critical(self) -> bool:
        return self.status == HealthStatus.CRITICAL


class HealthCheck:
    """Base class for health checks."""

    def __init__(self, name: str, description: str = "", timeout: float = 10.0):
        self.name = name
        self.description = description
        self.timeout = timeout
        self.enabled = True
        self.last_result: Optional[HealthCheckResult] = None
        self.history: List[HealthCheckResult] = []
        self.max_history = 100

    async def check(self) -> HealthCheckResult:
        """Perform the health check. Override in subclasses."""
        raise NotImplementedError

    async def run_check(self) -> HealthCheckResult:
        """Run the health check with timeout and error handling."""
        if not self.enabled:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Health check is disabled",
            )

        start_time = time.time()
        try:
            result = await asyncio.wait_for(self.check(), timeout=self.timeout)
            result.duration_ms = (time.time() - start_time) * 1000

            # Store result
            self.last_result = result
            self.history.append(result)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration_ms,
            )
            self.last_result = result
            self.history.append(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                metadata={"error": str(e), "error_type": type(e).__name__},
            )
            self.last_result = result
            self.history.append(result)
            return result

    def get_success_rate(self, window_minutes: int = 5) -> float:
        """Get success rate over a time window."""
        if not self.history:
            return 0.0

        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_results = [r for r in self.history if r.timestamp >= cutoff]

        if not recent_results:
            return 0.0

        successful = sum(1 for r in recent_results if r.is_healthy)
        return successful / len(recent_results)


class SystemHealthCheck(HealthCheck):
    """System-level health checks."""

    def __init__(
        self,
        name: str,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        disk_threshold: float = 90.0,
    ):
        super().__init__(name, "System resource health check")
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    async def check(self) -> HealthCheckResult:
        """Check system health."""
        issues = []
        metadata = {}

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metadata["cpu_percent"] = cpu_percent
        if cpu_percent > self.cpu_threshold:
            issues.append(f"High CPU usage: {cpu_percent:.1f}%")

        # Memory usage
        memory = psutil.virtual_memory()
        metadata["memory_percent"] = memory.percent
        metadata["memory_available"] = memory.available
        if memory.percent > self.memory_threshold:
            issues.append(f"High memory usage: {memory.percent:.1f}%")

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        metadata["disk_percent"] = disk_percent
        metadata["disk_free"] = disk.free
        if disk_percent > self.disk_threshold:
            issues.append(f"High disk usage: {disk_percent:.1f}%")

        # Load average (Unix-like systems)
        try:
            load_avg = psutil.getloadavg()
            metadata["load_avg"] = load_avg
        except (AttributeError, OSError):
            pass

        # Determine status
        if not issues:
            status = HealthStatus.HEALTHY
            message = "System resources are healthy"
        elif len(issues) == 1:
            status = HealthStatus.WARNING
            message = f"System warning: {issues[0]}"
        else:
            status = HealthStatus.CRITICAL
            message = f"System issues: {', '.join(issues)}"

        return HealthCheckResult(
            name=self.name, status=status, message=message, metadata=metadata
        )


class ProcessHealthCheck(HealthCheck):
    """Process-specific health check."""

    def __init__(
        self,
        name: str,
        pid: int,
        max_memory_mb: float = 1000.0,
        max_cpu_percent: float = 80.0,
    ):
        super().__init__(name, f"Process health check for PID {pid}")
        self.pid = pid
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.process: Optional[psutil.Process] = None

    async def check(self) -> HealthCheckResult:
        """Check process health."""
        try:
            if not self.process:
                self.process = psutil.Process(self.pid)

            # Check if process exists
            if not self.process.is_running():
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Process {self.pid} is not running",
                )

            # Get process info
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            metadata = {
                "pid": self.pid,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "status": self.process.status(),
                "create_time": self.process.create_time(),
            }

            issues = []
            if cpu_percent > self.max_cpu_percent:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory_mb > self.max_memory_mb:
                issues.append(f"High memory usage: {memory_mb:.1f}MB")

            # Check for zombie processes
            if self.process.status() == psutil.STATUS_ZOMBIE:
                issues.append("Process is zombie")

            # Determine status
            if not issues:
                status = HealthStatus.HEALTHY
                message = f"Process {self.pid} is healthy"
            elif len(issues) == 1:
                status = HealthStatus.WARNING
                message = f"Process warning: {issues[0]}"
            else:
                status = HealthStatus.CRITICAL
                message = f"Process issues: {', '.join(issues)}"

            return HealthCheckResult(
                name=self.name, status=status, message=message, metadata=metadata
            )

        except psutil.NoSuchProcess:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Process {self.pid} not found",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Error checking process: {str(e)}",
            )


class HTTPHealthCheck(HealthCheck):
    """HTTP endpoint health check."""

    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: float = 10.0,
        headers: Dict[str, str] = None,
    ):
        super().__init__(name, f"HTTP health check for {url}", timeout)
        self.url = url
        self.method = method.upper()
        self.expected_status = expected_status
        self.headers = headers or {}

    async def check(self) -> HealthCheckResult:
        """Check HTTP endpoint health."""
        try:
            start_time = time.time()

            # Use requests in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.request(
                    self.method, self.url, headers=self.headers, timeout=self.timeout
                ),
            )

            response_time = (time.time() - start_time) * 1000

            metadata = {
                "url": self.url,
                "method": self.method,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "content_length": len(response.content),
                "headers": dict(response.headers),
            }

            if response.status_code == self.expected_status:
                status = HealthStatus.HEALTHY
                message = (
                    f"HTTP {self.method} {self.url} returned {response.status_code}"
                )
            elif 400 <= response.status_code < 500:
                status = HealthStatus.WARNING
                message = f"HTTP {self.method} {self.url} returned {response.status_code} (client error)"
            else:
                status = HealthStatus.CRITICAL
                message = f"HTTP {self.method} {self.url} returned {response.status_code} (server error)"

            return HealthCheckResult(
                name=self.name, status=status, message=message, metadata=metadata
            )

        except requests.exceptions.Timeout:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"HTTP {self.method} {self.url} timed out",
            )
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"HTTP {self.method} {self.url} connection failed",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"HTTP {self.method} {self.url} failed: {str(e)}",
            )


class DatabaseHealthCheck(HealthCheck):
    """Database connection health check."""

    def __init__(
        self,
        name: str,
        connection_string: str,
        query: str = "SELECT 1",
        timeout: float = 10.0,
    ):
        super().__init__(name, f"Database health check: {name}", timeout)
        self.connection_string = connection_string
        self.query = query

    async def check(self) -> HealthCheckResult:
        """Check database health."""
        try:
            import sqlalchemy
            from sqlalchemy import create_engine, text

            start_time = time.time()
            engine = create_engine(self.connection_string, pool_timeout=self.timeout)

            with engine.connect() as conn:
                result = conn.execute(text(self.query))
                result.fetchone()

            response_time = (time.time() - start_time) * 1000

            metadata = {
                "query": self.query,
                "response_time_ms": response_time,
                "connection_string": self.connection_string.split("@")[-1]
                if "@" in self.connection_string
                else "hidden",
            }

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"Database connection successful",
                metadata=metadata,
            )

        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message="SQLAlchemy not available for database health check",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
            )


class RedisHealthCheck(HealthCheck):
    """Redis connection health check."""

    def __init__(
        self,
        name: str,
        host: str = "localhost",
        port: int = 6379,
        password: str = None,
        db: int = 0,
        timeout: float = 10.0,
    ):
        super().__init__(name, f"Redis health check: {host}:{port}", timeout)
        self.host = host
        self.port = port
        self.password = password
        self.db = db

    async def check(self) -> HealthCheckResult:
        """Check Redis health."""
        try:
            import redis

            start_time = time.time()
            client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout,
            )

            # Ping Redis
            pong = client.ping()

            # Get info
            info = client.info()

            response_time = (time.time() - start_time) * 1000

            metadata = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "response_time_ms": response_time,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
            }

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"Redis connection successful: {pong}",
                metadata=metadata,
            )

        except ImportError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message="Redis library not available for health check",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Redis connection failed: {str(e)}",
            )


class PortHealthCheck(HealthCheck):
    """Port availability health check."""

    def __init__(self, name: str, host: str, port: int, timeout: float = 5.0):
        super().__init__(name, f"Port health check: {host}:{port}", timeout)
        self.host = host
        self.port = port

    async def check(self) -> HealthCheckResult:
        """Check port availability."""
        try:
            start_time = time.time()

            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            try:
                result = sock.connect_ex((self.host, self.port))
                response_time = (time.time() - start_time) * 1000

                metadata = {
                    "host": self.host,
                    "port": self.port,
                    "response_time_ms": response_time,
                }

                if result == 0:
                    status = HealthStatus.HEALTHY
                    message = f"Port {self.host}:{self.port} is open"
                else:
                    status = HealthStatus.CRITICAL
                    message = f"Port {self.host}:{self.port} is closed"

                return HealthCheckResult(
                    name=self.name, status=status, message=message, metadata=metadata
                )

            finally:
                sock.close()

        except socket.timeout:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Port {self.host}:{self.port} timed out",
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Port {self.host}:{self.port} check failed: {str(e)}",
            )


class DiskSpaceHealthCheck(HealthCheck):
    """Disk space health check."""

    def __init__(
        self,
        name: str,
        path: str = "/",
        warning_threshold: float = 80.0,
        critical_threshold: float = 90.0,
    ):
        super().__init__(name, f"Disk space health check: {path}")
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    async def check(self) -> HealthCheckResult:
        """Check disk space."""
        try:
            disk_usage = psutil.disk_usage(self.path)
            used_percent = (disk_usage.used / disk_usage.total) * 100

            metadata = {
                "path": self.path,
                "total_bytes": disk_usage.total,
                "used_bytes": disk_usage.used,
                "free_bytes": disk_usage.free,
                "used_percent": used_percent,
            }

            if used_percent >= self.critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Disk space critical: {used_percent:.1f}% used"
            elif used_percent >= self.warning_threshold:
                status = HealthStatus.WARNING
                message = f"Disk space warning: {used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space healthy: {used_percent:.1f}% used"

            return HealthCheckResult(
                name=self.name, status=status, message=message, metadata=metadata
            )

        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Disk space check failed: {str(e)}",
            )


class CustomHealthCheck(HealthCheck):
    """Custom health check with user-defined logic."""

    def __init__(
        self,
        name: str,
        check_function: Callable[[], HealthCheckResult],
        description: str = "",
        timeout: float = 10.0,
    ):
        super().__init__(name, description, timeout)
        self.check_function = check_function

    async def check(self) -> HealthCheckResult:
        """Execute custom health check function."""
        try:
            if asyncio.iscoroutinefunction(self.check_function):
                return await self.check_function()
            else:
                return self.check_function()
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Custom health check failed: {str(e)}",
            )


class HealthManager:
    """Central manager for health checks."""

    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.running = False
        self.check_interval = 30.0  # seconds
        self.task: Optional[asyncio.Task] = None
        self.callbacks: List[Callable] = []
        self.overall_status = HealthStatus.UNKNOWN

    def add_health_check(self, health_check: HealthCheck):
        """Add a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")

    def remove_health_check(self, name: str):
        """Remove a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Removed health check: {name}")

    def add_callback(self, callback: Callable):
        """Add callback for health check results."""
        self.callbacks.append(callback)

    def set_check_interval(self, interval: float):
        """Set the health check interval."""
        self.check_interval = interval

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = {}

        # Run all checks concurrently
        tasks = []
        for name, check in self.health_checks.items():
            task = asyncio.create_task(check.run_check())
            tasks.append((name, task))

        # Wait for all tasks to complete
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                logger.error(f"Error running health check {name}: {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check execution failed: {str(e)}",
                )

        # Calculate overall status
        self._calculate_overall_status(results)

        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(results, self.overall_status)
            except Exception as e:
                logger.error(f"Error in health check callback: {e}")

        return results

    def _calculate_overall_status(self, results: Dict[str, HealthCheckResult]):
        """Calculate overall health status."""
        if not results:
            self.overall_status = HealthStatus.UNKNOWN
            return

        statuses = [result.status for result in results.values()]

        if any(s == HealthStatus.CRITICAL for s in statuses):
            self.overall_status = HealthStatus.CRITICAL
        elif any(s == HealthStatus.WARNING for s in statuses):
            self.overall_status = HealthStatus.WARNING
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            self.overall_status = HealthStatus.HEALTHY
        else:
            self.overall_status = HealthStatus.UNKNOWN

    async def start(self):
        """Start the health check manager."""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._check_loop())
        logger.info("Started health check manager")

    async def stop(self):
        """Stop the health check manager."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped health check manager")

    async def _check_loop(self):
        """Main health check loop."""
        while self.running:
            try:
                await self.run_all_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.check_interval)

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        results = {}
        for name, check in self.health_checks.items():
            if check.last_result:
                results[name] = check.last_result.to_dict()

        return {
            "overall_status": self.overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": results,
            "summary": {
                "total_checks": len(self.health_checks),
                "healthy": sum(
                    1
                    for c in self.health_checks.values()
                    if c.last_result and c.last_result.is_healthy
                ),
                "warning": sum(
                    1
                    for c in self.health_checks.values()
                    if c.last_result and c.last_result.is_warning
                ),
                "critical": sum(
                    1
                    for c in self.health_checks.values()
                    if c.last_result and c.last_result.is_critical
                ),
            },
        }

    def get_health_check_history(self, name: str) -> List[Dict[str, Any]]:
        """Get history for a specific health check."""
        if name in self.health_checks:
            return [result.to_dict() for result in self.health_checks[name].history]
        return []


# Global health manager instance
health_manager = HealthManager()


def get_health_manager() -> HealthManager:
    """Get the global health manager instance."""
    return health_manager


def setup_default_health_checks():
    """Setup default health checks."""
    manager = get_health_manager()

    # System health
    system_check = SystemHealthCheck("system")
    manager.add_health_check(system_check)

    # Disk space
    disk_check = DiskSpaceHealthCheck("disk_space", "/")
    manager.add_health_check(disk_check)

    return manager


# Convenience functions
def add_http_check(name: str, url: str, **kwargs):
    """Add HTTP health check."""
    check = HTTPHealthCheck(name, url, **kwargs)
    health_manager.add_health_check(check)


def add_database_check(name: str, connection_string: str, **kwargs):
    """Add database health check."""
    check = DatabaseHealthCheck(name, connection_string, **kwargs)
    health_manager.add_health_check(check)


def add_redis_check(name: str, host: str = "localhost", port: int = 6379, **kwargs):
    """Add Redis health check."""
    check = RedisHealthCheck(name, host, port, **kwargs)
    health_manager.add_health_check(check)


def add_port_check(name: str, host: str, port: int, **kwargs):
    """Add port health check."""
    check = PortHealthCheck(name, host, port, **kwargs)
    health_manager.add_health_check(check)


def add_process_check(name: str, pid: int, **kwargs):
    """Add process health check."""
    check = ProcessHealthCheck(name, pid, **kwargs)
    health_manager.add_health_check(check)


def add_custom_check(name: str, check_function: Callable, **kwargs):
    """Add custom health check."""
    check = CustomHealthCheck(name, check_function, **kwargs)
    health_manager.add_health_check(check)


if __name__ == "__main__":
    import asyncio

    async def main():
        # Setup health checks
        manager = setup_default_health_checks()

        # Add some additional checks
        add_http_check("google", "https://www.google.com", timeout=5.0)
        add_port_check("localhost_8000", "localhost", 8000)

        # Add a custom check
        def custom_check():
            return HealthCheckResult(
                name="custom_test",
                status=HealthStatus.HEALTHY,
                message="Custom check passed",
            )

        add_custom_check("custom_test", custom_check)

        # Run checks once
        print("Running health checks...")
        results = await manager.run_all_checks()

        # Print results
        status = manager.get_health_status()
        print(f"\nOverall Status: {status['overall_status']}")
        print(f"Summary: {status['summary']}")

        for name, result in results.items():
            print(f"\n{name}: {result.status.value}")
            print(f"  Message: {result.message}")
            print(f"  Duration: {result.duration_ms:.2f}ms")

    asyncio.run(main())
