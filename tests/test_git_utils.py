"""
Tests for git utilities module.
"""

import os
from unittest.mock import MagicMock, patch

from lucidity.tools.git_utils import (
    clone_repository,
    ensure_repository,
    extract_repo_info_from_path,
    get_clone_directory,
    is_git_repository,
    update_repository,
)


def test_is_git_repository_with_git_dir(tmp_path):
    """Test is_git_repository returns True for directory with .git."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    assert is_git_repository(str(tmp_path))


def test_is_git_repository_without_git_dir(tmp_path):
    """Test is_git_repository returns False for directory without .git."""
    assert not is_git_repository(str(tmp_path))


def test_is_git_repository_nonexistent_path():
    """Test is_git_repository returns False for nonexistent path."""
    assert not is_git_repository("/nonexistent/path")


def test_extract_repo_info_ssh_format():
    """Test extracting repository info from SSH URL."""
    url = "git@github.com:username/repo.git"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == url
    assert result["name"] == "repo"


def test_extract_repo_info_https_format():
    """Test extracting repository info from HTTPS URL."""
    url = "https://github.com/username/repo.git"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == url
    assert result["name"] == "repo"


def test_extract_repo_info_short_format():
    """Test extracting repository info from short format."""
    short_url = "username/repo"
    result = extract_repo_info_from_path(short_url)

    assert result is not None
    assert result["url"] == "git@github.com:username/repo.git"
    assert result["name"] == "repo"


def test_extract_repo_info_github_format():
    """Test extracting repository info from github.com format."""
    url = "github.com/username/repo"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == "git@github.com:username/repo.git"
    assert result["name"] == "repo"


def test_extract_repo_info_local_path(tmp_path):
    """Test that local paths return None."""
    result = extract_repo_info_from_path(str(tmp_path))
    assert result is None


def test_extract_repo_info_empty_string():
    """Test that empty string returns None."""
    result = extract_repo_info_from_path("")
    assert result is None


def test_get_clone_directory():
    """Test get_clone_directory creates proper path and parent directory."""
    repo_name = "test-repo"
    clone_dir = get_clone_directory(repo_name)

    assert repo_name in clone_dir
    assert "lucidity-mcp-repos" in clone_dir
    # Verify parent directory structure is created (not the clone dir itself yet)
    assert os.path.exists(os.path.dirname(clone_dir))


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_clone_repository_success(mock_is_repo, mock_run):
    """Test successful repository cloning."""
    mock_is_repo.return_value = False
    mock_run.return_value = MagicMock(stdout="Cloning...", returncode=0)

    result = clone_repository("git@github.com:user/repo.git", "test-repo")

    assert result is not None
    assert "test-repo" in result
    mock_run.assert_called_once()


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_clone_repository_already_exists(mock_is_repo, mock_run):
    """Test cloning when repository already exists."""
    # First call checks if repo exists (True)
    # Second call is for update_repository -> chdir context
    mock_is_repo.side_effect = [True, True]

    # Mock the git fetch and pull commands in update_repository
    mock_run.return_value = MagicMock(stdout="Already up to date.", returncode=0)

    with (
        patch("lucidity.tools.git_utils.os.chdir"),
        patch("lucidity.tools.git_utils.os.getcwd", return_value="/current"),
    ):
        result = clone_repository("git@github.com:user/repo.git", "test-repo")

    assert result is not None
    # Should call fetch and pull, not clone
    assert mock_run.call_count >= 2


@patch("lucidity.tools.git_utils.subprocess.run")
def test_clone_repository_failure(mock_run):
    """Test repository cloning failure."""
    mock_run.side_effect = Exception("Clone failed")

    result = clone_repository("git@github.com:user/repo.git", "test-repo")

    assert result is None


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_update_repository_success(mock_is_repo, mock_run):
    """Test successful repository update."""
    mock_is_repo.return_value = True
    mock_run.return_value = MagicMock(stdout="Updated", returncode=0)

    with (
        patch("lucidity.tools.git_utils.os.chdir"),
        patch("lucidity.tools.git_utils.os.getcwd", return_value="/current"),
    ):
        result = update_repository("/path/to/repo")

    assert result is True
    # Should call both fetch and pull
    assert mock_run.call_count == 2


@patch("lucidity.tools.git_utils.is_git_repository")
def test_update_repository_not_a_repo(mock_is_repo):
    """Test updating a non-repository path."""
    mock_is_repo.return_value = False

    result = update_repository("/path/to/not-a-repo")

    assert result is False


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_update_repository_failure(mock_is_repo, mock_run):
    """Test repository update failure."""
    mock_is_repo.return_value = True
    mock_run.side_effect = Exception("Update failed")

    with (
        patch("lucidity.tools.git_utils.os.chdir"),
        patch("lucidity.tools.git_utils.os.getcwd", return_value="/current"),
    ):
        result = update_repository("/path/to/repo")

    assert result is False


@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_local_repo(mock_is_repo, tmp_path):
    """Test ensure_repository with local repository."""
    mock_is_repo.return_value = True

    result = ensure_repository(str(tmp_path))

    assert result == str(tmp_path)


@patch("lucidity.tools.git_utils.clone_repository")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_remote_url(mock_is_repo, mock_clone):
    """Test ensure_repository with remote URL."""
    mock_is_repo.return_value = False
    mock_clone.return_value = "/tmp/cloned/repo"

    result = ensure_repository("git@github.com:user/repo.git")

    assert result == "/tmp/cloned/repo"
    mock_clone.assert_called_once()


@patch("lucidity.tools.git_utils.clone_repository")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_short_url(mock_is_repo, mock_clone):
    """Test ensure_repository with short GitHub format."""
    mock_is_repo.return_value = False
    mock_clone.return_value = "/tmp/cloned/repo"

    result = ensure_repository("username/repo")

    assert result == "/tmp/cloned/repo"
    # Should be called with converted SSH URL
    mock_clone.assert_called_once()
    call_args = mock_clone.call_args[0]
    assert "git@github.com:" in call_args[0]


@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_nonexistent_local(mock_is_repo):
    """Test ensure_repository with nonexistent local path."""
    mock_is_repo.return_value = False

    result = ensure_repository("/nonexistent/path")

    assert result is None


@patch("lucidity.tools.git_utils.clone_repository")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_clone_failure(mock_is_repo, mock_clone):
    """Test ensure_repository when cloning fails."""
    mock_is_repo.return_value = False
    mock_clone.return_value = None

    result = ensure_repository("git@github.com:user/repo.git")

    assert result is None


def test_extract_repo_info_with_branch_ssh():
    """Test extracting repository info from SSH URL with branch."""
    url = "git@github.com:username/repo.git@develop"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == "git@github.com:username/repo.git"
    assert result["name"] == "repo"
    assert result["branch"] == "develop"


def test_extract_repo_info_with_branch_https():
    """Test extracting repository info from HTTPS URL with branch."""
    url = "https://github.com/username/repo.git@feature-branch"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == "https://github.com/username/repo.git"
    assert result["name"] == "repo"
    assert result["branch"] == "feature-branch"


def test_extract_repo_info_with_branch_short_format():
    """Test extracting repository info from short format with branch."""
    url = "username/repo@main"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == "git@github.com:username/repo.git"
    assert result["name"] == "repo"
    assert result["branch"] == "main"


def test_extract_repo_info_with_branch_github_format():
    """Test extracting repository info from github.com format with branch."""
    url = "github.com/username/repo@release-1.0"
    result = extract_repo_info_from_path(url)

    assert result is not None
    assert result["url"] == "git@github.com:username/repo.git"
    assert result["name"] == "repo"
    assert result["branch"] == "release-1.0"


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_clone_repository_with_branch(mock_is_repo, mock_run):
    """Test cloning repository with specific branch."""
    mock_is_repo.return_value = False
    mock_run.return_value = MagicMock(stdout="Cloning...", returncode=0)

    result = clone_repository("git@github.com:user/repo.git", "test-repo", "develop")

    assert result is not None
    assert "test-repo" in result
    # Verify that --branch flag was used
    call_args = mock_run.call_args[0][0]
    assert "--branch" in call_args
    assert "develop" in call_args


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_update_repository_with_branch(mock_is_repo, mock_run):
    """Test updating repository with branch checkout."""
    mock_is_repo.return_value = True
    mock_run.return_value = MagicMock(stdout="Updated", returncode=0)

    with (
        patch("lucidity.tools.git_utils.os.chdir"),
        patch("lucidity.tools.git_utils.os.getcwd", return_value="/current"),
    ):
        result = update_repository("/path/to/repo", "feature-branch")

    assert result is True
    # Should call fetch, checkout, and pull
    assert mock_run.call_count == 3
    # Verify checkout was called with branch name
    checkout_call = mock_run.call_args_list[1]
    assert "checkout" in checkout_call[0][0]
    assert "feature-branch" in checkout_call[0][0]


@patch("lucidity.tools.git_utils.clone_repository")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_ensure_repository_with_branch(mock_is_repo, mock_clone):
    """Test ensure_repository with branch specification."""
    mock_is_repo.return_value = False
    mock_clone.return_value = "/tmp/cloned/repo"

    result = ensure_repository("username/repo@develop")

    assert result == "/tmp/cloned/repo"
    # Verify clone was called with branch parameter (third positional argument)
    mock_clone.assert_called_once()
    call_args = mock_clone.call_args
    assert call_args[0][2] == "develop"  # branch is the third positional argument


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_clone_repository_disables_host_key_checking(mock_is_repo, mock_run):
    """Test that clone_repository disables SSH host key checking."""
    mock_is_repo.return_value = False
    mock_run.return_value = MagicMock(stdout="Cloning...", returncode=0)

    result = clone_repository("git@github.com:user/repo.git", "test-repo")

    assert result is not None
    # Verify subprocess.run was called with env containing GIT_SSH_COMMAND
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    assert "env" in call_kwargs
    assert "GIT_SSH_COMMAND" in call_kwargs["env"]
    assert "StrictHostKeyChecking=no" in call_kwargs["env"]["GIT_SSH_COMMAND"]
    assert "UserKnownHostsFile=/dev/null" in call_kwargs["env"]["GIT_SSH_COMMAND"]


@patch("lucidity.tools.git_utils.subprocess.run")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_update_repository_disables_host_key_checking(mock_is_repo, mock_run):
    """Test that update_repository disables SSH host key checking."""
    mock_is_repo.return_value = True
    mock_run.return_value = MagicMock(stdout="Updated", returncode=0)

    with (
        patch("lucidity.tools.git_utils.os.chdir"),
        patch("lucidity.tools.git_utils.os.getcwd", return_value="/current"),
    ):
        result = update_repository("/path/to/repo")

    assert result is True
    # Verify that subprocess.run calls for fetch and pull include env with GIT_SSH_COMMAND
    assert mock_run.call_count >= 2  # fetch and pull
    for call in mock_run.call_args_list:
        # Check if this is a fetch or pull command (not checkout)
        if call[0][0][1] in ["fetch", "pull"]:
            call_kwargs = call[1]
            assert "env" in call_kwargs
            assert "GIT_SSH_COMMAND" in call_kwargs["env"]
            assert "StrictHostKeyChecking=no" in call_kwargs["env"]["GIT_SSH_COMMAND"]
            assert "UserKnownHostsFile=/dev/null" in call_kwargs["env"]["GIT_SSH_COMMAND"]


def test_get_cache_directory_default():
    """Test get_cache_directory returns default path when no env var set."""
    from lucidity.tools.git_utils import get_cache_directory

    with patch.dict("os.environ", {}, clear=True):
        cache_dir = get_cache_directory()
        assert "lucidity-mcp-repos" in cache_dir


def test_get_cache_directory_custom():
    """Test get_cache_directory returns custom path from env var."""
    from lucidity.tools.git_utils import get_cache_directory

    custom_dir = "/custom/cache/path"
    with patch.dict("os.environ", {"LUCIDITY_CACHE_DIR": custom_dir}):
        cache_dir = get_cache_directory()
        assert cache_dir == custom_dir


def test_touch_repository_access(tmp_path):
    """Test touch_repository_access creates/updates .last_accessed file."""
    from lucidity.tools.git_utils import touch_repository_access

    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    access_file = repo_path / ".last_accessed"
    assert not access_file.exists()

    touch_repository_access(str(repo_path))
    assert access_file.exists()

    # Get initial mtime
    first_mtime = access_file.stat().st_mtime

    # Wait a bit and touch again
    import time
    time.sleep(0.1)
    touch_repository_access(str(repo_path))

    # Verify mtime was updated
    second_mtime = access_file.stat().st_mtime
    assert second_mtime > first_mtime


@patch("lucidity.tools.git_utils.shutil.rmtree")
@patch("lucidity.tools.git_utils.get_cache_directory")
@patch("lucidity.tools.git_utils.is_git_repository")
def test_cleanup_inactive_repositories(mock_is_repo, mock_get_cache, mock_rmtree, tmp_path):
    """Test cleanup_inactive_repositories removes old repos."""
    from lucidity.tools.git_utils import cleanup_inactive_repositories

    # Set up test cache directory
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_get_cache.return_value = str(cache_dir)

    # Create test repositories
    old_repo = cache_dir / "old-repo"
    old_repo.mkdir()
    (old_repo / ".git").mkdir()
    
    new_repo = cache_dir / "new-repo"
    new_repo.mkdir()
    (new_repo / ".git").mkdir()

    # Set access times - old repo 10 days ago, new repo now
    import time
    current_time = time.time()
    old_time = current_time - (10 * 24 * 60 * 60)  # 10 days ago

    # Create .last_accessed files
    old_access = old_repo / ".last_accessed"
    old_access.touch()
    os.utime(str(old_access), (old_time, old_time))

    new_access = new_repo / ".last_accessed"
    new_access.touch()

    # Mock is_git_repository to return True
    mock_is_repo.return_value = True

    # Run cleanup with 7 day threshold
    result = cleanup_inactive_repositories(days=7, dry_run=False)

    # Verify results
    assert result["scanned"] == 2
    assert result["removed"] == 1
    assert "old-repo" in result["repositories"]
    assert "new-repo" not in result["repositories"]
    
    # Verify rmtree was called for old repo
    mock_rmtree.assert_called_once()
    assert "old-repo" in str(mock_rmtree.call_args[0][0])


@patch("lucidity.tools.git_utils.shutil.rmtree")
@patch("lucidity.tools.git_utils.get_cache_directory")
def test_cleanup_inactive_repositories_dry_run(mock_get_cache, mock_rmtree, tmp_path):
    """Test cleanup_inactive_repositories dry run doesn't delete."""
    from lucidity.tools.git_utils import cleanup_inactive_repositories

    # Set up test cache directory
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_get_cache.return_value = str(cache_dir)

    # Create test repository
    old_repo = cache_dir / "old-repo"
    old_repo.mkdir()
    (old_repo / ".git").mkdir()

    # Set old access time
    import time
    current_time = time.time()
    old_time = current_time - (10 * 24 * 60 * 60)

    old_access = old_repo / ".last_accessed"
    old_access.touch()
    os.utime(str(old_access), (old_time, old_time))

    # Run dry run cleanup
    result = cleanup_inactive_repositories(days=7, dry_run=True)

    # Verify results
    assert result["removed"] == 1
    assert "old-repo" in result["repositories"]
    
    # Verify rmtree was NOT called
    mock_rmtree.assert_not_called()
    
    # Verify directory still exists
    assert old_repo.exists()
