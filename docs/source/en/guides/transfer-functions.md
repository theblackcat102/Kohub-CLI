<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# Transfer Functions

The `transfer` command is one of `kohub-cli`'s most powerful features, allowing you to seamlessly transfer repositories between different AI model hubs, including HuggingFace Hub, KohakuHub, and other custom hubs.

## Quick Start

Transfer a model from HuggingFace to your current KohakuHub endpoint:

```bash
kohub-cli transfer microsoft/DialoGPT-medium user/DialoGPT-medium
```

## Basic Usage

```bash
kohub-cli transfer <source_repo_id> <dest_repo_id> [OPTIONS]
```

The transfer command automatically detects repository types, handles authentication, and transfers all files including large model weights using Git LFS when appropriate.

## Common Transfer Scenarios

### From HuggingFace to KohakuHub

This is the most common use case - bringing models from the public HuggingFace Hub to your KohakuHub instance:

```bash
# Transfer a popular model
kohub-cli transfer microsoft/DialoGPT-medium user/DialoGPT-medium

# Transfer a dataset
kohub-cli transfer squad user/squad --repo-type dataset

# Transfer with verbose output to see progress
kohub-cli transfer microsoft/DialoGPT-large user/DialoGPT-large --verbose
```

### Between KohakuHub Instances

Transfer repositories between different KohakuHub deployments:

```bash
# Between different KohakuHub instances
kohub-cli transfer user/model user/model \
  --src-endpoint https://hub1.kohaku-lab.org \
  --target-endpoint https://hub2.kohaku-lab.org
```

### Within the Same Hub

Create copies or backups within the same hub instance:

```bash
# Create a backup copy
kohub-cli transfer user/model-v1 user/model-v1-backup

# Create a new version
kohub-cli transfer user/model user/model-v2
```

## Hub Types and Dependencies

### KohakuHub ↔ KohakuHub Transfers

**No external dependencies required** ✅

These transfers use the native KohubClient and work out of the box:

```bash
# Same instance transfer
kohub-cli transfer user/model-v1 user/model-v2

# Between different KohakuHub instances  
kohub-cli transfer user/model user/model \
  --src-endpoint https://hub1.kohaku-lab.org \
  --target-endpoint https://hub2.kohaku-lab.org
```

### HuggingFace Hub Operations

**Requires `huggingface_hub` package** ⚠️

The `huggingface_hub` package is **not** automatically installed with `kohub-cli`. Install it when needed:

```bash
# Install the required dependency
pip install huggingface_hub
```

Once installed, you can transfer from/to HuggingFace Hub:

```bash
# FROM HuggingFace Hub
kohub-cli transfer microsoft/DialoGPT-medium user/DialoGPT-medium

# TO HuggingFace Hub
kohub-cli transfer user/model user/model --target-endpoint hf

# Between HuggingFace accounts
kohub-cli transfer user1/model user2/model \
  --src-endpoint hf --target-endpoint hf \
  --hf-token <your-hf-token>
```

## Authentication and Tokens

### Token Priority

The CLI uses this priority order for authentication:

**Source Hub:**
1. `--src-token` (highest priority)
2. `--hf-token` (if source is HuggingFace Hub)
3. `--token` (fallback)

**Target Hub:**
1. `--target-token` (highest priority)
2. `--hf-token` (if target is HuggingFace Hub)  
3. `--token` (fallback)

### Authentication Examples

```bash
# Use general token for both hubs
kohub-cli transfer user/model user/model --token <your-token>

# Use HuggingFace token for private repositories
kohub-cli transfer private/model user/model --hf-token <hf-token>

# Use different tokens for different hubs
kohub-cli transfer user/model user/model \
  --src-endpoint https://hub1.com --src-token <token1> \
  --target-endpoint https://hub2.com --target-token <token2>
```

## Repository Types and Detection

### Auto-Detection (Default)

The CLI automatically detects if a repository is a model or dataset:

```bash
# Auto-detects repository type
kohub-cli transfer user/unknown-repo user/unknown-repo
```

Detection process:
1. **HuggingFace Hub**: Uses `repo_info()` API
2. **Custom Hubs**: Uses KohubClient `repo_info()` API
3. Tries "model" first, then "dataset"
4. Raises error if neither exists

### Manual Specification

For faster transfers or when auto-detection fails:

```bash
# Specify repository type explicitly
kohub-cli transfer user/dataset user/dataset --repo-type dataset
kohub-cli transfer user/model user/model --repo-type model
```

## File Handling

### Included Files

The transfer includes:
- All repository files and directories
- README, config files, code files
- Model weights and datasets (based on `--include-lfs` setting)

### Excluded Files

These are automatically filtered out:
- Hidden files (`.gitignore`, `.DS_Store`)
- Cache directories (`.cache`, `__pycache__`, `node_modules`)
- Temporary files (`.lock`, `.tmp`, `.temp`)
- Git metadata (`.git/`)

### Large File Storage (LFS)

```bash
# Include all files (default)
kohub-cli transfer user/model user/model --include-lfs

# Skip large binary files to save time/bandwidth
kohub-cli transfer user/model user/model --no-include-lfs
```

