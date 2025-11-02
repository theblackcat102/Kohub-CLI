<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# Quick Start

The [KohakuHub](https://kohaku.blue/) is a Git-based platform for hosting and sharing machine learning models, datasets, and spaces. The `kohub-cli` helps you interact with KohakuHub without leaving your development environment. You can create and manage repositories easily, download and upload files, and collaborate with the community.

## Installation

To get started, install `kohub-cli`:

```bash
pip install git+https://github.com/KohakuBlueleaf/Kohub-CLI.git
```

For more details, check out the [installation](installation) guide.

## Authentication

Before you can use `kohub-cli` to interact with KohakuHub, you need to authenticate:

```bash
kohub-cli auth login
```

This will prompt you to enter your KohakuHub credentials or API token. Alternatively, you can set your token as an environment variable:

```bash
export HF_TOKEN=your_token_here
```

You can also configure a custom KohakuHub endpoint if you're using a self-hosted instance:

```bash
export HF_ENDPOINT=https://your-kohaku-instance.com
```

## Create Your First Repository

Let's create a new model repository:

```bash
kohub-cli repo create my-username/my-first-model --type model
```

You can also create datasets and spaces:

```bash
# Create a dataset repository
kohub-cli repo create my-username/my-dataset --type dataset

# Create a private space
kohub-cli repo create my-username/my-space --type space --private
```

## Upload Files

Upload a single file to your repository:

```bash
kohub-cli settings repo upload my-username/my-first-model /local/path/README.md --path README.md
```

You can also upload entire directories. Large files will automatically use Git LFS:

```bash
kohub-cli settings repo upload my-username/my-first-model /local/path/model.bin --path model.bin
```

## Download Files

Download files from any public repository:

```bash
# Download a single file
kohub-cli settings repo download my-username/my-first-model config.json --output ./config.json

# Download to current directory
kohub-cli settings repo download my-username/my-first-model README.md
```

You can also download specific versions of files using commit hashes, branches, or tags:

```bash
kohub-cli settings repo download my-username/my-first-model config.json --revision main
```

## Browse Repository Contents

List all files in a repository:

```bash
kohub-cli repo files my-username/my-first-model
```

For a detailed view with file sizes and types:

```bash
kohub-cli repo files my-username/my-first-model --recursive --json
```

## Repository Information

Get detailed information about a repository:

```bash
kohub-cli repo info my-username/my-first-model
```

View the commit history:

```bash
kohub-cli repo commits my-username/my-first-model --limit 10
```

## Interactive Mode

For a more user-friendly experience, launch the interactive TUI:

```bash
kohub-cli interactive
```

This provides a menu-driven interface where you can:
- Browse your repositories
- Upload and download files
- Manage organizations
- View repository information
- And much more!

## Organization Management

Create an organization to collaborate with others:

```bash
# Create an organization
kohub-cli org create my-org --description "My awesome organization"

# Add members to your organization
kohub-cli org member add my-org friend-username --role member

# List organization members
kohub-cli settings organization members my-org
```

## Configuration

You can configure default settings for `kohub-cli`:

```bash
# Set default endpoint
kohub-cli config set endpoint https://your-kohaku-instance.com

# Set default organization
kohub-cli config set default_org my-organization

# View all configuration
kohub-cli config list
```

## Transfer Functions

One of the unique features of `kohub-cli` is the ability to transfer content between different hub platforms:

```bash
# Transfer a repository from Hugging Face to KohakuHub
kohub-cli transfer huggingface-to-kohaku username/repo-name
```

## JSON Output for Automation

Most commands support `--json` output for scripting and automation:

```bash
# Get repository info as JSON
kohub-cli repo info my-username/my-repo --json

# List files as JSON
kohub-cli repo files my-username/my-repo --json
```

## What's Next?

Now that you know the basics, explore these guides for more advanced usage:

- [Authentication Guide](guides/authentication) - Learn about token management and security
- [Repository Management](guides/repository-management) - Advanced repository operations
- [File Operations](guides/file-operations) - Detailed file upload/download workflows
- [Organization Management](guides/organization-management) - Team collaboration features
- [Interactive Mode](guides/interactive-mode) - Master the TUI interface
- [Transfer Functions](guides/transfer-functions) - Move content between platforms

For a complete reference of all available commands, see the [CLI Reference](package_reference/cli).