"""
Git utility functions for handling local and remote repositories.

This module provides utilities to:
- Check if a directory is a git repository
- Clone remote repositories when not available locally
- Fetch/update existing cloned repositories
"""

import os
import shutil
import subprocess
import tempfile
from typing import Any

from ..log import logger


def is_git_repository(path: str) -> bool:
    """Check if the given path is a git repository.

    Args:
        path: The directory path to check

    Returns:
        True if the path is a git repository, False otherwise
    """
    git_dir = os.path.join(path, ".git")
    return os.path.exists(git_dir) and os.path.isdir(git_dir)


def extract_repo_info_from_path(workspace_root: str) -> dict[str, Any] | None:
    """Try to extract remote repository information from a path.

    This function attempts to parse a workspace_root that might be in the format:
    - git@github.com:username/repo.git
    - https://github.com/username/repo.git
    - github.com/username/repo
    - username/repo (assumes github.com)

    Args:
        workspace_root: The workspace root path or URL

    Returns:
        Dictionary with 'url' and 'name' keys if parseable, None otherwise
    """
    if not workspace_root:
        return None

    # If it's a local path that exists, no need to parse
    if os.path.exists(workspace_root):
        return None

    # Try to detect if this looks like a git URL
    workspace_root = workspace_root.strip()

    # Handle SSH format: git@github.com:username/repo.git
    if workspace_root.startswith("git@"):
        logger.debug("Detected SSH git URL format: %s", workspace_root)
        return {"url": workspace_root, "name": _extract_repo_name(workspace_root)}

    # Handle HTTPS format: https://github.com/username/repo.git
    if workspace_root.startswith(("https://", "http://")):
        logger.debug("Detected HTTPS git URL format: %s", workspace_root)
        return {"url": workspace_root, "name": _extract_repo_name(workspace_root)}

    # Handle github.com/username/repo format
    if "/" in workspace_root and not workspace_root.startswith("/"):
        # Assume it's a github repository
        if not workspace_root.startswith("github.com"):
            # Try username/repo format
            if workspace_root.count("/") == 1:
                workspace_root = f"github.com/{workspace_root}"

        logger.debug("Detected short format, assuming GitHub: %s", workspace_root)
        # Convert to SSH URL (assuming SSH key is available per requirements)
        if workspace_root.startswith("github.com/"):
            ssh_url = f"git@{workspace_root.replace('/', ':', 1)}.git"
            return {"url": ssh_url, "name": _extract_repo_name(workspace_root)}

    return None


def _extract_repo_name(url: str) -> str:
    """Extract repository name from a git URL.

    Args:
        url: Git repository URL

    Returns:
        Repository name
    """
    # Remove .git suffix if present
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Extract the last part of the path
    parts = url.replace(":", "/").split("/")
    return parts[-1] if parts else "repo"


def get_clone_directory(repo_name: str) -> str:
    """Get the directory path where a repository should be cloned.

    Creates a temporary directory structure for cloned repositories.

    Args:
        repo_name: Name of the repository

    Returns:
        Path to the directory where the repo should be cloned
    """
    # Create a dedicated directory for cloned repos in temp
    clone_base = os.path.join(tempfile.gettempdir(), "lucidity-mcp-repos")
    os.makedirs(clone_base, exist_ok=True)

    return os.path.join(clone_base, repo_name)


def clone_repository(repo_url: str, repo_name: str) -> str | None:
    """Clone a git repository to a temporary location.

    Args:
        repo_url: The git repository URL to clone
        repo_name: Name for the cloned repository directory

    Returns:
        Path to the cloned repository, or None if cloning failed
    """
    clone_path = get_clone_directory(repo_name)

    logger.info("Attempting to clone repository %s to %s", repo_url, clone_path)

    try:
        # If the directory already exists and is a git repo, try to update it instead
        if is_git_repository(clone_path):
            logger.info("Repository already exists at %s, attempting to update", clone_path)
            if update_repository(clone_path):
                return clone_path
            logger.warning("Failed to update existing repository, will try to re-clone")
            # If update fails, remove and re-clone
            shutil.rmtree(clone_path)

        # Clone the repository
        result = subprocess.run(
            ["git", "clone", repo_url, clone_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout for cloning
        )
        logger.debug("Clone output: %s", result.stdout)
        logger.info("Successfully cloned repository to %s", clone_path)
        return clone_path

    except subprocess.TimeoutExpired:
        logger.error("Timeout while cloning repository %s", repo_url)
        return None
    except subprocess.CalledProcessError as e:
        logger.error("Error cloning repository %s: %s (stderr: %s)", repo_url, e, e.stderr)
        return None
    except Exception as e:
        logger.error("Unexpected error cloning repository %s: %s", repo_url, e)
        return None


def update_repository(repo_path: str) -> bool:
    """Update an existing git repository by fetching latest changes.

    Args:
        repo_path: Path to the git repository

    Returns:
        True if update was successful, False otherwise
    """
    if not is_git_repository(repo_path):
        logger.error("Path %s is not a git repository", repo_path)
        return False

    logger.info("Updating repository at %s", repo_path)

    try:
        # Store current directory
        current_dir = os.getcwd()

        try:
            # Change to repository directory
            os.chdir(repo_path)

            # Fetch latest changes
            result = subprocess.run(
                ["git", "fetch", "--all"],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,  # 1 minute timeout for fetching
            )
            logger.debug("Fetch output: %s", result.stdout)

            # Pull changes for the current branch
            result = subprocess.run(
                ["git", "pull"],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            logger.debug("Pull output: %s", result.stdout)

            logger.info("Successfully updated repository at %s", repo_path)
            return True

        finally:
            # Restore original directory
            os.chdir(current_dir)

    except subprocess.TimeoutExpired:
        logger.error("Timeout while updating repository at %s", repo_path)
        return False
    except subprocess.CalledProcessError as e:
        logger.error("Error updating repository at %s: %s (stderr: %s)", repo_path, e, e.stderr)
        return False
    except Exception as e:
        logger.error("Unexpected error updating repository at %s: %s", repo_path, e)
        return False


def ensure_repository(workspace_root: str) -> str | None:
    """Ensure a git repository is available, cloning if necessary.

    This function:
    1. Checks if workspace_root is already a local git repository
    2. If not, tries to parse it as a remote repository URL
    3. Clones the remote repository to a temporary location if needed

    Args:
        workspace_root: Either a local path to a git repository or a remote git URL

    Returns:
        Path to the git repository (local or cloned), or None if unavailable
    """
    logger.debug("Ensuring repository is available: %s", workspace_root)

    # Check if it's already a local git repository
    if is_git_repository(workspace_root):
        logger.debug("Workspace root %s is already a git repository", workspace_root)
        return workspace_root

    # Try to parse as a remote repository
    repo_info = extract_repo_info_from_path(workspace_root)
    if repo_info:
        logger.info("Workspace root appears to be a remote repository: %s", repo_info["url"])
        cloned_path = clone_repository(repo_info["url"], repo_info["name"])
        if cloned_path:
            return cloned_path
        logger.error("Failed to clone remote repository")
        return None

    # If it's a local path but not a git repository
    if os.path.exists(workspace_root):
        logger.warning("Path %s exists but is not a git repository", workspace_root)
    else:
        logger.warning("Path %s does not exist and could not be parsed as a remote URL", workspace_root)

    return None
