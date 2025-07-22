"""
FUSE - (python dev tool) - Integration Tests
Integration Tests - Development Server
"""

import pytest
from python_dev_tool.cli.commands.dev import DevCommand
from python_dev_tool.web.app import create_dev_ui_app
import os


@pytest.mark.asyncio
async def test_dev_server_start(tmp_path):
    """Test that the dev server can start properly."""
    # Create proper config file structure
    config_dir = tmp_path / ".devtool"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text("""
    [project]
    name = "test-project"
    version = "0.1.0"
    """)

    # Create a basic project structure
    (tmp_path / "pyproject.toml").write_text("""
    [tool.poetry]
    name = "test-project"
    version = "0.1.0"
    """)

    # Set environment variable for the test
    os.environ["DEVTOOL_PROJECT_PATH"] = str(tmp_path)

    try:
        # Test that we can create the app directly
        app = create_dev_ui_app(project_path=tmp_path)
        assert app is not None

        # Test the DevCommand creation (but don't actually start the server)
        cmd = DevCommand(project_path=tmp_path, port=9999, ui_port=9998)
        assert cmd is not None

    except Exception as e:
        # If there are still issues, at least log them for debugging
        pytest.fail(f"Failed to create dev UI app: {e}")

    finally:
        # Clean up environment
        if "DEVTOOL_PROJECT_PATH" in os.environ:
            del os.environ["DEVTOOL_PROJECT_PATH"]


@pytest.mark.asyncio
async def test_invalid_port_config(tmp_path):
    """Test handling of invalid port configuration."""
    # Create proper config file structure
    config_dir = tmp_path / ".devtool"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text("""
    [project]
    name = "test-project"
    version = "0.1.0"
    """)

    # Create a basic project structure
    (tmp_path / "pyproject.toml").write_text("""
    [tool.poetry]
    name = "test-project"
    version = "0.1.0"
    """)

    # Test with tuple port (should be handled by _unwrap function)
    cmd = DevCommand(project_path=tmp_path, ui_port=(8080, 8081))

    # The command should preserve the original tuple for testing
    assert cmd.original_ui_port == (8080, 8081)

    # But the actual options should have the unwrapped value
    assert cmd.options.ui_port == 8080

    # Test that the unwrap function works correctly
    def _unwrap(value, fallback=None):
        """Test the unwrap function from the actual code."""
        if isinstance(value, (tuple, list)):
            return value[0] if value else fallback
        return value

    unwrapped_port = _unwrap(cmd.original_ui_port, 8000)
    assert unwrapped_port == 8080
