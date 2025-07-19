"""
FUSE - (python dev tool) - Utils
File Utils - Robust file system utilities with error handling
"""

from pathlib import Path
from typing import Union, Any

import shutil
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """Robust file system utilities with comprehensive error handling."""

    @staticmethod
    def create_directory(path: Union[str, Path], exist_ok: bool = True) -> None:
        """
        Create a directory if it doesn't exist.

        Args:
            path: Path to directory (str or Path)
            exist_ok: If True, no error raised if directory exists (default: True)

        Raises:
            OSError: If directory creation fails
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=exist_ok)
        except OSError as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise

    @staticmethod
    def write_file(
        path: Union[str, Path],
        content: Any,
        mode: str = "w",
        encoding: str = "utf-8",
        make_dirs: bool = True,
    ) -> None:
        """
        Write content to a file with comprehensive error handling.

        Args:
            path: File path (str or Path)
            content: Content to write
            mode: File mode ('w' for write, 'a' for append)
            encoding: File encoding
            make_dirs: Create parent directories if needed

        Raises:
            IOError: If file writing fails
        """
        path = Path(path)
        try:
            if make_dirs:
                FileUtils.create_directory(path.parent, exist_ok=True)

            with open(path, mode, encoding=encoding) as f:
                if isinstance(content, (str, bytes)):
                    f.write(content)
                else:
                    # Handle non-string content (e.g., JSON serializable objects)
                    import json

                    json.dump(content, f)
        except (IOError, OSError) as e:
            logger.error(f"Failed to write to file {path}: {e}")
            raise

    @staticmethod
    def read_file(
        path: Union[str, Path], mode: str = "r", encoding: str = "utf-8"
    ) -> Union[str, bytes]:
        """
        Read content from a file with error handling.

        Args:
            path: File path (str or Path)
            mode: File mode ('r' for text, 'rb' for binary)
            encoding: File encoding (for text mode)

        Returns:
            File content as str or bytes

        Raises:
            IOError: If file reading fails
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)
        try:
            with open(path, mode, encoding=encoding if "b" not in mode else None) as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            raise
        except (IOError, OSError) as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise

    @staticmethod
    def delete_file(path: Union[str, Path]) -> bool:
        """
        Delete a file if it exists.

        Args:
            path: File path (str or Path)

        Returns:
            True if file was deleted, False if it didn't exist

        Raises:
            OSError: If deletion fails
        """
        path = Path(path)
        try:
            if path.exists():
                path.unlink()
                return True
            return False
        except OSError as e:
            logger.error(f"Failed to delete file {path}: {e}")
            raise

    @staticmethod
    def delete_directory(path: Union[str, Path], ignore_errors: bool = False) -> bool:
        """
        Delete a directory recursively.

        Args:
            path: Directory path (str or Path)
            ignore_errors: If True, ignore errors during deletion

        Returns:
            True if directory was deleted, False if it didn't exist

        Raises:
            OSError: If deletion fails and ignore_errors is False
        """
        path = Path(path)
        try:
            if path.exists():
                shutil.rmtree(path, ignore_errors=ignore_errors)
                return True
            return False
        except OSError as e:
            logger.error(f"Failed to delete directory {path}: {e}")
            if not ignore_errors:
                raise
            return False

    @staticmethod
    def copy_file(
        src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False
    ) -> None:
        """
        Copy a file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Overwrite if destination exists

        Raises:
            IOError: If copy operation fails
        """
        src_path = Path(src)
        dst_path = Path(dst)

        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")

        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"Destination file exists: {dst_path}")

        try:
            shutil.copy2(src_path, dst_path)
        except (IOError, OSError) as e:
            logger.error(f"Failed to copy file from {src_path} to {dst_path}: {e}")
            raise

    @staticmethod
    def file_exists(path: Union[str, Path]) -> bool:
        """Check if a file exists."""
        return Path(path).exists()

    @staticmethod
    def is_file(path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()

    @staticmethod
    def is_dir(path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    @staticmethod
    def get_file_size(path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        return Path(path).stat().st_size

    @staticmethod
    def get_file_extension(path: Union[str, Path]) -> str:
        """Get file extension (including dot)."""
        return Path(path).suffix

    @staticmethod
    def get_file_name(path: Union[str, Path], with_extension: bool = True) -> str:
        """Get file name with or without extension."""
        path = Path(path)
        return path.name if with_extension else path.stem
