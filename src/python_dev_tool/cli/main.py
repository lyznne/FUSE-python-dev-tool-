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
    no_args_is_help=True,
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


@app.callback()
def main(
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
        help="Framework to use (django, flask, fastapi, streamlit)",
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    template: Optional[str] = typer.Option(
        None, "--template", "-t", help="Project template to use"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force initialization even if directory is not empty"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output for debugging")

) -> None:
    """
    🎯 Initialize a new Python project with development tools

    Creates a new project structure with:
    • Framework-specific configuration
    • Development server setup
    • Docker configuration
    • CI/CD pipeline templates
    • Testing framework setup
    """
    try:
        # validate project path
        validate_project_path(project_path)

        # init banner
        console.print(
            Panel.fit(
                "[bold blue]🎯 Initializing Python Development Project[/bold blue]",
                style="blue",
            )
        )

        # run initilization
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[bold blue]Initializing...", total=None)

            # import init command
            from python_dev_tool.cli.commands.init import InitCommand

            init_cmd = InitCommand(project_path, framework, name, template, force)
            result = init_cmd.run()

            progress.update(task, description=" initialization complete")

        # print success message
        console.print(f"\n[bold green]Project initialized successfully![/bold green]")  # noqa: F541
        console.print(f"📁 Project location: [bold]{project_path.absolute()}[/bold]")

        if result.get("next_steps"):
            console.print(f"\n[bold yellow]Next steps:[/bold yellow]")  # noqa: F541
            for step in result.get("next_steps"):
                console.print(f" • [bold]{step}[/bold]")

    except DevToolError as e:
        error_console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Unexpected error occurred: {e}[/bold red]")
        if verbose:
            console.print_exception()

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
        config_cmd  =  ConfigCommand(
            action=action,
            key=key,
            value=value,
            global_config=global_config,
            project_path=project_path,
        )

        result  =  config_cmd.run()

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
            console.print(f"[bold blue]{key}:[/bold blue] [green]{result.get('value', 'Not set')}[/green]")

        elif action == "set":
            console.print(f"[bold green]Configuration updated:[/bold green] {key} = {value}")

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


# --- continue

if __name__ == "__main__":
    app()
