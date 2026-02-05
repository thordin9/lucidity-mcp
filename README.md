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
- 🔀 **Flexible Transport** - Supports both stdio for terminal-based interaction and SSE for network-based communication
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

# Run with debug logging
lucidity-mcp --debug

# Run with file logging
lucidity-mcp --log-file lucidity.log
```

### Using with AI Assistants

1. Start Lucidity in SSE mode:

   ```bash
   lucidity-mcp --transport sse
   ```

2. Connect your AI assistant using the MCP protocol URI:

   ```
   sse://localhost:6969/sse
   ```

3. The AI can now invoke the `analyze_changes` tool to get code quality feedback!

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

1. **Automatically clone** the repository to a temporary location (`/tmp/lucidity-mcp-repos/`)
2. **Cache the clone** for future use to avoid repeated cloning
3. **Update automatically** by fetching latest changes if the repository already exists
4. **Checkout specific branches** when specified using the `@branch` syntax
5. **Work seamlessly** with the existing analysis workflow
6. **Skip SSH host key verification** for convenience (see security note below)

**Prerequisites for remote repositories:**
- Git must be installed and accessible
- For SSH URLs (default), a valid SSH key must be configured for authentication
- For HTTPS URLs, appropriate credentials may be required

**Security Note:**
SSH host key verification is automatically disabled when cloning or updating repositories via SSH. This allows seamless operation without requiring manual host key acceptance. While this is convenient for development and automated workflows, be aware that it bypasses a security measure that normally protects against man-in-the-middle attacks.

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

### Instructions for AI Agents

If you are an AI agent using this tool, follow these guidelines:

1. **Default Usage**: For most cases, use the short format `username/repo` which will clone the default branch
   ```python
   analyze_changes(workspace_root="username/repo")
   ```

2. **Specify Branch**: If you need to analyze a specific branch (e.g., a development branch, pull request branch, or feature branch), append `@branch-name`:
   ```python
   analyze_changes(workspace_root="username/repo@develop")
   analyze_changes(workspace_root="username/repo@feature/new-api")
   ```

3. **Local Repositories**: If the user provides a local path, use it directly:
   ```python
   analyze_changes(workspace_root="/home/user/project")
   ```

4. **Workflow Example**: When a user asks to analyze their code changes:
   - Ask if they want to analyze a specific branch (if not specified)
   - Use the appropriate format based on their response
   - The tool will handle cloning, caching, and updating automatically

5. **Error Handling**: If cloning fails:
   - Check if the repository URL is correct
   - Verify the branch name exists
   - Ensure SSH keys are configured for private repositories
   - Try HTTPS format if SSH fails

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
- **Stdio transport with --log-file**: All logs go to the file, console is disabled
- **Stdio transport without --log-file**: Only warnings and errors go to stderr, info logs are disabled

This ensures that stdio communication isn't broken by logs appearing on stdout.

## 🎛️ Command-line Options

```
usage: lucidity-mcp [-h] [--debug] [--host HOST] [--port PORT] [--transport {stdio,sse}]
                [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--verbose]
                [--log-file LOG_FILE]

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging
  --host HOST           Host to bind the server to (use 0.0.0.0 for all interfaces)
  --port PORT           Port to listen on for network connections
  --transport {stdio,sse}
                        Transport type to use (stdio for terminal, sse for network)
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
