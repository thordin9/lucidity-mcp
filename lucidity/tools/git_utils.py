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
import time
from pathlib import Path
from typing import Any

from ..config import get_config
from ..git_command import GitCommandError, GitTimeoutError, run_git_command
from ..log import logger
from ..validation import is_valid_branch_name


def get_cache_directory() -> str:
    """Get the base directory for caching cloned repositories.

    The cache directory can be configured via the LUCIDITY_CACHE_DIR environment variable.
    If not set, defaults to /tmp/lucidity-mcp-repos.

    Returns:
        Path to the cache directory
    """
    config = get_config()
    return config.cache_dir


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
            # Validate branch name for security
            if is_valid_branch_name(branch):
                logger.debug("Detected branch specification: %s", branch)
            else:
                logger.error("Invalid branch name format: %s", branch)
                # Invalid branch format, restore
                workspace_root = workspace_root + "@" + branch
                branch = None
    elif "@" in workspace_root and not workspace_root.startswith(("http://", "https://")):
        # Split on the last @ for other formats
        parts = workspace_root.rsplit("@", 1)
        if len(parts) == 2 and is_valid_branch_name(parts[1]):
            workspace_root = parts[0]
            branch = parts[1]
            logger.debug("Detected branch specification: %s", branch)
    elif workspace_root.startswith(("https://", "http://")):
        # For HTTPS URLs, check for @branch at the end
        if "@" in workspace_root:
            parts = workspace_root.rsplit("@", 1)
            if len(parts) == 2 and is_valid_branch_name(parts[1]):
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
    # Validate branch name if provided
    if branch and not is_valid_branch_name(branch):
        logger.error("Invalid branch name: %s", branch)
        return None

    clone_path = get_clone_directory(repo_name)
    config = get_config()

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

        # Build clone command
        clone_args = ["clone", repo_url, clone_path]
        if branch:
            # Clone specific branch for efficiency
            clone_args.extend(["--branch", branch])

        # Use run_git_command which handles SSH verification based on config
        result = run_git_command(
            clone_args,
            cwd=os.path.dirname(clone_path) or ".",
            timeout=config.clone_timeout,
        )
        logger.debug("Clone output: %s", result.stdout)
        logger.info("Successfully cloned repository to %s", clone_path)
        
        # Track repository access time
        touch_repository_access(clone_path)
        
        return clone_path

    except GitTimeoutError:
        logger.error("Timeout while cloning repository %s", repo_url)
        # Clean up partial clone
        if os.path.exists(clone_path):
            logger.debug("Cleaning up partial clone at %s", clone_path)
            shutil.rmtree(clone_path)
        return None
    except GitCommandError as e:
        logger.error("Error cloning repository %s: %s", repo_url, e.stderr)
        # Clean up failed clone
        if os.path.exists(clone_path):
            logger.debug("Cleaning up failed clone at %s", clone_path)
            shutil.rmtree(clone_path)
        return None
    except Exception as e:
        logger.error("Unexpected error cloning repository %s: %s", repo_url, e)
        # Clean up on any error
        if os.path.exists(clone_path):
            logger.debug("Cleaning up failed clone at %s", clone_path)
            shutil.rmtree(clone_path)
        return None


def update_repository(repo_path: str, branch: str | None = None) -> bool:
    """Update an existing git repository by fetching latest changes.

    Args:
        repo_path: Path to the git repository
        branch: Optional branch name to checkout before updating

    Returns:
        True if update was successful, False otherwise
    """
    # Validate branch name if provided
    if branch and not is_valid_branch_name(branch):
        logger.error("Invalid branch name: %s", branch)
        return False

    if not is_git_repository(repo_path):
        logger.error("Path %s is not a git repository", repo_path)
        return False

    config = get_config()
    logger.info("Updating repository at %s", repo_path)
    if branch:
        logger.info("Will checkout branch: %s", branch)

    try:
        # Fetch latest changes using cwd parameter instead of os.chdir
        run_git_command(
            ["fetch", "--all"],
            cwd=repo_path,
            timeout=config.fetch_timeout,
        )
        logger.debug("Successfully fetched latest changes")

        # Checkout the specified branch if provided
        if branch:
            run_git_command(
                ["checkout", branch],
                cwd=repo_path,
                timeout=30,
            )
            logger.debug("Checked out branch: %s", branch)

        # Pull changes for the current branch
        run_git_command(
            ["pull"],
            cwd=repo_path,
            timeout=config.fetch_timeout,
        )
        logger.debug("Successfully pulled changes")

        logger.info("Successfully updated repository at %s", repo_path)
        
        # Track repository access time
        touch_repository_access(repo_path)
        
        return True

    except (GitTimeoutError, GitCommandError) as e:
        logger.error("Error updating repository at %s: %s", repo_path, e)
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
        # Path doesn't exist - provide helpful guidance
        if workspace_root.startswith('/') or workspace_root.startswith('./') or workspace_root.startswith('../'):
            logger.error(
                "Local path '%s' does not exist. "
                "If the MCP server is running remotely, use a remote repository URL instead. "
                "Examples: 'username/repo', 'username/repo@branch', or 'git@github.com:username/repo.git'",
                workspace_root
            )
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
                # Calculate size before deletion using du command for better performance
                repo_size = 0
                try:
                    result = subprocess.run(
                        ["du", "-sb", repo_path],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0:
                        repo_size = int(result.stdout.split()[0])
                    else:
                        # Fallback to os.walk if du fails
                        for dirpath, dirnames, filenames in os.walk(repo_path):
                            for filename in filenames:
                                filepath = os.path.join(dirpath, filename)
                                try:
                                    repo_size += os.path.getsize(filepath)
                                except OSError:
                                    pass  # Skip files we can't access
                except (subprocess.TimeoutExpired, ValueError, OSError, FileNotFoundError) as e:
                    logger.warning("Error running du command for %s: %s, falling back to os.walk", repo_path, e)
                    # Fallback to os.walk if du is not available or fails
                    try:
                        for dirpath, dirnames, filenames in os.walk(repo_path):
                            for filename in filenames:
                                filepath = os.path.join(dirpath, filename)
                                try:
                                    repo_size += os.path.getsize(filepath)
                                except OSError:
                                    pass  # Skip files we can't access
                    except OSError as walk_error:
                        logger.warning("Error calculating size with os.walk for %s: %s", repo_path, walk_error)
                
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
