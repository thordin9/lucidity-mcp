"""
Common git command execution utilities.

This module provides reusable functions for executing git commands with
standard error handling, timeouts, and security considerations.
"""

import os
import subprocess

from .config import get_config
from .log import logger
from .validation import sanitize_git_command_args


class GitCommandError(Exception):
    """Exception raised when a git command fails."""

    def __init__(self, command: list[str], stderr: str, returncode: int) -> None:
        """Initialize GitCommandError.

        Args:
            command: The git command that failed
            stderr: Standard error output
            returncode: Command return code
        """
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"Git command failed: {' '.join(command)}")


class GitTimeoutError(Exception):
    """Exception raised when a git command times out."""

    def __init__(self, command: list[str], timeout: int) -> None:
        """Initialize GitTimeoutError.

        Args:
            command: The git command that timed out
            timeout: Timeout value in seconds
        """
        self.command = command
        self.timeout = timeout
        super().__init__(f"Git command timed out after {timeout}s: {' '.join(command)}")


def run_git_command(
    args: list[str],
    cwd: str,
    timeout: int | None = None,
    check: bool = True,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git command with standard error handling and logging.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory for the command
        timeout: Timeout in seconds (uses config default if None)
        check: Whether to raise on non-zero exit code
        env_overrides: Optional environment variable overrides

    Returns:
        CompletedProcess instance with command results

    Raises:
        GitCommandError: If command fails and check=True
        GitTimeoutError: If command times out

    Examples:
        >>> result = run_git_command(["status"], "/path/to/repo")
        >>> result = run_git_command(["diff", "HEAD~1..HEAD"], "/path/to/repo")
    """
    config = get_config()

    # Use default timeout if not specified
    if timeout is None:
        timeout = config.fetch_timeout

    # Sanitize arguments
    try:
        sanitized_args = sanitize_git_command_args(args)
    except ValueError as e:
        logger.error("Invalid git command arguments: %s", e)
        raise

    # Set up environment
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    # Configure SSH behavior based on settings
    if not config.ssh_verify:
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        logger.debug("SSH host key verification disabled")

    command = ["git"] + sanitized_args
    logger.debug("Running git command: %s (cwd=%s, timeout=%s)", command, cwd, timeout)

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,  # We'll handle errors ourselves
            timeout=timeout,
            env=env,
        )

        if result.returncode != 0 and check:
            logger.error("Git command failed: %s (stderr: %s)", command, result.stderr)
            raise GitCommandError(command, result.stderr, result.returncode)

        logger.debug("Git command succeeded: %s", command)
        return result

    except subprocess.TimeoutExpired as e:
        logger.error("Git command timed out after %ds: %s", timeout, command)
        raise GitTimeoutError(command, timeout) from e
    except Exception as e:
        logger.error("Unexpected error running git command %s: %s", command, e)
        raise
