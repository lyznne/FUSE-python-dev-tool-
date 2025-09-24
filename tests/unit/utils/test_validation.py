from pathlib import Path

import pytest

from python_dev_tool.core.exceptions import DevToolError
from python_dev_tool.utils.validation import (
    validate_choice,
    validate_config_key,
    validate_environment,
    validate_framework,
    validate_name,
    validate_port,
    validate_positive_int,
    validate_project_path,
    validate_url,
)


class TestValidateProjectPath:
    def test_valid_path(self, tmp_path):
        result = validate_project_path(tmp_path)
        assert isinstance(result, Path)
        assert result == tmp_path.resolve()

    def test_nonexistent_path(self, tmp_path):
        non_existent = tmp_path / "nonexistent"
        with pytest.raises(DevToolError, match="does not exist"):
            validate_project_path(non_existent)

    def test_nonexistent_allowed(self, tmp_path):
        non_existent = tmp_path / "nonexistent"
        result = validate_project_path(
            non_existent, must_exist=False, must_be_dir=False
        )
        assert result == non_existent.resolve()

    def test_file_instead_of_dir(self, tmp_path):
        file_path = tmp_path / "file.txt"
        file_path.touch()
        with pytest.raises(DevToolError, match="not a directory"):
            validate_project_path(file_path)

    def test_hidden_directory(self, tmp_path):
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        with pytest.raises(DevToolError, match="Hidden directories are not allowed"):
            validate_project_path(hidden_dir)

    def test_check_empty_directory(self, tmp_path):
        """Test validation of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Create a file to make directory non-empty
        (empty_dir / "file.txt").write_text("content")

        # Now test that non-empty directory raises error when check_empty=True
        with pytest.raises(DevToolError, match="Project directory is not empty"):
            validate_project_path(empty_dir, check_empty=True)

        # Test that empty directory passes when check_empty=True
        empty_dir2 = tmp_path / "empty2"
        empty_dir2.mkdir()

        # This should NOT raise an error
        result = validate_project_path(empty_dir2, check_empty=True)
        assert result == empty_dir2.resolve()

    def test_relative_path_conversion(self):
        relative_path = Path("relative/path")
        result = validate_project_path(relative_path, must_exist=False)
        assert result.is_absolute()

    def test_hidden_directory_allowed(self, tmp_path):
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        result = validate_project_path(hidden_dir, allow_hidden=True)
        assert result == hidden_dir.resolve()


class TestValidateName:
    def test_valid_name(self):
        assert validate_name("myapp") == "myapp"
        assert validate_name("my-app") == "my-app"
        assert validate_name("my_app") == "my_app"
        assert validate_name("myApp123") == "myApp123"

    def test_empty_name(self):
        with pytest.raises(DevToolError):
            validate_name("")

    def test_too_long_name(self):
        with pytest.raises(DevToolError):
            validate_name("a" * 51)

    def test_invalid_chars(self):
        with pytest.raises(DevToolError):
            validate_name("my app")
        with pytest.raises(DevToolError):
            validate_name("my@pp")

    def test_starts_with_number(self):
        with pytest.raises(DevToolError):
            validate_name("1app")


class TestValidatePort:
    def test_valid_port(self):
        assert validate_port(8000) == 8000
        assert validate_port(1024) == 1024
        assert validate_port(65535) == 65535

    def test_invalid_port(self):
        with pytest.raises(DevToolError):
            validate_port(0)
        with pytest.raises(DevToolError):
            validate_port(65536)
        with pytest.raises(DevToolError):
            validate_port(-1)

    def test_system_port_warning(self):
        with pytest.raises(DevToolError):
            validate_port(80)


class TestValidateFramework:
    def test_valid_frameworks(self):
        assert validate_framework("django") == "django"
        assert validate_framework("Flask") == "flask"
        assert validate_framework("FASTAPI") == "fastapi"

    def test_invalid_framework(self):
        with pytest.raises(DevToolError):
            validate_framework("invalid")


class TestValidateUrl:
    def test_valid_urls(self):
        assert validate_url("http://example.com") == "http://example.com"
        assert validate_url("https://example.com/path") == "https://example.com/path"
        assert validate_url("http://localhost:8000") == "http://localhost:8000"
        assert validate_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"

    def test_invalid_urls(self):
        with pytest.raises(DevToolError):
            validate_url("not a url")
        with pytest.raises(DevToolError):
            validate_url("example.com")  # missing protocol


class TestValidatePositiveInt:
    def test_valid_ints(self):
        assert validate_positive_int(1) == 1
        assert validate_positive_int(100) == 100

    def test_invalid_ints(self):
        with pytest.raises(DevToolError):
            validate_positive_int(0)
        with pytest.raises(DevToolError):
            validate_positive_int(-1)


class TestValidateChoice:
    def test_valid_choice(self):
        choices = ["a", "b", "c"]
        assert validate_choice("a", choices) == "a"
        assert validate_choice("b", choices) == "b"

    def test_invalid_choice(self):
        choices = ["a", "b", "c"]
        with pytest.raises(DevToolError):
            validate_choice("d", choices)


class TestValidateConfigKey:
    def test_valid_keys(self):
        assert validate_config_key("server.port") == "server.port"
        assert validate_config_key("database") == "database"
        assert validate_config_key("auth.token_expiry") == "auth.token_expiry"

    def test_invalid_keys(self):
        with pytest.raises(DevToolError):
            validate_config_key("server port")
        with pytest.raises(DevToolError):
            validate_config_key("server@port")


class TestValidateEnvironment:
    def test_valid_environments(self):
        assert validate_environment("development") == "development"
        assert validate_environment("PRODUCTION") == "production"

    def test_invalid_environment(self):
        with pytest.raises(DevToolError):
            validate_environment("invalid")
