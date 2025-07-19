"""
FUSE (Python Dev Tool) - CLI Command Tests
This module contains unit tests for the CLI commands of the Python Dev Tool.
"""

import pytest
from typer.testing import CliRunner
from python_dev_tool.cli.main import app

runner = CliRunner()


def test_init_command(tmp_path):
    """Test the init command with proper setup."""
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, f"Init failed: {result.stdout}"
    assert "Project initialized successfully" in result.stdout
    assert (tmp_path / ".devtool/config.toml").exists()


def test_dev_command(tmp_path):
    """Test the dev command with proper setup."""
    result = runner.invoke(app, ["dev", str(tmp_path)])
    assert result.exit_code == 0, f"Dev command failed: {result.stdout}"
    assert "Development server started successfully" in result.stdout


def test_build_command(tmp_path):
    """Test the build command with proper setup."""
    result = runner.invoke(app, ["build", str(tmp_path)])
    assert result.exit_code == 0, f"Build failed: {result.stdout}"
    assert "Build completed successfully" in result.stdout


def test_deploy_command(tmp_path):
    """Test the deploy command with proper setup."""
    result = runner.invoke(app, ["deploy", str(tmp_path), "--platform", "heroku"])
    assert result.exit_code == 0, f"Deploy failed: {result.stdout}"
    assert "Deployment completed successfully" in result.stdout


def test_status_command(tmp_path):
    """Test the status command with proper setup."""
    result = runner.invoke(app, ["status", str(tmp_path)])
    assert result.exit_code == 0, f"Status failed: {result.stdout}"
    assert "Project Status" in result.stdout


@pytest.mark.skip(reason="Not implemented yet")
def test_config_command(tmp_path):
    result = runner.invoke(app, ["config", str(tmp_path)])
    assert result.exit_code == 0
    assert "Configuration updated" in result.stdout
-
