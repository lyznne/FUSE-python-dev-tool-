"""
FUSE - (python dev tool) - CLI Commands - Build Command
CLI - Build Command
"""

# sys imports
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# 3rd party imports
from rich.console import Console

# local imports
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.utils.file_utils import FileUtils


@dataclass
class BuildOptions:
    """Options for build command."""

    project_path: Path
    target: str = "Production"
    output_dir: Path = None
    clean: bool = False
    optimize: bool = True

class BuildCommand:
    """Command for building projects."""

    def __init__(
        self,
        project_path: Path,
        target: str = "production",
        output_dir: Optional[Path] = None,
        clean: bool = False,
        optimize: bool = True,
    ):
        self.options = BuildOptions(
            project_path=project_path,
            target=target,
            output_dir=output_dir,
            clean=clean,
            optimize=optimize,
        )
        self.console = Console()

    def run(self) -> Dict[str, Any]:
        """Run the build process."""
        try:
            # Validate project
            self._validate_project()

            # Setup output directory
            output_path = self._setup_output_dir()

            # Framework-specific build
            framework_info = self._detect_framework()
            self._run_framework_build(framework_info, output_path)

            # Common build steps
            self._copy_static_files(output_path)
            self._generate_requirements(output_path)

            # Calculate build size
            size_info = FileUtils.get_folder_size(output_path)

            return {
                "success": True,
                "output_path": str(output_path),
                "size_info": size_info,
                "framework": framework_info.name if framework_info else None,
            }

        except Exception as e:
            raise DevToolError(f"Build failed: {e}")

    def _validate_project(self) -> None:
        """Validate project structure."""
        if not self.options.project_path.exists():
            raise DevToolError("Project directory does not exist")

        # Check for required files
        required_files = ["pyproject.toml", "requirements.txt"]
        for f in required_files:
            if not (self.options.project_path / f).exists():
                raise DevToolError(f"Missing required file: {f}")

    def _setup_output_dir(self) -> Path:
        """Setup output directory."""
        output_path = self.options.output_dir or self.options.project_path / "dist"

        if self.options.clean and output_path.exists():
            shutil.rmtree(output_path)

        output_path.mkdir(exist_ok=True, parents=True)
        return output_path

    def _detect_framework(self):
        """Detect project framework."""
        detector = FrameworkDetector()
        return detector.detect_framework(self.options.project_path)

    def _run_framework_build(self, framework_info, output_path: Path) -> None:
        """Run framework-specific build steps."""
        if not framework_info:
            self.console.print(
                "[yellow]No framework detected, skipping framework build[/yellow]"
            )
            return

        self.console.print(f"[blue]Running {framework_info.name} build...[/blue]")

        # Framework-specific build logic would go here
        # For example, collectstatic for Django, etc.

        self.console.print(f"[green]✓ {framework_info.name} build complete[/green]")

    def _copy_static_files(self, output_path: Path) -> None:
        """Copy static files to output directory."""
        static_dir = self.options.project_path / "static"
        if static_dir.exists():
            self.console.print("[blue]Copying static files...[/blue]")
            shutil.copytree(static_dir, output_path / "static")
            self.console.print("[green]✓ Static files copied[/green]")

    def _generate_requirements(self, output_path: Path) -> None:
        """Generate requirements file."""
        self.console.print("[blue]Generating requirements...[/blue]")

        # In a real implementation, this would analyze dependencies
        requirements_file = self.options.project_path / "requirements.txt"
        if requirements_file.exists():
            shutil.copy(requirements_file, output_path / "requirements.txt")

        self.console.print("[green]✓ Requirements generated[/green]")
