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
    - git@github.com:username/repo.git@branch (with branch specification)
    - https://github.com/username/repo.git
    - https://github.com/username/repo.git@branch (with branch specification)
    - github.com/username/repo
    - github.com/username/repo@branch (with branch specification)
    - username/repo (assumes github.com)
    - username/repo@branch (with branch specification)

    Args:
        workspace_root: The workspace root path or URL, optionally with @branch suffix

    Returns:
        Dictionary with 'url', 'name', and optional 'branch' keys if parseable, None otherwise
    """
    if not workspace_root:
        return None

    # If it's a local path that exists, no need to parse
    if os.path.exists(workspace_root):
        return None

    # Try to detect if this looks like a git URL
    workspace_root = workspace_root.strip()

    # Check for branch specification in the format @branch at the end
    branch = None
    # First check if it starts with git@ to avoid splitting on that @
    if workspace_root.startswith("git@"):
        # Look for a second @ which would indicate a branch
        second_at = workspace_root.find("@", 4)  # Start search after "git@"
        if second_at != -1:
            # Extract branch and clean up the URL
            branch = workspace_root[second_at + 1:]
            workspace_root = workspace_root[:second_at]
            # Validate branch (no slashes, no dots at start)
            if "/" not in branch and not branch.startswith("."):
                logger.debug("Detected branch specification: %s", branch)
            else:
                # Invalid branch format, restore
                workspace_root = workspace_root + "@" + branch
                branch = None
    elif "@" in workspace_root and not workspace_root.startswith(("http://", "https://")):
        # Split on the last @ for other formats
        parts = workspace_root.rsplit("@", 1)
        if len(parts) == 2 and "/" not in parts[1] and not parts[1].startswith("."):
            workspace_root = parts[0]
            branch = parts[1]
            logger.debug("Detected branch specification: %s", branch)
    elif workspace_root.startswith(("https://", "http://")):
        # For HTTPS URLs, check for @branch at the end
        if "@" in workspace_root:
            parts = workspace_root.rsplit("@", 1)
            if len(parts) == 2 and "/" not in parts[1] and not parts[1].startswith("."):
                workspace_root = parts[0]
                branch = parts[1]
                logger.debug("Detected branch specification: %s", branch)

    # Handle SSH format: git@github.com:username/repo.git
    if workspace_root.startswith("git@"):
        logger.debug("Detected SSH git URL format: %s", workspace_root)
        result = {"url": workspace_root, "name": _extract_repo_name(workspace_root)}
        if branch:
            result["branch"] = branch
        return result

    # Handle HTTPS format: https://github.com/username/repo.git
    if workspace_root.startswith(("https://", "http://")):
        logger.debug("Detected HTTPS git URL format: %s", workspace_root)
        result = {"url": workspace_root, "name": _extract_repo_name(workspace_root)}
        if branch:
            result["branch"] = branch
        return result

    # Handle github.com/username/repo format
    if "/" in workspace_root and not workspace_root.startswith("/"):
        # Normalize and validate GitHub repository format
        parts = workspace_root.split("/")

        # Check if it's already in github.com/username/repo format
        if len(parts) >= 3 and parts[0] == "github.com":
            # Valid format: github.com/username/repo
            username = parts[1]
            repo = parts[2]
            ssh_url = f"git@github.com:{username}/{repo}.git"
            logger.debug("Detected GitHub format: %s -> %s", workspace_root, ssh_url)
            result = {"url": ssh_url, "name": _extract_repo_name(repo)}
            if branch:
                result["branch"] = branch
            return result

        # Check if it's in username/repo format (exactly 2 parts)
        if len(parts) == 2 and not parts[0].startswith("."):
            # Assume it's a GitHub repository in short format
            username = parts[0]
            repo = parts[1]
            ssh_url = f"git@github.com:{username}/{repo}.git"
            logger.debug("Detected short GitHub format: %s -> %s", workspace_root, ssh_url)
            result = {"url": ssh_url, "name": _extract_repo_name(repo)}
            if branch:
                result["branch"] = branch
            return result

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


def clone_repository(repo_url: str, repo_name: str, branch: str | None = None) -> str | None:
    """Clone a git repository to a temporary location.

    Args:
        repo_url: The git repository URL to clone
        repo_name: Name for the cloned repository directory
        branch: Optional branch name to checkout after cloning

    Returns:
        Path to the cloned repository, or None if cloning failed
    """
    clone_path = get_clone_directory(repo_name)

    logger.info("Attempting to clone repository %s to %s", repo_url, clone_path)
    if branch:
        logger.info("Will checkout branch: %s", branch)

    try:
        # If the directory already exists and is a git repo, try to update it instead
        if is_git_repository(clone_path):
            logger.info("Repository already exists at %s, attempting to update", clone_path)
            if update_repository(clone_path, branch):
                return clone_path
            logger.warning("Failed to update existing repository, will try to re-clone")
            # If update fails, remove and re-clone
            shutil.rmtree(clone_path)

        # Clone the repository
        clone_cmd = ["git", "clone", repo_url, clone_path]
        if branch:
            # Clone specific branch for efficiency
            clone_cmd.extend(["--branch", branch])

        result = subprocess.run(
            clone_cmd,
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


def update_repository(repo_path: str, branch: str | None = None) -> bool:
    """Update an existing git repository by fetching latest changes.

    Args:
        repo_path: Path to the git repository
        branch: Optional branch name to checkout before updating

    Returns:
        True if update was successful, False otherwise
    """
    if not is_git_repository(repo_path):
        logger.error("Path %s is not a git repository", repo_path)
        return False

    logger.info("Updating repository at %s", repo_path)
    if branch:
        logger.info("Will checkout branch: %s", branch)

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

            # Checkout the specified branch if provided
            if branch:
                result = subprocess.run(
                    ["git", "checkout", branch],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                logger.debug("Checkout output: %s", result.stdout)

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
    2. If not, tries to parse it as a remote repository URL (with optional branch)
    3. Clones the remote repository to a temporary location if needed
    4. Checks out the specified branch if provided

    Args:
        workspace_root: Either a local path to a git repository or a remote git URL,
                       optionally with @branch suffix (e.g., username/repo@develop)

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
        branch = repo_info.get("branch")
        if branch:
            logger.info("Branch specified: %s", branch)
        cloned_path = clone_repository(repo_info["url"], repo_info["name"], branch)
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
