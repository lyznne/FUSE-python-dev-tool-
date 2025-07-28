"""
FUSE (Python Development Tool) - Template Manager
Handles dynamic file creation from templates with data injection
"""

# sys imports
from dataclasses import dataclass
import os
import shutil
import sys
import venv
import subprocess

from pathlib import Path
from typing import Optional, Any, Dict, List, Union
from string import Template

from rich.console import Console
from rich.panel import Panel


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    output: str
    error: Optional[str] = None
    return_code: Optional[int] = None


class TemplateManager:
    """Manages templates and dynamic file creation with command execution."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the template manager."""
        self.console = Console()

        if templates_dir is None:
            current_dir = Path(__file__).parent
            self.templates_dir = (current_dir / ".." / "templates").resolve()
        else:
            self.templates_dir = templates_dir

        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def create_from_template(
        self,
        template_name: str,
        destination: Path,
        context: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Create a file from a template with context data.

        Args:
            template_name: Name of template file (relative to templates_dir)
            destination: Path to create the new file
            context: Dictionary of template variables
            overwrite: Whether to overwrite existing files

        Returns:
            bool: True if file was created successfully
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            self.console.print(f"[red]Template not found: {template_path}[/red]")
            return False

        if destination.exists() and not overwrite:
            self.console.print(f"[yellow]File already exists: {destination}[/yellow]")
            return False

        try:
            with open(template_path, "r") as f:
                template_content = f.read()

            template = Template(template_content)
            rendered = template.safe_substitute(context)

            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "w") as f:
                f.write(rendered)

            self.console.print(
                f"[green]Created file from template: {destination}[/green]"
            )
            return True

        except Exception as e:
            self.console.print(f"[red]Error creating file from template: {e}[/red]")
            return False

    def run_command(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        silent: bool = True,
    ) -> CommandResult:
        """
        Run a shell command securely with optional environment and working directory.

        Args:
            command: Command to run (string or list of args)
            cwd: Working directory to run command in
            env: Environment variables to use
            silent: Whether to suppress command output

        Returns:
            CommandResult: Result of command execution
        """
        if isinstance(command, str):
            command = command.split()

        try:
            result = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                env=env if env else None,
                capture_output=True,
                text=True,
                check=False,
                shell=False  # prevent shell injection
            )

            if not silent:
                if result.stdout:
                    self.console.print(result.stdout)
                if result.stderr:
                    self.console.print(f"[red]{result.stderr}[/red]")

            return CommandResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode,
            )

        except Exception as e:
            return CommandResult(success=False, output="", error=str(e), return_code=1)

    def create_virtualenv(
        self,
        venv_path: Path,
        python_executable: Optional[str] = None,
        silent: bool = True,
    ) -> bool:
        """
        Create a Python virtual environment.

        Args:
            venv_path: Path to create virtual environment
            python_executable: Specific Python interpreter to use
            silent: Whether to suppress output

        Returns:
            bool: True if virtualenv was created successfully
        """
        if venv_path.exists():
            if not silent:
                self.console.print(
                    f"[yellow]Virtualenv already exists: {venv_path}[/yellow]"
                )
            return False

        try:
            args = [str(venv_path)]
            if python_executable:
                args.insert(0, f"--python={python_executable}")

            result = self.run_command(
                [sys.executable, "-m", "venv"] + args, silent=silent
            )

            if result.success:
                if not silent:
                    self.console.print(
                        f"[green]Created virtualenv: {venv_path}[/green]"
                    )
                return True
            else:
                self.console.print(
                    f"[red]Failed to create virtualenv: {result.error}[/red]"
                )
                return False

        except Exception as e:
            self.console.print(f"[red]Error creating virtualenv: {e}[/red]")
            return False

    def install_dependencies(
        self,
        requirements_path: Path,
        venv_path: Optional[Path] = None,
        silent: bool = True,
    ) -> bool:
        """
        Install Python dependencies from requirements file.

        Args:
            requirements_path: Path to requirements.txt
            venv_path: Path to virtual environment (None for system Python)
            silent: Whether to suppress output

        Returns:
            bool: True if dependencies were installed successfully
        """
        if not requirements_path.exists():
            self.console.print(
                f"[red]Requirements file not found: {requirements_path}[/red]"
            )
            return False

        pip_cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]

        if venv_path:
            pip_executable = venv_path / "bin" / "pip"
            if sys.platform == "win32":
                pip_executable = venv_path / "Scripts" / "pip.exe"

            if not pip_executable.exists():
                self.console.print(
                    f"[red]Pip not found in virtualenv: {pip_executable}[/red]"
                )
                return False

            pip_cmd = [str(pip_executable), "install", "-r", str(requirements_path)]

        result = self.run_command(pip_cmd, silent=silent)

        if result.success:
            if not silent:
                self.console.print("[green]Successfully installed dependencies[/green]")
            return True
        else:
            self.console.print(
                f"[red]Failed to install dependencies: {result.error}[/red]"
            )
            return False

    def copy_template_directory(self, template_dir: Path, output_dir: Path, data: Dict[str, Any]) -> None:

        """
        Recursively copy a template directory and apply data substitutions.

        Args:
            template_dir: Source template directory
            output_dir: Destination directory
            data: Data for template substitutions
        """
        src_dir  =  self.templates_dir / template_dir

        if not src_dir.exists():
            raise FileNotFoundError(f"Template directory {template_dir} not found")

        for src_path in src_dir.rglob("*"):
            if src_path.is_file():
                rel_path = src_path.relative_to(self.templates_dir)
                dest_path = output_dir / rel_path
                if src_path.suffix == '.template':
                    # Process template files
                    self.create_from_template(str(rel_path), dest_path.with_suffix(''), data)
                else:
                    # Copy non-template files
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    self.console.print(f"[green]✓ Copied {dest_path}[/green]")


    def create_project_structure(
        self,
        project_path: Path,
        framework: str,
        context: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Create standard project structure with framework-specific files.

        Args:
            project_path: Root directory of project
            framework: Framework name (django, flask, etc.)
            context: Template variables
            overwrite: Whether to overwrite existing files

        Returns:
            bool: True if structure was created successfully
        """
        try:
            # Create .fuse directory and config
            fuse_dir = project_path / ".fuse"
            fuse_dir.mkdir(exist_ok=True)

            # Create config.toml from template
            config_success = self.create_from_template(
                "fuse/config.toml.template",
                fuse_dir / "config.toml",
                context,
                overwrite,
            )

            if not config_success:
                return False

            # Create framework-specific files
            framework_template_dir = Path(framework)
            template_files = [
                ("common/gitignore.template", project_path / ".gitignore"),
                (f"{framework}/app.py.template", project_path / "app.py"),
            ]

            for template, dest in template_files:
                template_path = self.templates_dir / template
                if template_path.exists():
                    if not self.create_from_template(
                        template, dest, context, overwrite
                    ):
                        return False

            return True

        except Exception as e:
            self.console.print(f"[red]Error creating project structure: {e}[/red]")
            return False
