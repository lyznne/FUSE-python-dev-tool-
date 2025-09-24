"""
FUSE - (python dev tool) - CLI Commands - Update Command
CLI - Update Command
Handles updating the python-dev-tool to latest or specific versions
"""

# sys imports
from dataclasses import dataclass
import os
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from packaging import version

# 3rd party imports
import requests
from rich.console import Console

# local imports
from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.core.config import Config


@dataclass
class UpdateOptions:
    """Options for update command."""

    target_version: Optional[str]
    include_pre_release: bool
    force: bool
    check_only: bool
    verbose: bool


class UpdateCommand:
    """Command to update the python-dev-tool"""

    def __init__(
        self,
        target_version: Optional[str] = None,
        include_pre_release: bool = False,
        force: bool = False,
        check_only: bool = False,
        verbose: bool = False,
    ):
        self.options = UpdateOptions(
            target_version=target_version,
            include_pre_release=include_pre_release,
            force=force,
            check_only=check_only,
            verbose=verbose,
        )
        self.console = Console()
        self.package_name = "python-dev-tool"
        self.current_version = self._get_current_version()

    def _get_current_version(self) -> str:
        """Get the currently installed version"""
        try:
            # Try to get version from package metadata
            import importlib.metadata

            return importlib.metadata.version(self.package_name)
        except Exception:
            # Fallback to hardcoded version
            from python_dev_tool.cli.main import __version__

            return __version__

    def check_for_updates(self) -> Dict[str, Any]:
        """Check if updates are available"""
        try:
            # Get available versions from PyPI
            response = requests.get(
                f"https://pypi.org/pypi/{self.package_name}/json", timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Get all versions
            all_versions = list(data["releases"].keys())

            # Filter versions based on pre-release preference
            if not self.include_pre_release:
                # Only stable releases
                stable_versions = [
                    v for v in all_versions if not version.parse(v).is_prerelease
                ]
                available_versions = stable_versions
            else:
                available_versions = all_versions

            # Sort versions
            sorted_versions = sorted(
                available_versions, key=version.parse, reverse=True
            )

            if not sorted_versions:
                return {
                    "update_available": False,
                    "current_version": self.current_version,
                    "latest_version": self.current_version,
                    "error": "No versions found",
                }

            # Determine target version
            if self.target_version:
                if self.target_version in available_versions:
                    latest_version = self.target_version
                else:
                    return {
                        "update_available": False,
                        "current_version": self.current_version,
                        "latest_version": self.current_version,
                        "error": f"Version {self.target_version} not found",
                    }
            else:
                latest_version = sorted_versions[0]

            # Check if update is needed
            current_parsed = version.parse(self.current_version)
            latest_parsed = version.parse(latest_version)

            update_available = latest_parsed > current_parsed or (
                self.target_version and latest_version != self.current_version
            )

            # Get changelog/release notes if available
            changelog = []
            try:
                release_info = data["releases"][latest_version]
                if release_info:
                    # Try to get release notes from GitHub releases
                    changelog = self._get_changelog(latest_version)
            except Exception:
                pass

            return {
                "update_available": update_available,
                "current_version": self.current_version,
                "latest_version": latest_version,
                "all_versions": sorted_versions[:10],  # Top 10 versions
                "changelog": changelog,
                "release_date": self._get_release_date(data, latest_version),
            }

        except requests.RequestException as e:
            raise DevToolError(f"Failed to check for updates: {e}")
        except Exception as e:
            raise DevToolError(f"Update check failed: {e}")

    def _get_changelog(self, version_tag: str) -> List[str]:
        """Get changelog for a specific version"""
        try:
            # Try to get from GitHub releases API
            github_repo = "your-org/python-dev-tool"

            response = requests.get(
                f"https://api.github.com/repos/{github_repo}/releases/tags/v{version_tag}",
                timeout=5,
            )

            if response.status_code == 200:
                release_data = response.json()
                body = release_data.get("body", "")

                # Parse markdown changelog
                changes = []
                for line in body.split("\n"):
                    line = line.strip()
                    if line.startswith("- ") or line.startswith("* "):
                        changes.append(line[2:])
                    elif line.startswith("## "):
                        break  # Stop at next section

                return changes[:10]  # Limit to 10 changes

        except Exception:
            pass

        return ["See GitHub releases for changelog"]

    def _get_release_date(self, pypi_data: Dict, version_str: str) -> Optional[str]:
        """Get release date for a version"""
        try:
            release_info = pypi_data["releases"][version_str]
            if release_info:
                return release_info[0]["upload_time"]
        except Exception:
            pass
        return None

    def create_backup(self) -> Dict[str, Any]:
        """Create backup of current installation"""
        try:
            # Find current installation directory
            import python_dev_tool

            current_install_path = Path(python_dev_tool.__file__).parent.parent

            # Create backup directory
            backup_dir = Path.home() / ".fuse" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_name = f"fuse-{self.current_version}-backup"
            backup_path = backup_dir / backup_name

            # Remove existing backup if it exists
            if backup_path.exists():
                shutil.rmtree(backup_path)

            # Copy current installation
            shutil.copytree(current_install_path, backup_path)

            if self.verbose:
                self.console.print(f"[dim]Backup created: {backup_path}[/dim]")

            return {
                "success": True,
                "backup_path": backup_path,
                "backup_size": self._get_dir_size(backup_path),
            }

        except Exception as e:
            raise DevToolError(f"Failed to create backup: {e}")

    def download_update(self, target_version: str) -> Dict[str, Any]:
        """Download the update package"""
        try:
            # Create temporary directory for download
            temp_dir = Path(tempfile.mkdtemp(prefix="fuse-update-"))

            # Use pip to download package
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "download",
                f"{self.package_name}=={target_version}",
                "--dest",
                str(temp_dir),
                "--no-deps",
            ]

            if self.verbose:
                self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Find downloaded package
            downloaded_files = list(temp_dir.glob("*.whl"))
            if not downloaded_files:
                downloaded_files = list(temp_dir.glob("*.tar.gz"))

            if not downloaded_files:
                raise DevToolError("No package file found after download")

            package_path = downloaded_files[0]

            return {
                "success": True,
                "package_path": package_path,
                "temp_dir": temp_dir,
                "package_size": package_path.stat().st_size,
            }

        except subprocess.CalledProcessError as e:
            raise DevToolError(f"Download failed: {e.stderr}")
        except Exception as e:
            raise DevToolError(f"Download error: {e}")

    def install_update(self, package_path: Path) -> Dict[str, Any]:
        """Install the downloaded update"""
        try:
            # Use pip to install the package
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                str(package_path),
                "--force-reinstall",
                "--no-deps",
            ]

            if self.verbose:
                self.console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Clean up temp directory
            temp_dir = package_path.parent
            shutil.rmtree(temp_dir)

            return {"success": True, "output": result.stdout}

        except subprocess.CalledProcessError as e:
            raise DevToolError(f"Installation failed: {e.stderr}")
        except Exception as e:
            raise DevToolError(f"Installation error: {e}")

    def verify_installation(self) -> Dict[str, Any]:
        """Verify the installation was successful"""
        try:
            # Try to import and get version
            import importlib
            import sys

            # Clear module cache to get fresh import
            if "python_dev_tool" in sys.modules:
                importlib.reload(sys.modules["python_dev_tool"])

            # Get new version
            new_version = self._get_current_version()

            # Try to run basic command
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from python_dev_tool.cli.main import app; print('OK')",
                ],
                capture_output=True,
                text=True,
            )

            success = result.returncode == 0 and "OK" in result.stdout

            return {
                "success": success,
                "new_version": new_version,
                "old_version": self.current_version,
                "test_output": result.stdout if success else result.stderr,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "new_version": "unknown",
                "old_version": self.current_version,
            }

    def rollback(self, backup_path: Path) -> Dict[str, Any]:
        """Rollback to backup version"""
        try:
            if not backup_path.exists():
                return {"success": False, "error": "Backup path not found"}

            # Find current installation directory
            import python_dev_tool

            current_install_path = Path(python_dev_tool.__file__).parent.parent

            # Remove current installation
            if current_install_path.exists():
                shutil.rmtree(current_install_path)

            # Restore from backup
            shutil.copytree(backup_path, current_install_path)

            # Verify rollback
            restored_version = self._get_current_version()

            return {
                "success": True,
                "restored_version": restored_version,
                "backup_path": backup_path,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup_backup(self, backup_path: Path) -> bool:
        """Clean up backup directory"""
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            return True
        except Exception:
            return False

    def _get_dir_size(self, path: Path) -> int:
        """Get directory size in bytes"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