LFS extensions that are filtered when using `--no-include-lfs`:
- `.bin`, `.safetensors`, `.gguf`, `.h5`, `.onnx`

## Output and Progress Tracking

### Text Output (Default)

**Normal output:**
```bash
$ kohub-cli transfer user/model user/model
Successfully transferred user/model (127 files)
```

**Verbose output:**
```bash
$ kohub-cli transfer user/model user/model --verbose
🔄 Starting transfer from https://huggingface.co to http://localhost:28080
🔍 Detecting repository type...
✓ Detected as model
📥 Downloading from source...
📝 Creating repository...
📤 Uploading files...
  📄 README.md (2.1 KB)
  📄 config.json (1.2 KB)  
  📄 pytorch_model.bin (440.2 MB)
  ✓ Uploaded README.md
  ✓ Uploaded config.json
  ✓ Uploaded pytorch_model.bin
Successfully transferred user/model (127 files)
```

### JSON Output

Perfect for automation and scripting:

```bash
$ kohub-cli transfer user/model user/model --output json
{
  "source_repo": "user/model",
  "dest_repo": "user/model",
  "repo_type": "model", 
  "files_uploaded": 127,
  "files_skipped": 3,
  "files_failed": 0,
  "source_endpoint": "HuggingFace Hub",
  "target_endpoint": "http://localhost:28080",
  "failed_files": []
}
```

## Advanced Examples

### Private Repository Transfer

```bash
kohub-cli transfer private/model user/model \
  --hf-token <your-hf-token> \
  --private
```

### Cross-Platform with Different Tokens

```bash
kohub-cli transfer user/model user/model \
  --src-endpoint https://hub1.example.com \
  --target-endpoint https://hub2.example.com \
  --src-token <hub1-token> \
  --target-token <hub2-token>
```

### Force Overwrite Existing Repository

```bash
kohub-cli transfer user/model existing/model \
  --force \
  --verbose
```

### Large Model Transfer (Skip LFS Files)

```bash
kohub-cli transfer microsoft/DialoGPT-large user/DialoGPT-large \
  --no-include-lfs \
  --verbose
```

## Error Handling

### Missing Dependencies

```bash
$ kohub-cli transfer microsoft/DialoGPT-medium user/model
Error: huggingface_hub is required for HuggingFace Hub operations

To install huggingface_hub:
  pip install huggingface_hub

Or install with all optional dependencies:
  pip install 'kohub-cli[transfer]'
```

### Repository Not Found

```bash
$ kohub-cli transfer nonexistent/model user/model  
Error: Repository 'nonexistent/model' not found on https://huggingface.co
```

### Already Exists

```bash
$ kohub-cli transfer user/model existing/model
Error: Repository 'existing/model' already exists. Use --force to overwrite.
```

### Authentication Errors

```bash
$ kohub-cli transfer private/model user/model
Authentication Error: Token required for private repository
Hint: Login with 'kohub-cli auth login' or set HF_TOKEN
```

## Best Practices

### 1. Use Verbose Mode for Large Transfers

See detailed progress for large models:

```bash
kohub-cli transfer large/model user/model --verbose
```

### 2. Specify Repository Type for Speed

Avoid auto-detection overhead:

```bash
kohub-cli transfer user/dataset user/dataset --repo-type dataset
```

### 3. Use Specific Tokens for Multi-Hub Operations

Be explicit about authentication:

```bash
kohub-cli transfer user/model user/model \
  --src-endpoint hf --hf-token <hf-token> \
  --target-endpoint https://my-hub.com --target-token <my-token>
```

### 4. Test with JSON Output for Automation

Perfect for scripts and monitoring:

```bash
result=$(kohub-cli transfer user/model user/model --output json)
files_uploaded=$(echo "$result" | jq '.files_uploaded')
echo "Transferred $files_uploaded files"
```

### 5. Use Force Flag Carefully  

Always verify the destination before overwriting:

```bash
# Check what exists first
kohub-cli repo info user/existing-model
kohub-cli transfer user/model user/existing-model --force
```

## Troubleshooting

### Common Issues

**1. Missing HuggingFace Hub Dependency**
```bash
pip install huggingface_hub
```

**2. Authentication Failures**
```bash
export HF_TOKEN=your_token_here
# or
kohub-cli transfer user/model user/model --hf-token <token>
```

**3. Large File Upload Failures**
```bash
# Skip large files if having network issues
kohub-cli transfer user/model user/model --no-include-lfs
```

**4. Network Timeouts**
```bash
# Use verbose mode to monitor progress
kohub-cli transfer user/model user/model --verbose
```

### Debug Information

Use `--verbose` to see:
- Repository detection process
- File discovery and filtering  
- Individual file transfer status
- Error details for failed files

### Getting Help

```bash
# Show transfer command help
kohub-cli transfer --help

# Show all CLI help
kohub-cli --help
```

The transfer function makes it easy to migrate models and datasets between platforms, create backups, and manage content across different hub instances. It's designed to handle the complexity of different APIs and authentication systems while providing a simple, consistent interface.