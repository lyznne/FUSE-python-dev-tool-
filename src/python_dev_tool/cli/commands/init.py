"""
FUSE - Python Dev Tool
CLI Commands - Init Command
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import toml

from rich.console import Console
from rich.prompt import Prompt, Confirm

from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.utils.file_utils import create_directory, write_file
from python_dev_tool.templates.config import get_framework_config


@dataclass
class InitOptions:
    """Options for project initialization."""

    project_path: Path
    framework: Optional[str] = None
    name: Optional[str] = None
    template: Optional[str] = None
    force: bool = False


class InitCommand:
    """Command for initializing new Python projects."""

    def __init__(
        self,
        project_path: Path,
        framework: Optional[str] = None,
        name: Optional[str] = None,
        template: Optional[str] = None,
        force: bool = False,
    ):
        self.options = InitOptions(
            project_path=project_path,
            framework=framework,
            name=name,
            template=template,
            force=force,
        )
        self.console = Console()

    def run(self) -> Dict[str, Any]:
        """Execute the init command."""
        try:
            # Validate and prepare project
            self._validate_project_path()

            # Interactive setup if needed
            if not self.options.framework:
                self.options.framework = self._prompt_framework()

            if not self.options.name:
                self.options.name = self._prompt_project_name()

            # Create project structure
            self._create_project_structure()

            # Generate configuration
            self._generate_config()

            # Create framework-specific files
            self._create_framework_files()

            # Create development files
            self._create_dev_files()

            # Create deployment files
            self._create_deployment_files()

            # Initialize git repository
            self._initialize_git()

            return {
                "success": True,
                "project_path": str(self.options.project_path),
                "framework": self.options.framework,
                "next_steps": self._get_next_steps(),
            }

        except Exception as e:
            raise DevToolError(f"Project initialization failed: {e}")

    def _validate_project_path(self) -> None:
        """Validate the project path."""
        if self.options.project_path.exists():
            if not self.options.project_path.is_dir():
                raise DevToolError(
                    f"Path exists but is not a directory: {self.options.project_path}"
                )

            # Check if directory is empty
            if any(self.options.project_path.iterdir()) and not self.options.force:
                if not Confirm.ask(
                    f"Directory {self.options.project_path} is not empty. Continue?"
                ):
                    raise DevToolError("Initialization cancelled")
        else:
            # Create directory
            self.options.project_path.mkdir(parents=True, exist_ok=True)

    def _prompt_framework(self) -> str:
        """Prompt user to select framework."""
        frameworks = {
            "1": ("django", "Django - High-level Python web framework"),
            "2": ("flask", "Flask - Lightweight WSGI web application framework"),
            "3": ("fastapi", "FastAPI - Modern, fast web framework for building APIs"),
            "4": (
                "streamlit",
                "Streamlit - App framework for machine learning and data science",
            ),
            "5": ("tornado", "Tornado - Scalable, non-blocking web server"),
            "6": ("sanic", "Sanic - Async Python web server"),
            "7": ("python", "Generic Python application"),
        }

        self.console.print("\n[bold blue]Select Framework:[/bold blue]")
        for key, (name, description) in frameworks.items():
            self.console.print(
                f"  {key}. [bold cyan]{name}[/bold cyan] - {description}"
            )

        while True:
            choice = Prompt.ask(
                "\nEnter your choice", choices=list(frameworks.keys()), default="7"
            )
            framework_name = frameworks[choice][0]

            if Confirm.ask(f"Initialize {framework_name} project?", default=True):
                return framework_name

    def _prompt_project_name(self) -> str:
        """Prompt user for project name."""
        default_name = self.options.project_path.name
        return Prompt.ask("Project name", default=default_name)

    def _create_project_structure(self) -> None:
        """Create basic project structure."""
        # Only create essential directories for the dev tool
        directories = [
            ".devtool",
            ".devtool/logs",
            ".devtool/cache",
            ".devtool/templates",
            ".devtool/scripts",
        ]

        for directory in directories:
            create_directory(self.options.project_path / directory)

    def _generate_config(self) -> None:
        """Generate project configuration."""
        config_data = {
            "project": {
                "name": self.options.name,
                "framework": self.options.framework,
                "version": "1.0.0",
                "description": f"A {self.options.framework} project",
                "root_path": str(self.options.project_path),
                "created_at": str(self._get_current_timestamp()),
            },
            "development": {
                "host": "127.0.0.1",
                "port": 8000,
                "debug": True,
                "hot_reload": True,
                "auto_restart": True,
                "watch_patterns": ["*.py", "*.html", "*.css", "*.js"],
                "ignore_patterns": ["*.pyc", "__pycache__", ".git", ".devtool"],
            },
            "ui": {
                "port": 8001,
                "theme": "dark",
                "auto_open": True,
                "show_logs": True,
                "show_metrics": True,
            },
            "monitoring": {
                "metrics": True,
                "health_checks": True,
                "performance_profiling": True,
                "log_level": "INFO",
                "max_log_size": "10MB",
                "log_retention_days": 7,
            },
            "deployment": {
                "platforms": ["railway", "render", "heroku", "docker"],
                "docker": True,
                "ci_cd": True,
                "auto_deploy": False,
            },
        }

        # Add framework-specific config
        framework_config = get_framework_config(self.options.framework)
        config_data.update(framework_config)

        # Write main config file
        config_path = self.options.project_path / ".devtool" / "config.toml"
        write_file(config_path, toml.dumps(config_data))

        # Write environment-specific configs
        dev_config = {
            **config_data,
            "development": {**config_data["development"], "debug": True},
        }
        write_file(
            self.options.project_path / ".devtool" / "development.toml",
            toml.dumps(dev_config),
        )

        prod_config = {
            **config_data,
            "development": {**config_data["development"], "debug": False},
        }
        write_file(
            self.options.project_path / ".devtool" / "production.toml",
            toml.dumps(prod_config),
        )

    def _create_framework_files(self) -> None:
        """Create framework-specific files."""
        # Create framework detection file
        detection_file = self.options.project_path / ".devtool" / "framework.json"
        detection_data = {
            "framework": self.options.framework,
            "version": "1.0.0",
            "entry_point": self._get_framework_entry_point(),
            "commands": self._get_framework_commands(),
            "dependencies": self._get_framework_dependencies(),
        }
        write_file(detection_file, json.dumps(detection_data, indent=2))

        # Create framework-specific run script
        run_script = self._generate_run_script()
        script_path = self.options.project_path / ".devtool" / "run.py"
        write_file(script_path, run_script)

        # Make script executable
        script_path.chmod(0o755)

    def _create_dev_files(self) -> None:
        """Create development files."""
        # Create requirements.txt if it doesn't exist
        requirements_path = self.options.project_path / "requirements.txt"
        if not requirements_path.exists():
            base_requirements = self._get_base_requirements()
            write_file(requirements_path, base_requirements)

        # Create .gitignore if it doesn't exist
        gitignore_path = self.options.project_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_content = self._get_gitignore_content()
            write_file(gitignore_path, gitignore_content)

        # Create development script
        dev_script = self._generate_dev_script()
        dev_script_path = self.options.project_path / ".devtool" / "dev.py"
        write_file(dev_script_path, dev_script)

        # Create health check script
        health_script = self._generate_health_check_script()
        health_script_path = self.options.project_path / ".devtool" / "health.py"
        write_file(health_script_path, health_script)

    def _create_deployment_files(self) -> None:
        """Create deployment files."""
        # Create Dockerfile
        dockerfile_content = self._generate_dockerfile()
        dockerfile_path = self.options.project_path / "Dockerfile"
        write_file(dockerfile_path, dockerfile_content)

        # Create docker-compose.yml
        docker_compose_content = self._generate_docker_compose()
        docker_compose_path = self.options.project_path / "docker-compose.yml"
        write_file(docker_compose_path, docker_compose_content)

        # Create deployment configuration
        deployment_config = {
            "platforms": {
                "railway": {
                    "enabled": True,
                    "start_command": self._get_start_command(),
                    "build_command": "pip install -r requirements.txt",
                },
                "render": {
                    "enabled": True,
                    "start_command": self._get_start_command(),
                    "build_command": "pip install -r requirements.txt",
                },
                "heroku": {
                    "enabled": True,
                    "start_command": self._get_start_command(),
                    "build_command": "pip install -r requirements.txt",
                },
            }
        }
        deployment_path = self.options.project_path / ".devtool" / "deployment.json"
        write_file(deployment_path, json.dumps(deployment_config, indent=2))

    def _initialize_git(self) -> None:
        """Initialize git repository."""
        try:
            if not (self.options.project_path / ".git").exists():
                subprocess.run(
                    ["git", "init"],
                    cwd=self.options.project_path,
                    check=True,
                    capture_output=True,
                )
                self.console.print("✓ Git repository initialized")
        except subprocess.CalledProcessError:
            self.console.print(
                "[yellow]Warning: Could not initialize git repository[/yellow]"
            )

    def _get_next_steps(self) -> List[str]:
        """Get next steps for the user."""
        steps = [
            f"cd {self.options.project_path}",
            "fuse dev  # Start development server",
            "fuse status  # Check project status",
            "fuse --help  # See all available commands",
        ]

        if self.options.framework != "python":
            steps.insert(1, f"Install {self.options.framework} dependencies")

        return steps

    def _get_framework_entry_point(self) -> str:
        """Get framework entry point."""
        entry_points = {
            "django": "manage.py",
            "flask": "app.py",
            "fastapi": "main.py",
            "streamlit": "app.py",
            "tornado": "app.py",
            "sanic": "app.py",
            "python": "main.py",
        }
        return entry_points.get(self.options.framework, "main.py")

    def _get_framework_commands(self) -> Dict[str, str]:
        """Get framework-specific commands."""
        commands = {
            "django": {
                "dev": "python manage.py runserver",
                "migrate": "python manage.py migrate",
                "collectstatic": "python manage.py collectstatic",
                "shell": "python manage.py shell",
            },
            "flask": {
                "dev": "flask run",
                "shell": "flask shell",
            },
            "fastapi": {
                "dev": "uvicorn main:app --reload",
            },
            "streamlit": {
                "dev": "streamlit run app.py",
            },
            "tornado": {
                "dev": "python app.py",
            },
            "sanic": {
                "dev": "sanic app.app",
            },
            "python": {
                "dev": "python main.py",
            },
        }
        return commands.get(self.options.framework, {"dev": "python main.py"})

    def _get_framework_dependencies(self) -> List[str]:
        """Get framework dependencies."""
        dependencies = {
            "django": ["Django>=4.2.0", "django-cors-headers"],
            "flask": ["Flask>=2.3.0", "Flask-CORS"],
            "fastapi": ["fastapi>=0.100.0", "uvicorn[standard]"],
            "streamlit": ["streamlit>=1.25.0"],
            "tornado": ["tornado>=6.3.0"],
            "sanic": ["sanic>=23.6.0"],
            "python": [],
        }
        return dependencies.get(self.options.framework, [])

    def _generate_run_script(self) -> str:
        """Generate framework-specific run script."""
        return f'''#!/usr/bin/env python3
"""
Auto-generated run script for {self.options.framework} project
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Run the {self.options.framework} application."""
    os.chdir(project_root)

    # Framework-specific run command
    framework = "{self.options.framework}"

    if framework == "django":
        subprocess.run(["python", "manage.py", "runserver", "0.0.0.0:8000"])
    elif framework == "flask":
        os.environ["FLASK_APP"] = "app.py"
        os.environ["FLASK_ENV"] = "development"
        subprocess.run(["flask", "run", "--host=0.0.0.0", "--port=8000"])
    elif framework == "fastapi":
        subprocess.run(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    elif framework == "streamlit":
        subprocess.run(["streamlit", "run", "app.py", "--server.port", "8000"])
    elif framework == "tornado":
        subprocess.run(["python", "app.py"])
    elif framework == "sanic":
        subprocess.run(["sanic", "app.app", "--host", "0.0.0.0", "--port", "8000"])
    else:
        subprocess.run(["python", "main.py"])

if __name__ == "__main__":
    main()
'''

    def _generate_dev_script(self) -> str:
        """Generate development helper script."""
        return f'''#!/usr/bin/env python3
"""
Development helper script for {self.options.name}
"""

import os
import sys
import json
import subprocess
from pathlib import Path

class DevHelper:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_path = Path(__file__).parent / "config.toml"

    def start_server(self):
        """Start the development server."""
        print(f"Starting {self.options.framework} development server...")
        subprocess.run([sys.executable, "run.py"], cwd=self.project_root.parent)

    def install_dependencies(self):
        """Install project dependencies."""
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])

    def run_tests(self):
        """Run project tests."""
        subprocess.run([sys.executable, "-m", "pytest", "tests/"])

    def check_health(self):
        """Check application health."""
        subprocess.run([sys.executable, "health.py"])

if __name__ == "__main__":
    helper = DevHelper()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if hasattr(helper, command):
            getattr(helper, command)()
        else:
            print(f"Unknown command: {{command}}")
    else:
        helper.start_server()
'''

    def _generate_health_check_script(self) -> str:
        """Generate health check script."""
        return f'''#!/usr/bin/env python3
"""
Health check script for {self.options.name}
"""

import requests
import sys
import time
from pathlib import Path

def check_health():
    """Check if the application is healthy."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✓ Application is healthy")
            return True
        else:
            print(f"✗ Application returned status {{response.status_code}}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Health check failed: {{e}}")
        return False

