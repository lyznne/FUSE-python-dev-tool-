"""
FUSE - (python dev tool) - CLI Unit Tests
CLI - Unit Tests
"""
import pytest
from typer.testing import CliRunner
from python_dev_tool.cli.main import app

runner = CliRunner()

def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Python Dev Tool" in result.stdout
    assert "Supercharge your Python development workflow" in result.stdout
    assert result.stdout.endswith("0.0.1\n")

def test_init_command(tmp_path):
    result  = runner.invoke(app, ["init", str(tmp_path)])
    # result  = runner.invoke(app, ["init", str(tmp_path), "--framework", "django"])
    assert result.exit_code == 0
    assert "Project initialized successfully" in result.stdout
    assert (tmp_path / ".devtool/config.toml").exists()

def test_dev_command(tmp_path):
    result  = runner.invoke(app, ["dev", str(tmp_path)])
    assert result.exit_code == 0
    assert "Development server started successfully" in result.stdout

def test_build_command(tmp_path):
    result  = runner.invoke(app, ["build", str(tmp_path)])
    assert result.exit_code == 0
    assert "Build completed successfully" in result.stdout

def test_deploy_command(tmp_path):
    result  = runner.invoke(app, ["deploy", str(tmp_path)])
    assert result.exit_code == 0
    assert "Deployment completed successfully" in result.stdout

def test_status_command(tmp_path):
    result  = runner.invoke(app, ["status", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project Status" in result.stdout

@pytest.mark.skip(reason="Not implemented")
def test_config_command(tmp_path):
    result  = runner.invoke(app, ["config", str(tmp_path)])
    assert result.exit_code == 0
    assert "Configuration updated" in result.stdout
