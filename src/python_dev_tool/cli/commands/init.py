"""
FUSE - Python Dev Tool
CLI Commands - Init Command
"""

import os
import subprocess
import sys
from unittest import result
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from django import template
import toml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from python_dev_tool.cli.validation import ProjectValidator
from python_dev_tool.core import template_manager
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.framework_detector import FrameworkDetector
from python_dev_tool.core.template_manager import TemplateManager


@dataclass
class InitOptions:
    """Options for project initialization."""

    project_path: Path
    framework: Optional[str] = None
    name: Optional[str] = None
    template: Optional[str] = None
    force: bool = False
    verbose: bool = False
    install_deps: bool = True
    python_executable: Optional[str] = None


class InitCommand:
    """Command for initializing new Python projects with FUSE dev tools."""

    SUPPORTED_FRAMEWORKS = {
        "django": "Django - High-level Python web framework",
        "flask": "Flask - Lightweight WSGI web application framework",
        "fastapi": "FastAPI - Modern, fast web framework for building APIs",
        "streamlit": "Streamlit - App framework for ML and data science",
        "tornado": "Tornado - Scalable, non-blocking web server",
        "sanic": "Sanic - Async Python web server",
        "python": "Generic Python application",
    }

    def __init__(self, options: InitOptions):
        self.options = options
        self.console = Console()
        self.detector = FrameworkDetector()
        self.validator = ProjectValidator()
        self.template_manager = TemplateManager()
        self.next_steps: List[str] = []

    def run(self) -> Dict[str, Any]:
        """Execute the init command with interactive steps."""
        try:
            # Step 1: Validate and analyze project
            self.console.print("[cyan]Analyzing project structure...[/cyan]")
            project_info = self._analyze_project()
            self.console.print("[green]✓ Project analysis complete[/green]")

            # Step 2: Handle project directory setup
            self.console.print("[cyan]Setting up project directory...[/cyan]")
            self._setup_project_directory(project_info)
            self.console.print("[green]✓ Project directory setup complete[/green]")

            # Step 3: Interactive configuration
            self._interactive_setup()

            # Step 4: Create FUSE configuration and project files
            self.console.print("[cyan]Creating project files...[/cyan]")
            self._create_project_files()
            self.console.print("[green]✓ Project files created[/green]")

            # Step 5: Setup virtual environment and dependencies
            self.console.print("[cyan]Setting up environment...[/cyan]")
            self._setup_environment(project_info)
            self.console.print("[green]✓ Environment setup complete[/green]")

            # Step 6: Framework-specific setup
            self.console.print(f"[cyan]Setting up {self.options.framework}...[/cyan]")
            self._setup_framework()
            self.console.print(
                f"[green]✓ {self.options.framework} setup complete[/green]"
            )

            return self._generate_success_response()

        except Exception as e:
            raise DevToolError(f"Project initialization failed: {e}")

    def _analyze_project(self) -> Dict[str, Any]:
        """Analyze the project directory and detect existing setup."""
        project_path = self.options.project_path

        if self.options.verbose:
            self.console.print(f"[cyan]Analyzing project at: {project_path}[/cyan]")

        # check first the current dir ( "." )


        # Check if directory exists and is empty
        is_empty = not project_path.exists() or not any(project_path.iterdir())

        # Check for existing FUSE configuration
        fuse_config_paths = [
            project_path / ".fuse" / "config.toml",
            project_path / "fuse.toml",
        ]

        existing_config = None
        for config_path in fuse_config_paths:
            if config_path.exists():
                existing_config = config_path
                break

        # Detect existing framework
        detected_framework = None
        if not is_empty:
            detected_framework = self.detector.detect_framework(project_path)

        # Check for virtual environment
        has_venv = any(
            [
                (project_path / "venv").exists(),
                (project_path / ".venv").exists(),
                (project_path / ".env").exists(),
                # os.environ.get("VIRTUAL_ENV") is not None,  # TODO: Fix this -- when there is already activated venv
            ]
        )

        return {
            "is_empty": is_empty,
            "is_existing": not is_empty,
            "existing_config": existing_config,
            "detected_framework": detected_framework,
            "has_venv": has_venv,
            "files_count": len(list(project_path.rglob("*")))
            if project_path.exists()
            else 0,
        }

    def _setup_project_directory(self, project_info: Dict[str, Any]) -> None:
        """Handle project directory setup based on analysis."""
        if not self.options.name:
            self.options.name = self._prompt_project_name()

        # Create project directory with project name
        new_project_path = self.options.project_path / self.options.name

        if (
            new_project_path.exists()
            and any(new_project_path.iterdir())
            and not self.options.force
        ):
            self.console.print(
                Panel(
                    f"[yellow]✗ Directory {new_project_path} already exists and is not empty.[/yellow]\n"
                    "Use --force to overwrite.",
                    title="Directory Conflict",
                    border_style="yellow",
                )
            )
            raise DevToolError(
                "Directory exists and is not empty. Use --force to overwrite."
            )

        new_project_path.mkdir(parents=True, exist_ok=True)
        self.options.project_path = new_project_path
        self.console.print(
            f"[green]✓ Created project directory:[/green] [bold]{self.options.project_path}[/bold]"
        )

        # Handle existing project
        if project_info["is_existing"] and project_info["existing_config"]:
            self.console.print(
                Panel(
                    f"[yellow]✗ FUSE configuration found at:[/yellow]\n"
                    f"[bold]{project_info['existing_config']}[/bold]\n\n"
                    f"This project is already initialized with FUSE.",
                    title="Existing FUSE Project",
                    border_style="yellow",
                )
            )
            if not self.options.force and not Confirm.ask(
                "Do you want to reinitialize the project?"
            ):
                raise DevToolError("Initialization cancelled by user")

        # Auto-detect framework if not specified
        if not self.options.framework and project_info["detected_framework"]:
            self.options.framework = project_info["detected_framework"]
            self.console.print(
                f"[green]✓ Detected framework:[/green] [bold]{self.options.framework}[/bold]"
            )

    def _interactive_setup(self) -> None:
        """Interactive setup for missing configuration."""
        needs_interaction = not self.options.framework or not self.options.name

        if not needs_interaction:
            return

        self.console.print(
            Panel(
                "[bold blue]🔧 Project Configuration[/bold blue]", border_style="blue"
            )
        )

        # Framework selection
        if not self.options.framework:
            self._prompt_framework_selection()

        # Project name # XXX already handled in _setup_project_directory
        # if not self.options.name:
        #     self.options.name = self._prompt_project_name()

        # Show configuration summary
        self._show_configuration_summary()

    def _prompt_framework_selection(self) -> None:
        """Interactive framework selection."""
        self.console.print("\n[bold]📚 Available Frameworks:[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Framework", style="green", width=12)
        table.add_column("Description", style="white")

        framework_list = list(self.SUPPORTED_FRAMEWORKS.items())
        for i, (framework, description) in enumerate(framework_list, 1):
            table.add_row(str(i), framework.title(), description)

        self.console.print(table)

        while True:
            try:
                choice = Prompt.ask(
                    "\n🎯 Select framework",
                    choices=[str(i) for i in range(1, len(framework_list) + 1)],
                    default="7",  # Default to Python
                    console=self.console,
                )

                selected_framework = framework_list[int(choice) - 1][0]

                if Confirm.ask(
                    f"Initialize [bold green]{selected_framework}[/bold green] project?",
                    default=True,
                    console=self.console,
                ):
                    self.options.framework = selected_framework
                    break

            except (ValueError, IndexError):
                self.console.print("[red]Invalid selection. Please try again.[/red]")

    def _prompt_project_name(self) -> str:
        """Prompt for project name."""
        default_name = self.options.project_path.name
        return Prompt.ask(
            "📝 Project name",
            default=default_name,
            show_default=True,
            console=self.console,
        )

    def _show_configuration_summary(self) -> None:
        """Show configuration summary."""
        summary_table = Table(title="📋 Configuration Summary", show_header=False)
        summary_table.add_column("Setting", style="cyan", width=15)
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Project Path", str(self.options.project_path))
        summary_table.add_row("Project Name", self.options.name)
        summary_table.add_row("Framework", self.options.framework.title())

        self.console.print(summary_table)

        if not Confirm.ask(
            "\n✓ Proceed with this configuration?",
            default=True,
            console=self.console,
        ):
            raise DevToolError("Configuration cancelled by user")

    def _create_project_files(self) -> None:
        """Create all project files including FUSE config, README, etc."""
        # Create .fuse directory and config
        self.console.print("[cyan]Creating FUSE configuration...[/cyan]")
        self._create_fuse_config()
        self.console.print("[green]✓ FUSE configuration created[/green]")

        # Create README.md
        self._create_readme_file()
        self.console.print("[green]✓ Created README.md[/green]")

        # Initialize .git
        self._init_git()

        # Create .gitignore if not exists
        if not (self.options.project_path / ".gitignore").exists():
            self._create_gitignore()
            self.console.print("[green]✓ Created .gitignore[/green]")

    def _get_current_year(self) -> str:
        """Get current year."""
        from datetime import datetime

        return str(datetime.now().year)

    def _init_git(self):
        """Initialize git repository with proper error handling."""
        try:
            self.console.print("[cyan]Initializing git repository...[/cyan]")

            # Check if git is available
            git_check = self.template_manager.run_command(
                ["git", "--version"], silent=True
            )

            if not git_check.success:
                self.console.print(
                    "[yellow]⚠️ Git is not installed or not available in PATH[/yellow]"
                )
                self.next_steps.append(
                    "Install Git and initialize repository manually: git init"
                )
                return

            # Check if already a git repository
            git_dir = self.options.project_path / ".git"
            if git_dir.exists():
                self.console.print(
                    "[cyan]Git repository already exists, skipping initialization[/cyan]"
                )
                return

            # Initialize git repository
            result = self.template_manager.run_command(
                ["git", "init"],
                cwd=self.options.project_path,
                silent=not self.options.verbose,
            )

            if result.success:
                self.console.print("[green]✓ Git repository initialized[/green]")

                # Try to make initial commit if there are files
                if any(self.options.project_path.iterdir()):
                    self._make_initial_commit()
            else:
                self.console.print(
                    f"[yellow]⚠️ Failed to initialize git repository: {result.error}[/yellow]"
                )
                self.next_steps.append("Initialize git repository manually: git init")

        except Exception as e:
            self.console.print(
                f"[yellow]⚠️ Error during git initialization: {str(e)}[/yellow]"
            )
            self.next_steps.append("Initialize git repository manually: git init")

    def _make_initial_commit(self):
        """Make an initial commit with project files."""
        try:
            # Add all files
            add_result = self.template_manager.run_command(
                ["git", "add", "."],
                cwd=self.options.project_path,
                silent=not self.options.verbose,
            )

            if add_result.success:
                # Make initial commit
                commit_result = self.template_manager.run_command(
                    ["git", "commit", "-m", f"Initial commit for {self.options.name}"],
                    cwd=self.options.project_path,
                    silent=not self.options.verbose,
                )

                if commit_result.success:
                    self.console.print("[green]✓ Made initial git commit[/green]")
                else:
                    # Don't treat commit failure as critical
                    if self.options.verbose:
                        self.console.print(
                            f"[yellow]Initial commit failed: {commit_result.error}[/yellow]"
                        )
                    self.next_steps.append(
                        "Make initial commit: git add . && git commit -m 'Initial commit'"
                    )
            else:
                if self.options.verbose:
                    self.console.print(
                        f"[yellow]Git add failed: {add_result.error}[/yellow]"
                    )

        except Exception as e:
            if self.options.verbose:
                self.console.print(
                    f"[yellow]Error making initial commit: {str(e)}[/yellow]"
                )

    def _create_fuse_config(self) -> None:
        """Create FUSE configuration files."""
        fuse_dir = self.options.project_path / ".fuse"
        fuse_dir.mkdir(exist_ok=True)

        # Create logs directory
        logs_dir = fuse_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Get framework info from detector
        framework_info = self.detector.get_framework_details(self.options.framework)
        commands = (
            framework_info.commands
            if framework_info and framework_info.commands
            else {"dev": self._get_dev_command()}
        )
        commands.update(
            {
                "test": "python -m pytest",
                "lint": "python -m flake8 .",
                "format": "python -m black .",
            }
        )

        logging_config = {
            "dir": str(logs_dir.relative_to(self.options.project_path)),
            "level": "INFO",
            "format": "default",
        }

        # Prepare template context
        context = {
            "project_name": self.options.name,
            "framework": self.options.framework,
            "framework_version": framework_info.version
            if framework_info
            else "unknown",
            "python_version": self.options.python_executable or "3.8",
            "version": "1.0.0",
            "host": "127.0.0.1",
            "port": 8000,
            # "deployment_platforms": toml.dumps(
            #     {"platforms": ["docker", "railway", "render"]}
            # ).strip(),
            "commands": toml.dumps(commands).strip(),
            "environment": toml.dumps({}).strip(),
            "plugins": toml.dumps([]).strip(),
            "debug": str(True).lower(),   # "true"
            "testing": str(False).lower(), # "false"
            "year": self._get_current_year(),
            "logging": logging_config,
            "logging_dir": logging_config["dir"],
            "logging_level": logging_config["level"],
            "logging_format": logging_config["format"],
        }

        # Create config.toml from template
        self.template_manager.create_from_template(
            "fuse/config.toml.template",
            fuse_dir / "config.toml",
            context=context,
            overwrite=self.options.force,
        )

        # Create state.db and logs directory
        (fuse_dir / "state.db").touch()
        (fuse_dir / "logs").mkdir(exist_ok=True)

    def _create_readme_file(self) -> None:
        """Create README.md file for the project."""
        framework_info = self.detector.get_framework_details(self.options.framework)

        context = {
            "project_name": self.options.name,
            "framework": self.options.framework,
            "framework_title": self.options.framework.title(),
            "python_version": self.options.python_executable or "3.8+",
            "year": self._get_current_year(),
            "author": os.getenv("USER", "Unknown"),
            "project_dir_name": self.options.project_path.name,
            "main_file": self._get_main_file(),
            "activation_command": self._get_activation_command(),
        }

        self.template_manager.create_from_template(
            "fuse/README.md.template",
            self.options.project_path / "README.md",
            context=context,
            overwrite=self.options.force,
        )

    def _create_gitignore(self) -> None:
        """Create .gitignore file."""
        self.template_manager.create_from_template(
            "fuse/gitignore.template",
            self.options.project_path / ".gitignore",
            {"project_name": self.options.name},
            overwrite=self.options.force,
        )

    def _get_dev_command(self) -> str:
        """Get the appropriate dev command based on framework."""
        commands = {
            "django": "python manage.py runserver 0.0.0.1:8000",
            "flask": "python app.py",
            "fastapi": "uvicorn main:app --reload --host 0.0.0.0 --port 8000",
            "streamlit": "streamlit run app.py --server.port 8000",
            "python": "python main.py",
        }
        return commands.get(self.options.framework, "python main.py")

    def _get_main_file(self) -> str:
        """Get the main file name based on framework."""
        files = {
            "django": "manage.py",
            "flask": "app.py",
            "fastapi": "main.py",
            "streamlit": "app.py",
            "python": "main.py",
        }
        return files.get(self.options.framework, "main.py")

    def _get_activation_command(self) -> str:
        """Get the appropriate virtualenv activation command."""
        if sys.platform == "win32":
            return ".venv\\Scripts\\activate"
        return "source .venv/bin/activate"

    def _setup_environment(self, project_info: Dict[str, Any]) -> None:
        """Setup virtual environment and install dependencies."""
        venv_path = self.options.project_path / ".venv"

        # Initialize venv tracking variables
        self.venv_python = None
        self.venv_pip = None

        if project_info["has_venv"] and venv_path.exists():
            self.console.print(
                "[cyan]Found existing virtual environment, verifying...[/cyan]"
            )
            if self._activate_venv(venv_path):
                self.console.print(
                    "[green]✓ Virtual environment verified and ready[/green]"
                )
            else:
                self.console.print(
                    "[yellow]⚠️ Existing virtual environment has issues[/yellow]"
                )
                if Confirm.ask(
                    "Create a new virtual environment?",
                    default=True,
                    console=self.console,
                ):
                    # Remove old venv and create new one
                    import shutil

                    shutil.rmtree(venv_path, ignore_errors=True)
                    self._create_virtualenv()
                else:
                    self.next_steps.append(
                        f"Fix virtual environment or activate manually: {self._get_activation_command()}"
                    )
                    return
        else:
            self.console.print("[cyan]Creating virtual environment...[/cyan]")
            self._create_virtualenv()

        if self.options.install_deps:
            self.console.print("[cyan]Installing dependencies...[/cyan]")
            self._create_requirements_file()
            self._install_dependencies(venv_path)
        else:
            self.console.print(
                "[cyan]Skipping dependency installation (--no-install-deps)[/cyan]"
            )

    def _activate_venv(self, venv_path: Path) -> bool:
        """Attempt to activate the virtual environment."""
        try:
            if sys.platform.startswith("win"):  # TODO: Be more flexible
                # Windows paths
                python_exe = venv_path / "Scripts" / "python.exe"
                pip_exe = venv_path / "Scripts" / "pip.exe"
            else:
                # Unix-like systems
                python_exe = venv_path / "bin" / "python"
                pip_exe = venv_path / "bin" / "pip"

            if not python_exe.exists():
                self.console.print(
                    f"[yellow]Python executable not found: {python_exe}[/yellow]"
                )
                return False

            # Test if virtual environment is functional by running python --version
            result = self.template_manager.run_command(
                [str(python_exe), "--version"],
                cwd=self.options.project_path,
                silent=not self.options.verbose,
            )

            if result.success:
                # store thepaths for later use in dependency installation
                self.venv_python = str(python_exe)
                self.venv_pip = str(pip_exe)
                return True
            else:
                return False

        except Exception as e:
            self.console.print(
                f"[yellow]⚠️ Failed to verfy virtual environment: {str(e)}[/yellow]"
            )

    def _create_virtualenv(self) -> None:
        """Create a Python virtual environment."""
        venv_path = self.options.project_path / ".venv"
        try:
            venv.create(venv_path, with_pip=True)
            # verify the virtual env
            if not self._activate_venv(venv_path):
                raise DevToolError("Failed to create virtual environment")

        except Exception as e:
            raise DevToolError(f"Failed to create virtual environment: {str(e)}")

    def _create_requirements_file(self) -> None:
        """Create requirements.txt with framework dependencies."""
        requirements_path = self.options.project_path / "requirements.txt"

        if requirements_path.exists() and not self.options.force:
            self.console.print("[yellow]✗ requirements.txt already exists[/yellow]")
            return

        # Prioritize dependencies from FrameworkDetector
        framework_info = self.detector.get_framework_details(self.options.framework)
        dependencies = (
            framework_info.dependencies
            if framework_info and framework_info.dependencies
            else self._get_framework_dependencies()
        )

        with open(requirements_path, "w") as f:
            f.write("\n".join(dependencies))
            f.write("\n")
        self.console.print("[green]✓ Created requirements.txt[/green]")

    def _install_dependencies(self, venv_path: Path) -> None:
        """Install project dependencies using the virtual environment."""
        requirements_path = self.options.project_path / "requirements.txt"

        if not requirements_path.exists():
            self.console.print(
                "[yellow]No requirements.txt found, skipping dependency installation[/yellow]"
            )
            return

        try:
            # Use the stored venv python/pip paths if available, otherwise construct them
            if hasattr(self, "venv_pip") and Path(self.venv_pip).exists():
                pip_cmd = [self.venv_pip, "install", "-r", str(requirements_path)]
            else:
                # Fallback to constructing the path
                if sys.platform.startswith("win"):
                    pip_exe = venv_path / "Scripts" / "pip.exe"
                else:
                    pip_exe = venv_path / "bin" / "pip"
                pip_cmd = [str(pip_exe), "install", "-r", str(requirements_path)]

            self.console.print(
                "[cyan]⏳ Installing dependencies — this might take a moment...[/cyan]"
            )

            result = self.template_manager.run_command(
                pip_cmd,
                cwd=self.options.project_path,
                silent=not self.options.verbose,
            )

            if result.success:
                self.console.print(
                    "[green]✓ Dependencies installed successfully[/green]"
                )
            else:
                self.console.print(
                    f"[yellow]⚠️ Failed to install dependencies: {result.error}[/yellow]"
                )
                self.next_steps.append(
                    f"Install dependencies manually: pip install -r {requirements_path}"
                )

        except Exception as e:
            self.console.print(
                f"[yellow]⚠️ Failed to install dependencies: {str(e)}[/yellow]"
            )
            self.next_steps.append(
                f"Install dependencies manually: pip install -r {requirements_path}"
            )

    def _setup_framework(self) -> None:
        """Run framework-specific initialization."""
        self.console.print(f"[cyan]Setting up {self.options.framework}...[/cyan]")

        if self.options.framework == "python":
            self._setup_python_project()
        elif self.options.framework == "django":
            self._setup_django_project()
        elif self.options.framework == "flask":
            self._setup_flask_project()
        elif self.options.framework == "fastapi":
            self._setup_fastapi_project()
        elif self.options.framework == "streamlit":
            self._setup_streamlit_project()
        else:
            self.console.print(
                f"[yellow]Framework '{self.options.framework}' setup not implemented yet[/yellow]"
            )

        self.console.print(f"[green]✓ {self.options.framework} setup complete[/green]")

    def _setup_python_project(self) -> None:
        """Setup generic Python project."""
        main_file = self.options.project_path / "main.py"

        context = {
            "project_name": self.options.name,
            "framework": self.options.framework,
            "year": self._get_current_year(),
        }
        if not main_file.exists():
            self.template_manager.create_from_template(
                "python/main.py.template",
                main_file,
                context=context,
                overwrite=self.options.force,
            )

    def _setup_django_project(self) -> None:
        """Setup Django project."""
        if not self._check_command_available("django-admin"):
            # Install Django first
            result = self.template_manager.run_command(
                [sys.executable, "-m", "pip", "install", "django"],
                silent=not self.options.verbose,
            )
            if not result.success:
                raise DevToolError("Failed to install Django")

        # Create Django project
        result = self.template_manager.run_command(
            ["django-admin", "startproject", self.options.name, "."],
            cwd=self.options.project_path,
            silent=not self.options.verbose,
        )
        if not result.success:
            raise DevToolError("Failed to create Django project")

    def _setup_flask_project(self) -> None:
        """Setup Flask project."""
        app_file = self.options.project_path / "app.py"

        context = {
            "project_name": self.options.name,
            "author": os.getenv("USER", "Unknown"),
            "framework": self.options.framework,
            "year": self._get_current_year(),
            "host": "0.0.0.0",
            "port": "5000",
            "python_version": self.options.python_executable or "3.8+",
        }
        if not app_file.exists():
            self.template_manager.create_from_template(
                "flask/app.py.template",
                app_file,
                context=context,
                overwrite=self.options.force,
            )

    def _setup_fastapi_project(self) -> None:
        """Setup FastAPI project."""
        main_file = self.options.project_path / "main.py"
        context = {
            "project_name": self.options.name,
            "framework": self.options.framework,
            "year": self._get_current_year(),
            "python_version": self.options.python_executable or "3.8+",
            "host": "0.0.0.0",
            "port": "8000",
        }
        if not main_file.exists():
            self.template_manager.create_from_template(
                "fastapi/main.py.template",
                main_file,
                context=context,
                overwrite=self.options.force,
            )

    def _setup_streamlit_project(self) -> None:
        """Setup Streamlit project."""
        app_file = self.options.project_path / "app.py"
        context = {
            "project_name": self.options.name,
            "framework": self.options.framework,
            "year": self._get_current_year(),
        }
        if not app_file.exists():
            self.template_manager.create_from_template(
                "streamlit/app.py.template",
                app_file,
                context=context,
                overwrite=self.options.force,
            )

    def _check_command_available(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            result = subprocess.run(
                ["which", command]
                if not sys.platform == "win32"
                else ["where", command],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_framework_dependencies(self) -> List[str]:
        """Get framework-specific dependencies."""
        dependencies_map = {
            "django": ["Django>=4.0", "python-dotenv"],
            "flask": ["Flask>=2.0", "python-dotenv"],
            "fastapi": ["fastapi>=0.75", "uvicorn[standard]", "python-dotenv"],
            "streamlit": ["streamlit~=1.30.0", "python-dotenv"],
            "tornado": ["tornado>=6.1", "python-dotenv"],
            "sanic": ["sanic>=21.12", "python-dotenv"],
            "python": ["python-dotenv"],
        }
        return dependencies_map.get(self.options.framework, ["python-dotenv"])

    def _generate_success_response(self) -> Dict[str, Any]:
        """Generate success response with next steps."""
        # Add standard next steps
        self.next_steps.extend(
            [
                f"cd {self.options.project_path}",
                self._get_activation_command(),
                "fuse dev",
            ]
        )

        return {
            "success": True,
            "project_path": str(self.options.project_path),
            "framework": self.options.framework,
            "name": self.options.name,
            "next_steps": self.next_steps,
        }


# Main function for CLI integration
def init_project(
    project_path: Path,
    framework: Optional[str] = None,
    name: Optional[str] = None,
    template: Optional[str] = None,
    force: bool = False,
    verbose: bool = False,
    install_deps: bool = True,
    python_executable: Optional[str] = None,
) -> Dict[str, Any]:
    """Initialize a new project with FUSE development tools."""
    options = InitOptions(
        project_path=project_path,
        framework=framework,
        name=name,
        template=template,
        force=force,
        verbose=verbose,
        install_deps=install_deps,
        python_executable=python_executable,
    )
    init_cmd = InitCommand(options)
    return init_cmd.run()
