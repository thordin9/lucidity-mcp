"""
Code analysis tools for Lucidity.

This module provides tools for analyzing code quality using MCP.
"""

import os
import subprocess
from typing import Any

from ..config import MIN_CODE_CHANGE_BYTES
from ..context import mcp
from ..git_command import GitCommandError, run_git_command
from ..log import logger
from ..validation import is_valid_commit_range, is_valid_path
from .git_utils import ensure_repository


def get_git_diff(workspace_root: str, path: str | None = None, commits: str | None = None) -> tuple[str, str]:
    """Get the current git diff and the staged files content, or diff between commits.

    Args:
        workspace_root: The root directory of the workspace/git repository (can be a remote URL)
        path: Optional specific file path to get diff for
        commits: Optional commit range (e.g., "HEAD~1..HEAD", "abc123^..abc123").
                If provided, gets diff between commits instead of uncommitted changes.
                Common patterns:
                - "HEAD~1..HEAD" - last commit
                - "HEAD~5..HEAD" - last 5 commits
                - "abc123^..abc123" - specific commit
                - "main..feature-branch" - changes in feature branch

    Returns:
        Tuple of (diff_content, staged_files_content).
        When commits parameter is used, staged_files_content will be empty.
    """
    # Validate inputs
    if commits and not is_valid_commit_range(commits):
        logger.error("Invalid commit range format: %s", commits)
        return "", ""
    
    if path and not is_valid_path(path):
        logger.error("Invalid path format: %s", path)
        return "", ""

    logger.debug("Getting git diff%s in workspace %s%s", 
                f" for path: {path}" if path else "", 
                workspace_root,
                f" for commits: {commits}" if commits else "")

    try:
        # Ensure we have a local git repository (clone if remote)
        actual_repo_path = ensure_repository(workspace_root)
        if not actual_repo_path:
            logger.error("Could not access or clone repository: %s", workspace_root)
            return "", ""

        workspace_root = actual_repo_path

        # Build diff command based on whether we're analyzing commits or working directory
        if commits:
            # Analyze committed changes
            diff_args = ["diff", commits]
            if path:
                normalized_path = path.replace("\\", "/")
                diff_args.append(normalized_path)
            
            logger.debug("Running diff command for commits: %s", diff_args)
            result = run_git_command(diff_args, cwd=workspace_root)
            logger.debug("Git diff size: %d bytes", len(result.stdout))
            
            # No staged content when analyzing commits
            return result.stdout, ""
        else:
            # Analyze uncommitted changes (original behavior)
            diff_args = ["diff"]
            if path:
                # Normalize path for Windows/WSL
                normalized_path = path.replace("\\", "/")
                diff_args.append(normalized_path)

            logger.debug("Running diff command: %s", diff_args)
            result = run_git_command(diff_args, cwd=workspace_root)
            logger.debug("Git diff size: %d bytes", len(result.stdout))

            # Get the staged files content
            staged_args = ["diff", "--cached"]
            if path:
                staged_args.append(normalized_path)

            logger.debug("Running staged command: %s", staged_args)
            staged_result = run_git_command(staged_args, cwd=workspace_root)
            logger.debug("Git staged diff size: %d bytes", len(staged_result.stdout))

            return result.stdout, staged_result.stdout

    except GitCommandError as e:
        logger.error("Error getting git diff: %s", e.stderr)
        return "", ""
    except Exception as e:
        logger.error("Unexpected error getting git diff: %s", e)
        return "", ""


def get_changed_files(workspace_root: str) -> list[str]:
    """Get a list of all modified files (both staged and unstaged).

    Args:
        workspace_root: The root directory of the workspace/git repository (can be a remote URL)

    Returns:
        List of modified file paths
    """
    logger.debug("Getting changed files in workspace %s", workspace_root)

    try:
        # Ensure we have a local git repository (clone if remote)
        actual_repo_path = ensure_repository(workspace_root)
        if not actual_repo_path:
            logger.error("Could not access or clone repository: %s", workspace_root)
            return []

        workspace_root = actual_repo_path

        # Get unstaged modified files using cwd parameter instead of os.chdir
        unstaged_result = run_git_command(
            ["diff", "--name-only"],
            cwd=workspace_root,
        )
        unstaged_files = unstaged_result.stdout.strip().split("\n")

        # Get staged modified files
        staged_result = run_git_command(
            ["diff", "--cached", "--name-only"],
            cwd=workspace_root,
        )
        staged_files = staged_result.stdout.strip().split("\n")

        # Combine and remove empty entries
        all_files = list(set(filter(None, unstaged_files + staged_files)))
        logger.debug("Found %d changed files", len(all_files))

        return all_files

    except GitCommandError as e:
        logger.error("Error getting changed files: %s", e.stderr)
        return []
    except Exception as e:
        logger.error("Unexpected error getting changed files: %s", e)
        return []


