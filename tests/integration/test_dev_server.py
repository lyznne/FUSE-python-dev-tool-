"""
FUSE - (python dev tool) - Integration Tests
Integration Tests - Development Server
"""

import pytest
import requests

from python_dev_tool.cli.commands.dev import DevCommand

@pytest.mark.asyncio
async def test_dev_server_start(tmp_path):
    cmd  =  DevCommand(project_path=tmp_path, port=9999)
    try:
        await cmd._start_dev_ui()
        response  =  requests.get("http://localhost:9999")
        assert response.status_code == 200
        # assert "Welcome to FUSE" in response.text
    finally:
        await cmd._cleanup()
