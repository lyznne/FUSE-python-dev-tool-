"""
FUSE - (python dev tool) - Core Unit Tests
Framework Detection Unit Tests
"""

from python_dev_tool.core.framework_detector import FrameworkDetector


def test_framework_detector_structure(tmp_path):
    # simulate fastapi project
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0")

    detector = FrameworkDetector(tmp_path)
    framework = detector.detect_framework()

    assert framework is not None
    assert isinstance(framework.commands, dict)
    assert "dev" in framework.commands
    assert isinstance(framework.commands["dev"], str)
