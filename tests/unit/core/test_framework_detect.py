"""
FUSE - (python dev tool) - Core Unit Tests
Framework Detection Unit Tests
"""

from python_dev_tool.core.framework_detector import FrameworkDetector


def test_framework_detector_structure(tmp_path):
    # Simulate fastapi project
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0")

    # Initialize detector with project root
    detector = FrameworkDetector(project_root=str(tmp_path))

    # Detect framework
    framework = detector.detect_framework()

    # Basic assertions
    assert framework is not None
    assert framework.name == "fastapi"
    assert framework.confidence > 0.3

    # Check commands structure if FRAMEWORK_SIGNATURES is properly configured
    if framework.commands:
        assert isinstance(framework.commands, dict)
        # Only check for 'dev' command if it exists in the framework signature
        if "dev" in framework.commands:
            assert isinstance(framework.commands["dev"], str)

    # Check other framework info
    assert isinstance(framework.config_files, list)
    assert isinstance(framework.dependencies, list)

    # Check that it detected FastAPI-specific indicators
    assert framework.main_file is not None or len(framework.entry_points) > 0


def test_framework_detector_django(tmp_path):
    # Simulate Django project
    (tmp_path / "manage.py").write_text("#!/usr/bin/env python\nimport django")
    (tmp_path / "settings.py").write_text("INSTALLED_APPS = []")
    (tmp_path / "requirements.txt").write_text("django==4.2.0")

    detector = FrameworkDetector(project_root=str(tmp_path))
    framework = detector.detect_framework()

    assert framework is not None
    assert framework.name == "django"
    assert framework.confidence > 0.3


def test_framework_detector_flask(tmp_path):
    # Simulate Flask project
    (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)")
    (tmp_path / "requirements.txt").write_text("flask==2.3.0")

    detector = FrameworkDetector(project_root=str(tmp_path))
    framework = detector.detect_framework()

    assert framework is not None
    assert framework.name == "flask"
    assert framework.confidence > 0.3


def test_framework_detector_no_framework(tmp_path):
    # Create a simple Python file without framework imports
    (tmp_path / "script.py").write_text("print('Hello, World!')")

    detector = FrameworkDetector(project_root=str(tmp_path))
    framework = detector.detect_framework()

    # Should return None or have very low confidence
    assert framework is None or framework.confidence < 0.3


def test_framework_detector_multiple_indicators(tmp_path):
    # Create FastAPI project with multiple indicators
    (tmp_path / "main.py").write_text("""
    from fastapi import FastAPI, APIRouter
    import uvicorn

    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"Hello": "World"}

    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000)
    """)

    # Create app directory (common FastAPI structure)
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "routers.py").write_text("from fastapi import APIRouter")

    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn==0.22.0")

    detector = FrameworkDetector(project_root=str(tmp_path))
    framework = detector.detect_framework()

    assert framework is not None
    assert framework.name == "fastapi"
    assert framework.confidence >= 0.5
    # Should have high confidence with multiple indicators


def test_framework_detector_get_all_frameworks(tmp_path):
    # Create a project that might match multiple frameworks weakly
    (tmp_path / "main.py").write_text("import os\nprint('Hello')")
    (tmp_path / "app.py").write_text("def main(): pass")

    detector = FrameworkDetector(project_root=str(tmp_path))
    detector.detect_framework()  # Run detection

    all_frameworks = detector.get_all_detected_frameworks()
    assert isinstance(all_frameworks, dict)


def test_framework_detector_version_detection(tmp_path):
    # Test version detection from requirements.txt
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn>=0.22.0")

    detector = FrameworkDetector(project_root=str(tmp_path))
    framework = detector.detect_framework()

    assert framework is not None
    # Version detection depends on VERSION_PATTERNS being properly configured
    assert framework.version == "0.100.0"


def test_framework_detector_recommended_structure(tmp_path):
    detector = FrameworkDetector(project_root=str(tmp_path))

    # Test recommended structure for different frameworks
    django_structure = detector.get_recommended_structure("django")
    assert "directories" in django_structure
    assert "files" in django_structure
    assert "templates" in django_structure["directories"]
    assert "manage.py" in django_structure["files"]

    flask_structure = detector.get_recommended_structure("flask")
    assert "templates" in flask_structure["directories"]
    assert "app.py" in flask_structure["files"]
