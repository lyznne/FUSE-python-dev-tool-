"""
FUSE - (python dev tool) - CLI Unit Tests
MAIN - Unit Tests for the CLI commands of the Python Dev Tool.
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
    assert "Python Dev Tool version 0.0.1" in result.stdout



# config
class MockConfig:
    @staticmethod
    def load_from_project(project_path):
        return MockConfig()

    @staticmethod
    def load_from_path(path):
        return MockConfig()




# Mock the Config class to avoid actual file operations
@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr("python_dev_tool.core.config.Config", MockConfig)
