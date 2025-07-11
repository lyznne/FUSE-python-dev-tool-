"""
Metrics Collection Module
Collects and manages performance metrics for the development tool
"""

import asyncio
import psutil
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import json
import os

# Internal imports
from python_dev_tool.core.logger import DevToolLogger
from python_dev_tool.core.events import EventEmitter


@dataclass
class MetricPoint:
    """Individual metric data point"""

    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags,
        }


@dataclass
class MetricSeries:
    """Time series of metric points"""

    name: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    unit: str = ""
    description: str = ""

    def add_point(self, value: float, tags: Dict[str, str] = None) -> None:
        """Add a new metric point"""
        self.points.append(
            MetricPoint(timestamp=datetime.now(), value=value, tags=tags or {})
        )

    def get_latest(self) -> Optional[MetricPoint]:
        """Get the latest metric point"""
        return self.points[-1] if self.points else None

    def get_average(self, duration: timedelta = None) -> float:
        """Get average value over specified duration"""
        if not self.points:
            return 0.0

        if duration is None:
            values = [p.value for p in self.points]
        else:
            cutoff_time = datetime.now() - duration
            values = [p.value for p in self.points if p.timestamp >= cutoff_time]

        return sum(values) / len(values) if values else 0.0

    def get_max(self, duration: timedelta = None) -> float:
        """Get maximum value over specified duration"""
        if not self.points:
            return 0.0

        if duration is None:
            values = [p.value for p in self.points]
        else:
            cutoff_time = datetime.now() - duration
            values = [p.value for p in self.points if p.timestamp >= cutoff_time]

        return max(values) if values else 0.0

    def get_min(self, duration: timedelta = None) -> float:
        """Get minimum value over specified duration"""
        if not self.points:
            return 0.0

        if duration is None:
            values = [p.value for p in self.points]
        else:
            cutoff_time = datetime.now() - duration
            values = [p.value for p in self.points if p.timestamp >= cutoff_time]

        return min(values) if values else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "unit": self.unit,
            "description": self.description,
            "points": [p.to_dict() for p in self.points],
            "latest": self.get_latest().to_dict() if self.get_latest() else None,
            "avg_5min": self.get_average(timedelta(minutes=5)),
            "avg_1hour": self.get_average(timedelta(hours=1)),
            "max_5min": self.get_max(timedelta(minutes=5)),
            "min_5min": self.get_min(timedelta(minutes=5)),
        }


