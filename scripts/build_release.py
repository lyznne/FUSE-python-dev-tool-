#!/usr/bin/env python3
"""
FUSE Release Builder
Builds release packages for multiple platforms and package managers
"""

import os
import sys
import shutil
import subprocess
import platform
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class Colors:
    """Terminal colors for output"""

    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


class ReleaseBuilder:
    """Main release builder class"""

    def __init__(self, version: str = None):
        self.root_dir = Path.cwd()
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.release_dir = self.root_dir / "releases"
        self.version = version or self._get_version()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _get_version(self) -> str:
        """Get version from pyproject.toml or __init__.py"""
        try:
            import tomli

            with open(self.root_dir / "pyproject.toml", "rb") as f:
                data = tomli.load(f)
                return data["project"]["version"]
        except:
            # Fallback to reading from __init__.py
            init_file = self.root_dir / "src" / "python_dev_tool" / "__init__.py"
            with open(init_file) as f:
                for line in f:
                    if line.startswith("__version__"):
                        return line.split("=")[1].strip().strip("\"'")
        return "0.1.0"

    def log(self, message: str, color: str = Colors.BLUE):
        """Print colored log message"""
        print(f"{color}{message}{Colors.END}")

    def run_command(self, cmd: List[str], cwd: Path = None) -> bool:
        """Run shell command and return success status"""
        try:
            self.log(f"Running: {' '.join(cmd)}", Colors.YELLOW)
            result = subprocess.run(
                cmd,
                cwd=cwd or self.root_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Error: {e.stderr}", Colors.RED)
            return False

    def clean(self):
        """Clean build directories"""
        self.log("Cleaning build directories...", Colors.BLUE)
        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                shutil.rmtree(directory)
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        self.release_dir.mkdir(exist_ok=True)

    def build_python_package(self):
        """Build Python wheel and source distribution"""
        self.log("Building Python packages...", Colors.GREEN)

        # Build with hatch or setuptools
        if (self.root_dir / "pyproject.toml").exists():
            return self.run_command(["python", "-m", "build"])
        else:
            return self.run_command(["python", "setup.py", "sdist", "bdist_wheel"])

    def build_pyinstaller_binary(self, platform_name: str):
        """Build standalone binary with PyInstaller"""
        self.log(f"Building PyInstaller binary for {platform_name}...", Colors.GREEN)

        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/python_dev_tool/cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/python_dev_tool/templates', 'python_dev_tool/templates'),
        ('src/python_dev_tool/static', 'python_dev_tool/static'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'watchdog',
        'click',
        'toml',
        'jinja2',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='fuse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

        spec_file = self.build_dir / "fuse.spec"
        spec_file.write_text(spec_content)

        return self.run_command(
            ["pyinstaller", "--clean", "--noconfirm", str(spec_file)]
        )

    def package_windows(self):
        """Create Windows installer packages"""
        self.log("Packaging for Windows...", Colors.GREEN)

        if not self.build_pyinstaller_binary("windows"):
            return False

        # Create portable ZIP
        windows_dir = self.release_dir / f"fuse-windows-x64-{self.version}"
        windows_dir.mkdir(exist_ok=True)

        shutil.copy(self.dist_dir / "fuse.exe", windows_dir / "fuse.exe")

        # Create README
        readme = windows_dir / "README.txt"
        readme.write_text(f"""
FUSE {self.version} - Windows Release

Installation:
1. Add the directory containing fuse.exe to your PATH
2. Run 'fuse --help' to get started

Or use the installer to automatically configure PATH.

For more information: https://fuse-dev-tool.github.io
""")

        # Create ZIP archive
        shutil.make_archive(
            str(self.release_dir / f"fuse-windows-x64-{self.version}"),
            "zip",
            windows_dir,
        )

        self.log(
            f"Windows package created: fuse-windows-x64-{self.version}.zip",
            Colors.GREEN,
        )
        return True

    def package_linux(self):
        """Create Linux packages (tarball, deb, rpm)"""
        self.log("Packaging for Linux...", Colors.GREEN)

        if not self.build_pyinstaller_binary("linux"):
            return False

        # Create tarball
        linux_dir = self.release_dir / f"fuse-linux-x64-{self.version}"
        linux_dir.mkdir(exist_ok=True)

        shutil.copy(self.dist_dir / "fuse", linux_dir / "fuse")
        os.chmod(linux_dir / "fuse", 0o755)

        # Create install script
        install_script = linux_dir / "install.sh"
        install_script.write_text("""#!/bin/bash
set -e

echo "Installing FUSE..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

# Copy binary
cp fuse /usr/local/bin/fuse
chmod +x /usr/local/bin/fuse

echo "FUSE installed successfully!"
echo "Run 'fuse --help' to get started"
""")
        os.chmod(install_script, 0o755)

        # Create tarball
        shutil.make_archive(
            str(self.release_dir / f"fuse-linux-x64-{self.version}"), "gztar", linux_dir
        )

        self.log(
            f"Linux tarball created: fuse-linux-x64-{self.version}.tar.gz", Colors.GREEN
        )
        return True

    def package_macos(self):
        """Create macOS packages (DMG)"""
        self.log("Packaging for macOS...", Colors.GREEN)

        if not self.build_pyinstaller_binary("macos"):
            return False

        macos_dir = self.release_dir / f"fuse-macos-{self.version}"
        macos_dir.mkdir(exist_ok=True)

        shutil.copy(self.dist_dir / "fuse", macos_dir / "fuse")
        os.chmod(macos_dir / "fuse", 0o755)

        # Create install script
        install_script = macos_dir / "install.sh"
        install_script.write_text("""#!/bin/bash
set -e

echo "Installing FUSE..."

# Copy binary
sudo cp fuse /usr/local/bin/fuse
sudo chmod +x /usr/local/bin/fuse

echo "FUSE installed successfully!"
echo "Run 'fuse --help' to get started"
""")
        os.chmod(install_script, 0o755)

        # Create tarball (DMG creation requires macOS-specific tools)
        shutil.make_archive(
            str(self.release_dir / f"fuse-macos-{self.version}"), "gztar", macos_dir
        )

        self.log(
            f"macOS package created: fuse-macos-{self.version}.tar.gz", Colors.GREEN
        )
        return True

    def create_checksums(self):
        """Create SHA256 checksums for all release files"""
        self.log("Creating checksums...", Colors.BLUE)

        import hashlib

        checksums = {}
        for file in self.release_dir.glob("*"):
            if file.is_file() and file.suffix in [".zip", ".gz", ".deb", ".rpm"]:
                sha256 = hashlib.sha256()
                with open(file, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                checksums[file.name] = sha256.hexdigest()

        # Write checksums file
        checksums_file = self.release_dir / "SHA256SUMS"
        with open(checksums_file, "w") as f:
            for filename, checksum in checksums.items():
                f.write(f"{checksum}  {filename}\n")

        self.log("Checksums created", Colors.GREEN)

    def generate_release_notes(self):
        """Generate release notes"""
        self.log("Generating release notes...", Colors.BLUE)

        notes = f"""# FUSE {self.version} Release

Release Date: {datetime.now().strftime("%Y-%m-%d")}

## Installation

### Windows
```bash
# Download and extract fuse-windows-x64-{self.version}.zip
# Add to PATH or use installer
fuse --version
```

### Linux
```bash
# Download and extract
tar -xzf fuse-linux-x64-{self.version}.tar.gz
cd fuse-linux-x64-{self.version}
sudo ./install.sh
```

### macOS
```bash
# Download and extract
tar -xzf fuse-macos-{self.version}.tar.gz
cd fuse-macos-{self.version}
./install.sh
```

### PyPI (All platforms)
```bash
pip install fuse-dev-tool=={self.version}
```

## Package Managers

### Homebrew (macOS/Linux)
```bash
brew tap fuse-dev-tool/fuse
brew install fuse
```

### Arch Linux (AUR)
```bash
yay -S fuse-dev-tool
```

## Changes in this release
- See CHANGELOG.md for detailed changes

## Verification
Download SHA256SUMS and verify:
```bash
sha256sum -c SHA256SUMS
```
"""

        notes_file = self.release_dir / "RELEASE_NOTES.md"
        notes_file.write_text(notes)

        self.log("Release notes generated", Colors.GREEN)

    def build_all(self):
        """Build packages for all platforms"""
        self.log(
            f"Building FUSE {self.version} for all platforms...",
            Colors.BOLD + Colors.GREEN,
        )

        # Clean first
        self.clean()

        # Build Python package (universal)
        if not self.build_python_package():
            self.log("Failed to build Python package", Colors.RED)
            return False

        # Detect current platform and build appropriate package
        current_os = platform.system().lower()

        if current_os == "windows":
            self.package_windows()
        elif current_os == "linux":
            self.package_linux()
        elif current_os == "darwin":
            self.package_macos()

        # Create checksums and release notes
        self.create_checksums()
        self.generate_release_notes()

        self.log(
            f"\n{Colors.BOLD}{Colors.GREEN}Build completed successfully!{Colors.END}",
            Colors.GREEN,
        )
        self.log(f"Release files in: {self.release_dir}", Colors.BLUE)

        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Build FUSE release packages")
    parser.add_argument(
        "--version", help="Version to build (default: from pyproject.toml)"
    )
    parser.add_argument(
        "--platform",
        choices=["windows", "linux", "macos", "all"],
        default="all",
        help="Platform to build for",
    )
    parser.add_argument(
        "--clean-only", action="store_true", help="Only clean build directories"
    )

    args = parser.parse_args()

    builder = ReleaseBuilder(version=args.version)

    if args.clean_only:
        builder.clean()
        return

    if args.platform == "all":
        success = builder.build_all()
    elif args.platform == "windows":
        builder.clean()
        success = builder.package_windows()
    elif args.platform == "linux":
        builder.clean()
        success = builder.package_linux()
    elif args.platform == "macos":
        builder.clean()
        success = builder.package_macos()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
