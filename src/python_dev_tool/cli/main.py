#!/usr/bin/env python3

"""
FUSE - (python dev tool) - CLI Main Entry Point
CLI - Terminal UI
"""

# sys imports
import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional

# 3rd party imports
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# local imports
from python_dev_tool.core.config import Config
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.utils.validation import validate_project_path
from python_dev_tool.cli.theme import DEV_THEME


# Initiate console
console = Console(theme=DEV_THEME, highlight=False)
error_console = Console(stderr=True, style="bold red")


# typer app
app = typer.Typer(
    name="fuse",
    help="🚀 Python Development Tool - Supercharge your Python development workflow",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",  # or markdown
    context_settings={"help_option_names": ["-h", "--help"]},
)

# version info
__version__ = "0.0.1"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def version_callback(value: bool) -> None:
    """Display version information and exit."""
    if value:
        console.print(
            f"[bold blue]Python Dev Tool[/bold blue] version [bold green]{__version__}[/bold green]"
        )
        console.print("🚀 Supercharge your Python development workflow")
        raise typer.Exit()


def verbose_callback(value: bool) -> None:
    """Enable verbose mode."""
    if value:
        import logging

        logging.basicConfig(level=logging.DEBUG)


# default message when no subcommand is provided
def show_welcome():
    """Show welcome screen message and help information."""
    console.print(
        Panel.fit(
            "[bold blue]👋 Welcome to the Python Dev Tool![/bold blue]",
            style="blue",
        )
    )
    console.print(
        "[bold yellow]🚀 Supercharge your Python development workflow[/bold yellow]"
    )
    console.print(
        "A comprehensive development tool that provides:\n"
        " • Live development server with hot reload\n"
        " • Beautiful web-based debugging UI\n"
        " • Multi-framework support (Django, Flask, FastAPI, etc.)\n"
        " • One-click deployment to multiple platforms\n"
        " • Real-time logs and performance monitoring\n"
    )
    console.print(
        "[bold yellow]📚 Documentation: https://python-dev-tool.readthedocs.io[/bold yellow]"
    )
    console.print(
        "[bold yellow]💬 Community: https://github.com/lyznne/python-dev-tool/discussions[/bold yellow]"
    )
    console.print("\n[bold yellow]💡 Next steps:[/bold yellow]")
    console.print(
        " • Run [bold]fuse init[/bold] to create a new project\n"
        " • Run [bold]fuse dev[/bold] to start the development server\n"
        " • Run [bold]fuse build[/bold] to build your project\n"
        " • Run [bold]fuse deploy[/bold] to deploy your project\n"
        " • Run [bold]fuse status[/bold] to check the status of your project\n"
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version information and exit.",
        callback=version_callback,
        is_eager=True,
        # is_flag=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose mode.",
        callback=verbose_callback,
        is_eager=True,
        # is_flag=True,
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.INFO,
        "--log-level",
        "-l",
        help="Set the log level.",
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
) -> None:
    """🚀 Python Development Tool - Supercharge your Python development workflow
    A comprehensive development tool that provides:
    • Live development server with hot reload
    • Beautiful web-based debugging UI
    • Multi-framework support (Django, Flask, FastAPI, etc.)
    • One-click deployment to multiple platforms
    • Real-time logs and performance monitoring
    """

    # set global config if provided
    if config_file:
        Config.set_config_file(config_file)

    if ctx.invoked_subcommand is None:
        # Show welcome message if no subcommand is provided
        show_welcome()


