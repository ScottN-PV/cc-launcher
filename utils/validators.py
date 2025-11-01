"""Input validation utilities for Claude Code Launcher."""

import os
import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse


def validate_path(path: str) -> Tuple[bool, str]:
    """
    Validate a file system path.

    Args:
        path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path or path.strip() == "":
        return False, "Path cannot be empty"

    try:
        # Expand environment variables first
        expanded_path = os.path.expandvars(path)
        path_obj = Path(expanded_path)

        # Check if path exists
        if not path_obj.exists():
            return False, f"Path does not exist: {expanded_path}"

        # Check if it's a directory
        if not path_obj.is_dir():
            return False, f"Path is not a directory: {expanded_path}"

        # Check if readable
        if not os.access(path_obj, os.R_OK):
            return False, f"Path is not readable: {expanded_path}"

        return True, ""

    except (ValueError, OSError) as e:
        return False, f"Invalid path: {str(e)}"


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate an HTTP/HTTPS URL.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or url.strip() == "":
        return False, "URL cannot be empty"

    try:
        result = urlparse(url)

        # Must have scheme and netloc
        if not result.scheme:
            return False, "URL must have a scheme (http:// or https://)"

        if not result.netloc:
            return False, "URL must have a host"

        # Only allow HTTP and HTTPS
        if result.scheme not in ["http", "https"]:
            return False, f"URL scheme must be http or https, got: {result.scheme}"

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_command(command: str, args: list) -> Tuple[bool, str]:
    """
    Validate command and arguments to prevent injection attacks.

    Args:
        command: Command to execute
        args: List of arguments

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not command or command.strip() == "":
        return False, "Command cannot be empty"

    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        if char in command:
            return False, f"Command contains dangerous character: {char}"

    for arg in args:
        if not isinstance(arg, str):
            return False, f"Argument must be a string, got: {type(arg).__name__}"

        injection_patterns = [
            r";\s*\w",
            r"&&",
            r"\|\|",
            r"`",
            r"\$\(",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, arg):
                return False, f"Argument contains potential injection pattern: {pattern}"

    return True, ""


def sanitize_path_for_command(path: str) -> str:
    """
    Sanitize a path for use in command line arguments.
    Adds quotes if path contains spaces.

    Args:
        path: Path to sanitize

    Returns:
        Sanitized path safe for command line use
    """
    # If path contains spaces, wrap in quotes
    if " " in path and not (path.startswith('"') and path.endswith('"')):
        return f'"{path}"'
    return path