class SystemMetrics:
    """System-level metrics collector"""

    def __init__(self):
        self.process = psutil.Process()
        self.boot_time = datetime.fromtimestamp(psutil.boot_time())

    def get_cpu_metrics(self) -> Dict[str, float]:
        """Get CPU metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "load_avg_1": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0,
            "load_avg_5": os.getloadavg()[1] if hasattr(os, "getloadavg") else 0,
            "load_avg_15": os.getloadavg()[2] if hasattr(os, "getloadavg") else 0,
        }

    def get_memory_metrics(self) -> Dict[str, float]:
        """Get memory metrics"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "memory_total": memory.total,
            "memory_available": memory.available,
            "memory_percent": memory.percent,
            "memory_used": memory.used,
            "memory_free": memory.free,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }

    def get_disk_metrics(self) -> Dict[str, float]:
        """Get disk metrics"""
        disk_usage = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()

        metrics = {
            "disk_total": disk_usage.total,
            "disk_used": disk_usage.used,
            "disk_free": disk_usage.free,
            "disk_percent": disk_usage.percent,
        }

        if disk_io:
            metrics.update(
                {
                    "disk_read_bytes": disk_io.read_bytes,
                    "disk_write_bytes": disk_io.write_bytes,
                    "disk_read_count": disk_io.read_count,
                    "disk_write_count": disk_io.write_count,
                }
            )

        return metrics

    def get_network_metrics(self) -> Dict[str, float]:
        """Get network metrics"""
        net_io = psutil.net_io_counters()

        if not net_io:
            return {}

        return {
            "network_bytes_sent": net_io.bytes_sent,
            "network_bytes_recv": net_io.bytes_recv,
            "network_packets_sent": net_io.packets_sent,
            "network_packets_recv": net_io.packets_recv,
            "network_errin": net_io.errin,
            "network_errout": net_io.errout,
            "network_dropin": net_io.dropin,
            "network_dropout": net_io.dropout,
        }

    def get_process_metrics(self) -> Dict[str, float]:
        """Get process-specific metrics"""
        try:
            with self.process.oneshot():
                return {
                    "process_cpu_percent": self.process.cpu_percent(),
                    "process_memory_percent": self.process.memory_percent(),
                    "process_memory_rss": self.process.memory_info().rss,
                    "process_memory_vms": self.process.memory_info().vms,
                    "process_num_threads": self.process.num_threads(),
                    "process_num_fds": self.process.num_fds()
                    if hasattr(self.process, "num_fds")
                    else 0,
                    "process_create_time": self.process.create_time(),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {}

    def get_python_metrics(self) -> Dict[str, float]:
        """Get Python-specific metrics"""
        import gc
        import sys

        return {
            "python_version": float(
                f"{sys.version_info.major}.{sys.version_info.minor}"
            ),
            "python_objects": len(gc.get_objects()),
            "python_gc_collections": sum(
                gc.get_stats()[i]["collections"] for i in range(3)
            ),
            "python_gc_collected": sum(
                gc.get_stats()[i]["collected"] for i in range(3)
            ),
            "python_gc_uncollectable": sum(
                gc.get_stats()[i]["uncollectable"] for i in range(3)
            ),
            "python_refcount": sys.gettotalrefcount()
            if hasattr(sys, "gettotalrefcount")
            else 0,
        }


class ApplicationMetrics:
    """Application-specific metrics collector"""

    def __init__(self):
        self.startup_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)
        self.active_connections = 0
        self.hot_reloads = 0
        self.file_changes = 0

    def record_request(self, response_time: float, error: bool = False) -> None:
        """Record a request with its response time"""
        self.request_count += 1
        if error:
            self.error_count += 1
        self.response_times.append(response_time)

    def record_connection(self, connected: bool = True) -> None:
        """Record connection change"""
        if connected:
            self.active_connections += 1
        else:
            self.active_connections = max(0, self.active_connections - 1)

    def record_hot_reload(self) -> None:
        """Record hot reload event"""
        self.hot_reloads += 1

    def record_file_change(self) -> None:
        """Record file change event"""
        self.file_changes += 1

    def get_metrics(self) -> Dict[str, float]:
        """Get all application metrics"""
        uptime = (datetime.now() - self.startup_time).total_seconds()

        metrics = {
            "app_uptime": uptime,
            "app_request_count": self.request_count,
            "app_error_count": self.error_count,
            "app_error_rate": (self.error_count / self.request_count)
            if self.request_count > 0
            else 0,
            "app_active_connections": self.active_connections,
            "app_hot_reloads": self.hot_reloads,
            "app_file_changes": self.file_changes,
            "app_requests_per_second": self.request_count / uptime if uptime > 0 else 0,
        }

        if self.response_times:
            metrics.update(
                {
                    "app_avg_response_time": sum(self.response_times)
                    / len(self.response_times),
                    "app_max_response_time": max(self.response_times),
                    "app_min_response_time": min(self.response_times),
                }
            )

        return metrics


