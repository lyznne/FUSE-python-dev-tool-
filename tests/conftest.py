import sys
import os
import pytest


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)


# For Integration tests


@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Ensure clean environment
    yield
    # Teardown: Clean up any running servers or temp files
