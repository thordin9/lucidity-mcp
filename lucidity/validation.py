"""
Input validation functions for security hardening.

This module provides validation functions to prevent:
- Command injection attacks
- Directory traversal attacks  
- Invalid git references
"""

import re
from typing import Any


# Regex patterns for validation
SAFE_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9/_.-]+$")
COMMIT_RANGE_PATTERN = re.compile(r"^[a-zA-Z0-9~^./_-]+\.\.[a-zA-Z0-9~^./_-]+$")
COMMIT_SHA_PATTERN = re.compile(r"^[a-fA-F0-9]{7,40}$")


def is_valid_branch_name(branch: str) -> bool:
    """Validate branch name to prevent directory traversal and injection attacks.

    Args:
        branch: Branch name to validate

    Returns:
        True if branch name is safe, False otherwise

    Examples:
        >>> is_valid_branch_name("main")
        True
        >>> is_valid_branch_name("feature/my-feature")
        True
        >>> is_valid_branch_name("../../etc/passwd")
        False
        >>> is_valid_branch_name("--option")
        False
    """
    if not branch or not isinstance(branch, str):
        return False

    # Check for directory traversal attempts
    if ".." in branch or branch.startswith((".", "-")):
        return False

    # Validate against safe pattern
    return bool(SAFE_BRANCH_PATTERN.match(branch))


def is_valid_commit_range(commits: str) -> bool:
    """Validate commit range format to prevent command injection.

    Args:
        commits: Commit range string (e.g., "HEAD~1..HEAD", "abc123..def456")

    Returns:
        True if commit range is safe, False otherwise

    Examples:
        >>> is_valid_commit_range("HEAD~1..HEAD")
        True
        >>> is_valid_commit_range("abc123..def456")
        True
        >>> is_valid_commit_range("HEAD; rm -rf /")
        False
        >>> is_valid_commit_range("--option")
        False
    """
    if not commits or not isinstance(commits, str):
        return False

    # Check for injection attempts
    if any(char in commits for char in [";", "&", "|", "$", "`", "\n", "\r"]):
        return False

    # Check for git options (starting with -)
    if commits.startswith("-"):
        return False

    # Validate against safe pattern
    return bool(COMMIT_RANGE_PATTERN.match(commits))


def is_valid_path(path: str) -> bool:
    """Validate file path to prevent directory traversal and injection.

    Args:
        path: File path to validate

    Returns:
        True if path is safe, False otherwise

    Examples:
        >>> is_valid_path("src/main.py")
        True
        >>> is_valid_path("../../etc/passwd")
        False
        >>> is_valid_path("--help")
        False
    """
    if not path or not isinstance(path, str):
        return False

    # Check for directory traversal
    normalized = path.replace("\\", "/")
    if ".." in normalized:
        return False

    # Check for git options
    if path.startswith("-"):
        return False

    # Check for shell metacharacters
    if any(char in path for char in [";", "&", "|", "$", "`", "\n", "\r"]):
        return False

    return True


def sanitize_git_command_args(args: list[str]) -> list[str]:
    """Sanitize git command arguments.

    Args:
        args: List of command arguments

    Returns:
        Sanitized list of arguments

    Raises:
        ValueError: If any argument is potentially dangerous
    """
    sanitized = []
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(f"Argument must be string, got {type(arg)}")

        # Check for shell metacharacters
        if any(char in arg for char in [";", "&", "|", "$", "`", "\n", "\r"]):
            raise ValueError(f"Argument contains shell metacharacters: {arg}")

        sanitized.append(arg)

    return sanitized
