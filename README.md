# kohub-cli
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/theblackcat102/KohakuHub/4a32355364b40c751735d59c651dab023f6c6d68/images/logo-banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/theblackcat102/KohakuHub/4a32355364b40c751735d59c651dab023f6c6d68/images/logo-banner.svg">
    <img alt="huggingface_hub library logo" src="https://raw.githubusercontent.com/theblackcat102/KohakuHub/4a32355364b40c751735d59c651dab023f6c6d68/images/logo-banner.svg" width="600" height="80" style="max-width: 100%; padding-left: 100px">
  </picture>
  <br/>
  <br/>
</p> 

<p align="center">
    <i>The official command-line interface for KohakuHub.</i>
</p>

<p align="center">
    <a href="https://github.com/KohakuBlueleaf/Kohub-CLI"><img alt="GitHub" src="https://img.shields.io/github/stars/KohakuBlueleaf/Kohub-CLI?style=social"></a>
    <!-- <a href="https://github.com/KohakuBlueleaf/Kohub-CLI/releases"><img alt="GitHub release" src="https://img.shields.io/github/release/KohakuBlueleaf/Kohub-CLI.svg"></a>
    <a href="https://pypi.org/project/kohub-cli"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/kohub-cli.svg"></a> -->
    <a href="https://github.com/KohakuBlueleaf/Kohub-CLI/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/KohakuBlueleaf/Kohub-CLI"></a>
    <a href="https://deepwiki.com/KohakuBlueleaf/Kohub-CLI"><img alt="Ask DeepWiki" src="https://deepwiki.com/badge.svg"></a>
</p>

---

**Source Code**: <a href="https://github.com/KohakuBlueleaf/Kohub-CLI" target="_blank">https://github.com/KohakuBlueleaf/Kohub-CLI</a>

---

## Welcome to kohub-cli

`kohub-cli` is a command-line interface for interacting with KohakuHub, a Git-based platform for hosting and sharing machine learning models, datasets, and spaces. It provides a simple and efficient way to manage your repositories, upload/download files, and transfer content between different hub platforms.

## Key Features

- **Authentication & User Management**: Login, manage API tokens, and user profiles
- **Repository Management**: Create, delete, and manage models, datasets, and spaces
- **File Operations**: Upload/download files with automatic LFS support
- **Organization Management**: Create and manage organizations and team members
- **Version Control**: Browse commits, view diffs, and manage branches/tags
- **External Token Management**: Manage tokens for external services like Hugging Face
- **Interactive TUI**: Menu-driven interface for easy navigation
- **JSON Output**: Programmatic access for automation and scripting

## Installation

### From Git (current method)

Install directly from the GitHub repository:

```bash
pip install git+https://github.com/KohakuBlueleaf/Kohub-CLI.git
```

Requirements:
- Python ≥ 3.10
- Git (for repository operations)

## Quick Start

### Authentication

Login to KohakuHub:

```bash
kohub-cli auth login
# or using an environment variable
export HF_TOKEN=your_token_here
```

### Create a Repository

```bash
# Create a model repository
kohub-cli repo create my-org/my-awesome-model --type model

# Create a private dataset
kohub-cli repo create my-org/my-dataset --type dataset --private
```

### Upload Files

Upload a single file:

```bash
kohub-cli settings repo upload my-org/my-repo /local/path/README.md --path README.md
```

### Download Files

Download a single file:

```bash
kohub-cli settings repo download my-org/my-repo config.json --output ./config.json
```

### List Repository Files

Browse repository contents:

```bash
kohub-cli repo files my-org/my-repo --recursive
```

### Interactive Mode

Launch the interactive TUI for a menu-driven experience:

```bash
kohub-cli interactive
```

## Advanced Usage

### Organization Management

```bash
# Create an organization
kohub-cli org create my-org --description "My organization"

# Add a member
kohub-cli org member add my-org new-member --role admin

# List organization members
kohub-cli settings organization members my-org
```

### Repository Operations

```bash
# List all your repositories
kohub-cli repo list --type model

# View repository information
kohub-cli repo info username/repo-name

# List repository files
kohub-cli repo files username/repo-name --recursive

# View commit history
kohub-cli repo commits username/repo-name --limit 10
```

### Configuration

Set default endpoint:

```bash
export HF_ENDPOINT=https://your-kohaku-instance.com
```

Configure through CLI:

```bash
kohub-cli config set endpoint https://your-kohaku-instance.com
kohub-cli config set default_org my-organization
kohub-cli config list
```

## Development

### Setting up the development environment

```bash
# Clone the repository
git clone https://github.com/KohakuBlueleaf/Kohub-CLI
cd Kohub-CLI

# Install in development mode
pip install -e .
```

### Running tests

```bash
pytest tests/
```

## Contributing

We welcome contributions! Please feel free to:

- Submit issues and feature requests
- Fork the repository and create pull requests
- Improve documentation
- Share feedback and suggestions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

`kohub-cli` is inspired by and compatible with the excellent [huggingface_hub](https://github.com/huggingface/huggingface_hub) library. We aim to provide similar functionality for KohakuHub users while maintaining compatibility with the broader ML ecosystem.

## Support

- **Issues**: [GitHub Issues](https://github.com/KohakuBlueleaf/Kohub-CLI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KohakuBlueleaf/Kohub-CLI/discussions)

---

Made with ❤️ by the KohakuHub community