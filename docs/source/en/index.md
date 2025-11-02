<!--⚠️ Note that this file is in Markdown but contains specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.
-->

# 🌸 KohakuHub CLI

The `kohub-cli` is the official command-line interface for [KohakuHub](https://kohaku.blue/), a Git-based platform for hosting and sharing machine learning models, datasets, and spaces. With `kohub-cli`, you can interact with KohakuHub directly from your development environment, making it easy to create and manage repositories, upload and download files, and collaborate with the community.

Read the [quick start guide](quick-start) to get up and running with `kohub-cli`. You will learn how to authenticate, create repositories, and manage your files. Keep reading to learn more about advanced features like organization management, transfer functions, and interactive mode.

<div class="mt-10">
  <div class="w-full flex flex-col space-y-4 md:space-y-0 md:grid md:grid-cols-2 md:gap-y-4 md:gap-x-5">

    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./guides/overview">
      <div class="w-full text-center bg-gradient-to-br from-indigo-400 to-indigo-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">How-to guides</div>
      <p class="text-gray-700">Practical guides to help you achieve specific goals. Learn how to use kohub-cli for authentication, repository management, file operations, and more.</p>
    </a>

    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./package_reference/overview">
      <div class="w-full text-center bg-gradient-to-br from-purple-400 to-purple-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Reference</div>
      <p class="text-gray-700">Complete technical documentation of kohub-cli commands, APIs, and configuration options.</p>
    </a>

    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./concepts/kohaku-vs-huggingface">
      <div class="w-full text-center bg-gradient-to-br from-pink-400 to-pink-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Conceptual guides</div>
      <p class="text-gray-700">High-level explanations for building a better understanding of KohakuHub and how it differs from other platforms.</p>
    </a>

  </div>
</div>

## Key Features

- **🔐 Authentication & User Management**: Login, manage API tokens, and user profiles
- **📦 Repository Management**: Create, delete, and manage models, datasets, and spaces
- **📁 File Operations**: Upload/download files with automatic LFS support for large files
- **👥 Organization Management**: Create and manage organizations and team members
- **🔄 Version Control**: Browse commits, view diffs, and manage branches/tags
- **🔑 External Token Management**: Manage tokens for external services like Hugging Face
- **🖥️ Interactive TUI**: Menu-driven interface for easy navigation
- **🔧 JSON Output**: Programmatic access for automation and scripting
- **↔️ Transfer Functions**: Transfer content between different hub platforms

## Contribute

All contributions to `kohub-cli` are welcomed and equally valued! 🌸 Besides adding or fixing existing issues in the code, you can also help improve the documentation by making sure it is accurate and up-to-date, help answer questions on issues, and request new features you think will improve the CLI. Take a look at the [contribution guide](https://github.com/KohakuBlueleaf/Kohub-CLI/blob/main/CONTRIBUTING.md) to learn more about how to submit a new issue or feature request, how to submit a pull request, and how to test your contributions to make sure everything works as expected.

Contributors should also be respectful of our [code of conduct](https://github.com/KohakuBlueleaf/Kohub-CLI/blob/main/CODE_OF_CONDUCT.md) to create an inclusive and welcoming collaborative space for everyone.