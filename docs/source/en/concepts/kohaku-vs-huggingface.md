<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# KohakuHub vs Hugging Face Hub

Understanding the similarities and differences between KohakuHub and Hugging Face Hub will help you make the most of `kohub-cli` and decide when to use each platform.

## Core Similarities

Both KohakuHub and Hugging Face Hub share fundamental concepts:

### Git-Based Version Control
Both platforms use Git for version control, meaning:
- Every repository has a complete history of changes
- You can work with branches, tags, and commits
- Large files are handled with Git LFS automatically
- Standard Git workflows apply (clone, push, pull, merge)

### Repository Types
Both platforms support three main repository types:
- **Models**: For storing trained machine learning models
- **Datasets**: For sharing training and evaluation data
- **Spaces**: For hosting interactive demos and applications

### Organization Structure
- Users can create personal repositories under their username
- Organizations allow team collaboration
- Repositories are identified by the format `username/repo-name` or `org/repo-name`

## Key Differences

### Platform Focus

**Hugging Face Hub**:
- Primarily focused on transformer models and NLP
- Extensive integration with the Transformers library
- Large, established community
- Many pre-trained models available
- Strong ecosystem of tools and integrations

**KohakuHub**:
- Broader focus beyond just transformers
- More flexible for various ML frameworks
- Newer platform with growing community
- Emphasis on customization and self-hosting
- Designed for both public and private deployments

### API Compatibility

`kohub-cli` is designed to be largely compatible with the Hugging Face Hub API, which means:

```bash
# These commands work similarly on both platforms
kohub-cli repo create username/my-model --type model
kohub-cli settings repo upload username/my-model ./model.bin --path model.bin
kohub-cli settings repo download username/my-model config.json
```

However, KohakuHub may have additional features or slight variations in behavior.

### Authentication

**Hugging Face Hub**:
- Uses Hugging Face account tokens
- Single sign-on with Hugging Face services

**KohakuHub**:
- Can use separate KohakuHub tokens
- Supports custom authentication systems
- Can be configured for enterprise SSO

### Self-Hosting

**Hugging Face Hub**:
- Primarily cloud-based (huggingface.co)
- Enterprise versions available

**KohakuHub**:
- Designed for easy self-hosting
- Can be deployed on private infrastructure
- Customizable for organizational needs

## When to Use Which Platform

### Use Hugging Face Hub When:

- Working primarily with transformer models
- Need access to the largest model repository
- Want maximum community visibility
- Using Hugging Face's other services (Spaces, Inference API)
- Following established NLP workflows

### Use KohakuHub When:

- Need a self-hosted solution
- Working with diverse ML frameworks
- Require custom authentication or access controls
- Want more control over your infrastructure
- Building internal or enterprise ML workflows

## Migration and Transfer

One of `kohub-cli`'s unique features is seamless transfer between platforms:

```bash
# Transfer from Hugging Face to KohakuHub
kohub-cli transfer huggingface-to-kohaku username/my-model

# Transfer specific versions
kohub-cli transfer huggingface-to-kohaku username/my-model --revision v1.0
```

This makes it easy to:
- Start on one platform and move to another
- Keep mirrors of important repositories
- Experiment with different hosting options

## Configuration for Multiple Platforms

You can configure `kohub-cli` to work with both platforms:

```bash
# Configure for Hugging Face
export HF_ENDPOINT=https://huggingface.co
export HF_TOKEN=hf_your_token_here

# Configure for KohakuHub
export HF_ENDPOINT=https://kohaku.blue
export HF_TOKEN=kh_your_token_here
```

Or use profiles to switch between them easily:

```bash
# Set up different configurations
kohub-cli config set endpoint https://huggingface.co --profile hf
kohub-cli config set endpoint https://kohaku.blue --profile kohaku

# Use specific profile
kohub-cli --profile kohaku repo list
```

## API Differences

While `kohub-cli` aims for compatibility, there are some differences in advanced features:

### KohakuHub-Specific Features:
- Enhanced organization management
- Custom metadata fields
- Advanced access controls
- Self-hosting capabilities

### Hugging Face-Specific Features:
- Model cards with special formatting
- Integration with Hugging Face services
- Automatic model evaluation
- Community features (discussions, etc.)

## Best Practices for Multi-Platform Use

1. **Consistent Naming**: Use the same repository names across platforms when possible
2. **Documentation**: Keep README and documentation platform-agnostic
3. **Automation**: Use `kohub-cli`'s JSON output for scripts that work with both platforms
4. **Testing**: Test your models and datasets on both platforms if you plan to use both

## Community and Support

Both platforms have active communities, but with different focuses:

- **Hugging Face**: Large community focused on sharing and collaboration
- **KohakuHub**: Growing community with emphasis on customization and enterprise use

Understanding these differences helps you choose the right platform for your needs and make the most of `kohub-cli`'s cross-platform capabilities.