"""
FUSE - (python dev tool) - Core App
framework_detector.py - Framework Detector & Intergration
"""

#  sys imports
from logging import config
import re
import ast
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

# 3rd party imports

# local imports
from python_dev_tool.core.globals import (
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

    def __post_init__(self):
        """Post initialization."""
        if self.config_files is None:
            self.config_files = []
        if self.dependencies is None:
            self.dependencies = []
        if self.commands is None:
            self.commands = {}

class FrameworkDetector:
    """Detects and analyzes Python frameworks."""

    def __init__(
        self, project_root: str = ".", host: str = "127.0.0.1", port: int = 8000
    ):
        self.project_root = Path(project_root)
        self.host = host
        self.port = str(port)
        self.detected_frameworks: List[FrameworkInfo] = []

    def detect_framework(self) -> Optional[FrameworkInfo]:
        """Detect the primary framework used in the project."""
        self.detected_frameworks = []

        # check each framework signature
        for framework_name, signature in FRAMEWORK_SIGNATURES.items():
            confidence = self._calculate_confidence(framework_name, signature)

            if confidence > 0.1: # minimum confidence threshold
                # format command with port and host
                commands  = {
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

                # try to detect version
                framework_info.version =  self._detect_version(framework_name)
                self.detected_frameworks.append(framework_info)


        # sort by confidence and return highest confidence framework
        self.detected_frameworks.sort(key=lambda x: x.confidence, reverse=True)

        return self.detected_frameworks[0] if self.detected_frameworks else None



    def _calculate_confidence(self, framework_name: str, signature: Dict) -> float:
        """Calculate confidence score for framework detection."""
        confidence = 0.0
        max_confidence = 0.0

        # Check for specific files
        file_score = self._check_files(signature.get('files', []))
        confidence += file_score * 0.3
        max_confidence += 0.3

        # Check for directories
        dir_score = self._check_directories(signature.get('directories', []))
        confidence += dir_score * 0.2
        max_confidence += 0.2

        # Check for imports in Python files
        import_score = self._check_imports(signature.get('imports', []))
        confidence += import_score * 0.3
        max_confidence += 0.3

        # Check for code patterns
        pattern_score = self._check_patterns(signature.get('patterns', []))
        confidence += pattern_score * 0.2
        max_confidence += 0.2

        return confidence / max_confidence if max_confidence > 0 else 0.0

    def _check_files(self, files: List[str]) -> float:
        """Check for existence of framework-specific files."""
        if not files:
            return 0.0

        found_files = 0
        for file_pattern in files:
            if '*' in file_pattern:
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
        possible_files  =  signature.get('files', [])

        for file_pattern in possible_files:
            if '*' in file_pattern:
                # Handle glob patterns
                matches =  list(self.project_root.glob(file_pattern))
                if matches:
                    return str(matches[0].relative_to(self.project_root))

            else:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    return file_pattern


        # fallback to default file
        fallback_pattern  = [
            f"{framework_name}.py",
            f"{self.project_root.name}.py",

        ]
        for pattern in fallback_pattern:
            file_path = self.project_root / pattern
            if file_path.exists():
                return pattern

        return None


    def _find_config_files(self, framework_name: str, signature: Dict) -> List[str]:
        """Find the framework-specific configuration files."""
        config_files  = []
        possible_files  =  signature.get('config_files', [])

        for file_pattern in possible_files:
            if '*' in file_pattern:
                # Handle glob patterns
                matches =  list(self.project_root.glob(file_pattern))
                config_files.extend(
                    str(m.relative_to(self.project_root))
                    for m in matches
                )
            else:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    config_files.append(file_pattern)


        return config_files


    def _detect_version(self, framework_name: str) -> Optional[str]:
        """Detect the framework version."""
        #  try to find version in requirements files
        pattern = VERSION_PATTERNS.get(framework_name.lower())
        if not pattern:
            return None

        for req_file in REQUIREMENTS_FILES:
            file_path  = self.project_root / req_file

            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        match  = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            return match.group(1)
                except Exception:
                    continue
        # try detect version from framework's own signature version api
        try:
            pass  # TODO
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
        except ImportError:
            pass

        return None

    def get_all_frameworks(self) -> List[FrameworkInfo]:
        """Get all detected frameworks with their confidence scores."""
        return self.detected_frameworks

    def has_framework(self, framework_name: str) -> bool:
        """Check if a specific framework is detected."""
        return any(
            f.name.lower() == framework_name.lower()
            for f in self.detected_frameworks
        )
