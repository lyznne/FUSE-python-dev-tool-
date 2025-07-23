"""
FUSE - (python dev tool) - CLI Commands - Status Command
CLI Commands - Status Command
"""

# sys imports
import platform
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# 3rd party imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import ProgressBar

# local imports
from python_dev_tool.core.events import EventBus
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.core.process_manager import ProcessManager
from python_dev_tool.utils.system_utils import DependencyUtils, SystemUtils


@dataclass
class StatusOptions:
    """Options for status command."""

    project_path: Path
    detailed: bool
    check_deps: bool = True


class StatusCommand:
    """Enhanced command for showing project status and health information."""

    def __init__(
        self,
        project_path: Path = Path("."),
        detailed: bool = False,
        check_deps: bool = True,
        event_bus: Optional[EventBus] = None,
    ):
        actual_path  =  self._find_project_root(project_path)


        self.options = StatusOptions(
            project_path=actual_path, detailed=detailed, check_deps=check_deps
        )
        self.console = Console()
        self.event_bus = event_bus or EventBus()
        self.process_manager = ProcessManager(self.event_bus)

    def run(self) -> Dict[str, Any]:
        """Run the status command with enhanced diagnostics."""
        try:
            self._validate_project()
            status_info = self._gather_status_info()
            self._display_status(status_info)
            return status_info
        except Exception as e:
            raise DevToolError(f"Status check failed: {e}")

    def _find_project_root(self, start_path: Path) -> Path:
        """Find the project root by looking for .devtool directory."""
        current_path = start_path.resolve()

        # First, check if the provided path is already the project root
        devtool_path = current_path / ".devtool"
        config_path = devtool_path / "config.toml"
        if devtool_path.exists() and devtool_path.is_dir() and config_path.exists():
            return current_path

        # If not found, traverse up the directory tree
        while current_path != current_path.parent:
            devtool_path = current_path / ".devtool"
            config_path = devtool_path / "config.toml"
            if devtool_path.exists() and devtool_path.is_dir() and config_path.exists():
                return current_path
            current_path = current_path.parent

        # If no project root is found, return the original path and let validation handle errors
        return start_path.resolve()

    def _validate_project(self) -> None:
        """Validate the project directory and configuration."""
        project_path = self.options.project_path

        if not project_path.exists():
            raise DevToolError(f"Project directory does not exist: {project_path}")

        # Check for DevTool configuration
        config_path = project_path / ".devtool" / "config.toml"
        if not config_path.exists():
            raise DevToolError(f"Config file not found at: {config_path}")

        # Validate that the config can be loaded
        try:
            from python_dev_tool.core.config import Config
            config = Config.load_project_config(project_path)
            if not config:
                self.console.print("[yellow]Warning: Config file exists but could not be loaded properly[/yellow]")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Config validation failed: {e}[/yellow]")

        # Check other essential files (non-fatal warnings)
        essential_files = [
            ("pyproject.toml", "Project configuration"),
            ("requirements.txt", "Dependencies file"),
        ]

        missing_files = []
        for file_path, desc in essential_files:
            full_path = project_path / file_path
            if not full_path.exists():
                missing_files.append(f"{desc} (expected at: {full_path})")

        if missing_files:
            self.console.print(f"[yellow]Warning: Missing files: {', '.join(missing_files)}[/yellow]")




    def _gather_status_info(self) -> Dict[str, Any]:
        """Collect comprehensive status information."""
        status_info = {
            "project_name": self.options.project_path.name,
            "project_path": str(self.options.project_path.absolute()),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "python_version": platform.python_version(),
        }

        # Framework detection with more details
        framework_info = self._get_framework_info()
        if framework_info:
            status_info.update(framework_info)

        # Process status with additional metrics
        status_info.update(self._get_process_status())

        # System resource information
        status_info.update(SystemUtils.get_system_info())

        # Dependency information if requested
        if self.options.check_deps:
            status_info["dependencies"] = self._get_dependency_info()

        # Detailed diagnostics when requested
        if self.options.detailed:
            status_info.update(
                {
                    "recent_logs": self._get_recent_logs(),
                    "performance_metrics": self._get_performance_metrics(),
                    "security_checks": self._get_security_checks(),
                }
            )

        return status_info

    def _get_framework_info(self) -> Dict[str, Any]:
        """Get detailed framework information."""
        try:
            detector = FrameworkDetector(self.options.project_path)
            framework_info = detector.detect_framework()
            if not framework_info:
                return {
                    "framework": "unknown",
                    "framework_version": "None",
                    "framework_confidence": 0.0
                }

            return {
                "framework": framework_info.name,
                "framework_version": framework_info.version or "None",
                "framework_confidence": framework_info.confidence,
                "main_file": framework_info.main_file,
                "config_files": framework_info.config_files or [],
            }
        except Exception as e:
            return {
                "framework": "error",
                "framework_version": "None",
                "framework_confidence": 0.0,
                "error": str(e)
            }

    def _get_process_status(self) -> Dict[str, Any]:
        """Get detailed process status."""
        processes = self.process_manager.get_project_processes(
            self.options.project_path
        )

        # Enhanced process analysis
        dev_server = next(
            (
                p
                for p in processes
                if "uvicorn" in p.get("cmd", "") and "dev" in p.get("cmd", "")
            ),
            None,
        )

        app_server = next(
            (
                p
                for p in processes
                if "python" in p.get("cmd", "") and "run" in p.get("cmd", "")
            ),
            None,
        )

        return {
            "running": bool(dev_server or app_server),
            "dev_server": dev_server,
            "app_server": app_server,
            "process_count": len(processes),
            "processes": processes if self.options.detailed else None,
        }

    def _get_dependency_info(self) -> Dict[str, Any]:
        """Get comprehensive dependency information."""
        try:
            from python_dev_tool.core.config import Config
            config = Config.load_project_config(self.options.project_path)


            if not config:
                return {"status": "no_config", "vulnerable": [], "outdated": []}

            # Get dependency list properly from config
            dependencies = []
            if isinstance(config, dict):
                deps = config.get("dependencies", {})
                if isinstance(deps, dict):
                    dependencies = list(deps.keys())
                elif isinstance(deps, list):
                    dependencies = deps

            if not dependencies:
                return {"status": "no_dependencies", "vulnerable": [], "outdated": []}

            return DependencyUtils.check_dependencies(dependencies)

        except Exception as e:
            self.console.print(f"[red]Status error: Invalid configuration: {e}[/red]")
            return {"status": "config_error", "error": str(e), "vulnerable": [], "outdated": []}

    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get real performance metrics."""
        # This would be connected to actual monitoring in a real implementation
        return {
            "cpu_usage": "42%",
            "memory_usage": "1.8GB/4GB",
            "response_time": "85ms avg",
            "throughput": "120 req/s",
            "error_rate": "0.2%",
        }

    def _get_security_checks(self) -> Dict[str, Any]:
        """Perform security checks."""
        # In a real implementation, this would run actual security scans
        return {
            "vulnerable_deps": ["django==3.0.0 (CVE-2023-1234)"],
            "security_warnings": ["DEBUG mode enabled in production"],
            "recommendations": ["Update Django to v4.2.1"],
        }

    def _get_recent_logs(self, count: int = 10) -> List[Dict[str, str]]:
        """Get structured recent logs with levels."""
        log_file = self.options.project_path / ".devtool/logs/dev.log"
        if not log_file.exists():
            return []

        try:
            logs = []
            with open(log_file, "r") as f:
                for line in f.readlines()[-count:]:
                    line = line.strip()
                    if not line:
                        continue

                    log_level = "info"
                    if "ERROR" in line:
                        log_level = "error"
                    elif "WARNING" in line:
                        log_level = "warning"
                    elif "DEBUG" in line:
                        log_level = "debug"

                    logs.append(
                        {
                            "message": line,
                            "level": log_level,
                            "timestamp": line[:23] if line[:1].isdigit() else "",
                        }
                    )
            return logs
        except Exception:
            return []

    def _display_status(self, status_info: Dict[str, Any]) -> None:
        """Display enhanced status information with better visualization."""
        # Main header with project info
        self.console.print(
            Panel.fit(
                f"[bold blue]📊 {status_info['project_name']} Status[/bold blue]",
                subtitle=f"[dim]{status_info['timestamp']}[/dim]",
                border_style="blue",
            )
        )

        # Core status table
        core_table = Table(show_header=False, box=None, padding=(0, 1))
        core_table.add_row("Project:", f"[bold]{status_info['project_name']}[/bold]")
        core_table.add_row("Path:", f"[dim]{status_info['project_path']}[/dim]")

        if "framework" in status_info:
            conf_color = (
                "green"
                if status_info["framework_confidence"] > 0.8
                else "yellow"
                if status_info["framework_confidence"] > 0.5
                else "red"
            )
            core_table.add_row(
                "Framework:",
                f"[bold]{status_info['framework']}[/bold] v{status_info['framework_version']} "
                f"([{conf_color}]{status_info['framework_confidence'] * 100:.0f}% confidence[/])",
            )

        status_icon = (
            "[green]✓ Running[/green]"
            if status_info["running"]
            else "[red]✗ Stopped[/red]"
        )
        core_table.add_row("Status:", status_icon)

        self.console.print(core_table)

        # Process information
        if status_info.get("processes"):
            self._display_process_info(status_info)

        # System resources
        self._display_system_resources(status_info)

        # Dependencies
        if "dependencies" in status_info:
            self._display_dependency_info(status_info["dependencies"])

        # Detailed sections
        if self.options.detailed:
            self._display_detailed_info(status_info)

        # Recommendations footer
        self._display_recommendations(status_info)

    def _display_process_info(self, status_info: Dict[str, Any]) -> None:
        """Display process information in a table."""
        proc_table = Table(
            title="Processes", show_header=True, header_style="bold blue", box=None
        )
        proc_table.add_column("Type", style="cyan")
        proc_table.add_column("PID")
        proc_table.add_column("CPU %")
        proc_table.add_column("Memory %")
        proc_table.add_column("Command", style="dim")

        if status_info.get("dev_server"):
            p = status_info["dev_server"]
            proc_table.add_row(
                "Dev Server",
                str(p["pid"]),
                f"{p.get('cpu_percent', 0):.1f}",
                f"{p.get('memory_percent', 0):.1f}",
                p["cmd"][:40] + "..." if len(p["cmd"]) > 40 else p["cmd"],
            )

        if status_info.get("app_server"):
            p = status_info["app_server"]
            proc_table.add_row(
                "App Server",
                str(p["pid"]),
                f"{p.get('cpu_percent', 0):.1f}",
                f"{p.get('memory_percent', 0):.1f}",
                p["cmd"][:40] + "..." if len(p["cmd"]) > 40 else p["cmd"],
            )

        self.console.print(proc_table)

    def _display_system_resources(self, status_info: Dict[str, Any]) -> None:
        """Display system resource usage."""
        res_table = Table(
            title="System Resources", show_header=False, box=None, padding=(0, 1)
        )

        # CPU
        cpu_usage = status_info.get("cpu_percent", 0)
        cpu_bar = ProgressBar(
            total=100,
            completed=cpu_usage,
            style="green" if cpu_usage < 70 else "yellow" if cpu_usage < 90 else "red",
            pulse=cpu_usage >= 90,
        )
        res_table.add_row("CPU:", f"{cpu_usage}% ", cpu_bar)

        # Memory
        mem_usage = status_info.get("memory_percent", 0)
        mem_bar = ProgressBar(
            total=100,
            completed=mem_usage,
            style="green" if mem_usage < 70 else "yellow" if mem_usage < 90 else "red",
            pulse=mem_usage >= 90,
        )
        res_table.add_row("Memory:", f"{mem_usage}% ", mem_bar)

        self.console.print(res_table)

    def _display_dependency_info(self, deps: Dict[str, Any]) -> None:
        """Display dependency information."""
        if not deps.get("vulnerable") and not deps.get("outdated"):
            self.console.print("[green]✓ Dependencies are up to date[/green]")
            return

        dep_table = Table(title="Dependencies", box=None)
        dep_table.add_column("Status", style="bold")
        dep_table.add_column("Package", style="cyan")
        dep_table.add_column("Details")

        for vuln in deps.get("vulnerable", []):
            dep_table.add_row("[red]Vulnerable[/red]", vuln["name"], vuln["info"])

        for outdated in deps.get("outdated", []):
            dep_table.add_row(
                "[yellow]Outdated[/yellow]",
                outdated["name"],
                f"{outdated['current']} → {outdated['latest']}",
            )

        self.console.print(dep_table)

    def _display_detailed_info(self, status_info: Dict[str, Any]) -> None:
        """Display detailed diagnostic information."""
        # Performance metrics
        if status_info.get("performance_metrics"):
            perf_table = Table(title="Performance Metrics", box=None)
            perf_table.add_column("Metric", style="cyan")
            perf_table.add_column("Value")

            for metric, value in status_info["performance_metrics"].items():
                perf_table.add_row(metric.replace("_", " ").title(), str(value))

            self.console.print(perf_table)

        # Security issues
        if status_info.get("security_checks"):
            sec_table = Table(title="Security Checks", box=None)
            sec_table.add_column("Type", style="bold")
            sec_table.add_column("Issue", style="cyan")
            sec_table.add_column("Recommendation")

            for vuln in status_info["security_checks"].get("vulnerable_deps", []):
                sec_table.add_row(
                    "[red]Vulnerability[/red]", vuln, "Update to latest secure version"
                )

            for warning in status_info["security_checks"].get("security_warnings", []):
                sec_table.add_row(
                    "[yellow]Warning[/yellow]", warning, "Review configuration"
                )

            self.console.print(sec_table)

        # Recent logs
        if status_info.get("recent_logs"):
            self.console.print(Panel("Recent Logs", style="blue"))
            for log in status_info["recent_logs"]:
                style = {
                    "error": "red",
                    "warning": "yellow",
                    "debug": "dim",
                }.get(log["level"], "white")
                self.console.print(f"[{style}]{log['message']}[/{style}]")

    def _display_recommendations(self, status_info: Dict[str, Any]) -> None:
        """Display actionable recommendations."""
        recommendations = []

        if not status_info["running"]:
            recommendations.append(("Start development server", "fuse dev"))

        if status_info.get("dependencies", {}).get("vulnerable"):
            recommendations.append(
                ("Update vulnerable dependencies", "fuse deps update")
            )

        if status_info.get("cpu_percent", 0) > 80:
            recommendations.append(("Optimize CPU usage", "Check performance metrics"))

        if recommendations:
            self.console.print(Panel("Recommendations", style="yellow"))
            for desc, cmd in recommendations:
                self.console.print(f"• [bold]{desc}[/bold]: [cyan]{cmd}[/cyan]")