def parse_git_diff(diff_content: str) -> dict[str, dict[str, Any]]:
    """Parse git diff content into a structured format.

    Args:
        diff_content: Raw git diff content

    Returns:
        Dictionary mapping filenames to their diff info
    """
    result: dict[str, dict[str, Any]] = {}
    current_file: str | None = None
    current_content: list[str] = []
    current_header: list[str] = []

    lines = diff_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for file header
        if line.startswith("diff --git "):
            # Save previous file content if any
            if current_file is not None:
                result[current_file]["content"] = "\n".join(current_content)
                result[current_file]["header"] = "\n".join(current_header)
                current_content = []
                current_header = []

            # Extract filename from diff header
            parts = line.split(" ")
            if len(parts) >= 4:
                # Extract the canonical filename (b/ version)
                file_path = parts[3][2:]  # Remove 'b/' prefix
                current_file = file_path
                result[current_file] = {
                    "status": "modified",
                    "content": "",
                    "original_content": "",
                    "header": line,
                    "raw_diff": line + "\n",
                }
                current_header.append(line)

            # Skip file metadata lines and collect headers
            while i + 1 < len(lines) and not lines[i + 1].startswith("@@"):
                i += 1
                if i < len(lines) and current_file is not None:
                    current_header.append(lines[i])
                    result[current_file]["raw_diff"] += lines[i] + "\n"

                    # Check for file status
                    if lines[i].startswith("new file"):
                        result[current_file]["status"] = "added"
                    elif lines[i].startswith("deleted file"):
                        result[current_file]["status"] = "deleted"
                    elif lines[i].startswith("rename from"):
                        result[current_file]["status"] = "renamed"

        # Collect diff hunk headers
        elif current_file is not None and line.startswith("@@"):
            current_header.append(line)
            result[current_file]["raw_diff"] += line + "\n"

        # Collect diff content
        elif current_file is not None and (line.startswith(("+", "-", " "))):
            current_content.append(line)
            result[current_file]["raw_diff"] += line + "\n"

        i += 1

    # Save the last file content
    if current_file is not None and current_content:
        result[current_file]["content"] = "\n".join(current_content)
        result[current_file]["header"] = "\n".join(current_header)

    return result


def extract_code_from_diff(diff_info: dict[str, Any]) -> tuple[str, str]:
    """Extract the original and modified code from diff info.

    Args:
        diff_info: Dictionary containing diff information

    Returns:
        Tuple of (original_code, modified_code)
    """
    original_lines = []
    modified_lines = []

    # Process the diff content
    for line in diff_info["content"].split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            # Line added
            modified_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            # Line removed
            original_lines.append(line[1:])
        elif line.startswith(" "):
            # Line unchanged
            original_lines.append(line[1:])
            modified_lines.append(line[1:])

    return "\n".join(original_lines), "\n".join(modified_lines)


