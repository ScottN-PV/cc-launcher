"""Unit tests for validators and env_expander."""

import pytest
import os
import tempfile
from pathlib import Path
from utils.validators import (
    validate_path,
    validate_url,
    validate_command,
    sanitize_path_for_command
)
from utils.env_expander import (
    expand_env_vars,
    expand_env_vars_in_list,
    get_preview
)


class TestValidatePath:
    """Tests for path validation."""

    def test_valid_existing_path(self, tmp_path):
        """Test validation of existing directory."""
        is_valid, error = validate_path(str(tmp_path))
        assert is_valid is True
        assert error == ""

    def test_empty_path(self):
        """Test validation of empty path."""
        is_valid, error = validate_path("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_nonexistent_path(self):
        """Test validation of non-existent path."""
        is_valid, error = validate_path("C:\\NonExistentPath123456")
        assert is_valid is False
        assert "not exist" in error.lower()

    def test_file_instead_of_directory(self, tmp_path):
        """Test validation when path is a file, not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        is_valid, error = validate_path(str(test_file))
        assert is_valid is False
        assert "not a directory" in error.lower()


class TestValidateURL:
    """Tests for URL validation."""

    def test_valid_http_url(self):
        """Test validation of HTTP URL."""
        is_valid, error = validate_url("http://localhost:3000")
        assert is_valid is True
        assert error == ""

    def test_valid_https_url(self):
        """Test validation of HTTPS URL."""
        is_valid, error = validate_url("https://example.com/api")
        assert is_valid is True
        assert error == ""

    def test_empty_url(self):
        """Test validation of empty URL."""
        is_valid, error = validate_url("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_missing_scheme(self):
        """Test validation of URL without scheme."""
        is_valid, error = validate_url("example.com")
        assert is_valid is False
        assert "scheme" in error.lower()

    def test_invalid_scheme(self):
        """Test validation of URL with invalid scheme."""
        is_valid, error = validate_url("ftp://example.com")
        assert is_valid is False
        assert "http" in error.lower()


class TestValidateCommand:
    """Tests for command validation."""

    def test_valid_command(self):
        """Test validation of safe command."""
        is_valid, error = validate_command("cmd", ["/c", "echo", "hello"])
        assert is_valid is True
        assert error == ""

    def test_empty_command(self):
        """Test validation of empty command."""
        is_valid, error = validate_command("", [])
        assert is_valid is False
        assert "empty" in error.lower()

    def test_command_injection_semicolon(self):
        """Test detection of command injection with semicolon."""
        is_valid, error = validate_command("cmd; rm -rf /", [])
        assert is_valid is False
        assert "dangerous" in error.lower()

    def test_command_injection_in_args(self):
        """Test detection of command injection in arguments."""
        is_valid, error = validate_command("cmd", ["/c", "echo test && rm -rf /"])
        assert is_valid is False
        assert "injection" in error.lower()

    def test_command_substitution_backtick(self):
        """Test detection of command substitution with backticks."""
        is_valid, error = validate_command("cmd", ["/c", "echo `whoami`"])
        assert is_valid is False
        assert "injection" in error.lower()

    def test_command_substitution_dollar(self):
        """Test detection of command substitution with $()."""
        is_valid, error = validate_command("cmd", ["/c", "echo $(whoami)"])
        assert is_valid is False
        assert "injection" in error.lower()


class TestSanitizePath:
    """Tests for path sanitization."""

    def test_path_without_spaces(self):
        """Test sanitization of path without spaces."""
        result = sanitize_path_for_command("C:\\Dev\\project")
        assert result == "C:\\Dev\\project"

    def test_path_with_spaces(self):
        """Test sanitization of path with spaces."""
        result = sanitize_path_for_command("C:\\Dev\\my project")
        assert result == '"C:\\Dev\\my project"'

    def test_already_quoted_path(self):
        """Test sanitization of already quoted path."""
        result = sanitize_path_for_command('"C:\\Dev\\my project"')
        assert result == '"C:\\Dev\\my project"'


class TestExpandEnvVars:
    """Tests for environment variable expansion."""

    def test_expand_cd_variable(self):
        """Test expansion of %CD% variable."""
        result = expand_env_vars("%CD%\\data", "C:\\Projects\\test")
        assert result == "C:\\Projects\\test\\data"

    def test_expand_userprofile(self):
        """Test expansion of %USERPROFILE% variable."""
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            result = expand_env_vars("%USERPROFILE%\\Documents", "C:\\Projects")
            assert result == f"{userprofile}\\Documents"

    def test_expand_temp(self):
        """Test expansion of %TEMP% variable."""
        temp = os.environ.get("TEMP", "")
        if temp:
            result = expand_env_vars("%TEMP%\\file.txt", "C:\\Projects")
            assert result == f"{temp}\\file.txt"

    def test_expand_multiple_variables(self):
        """Test expansion of multiple variables in one string."""
        result = expand_env_vars("%CD%\\data\\%USERNAME%", "C:\\Projects")
        assert "C:\\Projects\\data\\" in result
        # Username should be expanded
        assert "%USERNAME%" not in result

    def test_expand_with_extra_vars(self):
        """Test expansion with additional custom variables."""
        extra = {"CUSTOM": "custom_value"}
        result = expand_env_vars("%CUSTOM%\\file", "C:\\Projects", extra)
        assert result == "custom_value\\file"

    def test_expand_case_insensitive(self):
        """Test case insensitive expansion."""
        result1 = expand_env_vars("%cd%\\data", "C:\\Projects")
        result2 = expand_env_vars("%CD%\\data", "C:\\Projects")
        assert result1 == result2 == "C:\\Projects\\data"

    def test_expand_nonexistent_variable(self):
        """Test expansion of non-existent variable (should leave as-is)."""
        result = expand_env_vars("%NONEXISTENT%\\file", "C:\\Projects")
        assert result == "%NONEXISTENT%\\file"


class TestExpandEnvVarsInList:
    """Tests for list expansion."""

    def test_expand_list(self):
        """Test expansion in list of strings."""
        values = ["/c", "npx", "-y", "server", "%CD%"]
        result = expand_env_vars_in_list(values, "C:\\Projects\\test")
        assert result == ["/c", "npx", "-y", "server", "C:\\Projects\\test"]

    def test_expand_empty_list(self):
        """Test expansion of empty list."""
        result = expand_env_vars_in_list([], "C:\\Projects")
        assert result == []


class TestGetPreview:
    """Tests for preview generation."""

    def test_preview_with_cd(self):
        """Test preview generation with %CD%."""
        preview = get_preview("%CD%\\data", "C:\\Dev\\project")
        assert preview == "C:\\Dev\\project\\data"

    def test_preview_with_multiple_vars(self):
        """Test preview with multiple variables."""
        preview = get_preview("%CD%\\%USERNAME%", "C:\\Dev")
        assert "C:\\Dev\\" in preview
        assert "%USERNAME%" not in preview


if __name__ == "__main__":
    pytest.main([__file__, "-v"])