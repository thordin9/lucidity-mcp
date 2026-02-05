"""
Git utility functions for handling local and remote repositories.

This module provides utilities to:
- Check if a directory is a git repository
- Clone remote repositories when not available locally
- Fetch/update existing cloned repositories
- Clean up inactive repository caches
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from ..log import logger


def get_cache_directory() -> str:
    """Get the base directory for caching cloned repositories.

    The cache directory can be configured via the LUCIDITY_CACHE_DIR environment variable.
    If not set, defaults to /tmp/lucidity-mcp-repos.

    Returns:
        Path to the cache directory
    """
    cache_dir = os.environ.get("LUCIDITY_CACHE_DIR")
    if cache_dir:
        return cache_dir
    return os.path.join(tempfile.gettempdir(), "lucidity-mcp-repos")


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
            # Validate branch (no dots at start for security)
            if not branch.startswith("."):
                logger.debug("Detected branch specification: %s", branch)
            else:
                # Invalid branch format, restore
                workspace_root = workspace_root + "@" + branch
                branch = None
    elif "@" in workspace_root and not workspace_root.startswith(("http://", "https://")):
        # Split on the last @ for other formats
        parts = workspace_root.rsplit("@", 1)
        if len(parts) == 2 and not parts[1].startswith("."):
            workspace_root = parts[0]
            branch = parts[1]
            logger.debug("Detected branch specification: %s", branch)
    elif workspace_root.startswith(("https://", "http://")):
        # For HTTPS URLs, check for @branch at the end
        if "@" in workspace_root:
            parts = workspace_root.rsplit("@", 1)
            if len(parts) == 2 and not parts[1].startswith("."):
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

    Creates a directory structure for cloned repositories in the cache directory.

    Args:
        repo_name: Name of the repository

    Returns:
        Path to the directory where the repo should be cloned
    """
    # Create a dedicated directory for cloned repos in the configured cache location
    clone_base = get_cache_directory()
    os.makedirs(clone_base, exist_ok=True)

    return os.path.join(clone_base, repo_name)


def touch_repository_access(repo_path: str) -> None:
    """Update the last access time for a repository.

    Creates or updates a .last_accessed file in the repository directory
    to track when the repository was last used.

    Args:
        repo_path: Path to the repository directory
    """
    try:
        access_file = os.path.join(repo_path, ".last_accessed")
        # Create or update the file's modification time
        Path(access_file).touch()
        logger.debug("Updated access time for repository: %s", repo_path)
    except Exception as e:
        logger.warning("Failed to update access time for %s: %s", repo_path, e)


def clone_repository(repo_url: str, repo_name: str, branch: str | None = None) -> str | None:
    """Clone a git repository to a temporary location.

    Args:
        repo_url: The git repository URL to clone
        repo_name: Name for the cloned repository directory
        branch: Optional branch name to clone (uses --branch flag during clone)

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

        # Set up environment to disable SSH host key verification
        # This prevents "Host key verification failed" errors when cloning via SSH
        # Note: This reduces security by disabling protection against MITM attacks,
        # but is necessary for automated workflows and development environments.
        # Users requiring strict security should use HTTPS with credentials instead.
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout for cloning
            env=env,
        )
        logger.debug("Clone output: %s", result.stdout)
        logger.info("Successfully cloned repository to %s", clone_path)
        
        # Track repository access time
        touch_repository_access(clone_path)
        
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

        # Set up environment to disable SSH host key verification
        # This prevents "Host key verification failed" errors when fetching via SSH
        # Note: This reduces security by disabling protection against MITM attacks,
        # but is necessary for automated workflows and development environments.
        env = os.environ.copy()
        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

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
                env=env,
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
                env=env,
            )
            logger.debug("Pull output: %s", result.stdout)

            logger.info("Successfully updated repository at %s", repo_path)
            
            # Track repository access time
            touch_repository_access(repo_path)
            
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


def cleanup_inactive_repositories(days: int = 7, dry_run: bool = False) -> dict[str, Any]:
    """Clean up repository caches that haven't been accessed in the specified number of days.

    This function scans the cache directory and removes repositories that haven't been
    accessed within the specified time period. Access time is tracked via the .last_accessed
    file in each repository directory.

    Args:
        days: Number of days of inactivity before a repository is considered for cleanup (default: 7)
        dry_run: If True, only report what would be deleted without actually deleting (default: False)

    Returns:
        Dictionary containing cleanup statistics:
        - 'cache_dir': Path to the cache directory
        - 'scanned': Number of directories scanned
        - 'removed': Number of repositories removed
        - 'freed_bytes': Approximate bytes freed
        - 'repositories': List of repository paths that were removed or would be removed
    """
    cache_dir = get_cache_directory()
    
    logger.info("Starting cleanup of inactive repositories in %s (inactive for %d+ days)", cache_dir, days)
    if dry_run:
        logger.info("DRY RUN: No repositories will actually be deleted")
    
    if not os.path.exists(cache_dir):
        logger.info("Cache directory does not exist: %s", cache_dir)
        return {
            "cache_dir": cache_dir,
            "scanned": 0,
            "removed": 0,
            "freed_bytes": 0,
            "repositories": [],
        }
    
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)  # Convert days to seconds
    
    scanned = 0
    removed = 0
    freed_bytes = 0
    removed_repos = []
    
    try:
        for entry in os.listdir(cache_dir):
            repo_path = os.path.join(cache_dir, entry)
            
            # Skip non-directories
            if not os.path.isdir(repo_path):
                continue
            
            scanned += 1
            
            # Check if it's a git repository
            if not is_git_repository(repo_path):
                logger.debug("Skipping non-git directory: %s", repo_path)
                continue
            
            # Check access time via .last_accessed file
            access_file = os.path.join(repo_path, ".last_accessed")
            
            # If no .last_accessed file, check directory modification time as fallback
            if os.path.exists(access_file):
                last_access = os.path.getmtime(access_file)
            else:
                # Use directory modification time if .last_accessed doesn't exist
                last_access = os.path.getmtime(repo_path)
            
            # Check if repository is inactive
            if last_access < cutoff_time:
                # Calculate size before deletion
                repo_size = 0
                try:
                    for dirpath, dirnames, filenames in os.walk(repo_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            try:
                                repo_size += os.path.getsize(filepath)
                            except OSError:
                                pass  # Skip files we can't access
                except OSError as e:
                    logger.warning("Error calculating size for %s: %s", repo_path, e)
                
                days_inactive = (current_time - last_access) / (24 * 60 * 60)
                logger.info(
                    "%s repository: %s (%.1f days inactive, ~%.2f MB)",
                    "Would remove" if dry_run else "Removing",
                    entry,
                    days_inactive,
                    repo_size / (1024 * 1024),
                )
                
                if not dry_run:
                    try:
                        shutil.rmtree(repo_path)
                        logger.info("Successfully removed %s", repo_path)
                    except Exception as e:
                        logger.error("Failed to remove %s: %s", repo_path, e)
                        continue
                
                removed += 1
                freed_bytes += repo_size
                removed_repos.append(entry)
    
    except Exception as e:
        logger.error("Error during cleanup: %s", e)
    
    logger.info(
        "Cleanup complete: scanned %d, %s %d repositories, %s ~%.2f MB",
        scanned,
        "would remove" if dry_run else "removed",
        removed,
        "would free" if dry_run else "freed",
        freed_bytes / (1024 * 1024),
    )
    
    return {
        "cache_dir": cache_dir,
        "scanned": scanned,
        "removed": removed,
        "freed_bytes": freed_bytes,
        "repositories": removed_repos,
    }
