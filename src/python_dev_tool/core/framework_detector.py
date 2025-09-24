"""
FUSE - (python dev tool) - Core App
framework_detector.py - Framework Detector & Integration
"""

# sys imports
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

# local imports
from python_dev_tool.core.globals import (
    FRAMEWORK_PATTERNS,
    FRAMEWORK_SIGNATURES,
    REQUIREMENTS_FILES,
    VERSION_PATTERNS,
)


@dataclass
class FrameworkInfo:
    """Information about a detected framework."""

    name: str
    version: Optional[str] = None
    confidence: float = 0.0
    main_file: Optional[str] = None
    config_files: List[str] = None
    dependencies: List[str] = None
    commands: Dict[str, str] = None
    entry_points: List[str] = None

    def __post_init__(self):
        """Post initialization."""
        if self.config_files is None:
            self.config_files = []
        if self.dependencies is None:
            self.dependencies = []
        if self.commands is None:
            self.commands = {}
        if self.entry_points is None:
            self.entry_points = []


class FrameworkDetector:
    """Detects and analyzes Python frameworks."""

    def __init__(
        self, project_root: str = ".", host: str = "127.0.0.1", port: int = 8000
    ):
        self.project_root = Path(project_root)
        self.host = host
        self.port = port
        self.detected_frameworks: Dict[str, FrameworkInfo] = {}

        # Framework patterns
        self.FRAMEWORK_PATTERNS = FRAMEWORK_PATTERNS

    def detect_framework(self, project_path: Optional[Path] = None) -> Optional[str]:
        """
        Detect the primary framework used in the project.

        Args:
            project_path (Optional[Path]): Path to the project directory.
                                         If None, uses self.project_root.

        Returns:
            Optional[str]: Detected framework name or None if no framework is detected.
        """

        if project_path is not None:
            self.project_root = project_path

        if not project_path.exists() or not project_path.is_dir():
            return None

        # Reset detection results
        self.detected_frameworks = {}

        # Method 1: Use FRAMEWORK_SIGNATURES if available
        if "FRAMEWORK_SIGNATURES" in globals():
            self._detect_using_signatures()

        # Method 2: Analyze directory structure
        self._analyze_directory(project_path)

        # Return framework with highest confidence
        if self.detected_frameworks:
            best_framework = max(
                self.detected_frameworks.items(), key=lambda x: x[1].confidence
            )

            # Only return if confidence is above threshold
            if best_framework[1].confidence >= 0.3:
                return best_framework[0]

        return None

    def _detect_using_signatures(self) -> None:
        """Detect frameworks using FRAMEWORK_SIGNATURES."""
        for framework_name, signature in FRAMEWORK_SIGNATURES.items():
            confidence = self._calculate_confidence(framework_name, signature)

            if confidence > 0.1:  # minimum confidence threshold
                # Format command with port and host
                commands = {
                    key: cmd.format(host=self.host, port=self.port)
                    for key, cmd in signature.get("commands", {}).items()
                }

                framework_info = FrameworkInfo(
                    name=framework_name,
                    confidence=confidence,
                    main_file=self._find_main_file(framework_name, signature),
                    config_files=self._find_config_files(framework_name, signature),
                    dependencies=signature.get("requirements", []),
                    commands=commands,
                )

                # Try to detect version
                framework_info.version = self._detect_version(framework_name)
                self.detected_frameworks[framework_name] = framework_info

    def _analyze_directory(self, project_path: Path) -> None:
        """Analyze directory structure and files for framework indicators."""
        # Get all Python files
        python_files = list(project_path.rglob("*.py"))

        # Get all directories
        directories = [d.name for d in project_path.iterdir() if d.is_dir()]

        # Analyze each framework
        for framework_name, patterns in self.FRAMEWORK_PATTERNS.items():
            confidence = 0.0
            entry_points = []
            config_files = []

            # Check for specific files (high confidence)
            for file_pattern in patterns["files"]:
                matching_files = list(project_path.glob(file_pattern))
                if matching_files:
                    confidence += 0.3
                    entry_points.extend(
                        [str(f.relative_to(project_path)) for f in matching_files]
                    )

            # Check for directories (medium confidence)
            for dir_pattern in patterns.get("directories", []):
                if dir_pattern in directories:
                    confidence += 0.2

            # Check for config files (medium confidence)
            for config_file in patterns.get("config_files", []):
                if (project_path / config_file).exists():
                    confidence += 0.2
                    config_files.append(config_file)

            # Analyze Python files for imports and patterns
            import_confidence, pattern_confidence = self._analyze_python_files(
                python_files, patterns
            )

            confidence += import_confidence + pattern_confidence

            # Store framework info if any indicators found
            if confidence > 0:
                # Update existing or create new framework info
                if framework_name in self.detected_frameworks:
                    existing = self.detected_frameworks[framework_name]
                    existing.confidence = max(existing.confidence, min(confidence, 1.0))
                    existing.entry_points.extend(entry_points)
                    existing.config_files.extend(config_files)
                else:
                    self.detected_frameworks[framework_name] = FrameworkInfo(
                        name=framework_name,
                        confidence=min(confidence, 1.0),  # Cap at 1.0
                        entry_points=entry_points,
                        config_files=config_files,
                    )

    def _analyze_python_files(self, python_files: List[Path], patterns: Dict) -> tuple:
        """Analyze Python files for import statements and code patterns."""
        import_confidence = 0.0
        pattern_confidence = 0.0

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8")

                # Check for import statements
                imports_found = self._find_imports(content, patterns.get("imports", []))
                if imports_found:
                    import_confidence += 0.1 * len(imports_found)

                # Check for code patterns
                patterns_found = self._find_patterns(
                    content, patterns.get("patterns", [])
                )
                if patterns_found:
                    pattern_confidence += 0.1 * len(patterns_found)

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        return min(import_confidence, 0.4), min(pattern_confidence, 0.4)

    def _find_patterns(self, content: str, code_patterns: List[str]) -> Set[str]:
        """Find code patterns matching the patterns."""
        found_patterns = set()

        for pattern in code_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                found_patterns.add(pattern)

        return found_patterns

    def get_all_detected_frameworks(self) -> Dict[str, FrameworkInfo]:
        """Get all detected frameworks with their confidence scores."""
        return self.detected_frameworks.copy()

    def _calculate_confidence(self, framework_name: str, signature: Dict) -> float:
        """Calculate confidence score for framework detection."""
        confidence = 0.0
        max_confidence = 0.0

        # Check for specific files
        file_score = self._check_files(signature.get("files", []))
        confidence += file_score * 0.3
        max_confidence += 0.3

        # Check for directories
        dir_score = self._check_directories(signature.get("directories", []))
        confidence += dir_score * 0.2
        max_confidence += 0.2

        # Check for imports in Python files
        import_score = self._check_imports(signature.get("imports", []))
        confidence += import_score * 0.3
        max_confidence += 0.3

        # Check for code patterns
        pattern_score = self._check_patterns(signature.get("patterns", []))
        confidence += pattern_score * 0.2
        max_confidence += 0.2

        return confidence / max_confidence if max_confidence > 0 else 0.0

    def _check_files(self, files: List[str]) -> float:
        """Check for existence of framework-specific files."""
        if not files:
            return 0.0

        found_files = 0
        for file_pattern in files:
            if "*" in file_pattern:
                # Handle glob patterns
                pattern_files = list(self.project_root.glob(file_pattern))
                if pattern_files:
                    found_files += 1
            else:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    found_files += 1

        return found_files / len(files)

    def _check_directories(self, directories: List[str]) -> float:
        """Check for existence of framework-specific directories."""
        if not directories:
            return 0.0

        found_dirs = 0
        for dir_name in directories:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                found_dirs += 1

        return found_dirs / len(directories)

    def _check_imports(self, imports: List[str]) -> float:
        """Check for framework-specific imports in Python files."""
        if not imports:
            return 0.0

        python_files = list(self.project_root.glob("**/*.py"))
        if not python_files:
            return 0.0

        found_imports = set()

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse AST to find imports
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                found_imports.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                found_imports.add(node.module.split(".")[0])
                except SyntaxError:
                    # If AST parsing fails, fall back to regex
                    import_pattern = r"(?:from\s+(\w+)|import\s+(\w+))"
                    matches = re.findall(import_pattern, content)
                    for match in matches:
                        module = match[0] or match[1]
                        if module:
                            found_imports.add(module)

            except Exception:
                continue

        # Count how many required imports were found
        matched_imports = sum(1 for imp in imports if imp in found_imports)
        return matched_imports / len(imports)

    def _check_patterns(self, patterns: List[str]) -> float:
        """Check for framework-specific code patterns."""
        if not patterns:
            return 0.0

        python_files = list(self.project_root.glob("**/*.py"))
        if not python_files:
            return 0.0

        found_patterns = 0

        for pattern in patterns:
            pattern_found = False
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)

            for py_file in python_files:
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    if regex.search(content):
                        pattern_found = True
                        break
                except Exception:
                    continue

            if pattern_found:
                found_patterns += 1

        return found_patterns / len(patterns)

    def _find_main_file(self, framework_name: str, signature: Dict) -> Optional[str]:
        """Find the main application file."""
        possible_files = signature.get("files", [])

        for file_pattern in possible_files:
            if "*" in file_pattern:
                # Handle glob patterns
                matches = list(self.project_root.glob(file_pattern))
                if matches:
                    return str(matches[0].relative_to(self.project_root))
            else:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    return file_pattern

        # Fallback to default files
        fallback_patterns = [
            f"{framework_name}.py",
            f"{self.project_root.name}.py",
            "main.py",
            "app.py",
        ]
        for pattern in fallback_patterns:
            file_path = self.project_root / pattern
            if file_path.exists():
                return pattern

        return None

    def _find_imports(self, content: str, import_patterns: List[str]) -> Set[str]:
        """Find import statements matching the patterns."""
        found_imports = set()

        try:
            # Parse the file to find imports
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for pattern in import_patterns:
                            if pattern.lower() in alias.name.lower():
                                found_imports.add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for pattern in import_patterns:
                            if pattern.lower() in node.module.lower():
                                found_imports.add(node.module)

        except SyntaxError:
            # Fallback to regex if AST parsing fails
            for pattern in import_patterns:
                import_regex = (
                    rf"import\s+{re.escape(pattern)}|from\s+{re.escape(pattern)}"
                )
                if re.search(import_regex, content, re.IGNORECASE):
                    found_imports.add(pattern)

        return found_imports

    def _find_config_files(self, framework_name: str, signature: Dict) -> List[str]:
        """Find the framework-specific configuration files."""
        config_files = []
        possible_files = signature.get("config_files", [])

        for file_pattern in possible_files:
            if "*" in file_pattern:
                # Handle glob patterns
                matches = list(self.project_root.glob(file_pattern))
                config_files.extend(
                    str(m.relative_to(self.project_root)) for m in matches
                )
            else:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    config_files.append(file_pattern)

        return config_files

    def _detect_version(self, framework_name: str) -> Optional[str]:
        """Detect the framework version."""
        # Try to find version in requirements files
        pattern = VERSION_PATTERNS.get(framework_name.lower())
        if not pattern:
            return None

        for req_file in REQUIREMENTS_FILES:
            file_path = self.project_root / req_file

            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                except Exception:
                    continue

        # Try detect version from framework's own signature version api
        try:
            # TODO: Implement version detection from installed packages
            # if framework_name.lower() == "django":
            #     import django
            #     return django.get_version()
            # elif framework_name.lower() == "flask":
            #     import flask
            #     return flask.__version__
            # elif framework_name.lower() == "fastapi":
            #     import fastapi
            #     return fastapi.__version__
            # elif framework_name.lower() == "streamlit":
            #     import streamlit
            #     return streamlit.__version__
            pass
        except ImportError:
            pass

        return None

    def get_framework_details(self, framework_name: str) -> Optional[FrameworkInfo]:
        """Get detailed information about a detected framework."""
        return self.detected_frameworks.get(framework_name)

    def is_framework_project(self, project_path: Optional[Path] = None) -> bool:
        """Check if the directory contains any recognizable framework."""
        detected = self.detect_framework(project_path)
        return detected is not None

    def get_recommended_structure(self, framework: str) -> Dict[str, List[str]]:
        """Get recommended project structure for a framework."""
        structures = {
            "django": {
                "directories": ["templates", "static", "media", "locale"],
                "files": ["manage.py", "requirements.txt", ".env"],
            },
            "flask": {
                "directories": ["templates", "static", "instance"],
                "files": ["app.py", "config.py", "requirements.txt", ".env"],
            },
            "fastapi": {
                "directories": ["app", "tests", "alembic"],
                "files": ["main.py", "requirements.txt", ".env"],
            },
            "streamlit": {
                "directories": ["pages", "data", ".streamlit"],
                "files": ["app.py", "requirements.txt", ".env"],
            },
            "tornado": {
                "directories": ["handlers", "templates", "static"],
                "files": ["app.py", "settings.py", "requirements.txt"],
            },
            "sanic": {
                "directories": ["blueprints", "middleware", "config"],
                "files": ["app.py", "requirements.txt", ".env"],
            },
        }

        return structures.get(
            framework,
            {
                "directories": ["src", "tests"],
                "files": ["main.py", "requirements.txt", ".env"],
            },
        )

    def get_all_frameworks(self) -> List[FrameworkInfo]:
        """Get all detected frameworks with their confidence scores."""
        return list(self.detected_frameworks.values())

    def has_framework(self, framework_name: str) -> bool:
        """Check if a specific framework is detected."""
        return framework_name.lower() in [
            name.lower() for name in self.detected_frameworks.keys()
        ]


# Standalone utility functions
def detect_project_framework(project_path: Path) -> Optional[str]:
    """Standalone function to detect framework name in a project."""
    detector = FrameworkDetector()
    framework_info = detector.detect_framework(project_path)
    return framework_info.name if framework_info else None


def get_framework_info(
    project_path: Path, framework_name: str
) -> Optional[FrameworkInfo]:
    """Get detailed framework information."""
    detector = FrameworkDetector()
    detector.detect_framework(project_path)
    return detector.get_framework_details(framework_name)