def detect_language(filename: str) -> str:
    """Detect the programming language based on file extension.

    Args:
        filename: The name of the file

    Returns:
        The detected language or 'text' if unknown
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".sh": "bash",
        ".md": "markdown",
        ".json": "json",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
    }

    _, ext = os.path.splitext(filename)
    return extension_map.get(ext.lower(), "text")


@mcp.tool("analyze_changes")
def analyze_changes(workspace_root: str = "", path: str = "", commits: str | None = None) -> dict[str, Any]:
    """Prepare git changes for analysis through MCP.

    This tool examines git changes (either uncommitted or committed), extracts changed code,
    and prepares structured data with context for the AI to analyze.

    The tool doesn't perform analysis itself - it formats the git diff data
    and provides analysis instructions which get passed back to the AI model
    through the Model Context Protocol.

    IMPORTANT FOR AI AGENTS:
    ========================
    When the MCP server is running remotely (not on the same machine as the repository),
    you MUST provide a REMOTE repository URL, not a local filesystem path.
    
    ❌ WRONG: workspace_root="/home/runner/_work/repo/repo" 
       (local path that doesn't exist on MCP server)
    
    ✅ CORRECT: workspace_root="username/repo" 
       or workspace_root="git@github.com:username/repo.git@branch-name"
       (remote URL that can be cloned by MCP server)

    ANALYZING DIFFERENT TYPES OF CHANGES:
    ======================================
    
    **For Uncommitted Changes** (default behavior):
    - Use without 'commits' parameter
    - Analyzes working directory changes (git diff)
    - Example: analyze_changes(workspace_root="username/repo")
    
    **For Committed Changes** (e.g., remote repos, historical analysis):
    - Use 'commits' parameter to specify commit range
    - Analyzes changes between commits (git diff commit1..commit2)
    - Common patterns:
      * commits="HEAD~1..HEAD" - analyze last commit
      * commits="HEAD~5..HEAD" - analyze last 5 commits
      * commits="abc123^..abc123" - analyze specific commit
      * commits="main..feature-branch" - analyze branch differences
    - Example: analyze_changes(workspace_root="username/repo", commits="HEAD~1..HEAD")

    **When to use commits parameter:**
    - Remote repositories without local changes (freshly cloned)
    - CI/CD pipelines analyzing merged commits
    - Historical code review
    - Analyzing specific PRs or commits

    Common scenarios:
    - GitHub Actions / CI/CD: Use "username/repo@branch" format, NOT the local checkout path
    - Analyzing remote repositories: Always use remote URL format
    - Local development: Only use filesystem paths if MCP server runs on same machine

    Args:
        workspace_root: REQUIRED. The repository to analyze. Choose the appropriate format:
        
                       **REMOTE REPOSITORIES** (most common, especially in CI/CD):
                       - Short format: "username/repo" (uses default branch)
                       - With branch: "username/repo@branch-name"
                       - SSH URL: "git@github.com:username/repo.git"
                       - SSH with branch: "git@github.com:username/repo.git@branch-name"
                       - HTTPS URL: "https://github.com/username/repo.git"
                       - HTTPS with branch: "https://github.com/username/repo.git@branch-name"
                       
                       **LOCAL REPOSITORIES** (only when MCP server has filesystem access):
                       - Filesystem path: "/path/to/local/repo"
                       
                       If you're unsure, use the remote format (username/repo).
                       
        path: Optional specific file path to analyze (relative to repository root)
        
        commits: Optional commit range to analyze. Use this for remote repositories or 
                committed changes instead of uncommitted changes.
                Examples:
                - "HEAD~1..HEAD" - last commit
                - "HEAD~5..HEAD" - last 5 commits  
                - "abc123^..abc123" - specific commit by hash
                - "main..feature-branch" - changes in feature branch vs main
                
                If not provided, analyzes uncommitted changes (git diff of working directory).

    Returns:
        Structured git diff data with analysis instructions for the AI
    """
    logger.info("Starting git change analysis%s in workspace %s%s", 
                f" for {path}" if path else "", 
                workspace_root,
                f" with commits: {commits}" if commits else "")

    if not workspace_root:
        return {"status": "error", "message": "workspace_root parameter is required"}

    # First, ensure we can access the repository (will clone if remote)
    from .git_utils import ensure_repository
    actual_repo_path = ensure_repository(workspace_root)
    
    # Check if repository access failed
    if not actual_repo_path:
        # Check if this looks like a local path that might not exist on MCP server
        if workspace_root.startswith('/') or workspace_root.startswith('./') or workspace_root.startswith('../'):
            return {
                "status": "error",
                "message": (
                    f"Could not access or clone repository: {workspace_root}\n\n"
                    "This appears to be a local filesystem path. If the MCP server is running "
                    "remotely (separate from your local machine), you must provide a REMOTE "
                    "repository URL instead.\n\n"
                    "✅ CORRECT formats:\n"
                    "  - 'username/repo' (for GitHub default branch)\n"
                    "  - 'username/repo@branch-name' (for specific branch)\n"
                    "  - 'git@github.com:username/repo.git@branch-name'\n\n"
                    "❌ INCORRECT (local paths that don't exist on MCP server):\n"
                    "  - '/home/runner/_work/repo/repo'\n"
                    "  - '/github/workspace/project'\n"
                    "  - './local-checkout'\n\n"
                    "In CI/CD contexts (GitHub Actions, etc.), extract the repository URL "
                    "from environment variables instead of using the local checkout path."
                )
            }
        else:
            return {
                "status": "error",
                "message": f"Could not access or clone repository: {workspace_root}"
            }

    # Get git diff
    logger.debug("Fetching git diff...")
    diff_content, staged_content = get_git_diff(workspace_root, path, commits)

    # Get list of all changed files
    changed_files = get_changed_files(workspace_root)

    # Combine diff and staged content for complete changes
    combined_diff = diff_content
    if staged_content:
        combined_diff = combined_diff + "\n" + staged_content if combined_diff else staged_content

    logger.debug("Combined diff size: %d bytes", len(combined_diff))

    if not combined_diff:
        if commits:
            logger.warning("No changes detected in commit range: %s", commits)
            return {
                "status": "no_changes", 
                "message": f"No changes detected in commit range: {commits}", 
                "file_list": []
            }
        else:
            logger.warning("No uncommitted changes detected")
            return {
                "status": "no_changes", 
                "message": (
                    "No uncommitted changes detected in the git diff.\n\n"
                    "If you're analyzing a remote repository, use the 'commits' parameter to analyze "
                    "committed changes instead. Examples:\n"
                    "  - commits='HEAD~1..HEAD' (last commit)\n"
                    "  - commits='HEAD~5..HEAD' (last 5 commits)\n"
                    "  - commits='abc123^..abc123' (specific commit)"
                ),
                "file_list": []
            }

    # Parse the diff
    logger.debug("Parsing git diff...")
    parsed_diff = parse_git_diff(combined_diff)

    if not parsed_diff:
        logger.warning("No parseable changes in git diff")
        return {
            "status": "no_changes",
            "message": "No parseable changes detected in the git diff",
            "file_list": changed_files,
        }

    logger.info("Found %d files with changes to analyze", len(parsed_diff))

    # Process each changed file
    analysis_results = {}
    file_list = []

    for filename, diff_info in parsed_diff.items():
        logger.debug("Processing file: %s (status: %s)", filename, diff_info["status"])
        file_list.append(filename)

        # Skip certain files
        if filename.endswith((".lock", ".sum", ".mod", "package-lock.json", "yarn.lock", ".DS_Store")):
            logger.debug("Skipping excluded file: %s", filename)
            continue

        try:
            # Extract original and modified code
            logger.debug("Extracting code changes for %s", filename)
            original_code, modified_code = extract_code_from_diff(diff_info)

            # Skip if no significant code changes
            if len(modified_code.strip()) < MIN_CODE_CHANGE_BYTES:
                logger.debug("Skipping %s - insufficient code changes (< %d chars)", filename, MIN_CODE_CHANGE_BYTES)
                continue

            # Detect language
            language = detect_language(filename)
            logger.debug("Detected language for %s: %s", filename, language)

            # Create a prompt for analysis
            logger.debug("Generating analysis prompt for %s", filename)
            from ..prompts import analyze_changes_prompt

            analysis_prompt = analyze_changes_prompt(
                code=modified_code, language=language, original_code=original_code if original_code else None
            )
            logger.debug("Generated analysis prompt of size: %d chars", len(analysis_prompt))

            # Store the analysis prompt to be returned
            analysis_results[filename] = {
                "status": diff_info["status"],
                "language": language,
                "analysis_prompt": analysis_prompt,
                "raw_diff": diff_info["raw_diff"],
                "original_code": original_code,
                "modified_code": modified_code,
            }
            logger.info("Successfully analyzed %s", filename)

        except Exception as e:
            logger.error("Error analyzing %s: %s", filename, e)
            analysis_results[filename] = {"status": "error", "message": f"Error analyzing file: {e!s}"}

    logger.info("Code analysis complete - processed %d files", len(analysis_results))

    # Return results with instructions for AI analysis
    return {
        "status": "success",
        "file_count": len(analysis_results),
        "file_list": file_list,
        "all_changed_files": changed_files,
        "results": analysis_results,
        "instructions": """
This data contains git changes that you should analyze for code quality issues.
As an AI model receiving this through MCP, your task is to:

1. Review each changed file:
   - Examine the raw diff showing the exact changes
   - Compare the original and modified code
   - Consider the language and file status (added, modified, deleted)

2. For each file, perform the analysis following the provided analysis prompt:
   - Analyze relevant quality dimensions
   - Assign severity levels to issues you identify
   - Provide line-specific explanations
   - Suggest concrete improvements

3. After analyzing all files, provide:
   - An overall assessment of the code changes
   - A prioritized list of improvements
   - Any patterns or systemic issues you've identified

Your analysis should be thorough yet focused on actionable improvements.
""",
    }
