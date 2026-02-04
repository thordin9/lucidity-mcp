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
    # Verify clone was called with branch parameter
    mock_clone.assert_called_once()
    call_args = mock_clone.call_args
    assert call_args[1] == "develop"  # branch is the third positional argument
