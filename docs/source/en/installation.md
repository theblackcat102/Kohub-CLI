<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# Installation

This guide will help you install `kohub-cli` on your system.

## Requirements

Before installing `kohub-cli`, make sure you have:

- **Python ≥ 3.10**: `kohub-cli` requires Python 3.10 or higher
- **Git**: Required for repository operations and version control
- **Operating System**: Linux, macOS, or Windows

You can check your Python version with:

```bash
python --version
```

## Installation Methods

### From Git (Recommended)

Currently, the recommended way to install `kohub-cli` is directly from the GitHub repository:

```bash
pip install git+https://github.com/KohakuBlueleaf/Kohub-CLI.git
```

This will install the latest version of `kohub-cli` and all its dependencies.

### Development Installation

If you want to contribute to `kohub-cli` or need the latest development features:

```bash
# Clone the repository
git clone https://github.com/KohakuBlueleaf/Kohub-CLI.git
cd Kohub-CLI

# Install in development mode
pip install -e .
```

Development installation allows you to make changes to the code and see them immediately without reinstalling.

## Verify Installation

After installation, verify that `kohub-cli` is working correctly:

```bash
kohub-cli --version
```

You should see the version number displayed. You can also check available commands:

```bash
kohub-cli --help
```

## Upgrading

To upgrade to the latest version when installed from Git:

```bash
pip install --upgrade git+https://github.com/KohakuBlueleaf/Kohub-CLI.git
```

For development installations, pull the latest changes:

```bash
cd Kohub-CLI
git pull origin main
```

## Troubleshooting

### Common Issues

**Python version error**: If you see an error about Python version compatibility, make sure you're using Python 3.10 or higher. You might need to use `python3.10` or a similar command depending on your system.

**Git not found**: If you get errors about Git not being available, make sure Git is installed and in your system PATH.

**Permission errors**: On some systems, you might need to use `sudo` with pip commands, or consider using a virtual environment:

```bash
# Create and activate a virtual environment
python -m venv kohub-env
source kohub-env/bin/activate  # On Windows: kohub-env\Scripts\activate

# Install kohub-cli
pip install git+https://github.com/KohakuBlueleaf/Kohub-CLI.git
```

### Getting Help

If you encounter issues during installation:

1. Check the [GitHub Issues](https://github.com/KohakuBlueleaf/Kohub-CLI/issues) for similar problems
2. Create a new issue with details about your system and the error message
3. Join our [GitHub Discussions](https://github.com/KohakuBlueleaf/Kohub-CLI/discussions) for community support

## What's Next?

Once you have `kohub-cli` installed, head over to the [Quick Start guide](quick-start) to learn how to authenticate and start using the CLI.