# Command: init
@app.command()
def init(
    project_path: Path = typer.Argument(
        Path.cwd(), help="Path to initialize the project"
    ),
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        "-f",
        help="Framework to use (django, flask, fastapi, streamlit, tornado, sanic, python)",
        rich_help_panel="Project Configuration",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Project name (defaults to directory name)",
        rich_help_panel="Project Configuration",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Project template to use (future feature)",
        rich_help_panel="Project Configuration",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force initialization even if directory is not empty",
        rich_help_panel="Advanced Options",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output for debugging",
        rich_help_panel="Advanced Options",
    ),
    install_deps: bool = typer.Option(
        True,
        "--install-deps/--no-install-deps",
        help="Install Initial dependencies of the project.",
        rich_help_panel="Advanced options",
    ),
    python_executable: Optional[str] = typer.Option(
        None,
        "--python-bin",
        help="Python executable to use. Uses the defoult of Your System.",
    ),
) -> None:
    """
    🎯 Initialize a new Python project with FUSE development tools.

    Creates a comprehensive development environment with:

    • 🔧 Framework-specific configuration and setup
    • 🐍 Virtual environment management
    • 📦 Dependency management (requirements.txt)
    • 🔥 Hot-reload development server
    • 🌐 Web-based development dashboard
    • 🐳 Docker configuration templates
    • 📊 Built-in monitoring and logging
    • 🚀 One-click deployment configurations

    Examples:

        # Initialize in current directory (interactive)
        fuse init

        # Initialize Django project
        fuse init --framework django --name mysite

        # Initialize FastAPI project in specific directory
        fuse init /path/to/project --framework fastapi

        # Force initialization in non-empty directory
        fuse init --force --framework flask

        # Disable installation of dependencies
        fuse init --no-install-deps

        # Pass Custom python executable
        fuse init --python-bin /bin/script/python3.15
    """
    try:
        # Validate project path
        validate_project_path(project_path)

        # Display initialization banner
        console.print(
            Panel.fit(
                "[bold blue]🎯 FUSE - Python Development Tool[/bold blue]\n"
                "[dim]Initializing your development environment...[/dim]",
                style="blue",
                padding=(1, 2),
            )
        )

        # Run initialization
        # import init command
        from python_dev_tool.cli.commands.init import init_project

        result = init_project(
            project_path=project_path,
            framework=framework,
            name=name,
            template=template,
            force=force,
            verbose=verbose,
            install_deps=install_deps,
            python_executable=python_executable,
        )

        # Display success message
        console.print(
            f"\n[bold green]🎉 Project initialized successfully![/bold green]"
        )
        console.print(f"📁 Location: [bold cyan]{result['project_path']}[/bold cyan]")
        console.print(
            f"🔧 Framework: [bold magenta]{result['framework'].title()}[/bold magenta]"
        )
        console.print(f"📝 Name: [bold yellow]{result['name']}[/bold yellow]")

        # Display next steps
        if result.get("next_steps"):
            console.print(
                Panel(
                    "\n".join(
                        [
                            f"[bold cyan]{i + 1}.[/bold cyan] {step}"
                            for i, step in enumerate(result["next_steps"])
                        ]
                    ),
                    title="[bold green]🚀 Next Steps[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

        # Additional helpful information
        console.print(
            f"\n[dim]💡 Pro tip: Run [bold]fuse --help[/bold] to see all available commands[/dim]"
        )

    except DevToolError as e:
        error_console.print(
            Panel(
                f"[bold red]❌ Initialization Error[/bold red]\n\n{str(e)}",
                border_style="red",
                padding=(1, 2),
            )
        )
        if verbose:
            error_console.print_exception()
        raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print(f"\n[yellow]⚠️  Initialization cancelled by user[/yellow]")
        raise typer.Exit(130)

    except Exception as e:
        error_console.print(
            Panel(
                f"[bold red]💥 Unexpected Error[/bold red]\n\n{str(e)}",
                border_style="red",
                padding=(1, 2),
            )
        )
        if verbose:
            error_console.print_exception()
        raise typer.Exit(1)


# command: dev
@app.command()
def dev(
    project_path: Path = typer.Argument(Path.cwd(), help="Path to the project"),
    port: int = typer.Option(
        8000, "--port", "-p", help="Port to run the development server on"
    ),
    host: str = typer.Option(
        "127.0.0.1", "--host", "-h", help="Host to run the development server on"
    ),
    debug: bool = typer.Option(
        True, "--debug/--no-debug", help="Enable/disable debugging"
    ),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", help="Enable/disable hot reload"
    ),
    ui_port: int = typer.Option(
        8001, "--ui-port", help="Port to run the debugging UI on"
    ),
    open_browser: bool = typer.Option(
        True, "--open-browser/--no-open-browser", help="Open the browser after starting"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    🔥 Start the development server with live reload and debugging UI

    Features:
    • Live development server with hot reload
    • Real-time web-based debugging interface
    • Log streaming and error highlighting
    • Performance monitoring
    • Command execution interface
    """

    try:
        # validate project path
        validate_project_path(project_path)

        # show dev server banner
        console.print(
            Panel.fit(
                "[bold blue]🔥 Starting Development Server[/bold blue]",
                style="green",
            )
        )

        # create dev server info table
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_row("Project:", f"[bold]{project_path.name}[/bold]")
        info_table.add_row("Server:", f"[bold]http://{host}:{port}[/bold]")
        info_table.add_row("Debug UI:", f"[bold]http://{host}:{ui_port}[/bold]")
        info_table.add_row(
            "Reload:", f"[bold]{'Enabled' if reload else 'Disabled'}[/bold]"
        )
        info_table.add_row(
            "🐛 Debug:", f"[bold]{'Enabled' if debug else 'Disabled'}[/bold]"
        )

        console.print(info_table)
        console.print()

        # start dev server
        from python_dev_tool.cli.commands.dev import DevCommand

        dev_cmd = DevCommand(
            project_path=project_path,
            port=port,
            host=host,
            debug=debug,
            reload=reload,
            ui_port=ui_port,
            open_browser=open_browser,
        )

        # Run dev server - this will block
        asyncio.run(dev_cmd.run())

    except KeyboardInterrupt:
        console.print("\n[yellow]Development server stopped by user.[/yellow]")
        raise typer.Exit(1)
    except DevToolError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Command: build
@app.command()
def build(
    project_path: Path = typer.Argument(Path.cwd(), help="Path to the project"),
    target: str = typer.Option("Production", "--target", "-t", help="Build target"),
    output_dir: Path = typer.Option(
        None, "--output-dir", "-o", help="Output directory"
    ),
    clean: bool = typer.Option(
        False, "--clean/--no-clean", help="Clean output directory before build"
    ),
    optimize: bool = typer.Option(
        True,
        "--optimize/--no-optimize",
        help="Enable asset optimization / Build optimizations",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    🏗️ Build the project for deployment

    Features:
    • Multi-target builds (development, staging, production)
    • Asset optimization and minification
    • Docker image building
    • Static file collection
    • Dependency bundling
    """

    try:
        validate_project_path(project_path)

        console.print(
            Panel.fit(
                "[bold blue]🏗️ Building Project[/bold blue]",
                style="blue",
            )
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[bold blue]Building project...", total=None)

            from python_dev_tool.cli.commands.build import BuildCommand

            build_cmd = BuildCommand(
                project_path=project_path,
                target=target,
                output_dir=output_dir,
                clean=clean,
                optimize=optimize,
            )
            result = build_cmd.run()

            progress.update(task, description=" build complete successfully")

        console.print(f"\n[bold green]Build completed successfully![/bold green]")  # noqa: F541
        console.print(f"Build artifacts: [bold]{result['output_path']}[/bold]")

        if result.get("size_info"):
            console.print(
                f"\n[bold yellow]Build size:  [bold]{result['size_info']}[/bold]"
            )

    except DevToolError as e:
        console.print(f"[bold red]Build failed:: {e}[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Command: deploy
@app.command()
def deploy(
    project_path: Path = typer.Argument(
        Path.cwd(), help="Path to the project directory"
    ),
    platform: str = typer.Option(
        ...,
        "--platform",
        "-p",
        help="Deployment platform (railway, render, heroku, vercel, aws, docker)",
    ),
    environment: str = typer.Option(
        "production", "--env", "-e", help="Deployment environment"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Deployment configuration file"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show deployment plan without executing"
    ),
    auto_build: bool = typer.Option(
        True, "--build/--no-build", help="Build project before deployment"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    🚀 Deploy the project to various platforms

    Supported platforms:
    • Railway, Render, Heroku (PaaS)
    • Vercel, Netlify (Static/Serverless)
    • AWS, GCP, Azure (Cloud providers)
    • Docker registries
    • Custom deployment scripts
    """

    try:
        validate_project_path(project_path)

        console.print(
            Panel.fit(
                f"[bold magenta]🚀 Deploying Project to [bold]{platform}[/bold magenta]",
                style="magenta",
            )
        )

        if dry_run:
            console.print(
                console.print(
                    "[yellow]Dry run mode - showing deployment plan[/yellow]\n"
                )
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[bold blue]Preparring Deployment...", total=None)

            from python_dev_tool.cli.commands.deploy import DeployCommand

            deploy_cmd = DeployCommand(
                project_path=project_path,
                platform=platform,
                environment=environment,
                config_file=config_file,
                dry_run=dry_run,
                auto_build=auto_build,
            )
            result = deploy_cmd.run()

            if not dry_run:
                progress.update(task, description=" deployment complete successfully")
            else:
                progress.update(task, description=" deployment plan generated")

            if dry_run:
                console.print(f"\n[bold yellow] Deployment Plan:[/bold yellow]")  # noqa: F541
                for step in result.get("plan", []):
                    console.print(f"  • {step}")
            else:
                console.print(
                    f"\n[bold green]Deployment completed successfully![/bold green]"  # noqa: F541
                )
                console.print(
                    f"🌐 Application URL: [bold]{result.get('url', 'N/A')}[/bold]"
                )

            progress.update(task, description=" deployment complete")

    except DevToolError as e:
        console.print(f"[bold red]Deploy failed:: {e}[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Command: config
@app.command()
def config_command(
    action: str = typer.Argument(..., help="Action to perform (show, set, get, reset)"),
    key: Optional[str] = typer.Argument(None, help="Configuration key"),
    value: Optional[str] = typer.Argument(None, help="Configuration value"),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Use global configuration"
    ),
    project_path: Path = typer.Option(
        Path.cwd(), "--project", help="Project path for local configuration"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    ⚙️ Manage configuration settings

    Actions:
    • show: Display current configuration
    • set: Set configuration value
    • get: Get configuration value
    • reset: Reset to default values
    """

    try:
        from python_dev_tool.cli.commands.config import ConfigCommand

        config_cmd = ConfigCommand(
            action=action,
            key=key,
            value=value,
            global_config=global_config,
            project_path=project_path,
        )

        result = config_cmd.run()

        if action == "show":
            console.print(
                Panel.fit(
                    "[bold blue]⚙️ Configuration Settings[/bold blue]", style="blue"
                )
            )
            config_table = Table(show_header=True, header_style="bold blue")
            config_table.add_column("Key", style="cyan")
            config_table.add_column("Value", style="green")
            config_table.add_column("Source", style="yellow")

            for item in result.get("config", []):
                config_table.add_row(item["key"], item["value"], item["source"])

            console.print(config_table)

        elif action == "get":
            console.print(
                f"[bold blue]{key}:[/bold blue] [green]{result.get('value', 'Not set')}[/green]"
            )

        elif action == "set":
            console.print(
                f"[bold green]Configuration updated:[/bold green] {key} = {value}"
            )

        elif action == "reset":
            console.print("[bold yellow]Configuration reset to defaults[/bold yellow]")

    except DevToolError as e:
        console.print(f"[bold red]Configuration failed:: {e}[/bold red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Command: status
@app.command()
def status(
    project_path: Path = typer.Argument(
        Path.cwd(), help="Path to the project directory"
    ),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed status information"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    📊 Show project status and health information

    Displays:
    • Project configuration
    • Framework detection
    • Service health
    • Recent logs
    • Performance metrics
    """
    try:
        validate_project_path(project_path)

        console.print(
            Panel.fit("[bold blue]📊 Project Status[/bold blue]", style="blue")
        )

        from python_dev_tool.core.app import DevToolApp
        from python_dev_tool.cli.commands.status import StatusCommand

        status_cmd = StatusCommand(
            project_path=project_path, detailed=detailed, check_deps=True
        )
        status_info = status_cmd.run()

        app_instance = DevToolApp(project_path)
        app_status = app_instance.get_status()

        status_info.update(app_status)

        # Project info
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_row("Project:", f"[bold]{status_info['project_name']}[/bold]")
        info_table.add_row("Framework:", f"[bold]{status_info['framework']}[/bold]")
        info_table.add_row(
            "Status:",
            f"[bold green]{'Running' if status_info['running'] else 'Stopped'}[/bold green]",
        )
        info_table.add_row("Config:", f"[bold]{status_info['config_file']}[/bold]")

        console.print(info_table)

        if detailed:
            # Performance metrics
            if status_info.get("metrics"):
                console.print("\n[bold yellow]Performance Metrics:[/bold yellow]")
                metrics_table = Table(show_header=True, header_style="bold yellow")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="green")

                for metric, value in status_info["metrics"].items():
                    metrics_table.add_row(metric, str(value))

                console.print(metrics_table)

            # Recent logs
            if status_info.get("recent_logs"):
                console.print("\n[bold yellow]Recent Logs:[/bold yellow]")
                for log in status_info["recent_logs"][-5:]:  # Show last 5 logs
                    console.print(f"  {log}")

    except DevToolError as e:
        console.print(f"[bold red]❌ Status error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Command: help


# Command: update
@app.command()
def update(
    version: Optional[str] = typer.Option(
        None, "--version", "-V", help="Specific version to install (e.g., 1.2.3)"
    ),
    pre_release: bool = typer.Option(
        False, "--pre-release", "--pre", help="Include pre-release versions"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force update even if already up to date"
    ),
    check_only: bool = typer.Option(
        False, "--check", "-c", help="Check for updates without installing"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging"
    ),
) -> None:
    """
    🔄 Update the python-dev-tool to the latest version

    Features:
    • Check for latest stable or pre-release versions
    • Update to specific version
    • Backup current installation
    • Rollback on failure
    • Check-only mode for CI/CD
    """
    try:
        console.print(
            Panel.fit(
                "[bold blue]🔄 Python Dev Tool Updater[/bold blue]",
                style="blue",
            )
        )

        # Import update command
        from python_dev_tool.cli.commands.update import UpdateCommand

        update_cmd = UpdateCommand(
            target_version=version,
            include_pre_release=pre_release,
            force=force,
            check_only=check_only,
            verbose=verbose,
        )

        if check_only:
            # Just check for updates
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[bold blue]Checking for updates...", total=None
                )
                result = update_cmd.check_for_updates()
                progress.update(task, description="✓ Update check complete")

            if result["update_available"]:
                console.print(f"\n[bold yellow]📦 Update available![/bold yellow]")
                console.print(
                    f"Current version: [bold red]{result['current_version']}[/bold red]"
                )
                console.print(
                    f"Latest version:  [bold green]{result['latest_version']}[/bold green]"
                )

                if result.get("changelog"):
                    console.print(f"\n[bold blue]What's new:[/bold blue]")
                    for change in result["changelog"][:3]:  # Show top 3 changes
                        console.print(f"  • {change}")

                console.print(
                    f"\nRun [bold]fuse update[/bold] to install the latest version"
                )
            else:
                console.print(
                    f"\n[bold green]✅ You're already running the latest version ({result['current_version']})[/bold green]"
                )

            return

        # Perform the update
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Check for updates
            check_task = progress.add_task(
                "[bold blue]Checking for updates...", total=None
            )
            update_info = update_cmd.check_for_updates()
            progress.update(check_task, description="✓ Update check complete")

            if not update_info["update_available"] and not force:
                progress.update(check_task, description="✓ Already up to date")
                console.print(
                    f"\n[bold green]✅ Already running the latest version ({update_info['current_version']})[/bold green]"
                )
                return

            # Show update information
            if update_info["update_available"]:
                console.print(
                    f"\n[bold yellow]📦 Updating from {update_info['current_version']} to {update_info['latest_version']}[/bold yellow]"
                )

            # Create backup
            backup_task = progress.add_task("[bold blue]Creating backup...", total=None)
            backup_result = update_cmd.create_backup()
            progress.update(backup_task, description="✓ Backup created")

            # Download and install update
            download_task = progress.add_task(
                "[bold blue]Downloading update...", total=None
            )
            try:
                download_result = update_cmd.download_update(
                    update_info["latest_version"]
                )
                progress.update(download_task, description="✓ Download complete")

                # Install update
                install_task = progress.add_task(
                    "[bold blue]Installing update...", total=None
                )
                install_result = update_cmd.install_update(
                    download_result["package_path"]
                )
                progress.update(install_task, description="✓ Installation complete")

                # Verify installation
                verify_task = progress.add_task(
                    "[bold blue]Verifying installation...", total=None
                )
                verification_result = update_cmd.verify_installation()
                progress.update(verify_task, description="✓ Verification complete")

                if verification_result["success"]:
                    console.print(
                        f"\n[bold green]🎉 Successfully updated to version {verification_result['new_version']}![/bold green]"
                    )

                    # Show what's new
                    if update_info.get("changelog"):
                        console.print(
                            f"\n[bold blue]🆕 What's new in {verification_result['new_version']}:[/bold blue]"
                        )
                        for change in update_info["changelog"][
                            :5
                        ]:  # Show top 5 changes
                            console.print(f"  • {change}")

                    # Clean up backup if successful
                    update_cmd.cleanup_backup(backup_result["backup_path"])
                    console.print(f"\n[dim]Backup cleaned up[/dim]")

                else:
                    raise DevToolError("Installation verification failed")

            except Exception as e:
                # Rollback on failure
                progress.add_task(
                    "[bold red]Update failed, rolling back...", total=None
                )
                rollback_result = update_cmd.rollback(backup_result["backup_path"])

                if rollback_result["success"]:
                    console.print(
                        f"\n[bold yellow]⚠️  Update failed but successfully rolled back to {rollback_result['restored_version']}[/bold yellow]"
                    )
                else:
                    console.print(
                        f"\n[bold red]❌ Update and rollback failed! Manual intervention required.[/bold red]"
                    )
                    console.print(f"Backup location: {backup_result['backup_path']}")

                raise DevToolError(f"Update failed: {str(e)}")

        # Show next steps
        console.print(f"\n[bold blue]💡 Next steps:[/bold blue]")
        console.print("  • Restart any running development servers")
        console.print(
            "  • Run [bold]fuse status[/bold] to verify everything is working"
        )
        console.print("  • Check the changelog for breaking changes")

    except DevToolError as e:
        error_console.print(f"[bold red]Update failed: {e}[/bold red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Update cancelled by user.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


#
# if __name__ == "__main__":
#     app()
