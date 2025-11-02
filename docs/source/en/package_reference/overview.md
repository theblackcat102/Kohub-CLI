<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# Package Reference Overview

This section provides comprehensive technical documentation for all `kohub-cli` commands, APIs, and configuration options.

## Command Line Interface

The `kohub-cli` provides a rich set of commands organized into logical groups:

### Core Commands
- **[CLI Commands](cli)** - Complete reference for all available commands and options

### Authentication & Security
- **[Authentication](authentication)** - Token management, login/logout, and security configuration

### Repository Operations
- **[Repository API](repository-api)** - Create, manage, and query repositories

### File Management
- **[File Operations](file-operations)** - Upload, download, and manage files with Git LFS support

### Team Collaboration
- **[Organization API](organization-api)** - Organization and member management

### Configuration
- **[Configuration](configuration)** - Settings, profiles, and environment variables

## Command Structure

All `kohub-cli` commands follow a consistent structure:

```bash
kohub-cli [GLOBAL_OPTIONS] COMMAND [SUBCOMMAND] [OPTIONS] [ARGUMENTS]
```

### Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `--help, -h` | Show help message |
| `--version` | Show version information |
| `--json` | Output results in JSON format |
| `--verbose, -v` | Enable verbose output |
| `--quiet, -q` | Suppress non-error output |
| `--profile PROFILE` | Use specific configuration profile |

### Command Categories

#### Authentication Commands
```bash
kohub-cli auth login          # Authenticate with KohakuHub
kohub-cli auth logout         # Logout and clear credentials
kohub-cli auth whoami         # Show current user information
```

#### Repository Commands
```bash
kohub-cli repo create         # Create a new repository
kohub-cli repo delete         # Delete a repository
kohub-cli repo list           # List repositories
kohub-cli repo info           # Get repository information
kohub-cli repo files          # List repository files
kohub-cli repo commits        # Show commit history
```

#### File Operations
```bash
kohub-cli settings repo upload    # Upload files to repository
kohub-cli settings repo download  # Download files from repository
```

#### Organization Commands
```bash
kohub-cli org create          # Create an organization
kohub-cli org delete          # Delete an organization
kohub-cli org member add      # Add organization member
kohub-cli org member remove   # Remove organization member
kohub-cli settings organization members  # List organization members
```

#### Configuration Commands
```bash
kohub-cli config set          # Set configuration value
kohub-cli config get          # Get configuration value
kohub-cli config list         # List all configuration
kohub-cli config reset        # Reset configuration
```

#### Transfer Commands
```bash
kohub-cli transfer huggingface-to-kohaku  # Transfer from Hugging Face
```

#### Utility Commands
```bash
kohub-cli interactive         # Launch interactive TUI mode
kohub-cli cache clear         # Clear local cache
```

## Exit Codes

`kohub-cli` uses standard exit codes to indicate command status:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of command (invalid arguments) |
| 3 | Authentication error |
| 4 | Permission denied |
| 5 | Network error |
| 6 | File not found |
| 7 | Repository not found |

## Configuration Files

`kohub-cli` uses configuration files stored in:

- **Linux/macOS**: `~/.config/kohub-cli/`
- **Windows**: `%APPDATA%\kohub-cli\`

### Configuration Structure
```yaml
# ~/.config/kohub-cli/config.yaml
profiles:
  default:
    endpoint: "https://kohaku.blue"
    token: "your-token-here"
  huggingface:
    endpoint: "https://huggingface.co"
    token: "hf_your-token-here"

current_profile: "default"
cache_dir: "~/.cache/kohub-cli"
```

## Environment Variables

Key environment variables that affect `kohub-cli` behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_ENDPOINT` | KohakuHub endpoint URL | https://kohaku.blue |
| `HF_TOKEN` | Authentication token | None |
| `KOHUB_CACHE_DIR` | Cache directory | System default |
| `KOHUB_CONFIG_DIR` | Config directory | System default |
| `NO_COLOR` | Disable colored output | False |
| `KOHUB_PROFILE` | Default profile to use | default |

## Error Handling

`kohub-cli` provides detailed error messages and suggestions:

```bash
$ kohub-cli repo info nonexistent/repo
Error: Repository 'nonexistent/repo' not found
Suggestion: Check the repository name and ensure you have access permissions

$ kohub-cli settings repo upload missing-repo file.txt
Error: Authentication required
Suggestion: Run 'kohub-cli auth login' to authenticate
```

## JSON Output Format

When using `--json`, commands return structured data:

```json
{
  "status": "success",
  "data": {
    "repository": {
      "name": "my-repo",
      "type": "model",
      "private": false,
      "url": "https://kohaku.blue/username/my-repo"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

Error responses:
```json
{
  "status": "error",
  "error": {
    "code": "REPO_NOT_FOUND",
    "message": "Repository 'username/repo' not found",
    "suggestion": "Check the repository name and permissions"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## API Rate Limits

Be aware of API rate limits when using `kohub-cli` in scripts:

- **Authenticated requests**: 5000 per hour
- **Unauthenticated requests**: 60 per hour
- **File uploads**: 100 per hour

Use `--verbose` to see rate limit headers:

```bash
$ kohub-cli --verbose repo list
Rate limit: 4999/5000 remaining, resets at 2024-01-01T13:00:00Z
```

## Caching

`kohub-cli` caches API responses and downloaded files to improve performance:

- **API cache**: 5 minutes for repository metadata
- **File cache**: Indefinite for downloaded files
- **Clear cache**: `kohub-cli cache clear`

For more detailed information about specific commands and their options, see the individual reference pages listed above.