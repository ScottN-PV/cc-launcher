"""Environment variable expansion utilities for Claude Code Launcher."""

import os
import re
from typing import Dict


def expand_env_vars(value: str, project_path: str, extra_vars: Dict[str, str] = None) -> str:
    """
    Expand Windows environment variables in a string.

    Supports:
    - %CD% -> project_path
    - %USERPROFILE% -> user's home directory
    - %TEMP% -> temp directory
    - %PATH% -> system PATH
    - Any other %VAR% -> os.environ['VAR']

    Args:
        value: String potentially containing environment variables
        project_path: Current project directory (replaces %CD%)
        extra_vars: Additional variables to expand

    Returns:
        String with all environment variables expanded
    """
    if not value:
        return value

    # Create expanded vars dict
    expanded_vars = extra_vars.copy() if extra_vars else {}

    # Add special CD variable
    expanded_vars["CD"] = project_path
    expanded_vars["cd"] = project_path  # Case insensitive

    # Find all %VAR% patterns
    pattern = r"%([^%]+)%"
    matches = re.findall(pattern, value)

    result = value
    for var_name in matches:
        var_upper = var_name.upper()
        var_lower = var_name.lower()

        # Check extra vars first
        if var_name in expanded_vars:
            replacement = expanded_vars[var_name]
        elif var_upper in expanded_vars:
            replacement = expanded_vars[var_upper]
        elif var_lower in expanded_vars:
            replacement = expanded_vars[var_lower]
        # Then check environment variables (case insensitive on Windows)
        elif var_upper in os.environ:
            replacement = os.environ[var_upper]
        elif var_name in os.environ:
            replacement = os.environ[var_name]
        else:
            # Variable not found, leave as-is
            continue

        # Replace the variable
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