def wait_for_health(timeout=30):
    """Wait for the application to become healthy."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if check_health():
            return True
        time.sleep(1)

    return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "wait":
        if wait_for_health():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        if check_health():
            sys.exit(0)
        else:
            sys.exit(1)
'''

    def _get_base_requirements(self) -> str:
        """Get base requirements for the framework."""
        framework_deps = self._get_framework_dependencies()
        base_deps = [
            "python-dev-tool",  # The tool itself
            "requests",
            "python-dotenv",
        ]

        all_deps = framework_deps + base_deps
        return "\n".join(all_deps) + "\n"

    def _get_gitignore_content(self) -> str:
        """Get .gitignore content."""
        return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Dev tool specific
.devtool/logs/
.devtool/cache/
.devtool/tmp/
"""

    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile."""
        return """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python .devtool/health.py || exit 1

# Run the application
CMD ["python", ".devtool/run.py"]
"""

    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml."""
        return """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - ENVIRONMENT=development
    volumes:
      - .:/app
      - /app/.devtool/cache
    restart: unless-stopped

  devtool-ui:
    image: python-dev-tool:latest
    ports:
      - "8001:8001"
    depends_on:
      - app
    environment:
      - TARGET_APP=app:8000
    restart: unless-stopped
"""

    def _get_start_command(self) -> str:
        """Get start command for deployment."""
        commands = {
            "django": "python manage.py runserver 0.0.0.0:$PORT",
            "flask": "flask run --host=0.0.0.0 --port=$PORT",
            "fastapi": "uvicorn main:app --host 0.0.0.0 --port $PORT",
            "streamlit": "streamlit run app.py --server.port $PORT",
            "tornado": "python app.py",
            "sanic": "sanic app.app --host 0.0.0.0 --port $PORT",
            "python": "python main.py",
        }
        return commands.get(self.options.framework, "python .devtool/run.py")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    def _dict_to_toml(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to TOML format."""
        return toml.dumps(data)


def init_project(
    project_path: Path,
    framework: Optional[str] = None,
    name: Optional[str] = None,
    template: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Initialize a new project."""
    init_cmd = InitCommand(project_path, framework, name, template, force)
    return init_cmd.run()
