# ✨ Lucidity MCP 🔍

<div align="center">

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-9D00FF.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache_2.0-FF00FF.svg?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/status-active_development-39FF14.svg?style=for-the-badge)](docs/plan.md)
[![Code Style](https://img.shields.io/badge/code_style-ruff-00FFFF.svg?style=for-the-badge)](https://github.com/astral-sh/ruff)
[![Type Check](https://img.shields.io/badge/type_check-mypy-FFBF00.svg?style=for-the-badge)](https://mypy.readthedocs.io/en/stable/)

**Clarity in Code, Confidence in Creation**

</div>

Lucidity is a Model Context Protocol (MCP) server designed to enhance the quality of AI-generated code through intelligent, prompt-based analysis. By providing structured guidance to AI coding assistants, Lucidity helps identify and address common quality issues, resulting in cleaner, more maintainable, and more robust code.

Before you commit, just ask Lucidity to analyze the changes instead of vibe-coding yourself into a nightmare hellscape! 😱 💥 🚫

## 💫 Features

- 🔮 **Comprehensive Issue Detection** - Covers 10 critical quality dimensions from complexity to security vulnerabilities
- 🔄 **Contextual Analysis** - Compares changes against original code to identify unintended modifications
- 🌐 **Language Agnostic** - Works with any programming language the AI assistant understands
- 🎯 **Focused Analysis** - Option to target specific issue types based on project needs
- 📝 **Structured Outputs** - Guides AI to provide actionable feedback with clear recommendations
- 🤖 **MCP Integration** - Seamless integration with Claude and other MCP-compatible AI assistants
- 🪶 **Lightweight Implementation** - Simple server design with minimal dependencies
- 🧩 **Extensible Framework** - Easy to add new issue types or refine analysis criteria
- 🔀 **Flexible Transport** - Supports stdio for terminal-based interaction, SSE (legacy) for
  network-based communication, and Streamable HTTP (recommended) for modern network deployments
- 🔄 **Git-Aware Analysis** - Analyzes changes directly from git diff, making it ideal for pre-commit reviews
- 🌍 **Remote Repository Support** - Works with remote git repositories, automatically cloning and caching as needed

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/hyperbliss/lucidity-mcp.git
cd lucidity-mcp

# Set up a virtual environment with UV
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with UV
uv sync
```

## 📋 Prerequisites

- Python 3.13 or higher
- Git (for analyzing code changes)
- UV package manager (recommended for dependency management)

## 🔮 Quick Start

### Run the Lucidity server

```bash
# Start with stdio transport (for terminal use)
lucidity-mcp

# Start with SSE transport (for network use)
lucidity-mcp --transport sse --host 127.0.0.1 --port 6969

# Start with Streamable HTTP transport (recommended for network use)
lucidity-mcp --transport streamable-http --host 127.0.0.1 --port 6969

# Start with BOTH transports simultaneously (SSE + Streamable HTTP)
lucidity-mcp --transport both --host 127.0.0.1 --port 6969

# Run with debug logging
lucidity-mcp --debug

# Run with file logging
lucidity-mcp --log-file lucidity.log
```

### Using with AI Assistants

#### SSE Transport

1. Start Lucidity in SSE mode:

   ```bash
   lucidity-mcp --transport sse
   ```

2. Connect your AI assistant using the MCP protocol URI:

   ```
   sse://localhost:6969/sse
   ```

3. The AI can now invoke the `analyze_changes` tool to get code quality feedback!

#### Streamable HTTP Transport (Recommended)

1. Start Lucidity in Streamable HTTP mode:

   ```bash
   lucidity-mcp --transport streamable-http
   ```

2. Connect your AI assistant to the MCP endpoint:

   ```
   http://localhost:6969/mcp
   ```

3. The AI can now invoke the `analyze_changes` tool to get code quality feedback!

#### Both Transports Simultaneously

1. Start Lucidity with both transports enabled:

   ```bash
   lucidity-mcp --transport both
   ```

2. Connect different AI assistants to either endpoint:

   ```
   SSE: sse://localhost:6969/sse
   Streamable HTTP: http://localhost:6969/mcp
   ```

3. Multiple clients can connect using either transport simultaneously!

## ⚙️ Configuration

Lucidity can be configured using environment variables for deployment flexibility:

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LUCIDITY_CACHE_DIR` | `/tmp/lucidity-mcp-repos` | Directory for caching cloned repositories |
| `LUCIDITY_CLONE_TIMEOUT` | `300` | Timeout in seconds for git clone operations |
| `LUCIDITY_FETCH_TIMEOUT` | `60` | Timeout in seconds for git fetch operations |
| `LUCIDITY_CLEANUP_DAYS` | `7` | Days of inactivity before cleaning cached repos |
| `LUCIDITY_MCP_PORT` | `6969` | Default port for network transports |
| `LUCIDITY_CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `LUCIDITY_SSH_VERIFY` | `false` | Enable SSH host key verification |

### Example Configuration

```bash
# Development environment
export LUCIDITY_CACHE_DIR="/tmp/lucidity-cache"
export LUCIDITY_CORS_ORIGINS="*"
export LUCIDITY_SSH_VERIFY="false"

# Production environment
export LUCIDITY_CACHE_DIR="/var/cache/lucidity"
export LUCIDITY_CORS_ORIGINS="https://app.example.com,https://admin.example.com"
export LUCIDITY_SSH_VERIFY="true"
export LUCIDITY_MCP_PORT="8080"
```

**See the [Security Considerations](#️-security-considerations) section below for important information about secure configuration.**

## 🧠 Analysis Dimensions

Lucidity analyzes code across 10 critical quality dimensions:

1. **Unnecessary Complexity** - Identifies overly complex algorithms, excessive abstractions, and convoluted logic
2. **Poor Abstractions** - Detects leaky or inappropriate abstractions and unclear separation of concerns
3. **Unintended Code Deletion** - Catches accidental removal of critical functionality or validation
4. **Hallucinated Components** - Finds references to non-existent functions, classes, or APIs
5. **Style Inconsistencies** - Spots deviations from project coding standards and conventions
6. **Security Vulnerabilities** - Identifies potential security issues in code changes
7. **Performance Issues** - Detects inefficient algorithms or operations that could impact performance
8. **Code Duplication** - Finds repeated logic or functionality that should be refactored
9. **Incomplete Error Handling** - Spots missing or inadequate exception handling
10. **Test Coverage Gaps** - Identifies missing tests for critical functionality

## 📊 Example AI Assistant Queries

With an AI assistant connected to Lucidity, try these queries:

- "Analyze the code quality in my latest git changes"
- "Check for security vulnerabilities in my JavaScript changes"
- "Make sure my Python code follows best practices"
- "Identify any performance issues in my recent code changes"
- "Are there any unintended side effects in my recent refactoring?"
- "Help me improve the abstractions in my code"
- "Check if I've accidentally removed any important validation"
- "Find any hallucinated API calls in my latest commit"
- "Is my error handling complete and robust?"
- "Are there any test coverage gaps in my new feature?"

## 🛠️ Available MCP Tools

### Tools

- `analyze_changes` - Prepares git changes for analysis through MCP
  - Parameters:
    - `workspace_root`: The root directory of the workspace/git repository, or a remote git URL
      - Supports local paths: `/path/to/local/repo`
      - Supports SSH URLs: `git@github.com:username/repo.git`
      - Supports HTTPS URLs: `https://github.com/username/repo.git`
      - Supports short GitHub format: `username/repo` (automatically converted to SSH)
      - Supports GitHub domain format: `github.com/username/repo` (automatically converted to SSH)
      - **Branch specification**: Append `@branch` to any format (e.g., `username/repo@develop`)
    - `path`: Optional specific file path to analyze

### Remote Repository Support

Lucidity MCP now supports analyzing remote repositories without requiring a local clone! When you provide a remote repository URL as the `workspace_root`, Lucidity will:

1. **Automatically clone** the repository to a cache location (default: `/tmp/lucidity-mcp-repos/`)
2. **Cache the clone** for future use to avoid repeated cloning
3. **Update automatically** by fetching latest changes if the repository already exists
4. **Checkout specific branches** when specified using the `@branch` syntax
5. **Work seamlessly** with the existing analysis workflow
6. **Skip SSH host key verification** for convenience (see security note below)
7. **Track access times** to enable cleanup of inactive repositories

**Prerequisites for remote repositories:**
- Git must be installed and accessible
- For SSH URLs (default), a valid SSH key must be configured for authentication
- For HTTPS URLs, appropriate credentials may be required

**Cache Configuration:**
The repository cache location can be customized using the `LUCIDITY_CACHE_DIR` environment variable:
```bash
export LUCIDITY_CACHE_DIR="/path/to/custom/cache"
```

If not set, repositories are cached in `/tmp/lucidity-mcp-repos/`.

## ⚠️ Security Considerations

Lucidity includes several security-related configuration options that should be carefully considered based on your deployment environment.

### SSH Host Key Verification

**WARNING:** By default, SSH host key verification is disabled when cloning repositories.

**Security Risk:**
- Disabling host key verification removes protection against man-in-the-middle (MITM) attacks
- An attacker could intercept git clone/fetch operations and serve malicious code
- This is particularly risky when working with untrusted networks or repositories

**Default Behavior:**
For convenience in development and automated workflows, Lucidity automatically disables SSH host key verification. This allows seamless operation without requiring manual host key acceptance.

**Enable Verification (Recommended for Production):**
To enable SSH host key verification, set the `LUCIDITY_SSH_VERIFY` environment variable:

```bash
export LUCIDITY_SSH_VERIFY=true
```

When enabled, you must ensure that:
- SSH known_hosts file is properly configured
- Host keys for target repositories are pre-accepted
- Your deployment environment can handle SSH key verification prompts

**Alternative: Use HTTPS with Credentials**
For sensitive repositories or production environments, consider using HTTPS URLs with proper credential management instead of SSH:

```python
# Safer alternative to SSH for sensitive code
analyze_changes(workspace_root="https://github.com/username/private-repo.git")
```

### CORS Configuration

**Default:** CORS allows all origins (`*`)

**Security Risk:**
Allowing all origins exposes the server to:
- Cross-site scripting attacks
- Unauthorized access from malicious websites
- Data leakage through browser-based attacks

**Configure Restricted Origins (Recommended for Production):**
Set allowed origins via the `LUCIDITY_CORS_ORIGINS` environment variable:

```bash
# Single origin
export LUCIDITY_CORS_ORIGINS="https://yourdomain.com"

# Multiple origins (comma-separated)
export LUCIDITY_CORS_ORIGINS="https://app.yourdomain.com,https://admin.yourdomain.com"
```

**Development vs Production:**
- **Development:** Wildcard (`*`) is acceptable for local testing
- **Production:** Always specify explicit allowed origins

### Input Validation

Lucidity validates all user inputs to prevent:
- Command injection attacks through git commands
- Directory traversal attacks via branch names and paths
- Shell metacharacter injection

These protections are always active and cannot be disabled.

### Best Practices

1. **Network Security:**
   - Run Lucidity behind a firewall or reverse proxy in production
   - Use TLS/HTTPS for network transports
   - Bind to localhost (127.0.0.1) when possible to limit exposure

2. **Access Control:**
   - Implement authentication/authorization at the reverse proxy level
   - Use network-level access controls (firewall rules, security groups)
   - Monitor and log all access attempts

3. **Repository Security:**
   - Enable SSH host key verification for production (`LUCIDITY_SSH_VERIFY=true`)
   - Use HTTPS URLs with credentials for sensitive repositories
   - Regularly review and clean up cached repositories
   - Set appropriate cache directory permissions

4. **Configuration:**
   - Store sensitive configuration in environment variables, not in code
   - Use restrictive CORS origins in production
   - Enable audit logging for security-relevant events

**Example usage:**
```python
# Analyze a remote GitHub repository using short format (default branch)
analyze_changes(workspace_root="username/repo")

# Analyze a specific branch
analyze_changes(workspace_root="username/repo@develop")

# Or use full SSH URL with branch
analyze_changes(workspace_root="git@github.com:username/repo.git@feature-branch")

# Or HTTPS URL with branch
analyze_changes(workspace_root="https://github.com/username/repo.git@main")

# Local repositories still work as before
analyze_changes(workspace_root="/path/to/local/repo")
```

### Repository Cache Cleanup

To prevent disk space issues from accumulated cached repositories, Lucidity provides a cleanup command that removes repositories that haven't been accessed recently.

**Manual Cleanup:**
```bash
# Clean up repositories inactive for 7+ days (default)
lucidity-mcp --cleanup-cache

# Specify custom inactivity threshold (e.g., 30 days)
lucidity-mcp --cleanup-cache --cleanup-days 30

# Dry run to see what would be removed without actually deleting
lucidity-mcp --cleanup-cache --dry-run
```

**Automated Cleanup with Cron:**
Add to your crontab to run cleanup automatically:
```bash
# Clean up every Sunday at 2 AM
0 2 * * 0 /path/to/lucidity-mcp --cleanup-cache --cleanup-days 7

# Or using custom cache directory
0 2 * * 0 LUCIDITY_CACHE_DIR=/custom/path /path/to/lucidity-mcp --cleanup-cache
```

The cleanup process:
- Scans the cache directory for cloned repositories
- Checks the `.last_accessed` file in each repository
- Removes repositories that haven't been accessed within the specified time period
- Reports the number of repositories removed and disk space freed

**Note:** Each time a repository is cloned or updated, its access time is automatically tracked, so actively used repositories will never be removed.

### Instructions for AI Agents

If you are an AI agent using this tool, **read this carefully** to avoid common mistakes:

#### ⚠️ CRITICAL: Remote vs Local Repositories

**When the MCP server is running remotely** (separate from the repository location), you **MUST** use remote repository URLs, not local filesystem paths.

❌ **COMMON MISTAKE** - Using local paths that don't exist on MCP server:
```python
# These will FAIL if MCP server doesn't have access to this filesystem:
analyze_changes(workspace_root="/home/runner/_work/repo/repo")
analyze_changes(workspace_root="/github/workspace/myproject")
analyze_changes(workspace_root="./local-checkout")
```

✅ **CORRECT** - Using remote repository URLs:
```python
# These will work because MCP server can clone from remote:
analyze_changes(workspace_root="username/repo")
analyze_changes(workspace_root="username/repo@feature-branch")
analyze_changes(workspace_root="git@github.com:username/repo.git@branch-name")
```

#### Decision Tree: Which Format Should I Use?

```
Is the MCP server running on the same machine as the repository?
│
├─ NO (most common in CI/CD, GitHub Actions, remote servers)
│  └─> Use REMOTE format: "username/repo@branch"
│
└─ YES (local development with local MCP server)
   └─> Can use LOCAL format: "/path/to/repo"
```

#### Usage Guidelines

1. **Analyzing Uncommitted Changes (Local Development)**
   
   Use when you have local changes in your working directory:
   
   ```python
   # Analyze uncommitted changes in working directory
   analyze_changes(workspace_root="/path/to/local/repo")
   analyze_changes(workspace_root="username/repo")  # if already cloned remotely
   ```

2. **Analyzing Committed Changes (Remote Repositories / Historical Analysis)**
   
   **This is the recommended approach for remote repositories!**
   
   Use the `commits` parameter to analyze committed changes:
   
   ```python
   # Analyze last commit
   analyze_changes(workspace_root="username/repo", commits="HEAD~1..HEAD")
   
   # Analyze last 5 commits
   analyze_changes(workspace_root="username/repo", commits="HEAD~5..HEAD")
   
   # Analyze a specific commit
   analyze_changes(workspace_root="username/repo", commits="abc123^..abc123")
   
   # Analyze differences between branches
   analyze_changes(workspace_root="username/repo", commits="main..feature-branch")
   ```
   
   **Common commit range patterns:**
   - `"HEAD~1..HEAD"` - Last commit only
   - `"HEAD~5..HEAD"` - Last 5 commits
   - `"abc123^..abc123"` - Specific commit by hash
   - `"main..develop"` - All changes in develop not in main
   - `"v1.0..v2.0"` - Changes between tags

3. **Remote Repository (Default/Recommended)**
   
   Use this format in most cases, especially:
   - GitHub Actions / CI/CD pipelines
   - Remote MCP server deployments
   - When analyzing repositories you don't have locally
   
   ```python
   # Analyze default branch
   analyze_changes(workspace_root="username/repo")
   
   # Analyze specific branch
   analyze_changes(workspace_root="username/repo@develop")
   analyze_changes(workspace_root="username/repo@feature/new-api")
   
   # Full URL formats also work
   analyze_changes(workspace_root="git@github.com:username/repo.git@branch")
   analyze_changes(workspace_root="https://github.com/username/repo.git@main")
   ```

4. **GitHub Actions / CI/CD Context**
   
   When running in CI/CD, the local checkout path is on the **CI runner**, not the MCP server.
   
   ❌ **DON'T** use the CI workspace path:
   ```python
   # These paths exist on CI runner, NOT on MCP server
   analyze_changes(workspace_root="/home/runner/_work/repo/repo")
   analyze_changes(workspace_root="/github/workspace")  # Even if set via CI environment
   ```
   
   ✅ **DO** extract repository info from CI environment and use commits parameter:
   ```python
   # Use repository slug from CI environment variables
   # GitHub Actions example: GITHUB_REPOSITORY = "username/repo"
   
   # Analyze the last commit in a PR or push
   import os
   repo = os.environ.get('GITHUB_REPOSITORY', 'username/repo')  # e.g., "username/repo"
   branch = os.environ.get('GITHUB_REF_NAME', 'main')           # e.g., "feature-branch"
   
   # Analyze last commit
   analyze_changes(workspace_root=f"{repo}@{branch}", commits="HEAD~1..HEAD")
   
   # Or analyze multiple recent commits
   analyze_changes(workspace_root=f"{repo}@{branch}", commits="HEAD~5..HEAD")
   ```

5. **Local Development (Only if MCP Server Has Access)**
   
   Only use filesystem paths when:
   - MCP server runs on your local machine
   - The repository is on the same filesystem
   - You're developing and testing locally
   
   ```python
   analyze_changes(workspace_root="/home/user/projects/myrepo")
   ```

6. **Handling User Input**
   
   When a user provides a path:
   
   ```python
   # If user gives you a path like "/path/to/repo"
   # and you're in a remote context, ask for the repository URL:
   
   user_path = "/home/runner/_work/repo/repo"
   
   # ASK: "What is the GitHub repository URL for this project?"
   # Then use: "username/repo@branch" format with commits parameter
   
   # If unsure whether it's local or remote:
   if user_path.startswith('/') or user_path.startswith('./'):
       # Probably a local path - ask for remote URL instead
       # "I need the repository URL (e.g., username/repo) to analyze remotely"
       # "Should I analyze uncommitted changes or recent commits?"
   ```

7. **Error Handling**
   
   If you see "No uncommitted changes detected":
   
   ```
   ✓ For remote repositories, use the 'commits' parameter to analyze committed changes
   ✓ Example: commits="HEAD~1..HEAD" for last commit
   ```
   
   If you see "Could not access or clone repository":
   
   ```
   ✓ Check if you used a local path instead of remote URL
   ✓ Verify the repository URL is correct (username/repo format)
   ✓ Confirm the branch name exists
   ✓ Ensure SSH keys are configured for private repositories
   ✓ Try HTTPS format if SSH fails
   ```

#### Quick Reference

| Context | Format to Use | Commits Parameter | Example |
|---------|---------------|-------------------|---------|
| GitHub Actions (analyze PR) | `username/repo@branch` | `HEAD~1..HEAD` or `HEAD~N..HEAD` | `myorg/myapp@pr-branch` with `commits="HEAD~1..HEAD"` |
| CI/CD Pipeline | `username/repo@branch` | `HEAD~1..HEAD` | `company/project@develop` with `commits="HEAD~1..HEAD"` |
| Remote Analysis (last commit) | `username/repo@branch` | `HEAD~1..HEAD` | `user/repo@main` with `commits="HEAD~1..HEAD"` |
| Remote Analysis (multiple commits) | `username/repo@branch` | `HEAD~5..HEAD` | `user/repo@feature` with `commits="HEAD~5..HEAD"` |
| Local Uncommitted Changes | `/path/to/repo` | _(none)_ | `/home/dev/project` |

#### Example Scenarios

**Scenario 1: Analyzing a PR in GitHub Actions**
```python
# ❌ WRONG - uses local CI runner path
analyze_changes(workspace_root="/home/runner/_work/myrepo/myrepo")

# ✅ CORRECT - uses remote repository reference with commits
analyze_changes(workspace_root="myorg/myrepo@pr-123-feature", commits="HEAD~1..HEAD")
```

**Scenario 2: User asks to analyze their remote repository**
```
User: "Can you analyze the code in my repository username/myproject?"

✅ Agent: "Should I analyze uncommitted changes or recent commits?"
User: "Analyze the last commit"
Agent: analyze_changes(workspace_root="username/myproject", commits="HEAD~1..HEAD")
```

**Scenario 3: Analyzing a specific branch with multiple commits**
```python
# Analyze last 5 commits in a feature branch
analyze_changes(
    workspace_root="company/app@feature/user-auth",
    commits="HEAD~5..HEAD"
)

# Or using full SSH URL
analyze_changes(
    workspace_root="git@github.com:company/app.git@feature/user-auth",
    commits="HEAD~5..HEAD"
)
```

**Scenario 4: Historical code review**
```python
# Analyze a specific commit by hash
analyze_changes(
    workspace_root="username/repo",
    commits="abc123^..abc123"
)

# Analyze changes between two tags
analyze_changes(
    workspace_root="username/repo",
    commits="v1.0..v2.0"
)
```


## 💻 Development

Lucidity uses UV for dependency management and development workflows. UV is a fast, reliable Python package manager and resolver.

```bash
# Update dependencies
uv sync

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy .
```

## 🔧 Logging Behavior

Lucidity handles logging differently depending on the transport:

- **SSE transport**: Full console logging is enabled
- **Streamable HTTP transport**: Full console logging is enabled
- **Both transports**: Full console logging is enabled
- **Stdio transport with --log-file**: All logs go to the file, console is disabled
- **Stdio transport without --log-file**: Only warnings and errors go to stderr, info logs are disabled

This ensures that stdio communication isn't broken by logs appearing on stdout.

## 🌐 Transport Options

Lucidity supports four transport configurations:

### Stdio Transport
- **Use case**: Terminal-based interaction, local development
- **Connection**: Direct process communication via stdin/stdout
- **Best for**: Command-line tools, local testing

### SSE Transport (Legacy)
- **Use case**: Network-based communication (legacy support)
- **Connection**: Server-Sent Events over HTTP
- **Endpoints**: `/sse` for streaming, `/messages/` for posting
- **Best for**: Legacy systems already using SSE

### Streamable HTTP Transport (Recommended)
- **Use case**: Modern network-based communication
- **Connection**: Single HTTP endpoint with request/response and optional streaming
- **Endpoint**: `/mcp` for all communication
- **Advantages**:
  - Simpler architecture with a single endpoint
  - Better scalability and load balancing support
  - Improved compatibility with proxies and CDNs
  - Native HTTP semantics (easier debugging)
  - Recommended by the MCP specification for new deployments
- **Best for**: Production deployments, cloud environments, modern integrations

### Both Transports (SSE + Streamable HTTP)
- **Use case**: Supporting multiple client types simultaneously
- **Connection**: Both SSE and Streamable HTTP on the same server
- **Endpoints**: 
  - `/sse` + `/messages/` for SSE clients
  - `/mcp` for Streamable HTTP clients
- **Advantages**:
  - Backward compatibility with existing SSE clients
  - Modern Streamable HTTP support for new clients
  - Single server instance handles all client types
  - Seamless migration path from SSE to Streamable HTTP
- **Best for**: Transition periods, supporting diverse client ecosystems, maximum flexibility

## 🎛️ Command-line Options

```
usage: lucidity-mcp [-h] [--debug] [--host HOST] [--port PORT]
                    [--transport {stdio,sse,streamable-http,both}]
                    [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--verbose]
                    [--log-file LOG_FILE]

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging
  --host HOST           Host to bind the server to (use 0.0.0.0 for all interfaces)
  --port PORT           Port to listen on for network connections
  --transport {stdio,sse,streamable-http,both}
                        Transport type to use:
                        - stdio: for terminal interaction
                        - sse: for network (legacy, SSE-based)
                        - streamable-http: for network (recommended, modern HTTP)
                        - both: SSE + Streamable HTTP simultaneously
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level
  --verbose             Enable verbose logging for HTTP requests
  --log-file LOG_FILE   Path to log file (required for stdio transport if logs enabled)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Set up your development environment with UV
4. Make your changes
5. Run tests and linting
6. Commit your changes (`git commit -m 'Add some amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find Lucidity useful, [buy me a Monster Ultra Violet ⚡️](https://ko-fi.com/hyperb1iss)

</div>