class MetricsCollector:
    """Main metrics collector that orchestrates all metric collection"""

    def __init__(
        self,
        logger: Optional[DevToolLogger] = None,
        event_emitter: Optional[EventEmitter] = None,
    ):
        self.logger = logger
        self.event_emitter = event_emitter
        self.metrics: Dict[str, MetricSeries] = {}
        self.system_metrics = SystemMetrics()
        self.app_metrics = ApplicationMetrics()
        self.collectors: List[Callable] = []
        self.collection_interval = 5  # seconds
        self.running = False
        self.collection_task: Optional[asyncio.Task] = None
        self.last_collection_time = None
        self.collection_errors = 0

        # Initialize metric series
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize all metric series"""
        metric_definitions = [
            # System metrics
            ("cpu_percent", "%", "CPU usage percentage"),
            ("memory_percent", "%", "Memory usage percentage"),
            ("disk_percent", "%", "Disk usage percentage"),
            ("load_avg_1", "", "1-minute load average"),
            ("network_bytes_sent", "bytes", "Network bytes sent"),
            ("network_bytes_recv", "bytes", "Network bytes received"),
            # Process metrics
            ("process_cpu_percent", "%", "Process CPU usage"),
            ("process_memory_percent", "%", "Process memory usage"),
            ("process_memory_rss", "bytes", "Process RSS memory"),
            ("process_num_threads", "", "Number of threads"),
            # Python metrics
            ("python_objects", "", "Python objects count"),
            ("python_gc_collections", "", "GC collections count"),
            # Application metrics
            ("app_uptime", "seconds", "Application uptime"),
            ("app_request_count", "", "Total requests"),
            ("app_error_count", "", "Total errors"),
            ("app_error_rate", "%", "Error rate"),
            ("app_active_connections", "", "Active connections"),
            ("app_avg_response_time", "ms", "Average response time"),
            ("app_hot_reloads", "", "Hot reloads count"),
            ("app_file_changes", "", "File changes count"),
        ]

        for name, unit, description in metric_definitions:
            self.metrics[name] = MetricSeries(name, unit=unit, description=description)

    def add_collector(self, collector: Callable) -> None:
        """Add a custom metrics collector"""
        self.collectors.append(collector)

    def remove_collector(self, collector: Callable) -> None:
        """Remove a custom metrics collector"""
        if collector in self.collectors:
            self.collectors.remove(collector)

    def record_metric(
        self, name: str, value: float, tags: Dict[str, str] = None
    ) -> None:
        """Record a metric value"""
        if name not in self.metrics:
            self.metrics[name] = MetricSeries(name)

        self.metrics[name].add_point(value, tags)

        if self.event_emitter:
            self.event_emitter.emit(
                "metric_recorded", {"name": name, "value": value, "tags": tags or {}}
            )

    async def collect(self) -> Dict[str, Any]:
        """Collect all metrics"""
        try:
            start_time = time.time()
            all_metrics = {}

            # Collect system metrics
            try:
                system_metrics = {
                    **self.system_metrics.get_cpu_metrics(),
                    **self.system_metrics.get_memory_metrics(),
                    **self.system_metrics.get_disk_metrics(),
                    **self.system_metrics.get_network_metrics(),
                    **self.system_metrics.get_process_metrics(),
                    **self.system_metrics.get_python_metrics(),
                }
                all_metrics.update(system_metrics)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to collect system metrics: {e}")
                self.collection_errors += 1

            # Collect application metrics
            try:
                app_metrics = self.app_metrics.get_metrics()
                all_metrics.update(app_metrics)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to collect application metrics: {e}")
                self.collection_errors += 1

            # Collect custom metrics
            for collector in self.collectors:
                try:
                    custom_metrics = collector()
                    if isinstance(custom_metrics, dict):
                        all_metrics.update(custom_metrics)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Custom collector failed: {e}")
                    self.collection_errors += 1

            # Record all metrics
            for name, value in all_metrics.items():
                if isinstance(value, (int, float)):
                    self.record_metric(name, float(value))

            # Record collection performance
            collection_time = time.time() - start_time
            self.record_metric("metrics_collection_time", collection_time * 1000)  # ms
            self.record_metric("metrics_collection_errors", self.collection_errors)

            self.last_collection_time = datetime.now()

            # Emit metrics updated event
            if self.event_emitter:
                self.event_emitter.emit(
                    "metrics_updated",
                    {
                        "metrics": all_metrics,
                        "collection_time": collection_time,
                        "timestamp": self.last_collection_time.isoformat(),
                    },
                )

            return all_metrics

        except Exception as e:
            if self.logger:
                self.logger.error(f"Metrics collection failed: {e}")
            self.collection_errors += 1
            return {}

    async def start(self) -> None:
        """Start periodic metrics collection"""
        if self.running:
            return

        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())

        if self.logger:
            self.logger.info(
                f"Metrics collection started (interval: {self.collection_interval}s)"
            )

    async def stop(self) -> None:
        """Stop metrics collection"""
        self.running = False

        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

        if self.logger:
            self.logger.info("Metrics collection stopped")

    async def _collection_loop(self) -> None:
        """Main collection loop"""
        while self.running:
            try:
                await self.collect()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(self.collection_interval)

    def get_metric_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series by name"""
        return self.metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics as dictionary"""
        return {name: series.to_dict() for name, series in self.metrics.items()}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        summary = {
            "total_metrics": len(self.metrics),
            "collection_errors": self.collection_errors,
            "last_collection": self.last_collection_time.isoformat()
            if self.last_collection_time
            else None,
            "running": self.running,
            "collection_interval": self.collection_interval,
        }

        # Add key metrics
        key_metrics = [
            "cpu_percent",
            "memory_percent",
            "app_uptime",
            "app_request_count",
        ]
        for metric_name in key_metrics:
            if metric_name in self.metrics:
                latest = self.metrics[metric_name].get_latest()
                if latest:
                    summary[f"latest_{metric_name}"] = latest.value

        return summary

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        if format.lower() == "json":
            return json.dumps(self.get_all_metrics(), indent=2, default=str)
        elif format.lower() == "prometheus":
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        for name, series in self.metrics.items():
            if not series.points:
                continue

            latest = series.get_latest()
            if latest:
                # Add help and type
                lines.append(f"# HELP {name} {series.description}")
                lines.append(f"# TYPE {name} gauge")

                # Add metric with tags
                tags_str = ""
                if latest.tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in latest.tags.items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"

                lines.append(f"{name}{tags_str} {latest.value}")

        return "\n".join(lines)

    # Application-specific methods
    def record_request(self, response_time: float, error: bool = False) -> None:
        """Record an HTTP request"""
        self.app_metrics.record_request(response_time, error)

    def record_connection(self, connected: bool = True) -> None:
        """Record a connection change"""
        self.app_metrics.record_connection(connected)

    def record_hot_reload(self) -> None:
        """Record a hot reload event"""
        self.app_metrics.record_hot_reload()

    def record_file_change(self) -> None:
        """Record a file change event"""
        self.app_metrics.record_file_change()
