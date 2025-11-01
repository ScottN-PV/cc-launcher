"""Environment variable expansion utilities for Claude Code MCP Manager."""

import os
import re
import sys
from pathlib import Path
from typing import Dict


def expand_env_vars(value: str, project_path: str, extra_vars: Dict[str, str] = None) -> str:
    """
    Expand environment variables (cross-platform).

    Supports Windows (%VAR%) and Unix ($VAR, ${VAR}) syntax.
    Special vars: %CD%/$PWD -> project_path, %USERPROFILE%/$HOME -> home dir.

    Args:
        value: String potentially containing environment variables
        project_path: Current project directory
        extra_vars: Additional variables to expand

    Returns:
        String with all environment variables expanded
    """
    if not value:
        return value

    expanded_vars = extra_vars.copy() if extra_vars else {}

    # Map project path to common environment variable names
    expanded_vars["CD"] = project_path
    expanded_vars["cd"] = project_path
    expanded_vars["PWD"] = project_path
    expanded_vars["pwd"] = project_path

    is_windows = sys.platform == "win32"
    result = value

    # Unix-style: $VAR or ${VAR}
    if not is_windows or "$" in result:
        unix_pattern = r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)"
        unix_matches = re.finditer(unix_pattern, result)
        
        replacements = {}
        for match in unix_matches:
            var_name = match.group(1) or match.group(2)
            full_match = match.group(0)
            
            if var_name in expanded_vars:
                replacements[full_match] = expanded_vars[var_name]
            elif var_name in os.environ:
                replacements[full_match] = os.environ[var_name]
            elif var_name.upper() == "HOME" and "HOME" in os.environ:
                replacements[full_match] = os.environ["HOME"]
            elif var_name.upper() == "HOME":
                replacements[full_match] = str(Path.home())
        
        for old, new in replacements.items():
            result = result.replace(old, new)

    # Windows-style: %VAR%
    if is_windows or "%" in result:
        windows_pattern = r"%([^%]+)%"
        windows_matches = re.findall(windows_pattern, result)

        for var_name in windows_matches:
            var_upper = var_name.upper()
            var_lower = var_name.lower()

            if var_name in expanded_vars:
                replacement = expanded_vars[var_name]
            elif var_upper in expanded_vars:
                replacement = expanded_vars[var_upper]
            elif var_lower in expanded_vars:
                replacement = expanded_vars[var_lower]
            elif var_upper in os.environ:
                replacement = os.environ[var_upper]
            elif var_name in os.environ:
                replacement = os.environ[var_name]
            else:
                continue

            result = result.replace(f"%{var_name}%", replacement)

    return result


def expand_env_vars_in_list(values: list, project_path: str, extra_vars: Dict[str, str] = None) -> list:
    """
    Expand environment variables in a list of strings.

    Args:
        values: List of strings potentially containing environment variables
        project_path: Current project directory (replaces %CD%)
        extra_vars: Additional variables to expand

    Returns:
        List with all environment variables expanded
    """
    return [expand_env_vars(v, project_path, extra_vars) for v in values]


def get_preview(value: str, project_path: str) -> str:
    """
    Get a preview of what a value will look like after expansion.
    Used for UI preview in server dialog.

    Args:
        value: String with environment variables
        project_path: Current project directory

    Returns:
        Expanded preview string
    """
    return expand_env_vars(value, project_path)