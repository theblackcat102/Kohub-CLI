"""Click-based CLI commands for KohakuHub."""

import json
import sys
import click
from rich.console import Console
from rich.table import Table

from .client import KohubClient
from .config import Config
from .constants import STYLE_HIGHLIGHT
from .errors import (
    KohubError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    AlreadyExistsError,
    NetworkError
)

console = Console()


# Global options
@click.group()
@click.option("--endpoint", envvar="HF_ENDPOINT", help="KohakuHub endpoint URL")
@click.option("--token", envvar="HF_TOKEN", help="API token")
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def cli(ctx, endpoint, token, output):
    """KohakuHub CLI - Manage repositories, organizations, and users.

    Examples:

    \b
    # Login to KohakuHub
    kohub-cli auth login

    \b
    # Create a repository
    kohub-cli repo create my-org/my-model --type model

    \b
    # List repositories
    kohub-cli repo list --type model --author my-org

    \b
    # Launch interactive mode
    kohub-cli interactive

    For more help on a specific command, use:
    kohub-cli COMMAND --help
    """
    ctx.ensure_object(dict)
    config = Config()

    # Create client with provided options
    client = KohubClient(endpoint=endpoint, token=token, config=config)

    ctx.obj["client"] = client
    ctx.obj["output"] = output
    ctx.obj["console"] = console


def output_result(ctx, data, success_message=None):
    """Output result based on format preference."""
    output_format = ctx.obj.get("output", "text")

    if output_format == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        if success_message:
            console.print(success_message, style="bold green")
        elif isinstance(data, dict):
            for key, value in data.items():
                console.print(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                console.print(item)


def handle_error(e: Exception, ctx):
    """Handle CLI errors with appropriate output."""
    output_format = ctx.obj.get("output", "text")

    if output_format == "json":
        error_data = {
            "error": str(e),
            "type": type(e).__name__,
        }
        if isinstance(e, KohubError):
            error_data["status_code"] = e.status_code
        click.echo(json.dumps(error_data, indent=2))
    else:
        if isinstance(e, AuthenticationError):
            console.print(
                f"[bold red]Authentication Error:[/bold red] {e}",
            )
            console.print(
                "[yellow]Hint:[/yellow] Login with 'kohub-cli auth login' or set HF_TOKEN"
            )
        elif isinstance(e, AuthorizationError):
            console.print(f"[bold red]Permission Denied:[/bold red] {e}")
        elif isinstance(e, NotFoundError):
            console.print(f"[bold red]Not Found:[/bold red] {e}")
        elif isinstance(e, AlreadyExistsError):
            console.print(f"[bold red]Already Exists:[/bold red] {e}")
        else:
            console.print(f"[bold red]Error:[/bold red] {e}")

    sys.exit(1)


# ========== Auth Commands ==========


@cli.group()
def auth():
    """Authentication and user management."""
    pass


@auth.command()
@click.option("--username", prompt=True, help="Username")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.pass_context
def login(ctx, username, password):
    """Login to KohakuHub."""
    client = ctx.obj["client"]
    try:
        result = client.login(username, password)
        output_result(ctx, result, f"Logged in as {username}")
    except Exception as e:
        handle_error(e, ctx)


@auth.command()
@click.pass_context
def logout(ctx):
    """Logout from KohakuHub."""
    client = ctx.obj["client"]
    try:
        result = client.logout()
        output_result(ctx, result, "Logged out successfully")
    except Exception as e:
        handle_error(e, ctx)


@auth.command()
@click.pass_context
def whoami(ctx):
    """Show current user information."""
    client = ctx.obj["client"]
    try:
        user_info = client.whoami()
        if ctx.obj["output"] == "json":
            output_result(ctx, user_info)
        else:
            console.print(f"[bold]Username:[/bold] {user_info.get('username')}")
            console.print(f"[bold]Email:[/bold] {user_info.get('email')}")
            console.print(
                f"[bold]Email Verified:[/bold] {user_info.get('email_verified')}"
            )
            console.print(f"[bold]User ID:[/bold] {user_info.get('id')}")
    except Exception as e:
        handle_error(e, ctx)


@auth.group()
def token():
    """Manage API tokens."""
    pass


@token.command("create")
@click.option("--name", "-n", prompt=True, help="Token name")
@click.pass_context
def token_create(ctx, name):
    """Create a new API token."""
    client = ctx.obj["client"]
    try:
        result = client.create_token(name)
        token_value = result.get("token")

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            console.print(f"[bold green]Token created successfully![/bold green]")
            console.print(f"\n[bold]Token:[/bold] {token_value}")
            console.print(f"[bold]Name:[/bold] {name}")
            console.print(
                "\n[yellow]Save this token securely - you won't see it again![/yellow]"
            )
            console.print(
                "\n[bold]To use this token:[/bold]\nexport HF_TOKEN=" + token_value
            )
    except Exception as e:
        handle_error(e, ctx)


@token.command("list")
@click.pass_context
def token_list(ctx):
    """List all API tokens."""
    client = ctx.obj["client"]
    try:
        tokens = client.list_tokens()

        if ctx.obj["output"] == "json":
            output_result(ctx, tokens)
        else:
            if not tokens:
                console.print("[yellow]No tokens found[/yellow]")
                return

            table = Table(title="API Tokens")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Created", style="blue")
            table.add_column("Last Used", style="magenta")

            for t in tokens:
                table.add_row(
                    str(t.get("id")),
                    t.get("name", ""),
                    t.get("created_at", ""),
                    t.get("last_used", "Never"),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@token.command("delete")
@click.option("--id", "token_id", type=int, required=True, help="Token ID to delete")
@click.confirmation_option(prompt="Are you sure you want to delete this token?")
@click.pass_context
def token_delete(ctx, token_id):
    """Delete an API token."""
    client = ctx.obj["client"]
    try:
        result = client.revoke_token(token_id)
        output_result(ctx, result, f"Token {token_id} deleted successfully")
    except Exception as e:
        handle_error(e, ctx)


# ========== Repository Commands ==========


@cli.group()
def repo():
    """Repository management."""
    pass


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--private", is_flag=True, help="Make repository private")
@click.pass_context
def create(ctx, repo_id, repo_type, private):
    """Create a new repository.

    REPO_ID format: namespace/name or just name (uses your username)
    """
    client = ctx.obj["client"]
    try:
        result = client.create_repo(repo_id, repo_type=repo_type, private=private)
        output_result(ctx, result, f"Repository {repo_id} created successfully")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(
    prompt="Are you sure you want to delete this repository? This is irreversible!"
)
@click.pass_context
def delete(ctx, repo_id, repo_type):
    """Delete a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_repo(repo_id, repo_type=repo_type)
        output_result(ctx, result, f"Repository {repo_id} deleted successfully")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Specific revision/branch")
@click.pass_context
def info(ctx, repo_id, repo_type, revision):
    """Show repository information.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.repo_info(repo_id, repo_type=repo_type, revision=revision)
        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            from rich.panel import Panel
            from rich.text import Text

            # Build info display
            info_text = Text()

            # Repository header
            info_text.append(f"{result.get('id')}\n", style=STYLE_HIGHLIGHT)
            info_text.append("─" * 60 + "\n", style="dim")

            # Basic info
            info_text.append("Author:        ", style="bold")
            info_text.append(f"{result.get('author')}\n")

            info_text.append("Type:          ", style="bold")
            info_text.append(f"{repo_type}\n")

            info_text.append("Visibility:    ", style="bold")
            visibility = "🔒 Private" if result.get("private") else "🌐 Public"
            info_text.append(f"{visibility}\n")

            info_text.append("Created:       ", style="bold")
            info_text.append(f"{result.get('createdAt', 'N/A')}\n")

            if result.get("lastModified"):
                info_text.append("Last Modified: ", style="bold")
                info_text.append(f"{result.get('lastModified')}\n")

            # Revision info
            if result.get("sha"):
                info_text.append("\n")
                info_text.append("Commit SHA:    ", style="bold")
                info_text.append(f"{result.get('sha')}\n", style="yellow")

            # Stats
            info_text.append("\n")
            info_text.append("Downloads:     ", style="bold")
            info_text.append(f"{result.get('downloads', 0)}\n")

            info_text.append("Likes:         ", style="bold")
            info_text.append(f"{result.get('likes', 0)}\n")

            # Tags
            if result.get("tags"):
                info_text.append("\nTags:          ", style="bold")
                info_text.append(f"{', '.join(result.get('tags'))}\n")

            panel = Panel(
                info_text,
                title=f"[bold]{repo_type.capitalize()} Repository[/bold]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("list")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--author", help="Filter by author/namespace")
@click.option("--limit", default=50, help="Maximum number of results")
@click.pass_context
def list_repos(ctx, repo_type, author, limit):
    """List repositories."""
    client = ctx.obj["client"]
    try:
        repos = client.list_repos(repo_type=repo_type, author=author, limit=limit)

        if ctx.obj["output"] == "json":
            output_result(ctx, repos)
        else:
            if not repos:
                console.print("[yellow]No repositories found[/yellow]")
                return

            table = Table(title=f"{repo_type.capitalize()}s")
            table.add_column("Repository", style="cyan")
            table.add_column("Author", style="green")
            table.add_column("Private", style="yellow")
            table.add_column("Created", style="blue")

            for r in repos:
                table.add_row(
                    r.get("id", ""),
                    r.get("author", ""),
                    "Yes" if r.get("private") else "No",
                    r.get("createdAt", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("ls")
@click.argument("namespace")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    help="Filter by repository type",
)
@click.pass_context
def list_namespace_repos(ctx, namespace, repo_type):
    """List all repositories under a namespace.

    NAMESPACE can be a username or organization name.

    Examples:
    \b
        kohub-cli repo ls my-org
        kohub-cli repo ls my-org --type model
    """
    client = ctx.obj["client"]
    try:
        repos = client.list_namespace_repos(namespace, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, repos)
        else:
            if not repos:
                console.print(f"[yellow]No repositories found for {namespace}[/yellow]")
                return

            from rich.tree import Tree

            # Create tree root
            tree_root = Tree(
                f"[bold cyan]{namespace}[/bold cyan]'s repositories", guide_style="blue"
            )

            # Group by type if showing all types
            if repo_type is None:
                # Group repos by type
                by_type = {"model": [], "dataset": [], "space": []}
                for repo in repos:
                    rtype = repo.get("repo_type", "model")
                    by_type[rtype].append(repo)

                # Add to tree
                for rtype in ["model", "dataset", "space"]:
                    if by_type[rtype]:
                        type_node = tree_root.add(
                            f"[bold]{rtype.capitalize()}s[/bold] ({len(by_type[rtype])})"
                        )
                        for r in sorted(by_type[rtype], key=lambda x: x.get("id", "")):
                            visibility = "🔒" if r.get("private") else "🌐"
                            type_node.add(
                                f"{visibility} [cyan]{r.get('id')}[/cyan] [dim]({r.get('createdAt', 'N/A')})[/dim]"
                            )
            else:
                # Single type, flat list
                for r in sorted(repos, key=lambda x: x.get("id", "")):
                    visibility = "🔒" if r.get("private") else "🌐"
                    tree_root.add(
                        f"{visibility} [cyan]{r.get('id')}[/cyan] [dim]({r.get('createdAt', 'N/A')})[/dim]"
                    )

            console.print(tree_root)
            console.print(f"\n[dim]Total: {len(repos)} repositories[/dim]")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default="main", help="Branch or commit hash")
@click.option("--path", default="", help="Path within repository")
@click.option("--recursive", is_flag=True, help="List files recursively")
@click.pass_context
def files(ctx, repo_id, repo_type, revision, path, recursive):
    """List files in a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.list_repo_tree(
            repo_id,
            repo_type=repo_type,
            revision=revision,
            path=path,
            recursive=recursive,
        )

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            if not result:
                console.print("[yellow]No files found[/yellow]")
                return

            # Build tree structure
            from rich.tree import Tree

            def format_size(size_bytes):
                """Format file size in human-readable format (decimal: 1KB = 1000 bytes)."""
                if size_bytes < 1000:
                    return f"{size_bytes} B"
                elif size_bytes < 1000 * 1000:
                    return f"{size_bytes / 1000:.1f} KB"
                elif size_bytes < 1000 * 1000 * 1000:
                    return f"{size_bytes / (1000 * 1000):.1f} MB"
                else:
                    return f"{size_bytes / (1000 * 1000 * 1000):.1f} GB"

            # Create tree structure
            tree_root = Tree(
                f"[bold cyan]{repo_id}[/bold cyan] [dim]({revision})[/dim]",
                guide_style="blue",
            )

            # Build hierarchical structure
            if recursive:
                # Build tree from flat list
                tree_nodes = {".": tree_root}

                # Sort by path for better tree building
                sorted_items = sorted(result, key=lambda x: x.get("path", ""))

                for item in sorted_items:
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    item_size = item.get("size", 0)

                    # Split path into parts
                    parts = item_path.split("/")
                    parent_path = "/".join(parts[:-1]) if len(parts) > 1 else "."
                    name = parts[-1]

                    # Ensure parent exists
                    if parent_path not in tree_nodes:
                        # Create missing parent directories
                        parent_parts = parent_path.split("/")
                        for i in range(len(parent_parts)):
                            sub_path = "/".join(parent_parts[: i + 1])
                            if sub_path not in tree_nodes:
                                sub_parent = (
                                    "/".join(parent_parts[:i]) if i > 0 else "."
                                )
                                tree_nodes[sub_path] = tree_nodes[sub_parent].add(
                                    f"[bold blue]📁 {parent_parts[i]}[/bold blue]"
                                )

                    # Add item to tree
                    parent_node = tree_nodes.get(parent_path, tree_root)

                    if item_type == "directory":
                        tree_nodes[item_path] = parent_node.add(
                            f"[bold blue]📁 {name}[/bold blue]"
                        )
                    else:
                        # File with size and LFS indicator
                        size_str = format_size(item_size)
                        lfs_indicator = (
                            " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
                        )
                        parent_node.add(
                            f"[green]📄 {name}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
                        )
            else:
                # Simple flat list
                for item in sorted(
                    result,
                    key=lambda x: (x.get("type") != "directory", x.get("path", "")),
                ):
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    item_size = item.get("size", 0)

                    if item_type == "directory":
                        tree_root.add(f"[bold blue]📁 {item_path}[/bold blue]")
                    else:
                        size_str = format_size(item_size)
                        lfs_indicator = (
                            " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
                        )
                        tree_root.add(
                            f"[green]📄 {item_path}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
                        )

            console.print(tree_root)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("commits")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--branch", default="main", help="Branch name")
@click.option("--limit", default=20, help="Maximum number of commits")
@click.pass_context
def list_repo_commits_main(ctx, repo_id, repo_type, branch, limit):
    """List commit history for a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.list_commits(
            repo_id, branch=branch, repo_type=repo_type, limit=limit
        )

        commits = result.get("commits", [])

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            if not commits:
                console.print("[yellow]No commits found[/yellow]")
                return

            table = Table(title=f"Commits for {repo_id} ({branch})")
            table.add_column("SHA", style="yellow", no_wrap=True)
            table.add_column("Message", style="cyan")
            table.add_column("Author", style="green")
            table.add_column("Date", style="blue")

            for c in commits:
                sha_short = c.get("oid", "")[:8]
                message = c.get("title", c.get("message", ""))
                # Truncate long messages
                if len(message) > 60:
                    message = message[:57] + "..."
                author = c.get("author", "unknown")
                date = c.get("date", "")

                table.add_row(sha_short, message, author, date)

            console.print(table)

            if result.get("hasMore"):
                console.print(
                    f"\n[dim]Showing {len(commits)} commits. Use --limit to see more.[/dim]"
                )
            else:
                console.print(f"\n[dim]Total: {len(commits)} commits[/dim]")
    except Exception as e:
        handle_error(e, ctx)


@repo.command("commit")
@click.argument("repo_id")
@click.argument("commit_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.pass_context
def get_commit_info_main(ctx, repo_id, commit_id, repo_type):
    """Show detailed information about a specific commit.

    REPO_ID format: namespace/name
    COMMIT_ID: Full or short commit SHA
    """
    client = ctx.obj["client"]
    try:
        commit = client.get_commit_detail(repo_id, commit_id, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, commit)
        else:
            from rich.panel import Panel
            from rich.text import Text

            info_text = Text()

            # Commit header
            info_text.append(
                f"Commit {commit.get('oid', commit_id)}\n", style="bold yellow"
            )
            info_text.append("─" * 60 + "\n", style="dim")

            # Commit info
            info_text.append("Author:  ", style="bold")
            info_text.append(f"{commit.get('author', 'unknown')}\n")

            info_text.append("Date:    ", style="bold")
            info_text.append(f"{commit.get('date', 'N/A')}\n")

            if commit.get("parents"):
                info_text.append("Parents: ", style="bold")
                parents_str = ", ".join([p[:8] for p in commit["parents"]])
                info_text.append(f"{parents_str}\n")

            # Message
            info_text.append("\n", style="bold")
            info_text.append(commit.get("message", "No message") + "\n")

            # Description if available
            if commit.get("description"):
                info_text.append("\n")
                info_text.append(commit["description"] + "\n", style="dim")

            # Metadata
            if commit.get("metadata"):
                info_text.append("\n")
                info_text.append("Metadata:\n", style="bold")
                for key, value in commit["metadata"].items():
                    info_text.append(f"  {key}: {value}\n", style="dim")

            panel = Panel(
                info_text,
                title=f"[bold]Commit Details[/bold]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("commit-diff")
@click.argument("repo_id")
@click.argument("commit_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--show-diff", is_flag=True, help="Show actual diff content")
@click.pass_context
def get_commit_diff_cmd_main(ctx, repo_id, commit_id, repo_type, show_diff):
    """Show files changed in a commit.

    REPO_ID format: namespace/name
    COMMIT_ID: Full or short commit SHA
    """
    client = ctx.obj["client"]
    try:
        diff_result = client.get_commit_diff(repo_id, commit_id, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, diff_result)
        else:
            # Header
            console.print(
                f"\n[bold]Commit:[/bold] {diff_result.get('commit_id', commit_id)}"
            )
            console.print(
                f"[bold]Author:[/bold] {diff_result.get('author', 'unknown')}"
            )
            console.print(f"[bold]Date:[/bold] {diff_result.get('date', 'N/A')}")
            console.print(f"[bold]Message:[/bold] {diff_result.get('message', '')}\n")

            files = diff_result.get("files", [])
            if not files:
                console.print("[yellow]No files changed[/yellow]")
                return

            # Summary table
            table = Table(title="Files Changed")
            table.add_column("Type", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Size", style="yellow")
            table.add_column("LFS", style="magenta")

            for file_info in files:
                change_type = file_info.get("type", "unknown")
                path = file_info.get("path", "")
                size = file_info.get("size_bytes", 0)
                is_lfs = file_info.get("is_lfs", False)

                # Format size (decimal: 1KB = 1000 bytes)
                if size < 1000:
                    size_str = f"{size} B"
                elif size < 1000 * 1000:
                    size_str = f"{size / 1000:.1f} KB"
                else:
                    size_str = f"{size / (1000 * 1000):.1f} MB"

                # Change type icon
                type_icon = {
                    "added": "+ ",
                    "removed": "- ",
                    "changed": "M ",
                }.get(change_type, "  ")

                table.add_row(
                    type_icon + change_type,
                    path,
                    size_str,
                    "Yes" if is_lfs else "No",
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(files)} file(s) changed[/dim]")

            # Show diffs if requested
            if show_diff:
                console.print("\n[bold]Diffs:[/bold]\n")
                for file_info in files:
                    if file_info.get("diff"):
                        console.print(f"[cyan]File:[/cyan] {file_info['path']}")
                        console.print(file_info["diff"])
                        console.print()
    except Exception as e:
        handle_error(e, ctx)


# ========== Organization Commands ==========


@cli.group()
def org():
    """Organization management."""
    pass


@org.command()
@click.argument("org_name")
@click.option("--description", help="Organization description")
@click.pass_context
def create(ctx, org_name, description):
    """Create a new organization."""
    client = ctx.obj["client"]
    try:
        result = client.create_organization(org_name, description=description)
        output_result(ctx, result, f"Organization {org_name} created successfully")
    except Exception as e:
        handle_error(e, ctx)


@org.command()
@click.argument("org_name")
@click.pass_context
def info(ctx, org_name):
    """Show organization information."""
    client = ctx.obj["client"]
    try:
        result = client.get_organization(org_name)
        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            console.print(f"[bold]Name:[/bold] {result.get('name')}")
            console.print(
                f"[bold]Description:[/bold] {result.get('description', 'N/A')}"
            )
            console.print(f"[bold]Created:[/bold] {result.get('created_at')}")
    except Exception as e:
        handle_error(e, ctx)


@org.command("list")
@click.option("--username", help="Username (defaults to current user)")
@click.pass_context
def list_orgs(ctx, username):
    """List user's organizations."""
    client = ctx.obj["client"]
    try:
        orgs = client.list_user_organizations(username=username)

        if ctx.obj["output"] == "json":
            output_result(ctx, orgs)
        else:
            if not orgs:
                console.print("[yellow]No organizations found[/yellow]")
                return

            table = Table(title="Organizations")
            table.add_column("Name", style="cyan")
            table.add_column("Role", style="green")
            table.add_column("Description", style="blue")

            for o in orgs:
                table.add_row(
                    o.get("name", ""),
                    o.get("role", ""),
                    o.get("description", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@org.group()
def member():
    """Manage organization members."""
    pass


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.option(
    "--role",
    type=click.Choice(["member", "admin", "super-admin"]),
    default="member",
    help="Member role",
)
@click.pass_context
def add(ctx, org_name, username, role):
    """Add a member to an organization."""
    client = ctx.obj["client"]
    try:
        result = client.add_organization_member(org_name, username, role=role)
        output_result(ctx, result, f"Added {username} to {org_name} as {role}")
    except Exception as e:
        handle_error(e, ctx)


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.confirmation_option(prompt="Are you sure you want to remove this member?")
@click.pass_context
def remove(ctx, org_name, username):
    """Remove a member from an organization."""
    client = ctx.obj["client"]
    try:
        result = client.remove_organization_member(org_name, username)
        output_result(ctx, result, f"Removed {username} from {org_name}")
    except Exception as e:
        handle_error(e, ctx)


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.option(
    "--role",
    type=click.Choice(["member", "admin", "super-admin"]),
    required=True,
    help="New role",
)
@click.pass_context
def update(ctx, org_name, username, role):
    """Update a member's role."""
    client = ctx.obj["client"]
    try:
        result = client.update_organization_member(org_name, username, role=role)
        output_result(ctx, result, f"Updated {username}'s role in {org_name} to {role}")
    except Exception as e:
        handle_error(e, ctx)


# ========== Settings Commands ==========


@cli.group()
def settings():
    """Settings management for users, repos, and organizations."""
    pass


@settings.group()
def user():
    """User settings management."""
    pass


@user.command("update")
@click.option("--email", help="New email address")
@click.pass_context
def update_user(ctx, email):
    """Update user settings."""
    client = ctx.obj["client"]
    try:
        user_info = client.whoami()
        username = user_info["username"]

        result = client.update_user_settings(username=username, email=email)
        output_result(ctx, result, "User settings updated successfully")
    except Exception as e:
        handle_error(e, ctx)


@user.group(name="external-tokens")
def external_tokens():
    """Manage external fallback source tokens."""
    pass


@external_tokens.command("sources")
@click.pass_context
def list_sources(ctx):
    """List available fallback sources."""
    client = ctx.obj["client"]
    try:
        sources = client.list_available_sources()
        if ctx.obj.get("json"):
            output_result(ctx, sources)
        else:
            console = ctx.obj["console"]
            if not sources:
                console.print("[yellow]No fallback sources configured[/yellow]")
                return

            console.print(
                f"\n[bold]Available Fallback Sources ({len(sources)}):[/bold]\n"
            )
            for source in sources:
                console.print(f"  • [cyan]{source['name']}[/cyan]")
                console.print(f"    URL: {source['url']}")
                console.print(f"    Type: {source['source_type']}")
                console.print()
    except Exception as e:
        handle_error(e, ctx)


@external_tokens.command("list")
@click.argument("username", required=False)
@click.pass_context
def list_external_tokens_cmd(ctx, username):
    """List user's external tokens (tokens are masked).

    USERNAME: User to list tokens for (default: current user)
    """
    client = ctx.obj["client"]
    try:
        if not username:
            user_info = client.whoami()
            username = user_info["username"]

        tokens = client.list_external_tokens(username)
        if ctx.obj.get("json"):
            output_result(ctx, tokens)
        else:
            console = ctx.obj["console"]
            if not tokens:
                console.print(
                    f"[yellow]No external tokens configured for {username}[/yellow]"
                )
                return

            console.print(
                f"\n[bold]External Tokens for {username} ({len(tokens)}):[/bold]\n"
            )
            for token in tokens:
                console.print(f"  • [cyan]{token['url']}[/cyan]")
                console.print(f"    Token: {token['token_preview']}")
                console.print(f"    Created: {token['created_at']}")
                console.print()
    except Exception as e:
        handle_error(e, ctx)


@external_tokens.command("add")
@click.argument("username", required=False)
@click.option("--url", required=True, help="Source URL (e.g., https://huggingface.co)")
@click.option("--token", required=True, help="Token for this source")
@click.pass_context
def add_external_token_cmd(ctx, username, url, token):
    """Add or update external token for a source.

    USERNAME: User to add token for (default: current user)
    """
    client = ctx.obj["client"]
    try:
        if not username:
            user_info = client.whoami()
            username = user_info["username"]

        result = client.add_external_token(username, url, token)
        output_result(ctx, result, f"External token added for {url}")
    except Exception as e:
        handle_error(e, ctx)


@external_tokens.command("delete")
@click.argument("username", required=False)
@click.option("--url", required=True, help="Source URL")
@click.pass_context
def delete_external_token_cmd(ctx, username, url):
    """Delete external token for a source.

    USERNAME: User to delete token for (default: current user)
    """
    client = ctx.obj["client"]
    try:
        if not username:
            user_info = client.whoami()
            username = user_info["username"]

        result = client.delete_external_token(username, url)
        output_result(ctx, result, f"External token deleted for {url}")
    except Exception as e:
        handle_error(e, ctx)


@settings.group(name="repo")
def repo_settings():
    """Repository settings management."""
    pass


@repo_settings.command("update")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--private/--public", default=None, help="Set repository visibility")
@click.option(
    "--gated",
    type=click.Choice(["auto", "manual", "none"]),
    help="Set gating mode",
)
@click.pass_context
def update_repo(ctx, repo_id, repo_type, private, gated):
    """Update repository settings.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        gated_value = None if gated == "none" else gated

        result = client.update_repo_settings(
            repo_id,
            repo_type=repo_type,
            private=private,
            gated=gated_value,
        )
        output_result(ctx, result, f"Repository {repo_id} settings updated")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.command("move")
@click.argument("from_repo")
@click.argument("to_repo")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.pass_context
def move_repo(ctx, from_repo, to_repo, repo_type):
    """Move/rename a repository.

    FROM_REPO format: namespace/name
    TO_REPO format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.move_repo(
            from_repo=from_repo,
            to_repo=to_repo,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Repository moved from {from_repo} to {to_repo}")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.command("squash")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(
    prompt="This will clear all commit history. Are you sure you want to squash this repository?"
)
@click.pass_context
def squash_repo_cmd(ctx, repo_id, repo_type):
    """Squash repository to clear all commit history.

    This operation removes all commit history while preserving the current
    state of the repository. This can help reduce storage usage.

    REPO_ID format: namespace/name

    WARNING: This operation is irreversible!
    """
    client = ctx.obj["client"]
    try:
        console.print(
            "[yellow]Squashing repository (this may take a while)...[/yellow]"
        )
        result = client.squash_repo(repo_id, repo_type=repo_type)
        output_result(ctx, result, f"Repository {repo_id} squashed successfully")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.group()
def branch():
    """Branch management."""
    pass


@branch.command("create")
@click.argument("repo_id")
@click.argument("branch")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Source revision (defaults to main)")
@click.pass_context
def create_branch(ctx, repo_id, branch, repo_type, revision):
    """Create a new branch.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.create_branch(
            repo_id,
            branch=branch,
            repo_type=repo_type,
            revision=revision,
        )
        output_result(ctx, result, f"Branch '{branch}' created in {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@branch.command("delete")
@click.argument("repo_id")
@click.argument("branch")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(prompt="Are you sure you want to delete this branch?")
@click.pass_context
def delete_branch(ctx, repo_id, branch, repo_type):
    """Delete a branch.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_branch(
            repo_id,
            branch=branch,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Branch '{branch}' deleted from {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.group()
def tag():
    """Tag management."""
    pass


@tag.command("create")
@click.argument("repo_id")
@click.argument("tag")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Source revision (defaults to main)")
@click.option("--message", "-m", help="Tag message")
@click.pass_context
def create_tag(ctx, repo_id, tag, repo_type, revision, message):
    """Create a new tag.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.create_tag(
            repo_id,
            tag=tag,
            repo_type=repo_type,
            revision=revision,
            message=message,
        )
        output_result(ctx, result, f"Tag '{tag}' created in {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@tag.command("delete")
@click.argument("repo_id")
@click.argument("tag")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(prompt="Are you sure you want to delete this tag?")
@click.pass_context
def delete_tag(ctx, repo_id, tag, repo_type):
    """Delete a tag.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_tag(
            repo_id,
            tag=tag,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Tag '{tag}' deleted from {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.group()
def lfs():
    """LFS settings management."""
    pass


@lfs.command("get")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.pass_context
def get_lfs_settings(ctx, repo_id, repo_type):
    """Get repository LFS settings.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        settings = client.get_repo_lfs_settings(repo_id, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, settings)
        else:
            from rich.panel import Panel
            from rich.text import Text

            info_text = Text()

            # Threshold
            info_text.append("LFS Threshold:\n", style="bold cyan")
            info_text.append(f"  Configured:  ")
            if settings["lfs_threshold_bytes"] is None:
                info_text.append("Using server default\n", style="dim")
            else:
                threshold_mb = settings["lfs_threshold_bytes"] / (1000 * 1000)
                info_text.append(f"{threshold_mb:.1f} MB\n", style="yellow")

            threshold_effective_mb = settings["lfs_threshold_bytes_effective"] / (
                1000 * 1000
            )
            info_text.append(
                f"  Effective:   {threshold_effective_mb:.1f} MB ", style="green"
            )
            info_text.append(
                f"({settings['lfs_threshold_bytes_source']})\n", style="dim"
            )

            # Keep Versions
            info_text.append("\nLFS Keep Versions:\n", style="bold cyan")
            info_text.append(f"  Configured:  ")
            if settings["lfs_keep_versions"] is None:
                info_text.append("Using server default\n", style="dim")
            else:
                info_text.append(
                    f"{settings['lfs_keep_versions']} versions\n", style="yellow"
                )

            info_text.append(
                f"  Effective:   {settings['lfs_keep_versions_effective']} versions ",
                style="green",
            )
            info_text.append(f"({settings['lfs_keep_versions_source']})\n", style="dim")

            # Suffix Rules
            info_text.append("\nLFS Suffix Rules:\n", style="bold cyan")
            if settings["lfs_suffix_rules_effective"]:
                info_text.append(
                    f"  Active:      {', '.join(settings['lfs_suffix_rules_effective'])}\n",
                    style="yellow",
                )
            else:
                info_text.append("  Active:      None\n", style="dim")

            # Server Defaults
            info_text.append("\nServer Defaults:\n", style="bold cyan")
            server_threshold_mb = settings["server_defaults"]["lfs_threshold_bytes"] / (
                1000 * 1000
            )
            info_text.append(
                f"  Threshold:   {server_threshold_mb:.1f} MB\n", style="dim"
            )
            info_text.append(
                f"  Keep Versions: {settings['server_defaults']['lfs_keep_versions']} versions\n",
                style="dim",
            )

            panel = Panel(
                info_text,
                title=f"[bold]LFS Settings for {repo_id}[/bold]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
    except Exception as e:
        handle_error(e, ctx)


@lfs.command("threshold")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option(
    "--threshold", type=int, help="Threshold in bytes (minimum 1000000 = 1 MB)"
)
@click.option("--reset", is_flag=True, help="Reset to server default")
@click.pass_context
def set_lfs_threshold(ctx, repo_id, repo_type, threshold, reset):
    """Set repository LFS threshold.

    REPO_ID format: namespace/name

    Examples:
    \b
        kohub-cli settings repo lfs threshold my-org/my-model --threshold 10000000  # 10 MB
        kohub-cli settings repo lfs threshold my-org/my-model --reset
    """
    client = ctx.obj["client"]
    try:
        if reset:
            threshold_value = None
            message = f"LFS threshold reset to server default for {repo_id}"
        elif threshold is None:
            raise click.UsageError("Must specify either --threshold or --reset")
        else:
            if threshold < 1000000:
                raise click.BadParameter(
                    "Threshold must be at least 1000000 bytes (1 MB)"
                )
            threshold_value = threshold
            message = f"LFS threshold set to {threshold} bytes for {repo_id}"

        result = client.update_repo_settings(
            repo_id,
            repo_type=repo_type,
            lfs_threshold_bytes=threshold_value,
        )
        output_result(ctx, result, message)
    except Exception as e:
        handle_error(e, ctx)


@lfs.command("versions")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--count", type=int, help="Number of versions to keep (minimum 2)")
@click.option("--reset", is_flag=True, help="Reset to server default")
@click.pass_context
def set_lfs_versions(ctx, repo_id, repo_type, count, reset):
    """Set repository LFS keep versions.

    REPO_ID format: namespace/name

    Examples:
    \b
        kohub-cli settings repo lfs versions my-org/my-model --count 10
        kohub-cli settings repo lfs versions my-org/my-model --reset
    """
    client = ctx.obj["client"]
    try:
        if reset:
            versions_value = None
            message = f"LFS keep versions reset to server default for {repo_id}"
        elif count is None:
            raise click.UsageError("Must specify either --count or --reset")
        else:
            if count < 2:
                raise click.BadParameter("Keep versions must be at least 2")
            versions_value = count
            message = f"LFS keep versions set to {count} for {repo_id}"

        result = client.update_repo_settings(
            repo_id,
            repo_type=repo_type,
            lfs_keep_versions=versions_value,
        )
        output_result(ctx, result, message)
    except Exception as e:
        handle_error(e, ctx)


@lfs.command("suffix")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option(
    "--add", "add_suffixes", multiple=True, help="Add suffix rule (e.g., .safetensors)"
)
@click.option("--remove", "remove_suffixes", multiple=True, help="Remove suffix rule")
@click.option("--clear", is_flag=True, help="Clear all suffix rules")
@click.option(
    "--set", "set_suffixes", multiple=True, help="Set suffix rules (replaces all)"
)
@click.pass_context
def manage_lfs_suffix(
    ctx, repo_id, repo_type, add_suffixes, remove_suffixes, clear, set_suffixes
):
    """Manage repository LFS suffix rules.

    REPO_ID format: namespace/name

    Examples:
    \b
        kohub-cli settings repo lfs suffix my-org/my-model --add .safetensors --add .bin
        kohub-cli settings repo lfs suffix my-org/my-model --remove .bin
        kohub-cli settings repo lfs suffix my-org/my-model --set .safetensors --set .gguf
        kohub-cli settings repo lfs suffix my-org/my-model --clear
    """
    client = ctx.obj["client"]
    try:
        # Get current settings
        current_settings = client.get_repo_lfs_settings(repo_id, repo_type=repo_type)
        current_rules = current_settings.get("lfs_suffix_rules") or []

        new_rules = None

        if clear:
            new_rules = []
            message = f"Cleared all LFS suffix rules for {repo_id}"
        elif set_suffixes:
            # Validate suffixes
            for suffix in set_suffixes:
                if not suffix.startswith("."):
                    raise click.BadParameter(
                        f"Suffix must start with '.', got: {suffix}"
                    )
            new_rules = list(set_suffixes)
            message = f"Set LFS suffix rules for {repo_id}: {', '.join(new_rules)}"
        elif add_suffixes or remove_suffixes:
            new_rules = list(current_rules)

            # Add new suffixes
            for suffix in add_suffixes:
                if not suffix.startswith("."):
                    raise click.BadParameter(
                        f"Suffix must start with '.', got: {suffix}"
                    )
                if suffix not in new_rules:
                    new_rules.append(suffix)

            # Remove suffixes
            for suffix in remove_suffixes:
                if suffix in new_rules:
                    new_rules.remove(suffix)

            message = f"Updated LFS suffix rules for {repo_id}: {', '.join(new_rules) if new_rules else 'none'}"
        else:
            raise click.UsageError(
                "Must specify one of: --add, --remove, --set, or --clear"
            )

        result = client.update_repo_settings(
            repo_id,
            repo_type=repo_type,
            lfs_suffix_rules=new_rules if new_rules else None,
        )
        output_result(ctx, result, message)
    except Exception as e:
        handle_error(e, ctx)


@settings.group()
def organization():
    """Organization settings management."""
    pass


@organization.command("update")
@click.argument("org_name")
@click.option("--description", help="New description")
@click.pass_context
def update_org(ctx, org_name, description):
    """Update organization settings."""
    client = ctx.obj["client"]
    try:
        result = client.update_organization_settings(
            org_name,
            description=description,
        )
        output_result(ctx, result, f"Organization {org_name} settings updated")
    except Exception as e:
        handle_error(e, ctx)


@organization.command("members")
@click.argument("org_name")
@click.pass_context
def list_org_members(ctx, org_name):
    """List organization members."""
    client = ctx.obj["client"]
    try:
        members = client.list_organization_members(org_name)

        if ctx.obj["output"] == "json":
            output_result(ctx, members)
        else:
            if not members:
                console.print("[yellow]No members found[/yellow]")
                return

            table = Table(title=f"{org_name} Members")
            table.add_column("Username", style="cyan")
            table.add_column("Role", style="green")

            for m in members:
                table.add_row(
                    m.get("user", ""),
                    m.get("role", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


# ========== Configuration Commands ==========


@cli.group()
def config():
    """Configuration management."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Set a configuration value."""
    client = ctx.obj["client"]
    try:
        if key == "endpoint":
            client.config.endpoint = value
        elif key == "token":
            client.config.token = value
        else:
            client.config.set(key, value)

        output_result(ctx, {key: value}, f"Set {key} = {value}")
    except Exception as e:
        handle_error(e, ctx)


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Get a configuration value."""
    client = ctx.obj["client"]
    try:
        value = client.config.get(key)
        if value is None:
            console.print(f"[yellow]{key} is not set[/yellow]")
        else:
            output_result(ctx, {key: value})
    except Exception as e:
        handle_error(e, ctx)


@config.command("list")
@click.pass_context
def list_config(ctx):
    """Show all configuration."""
    client = ctx.obj["client"]
    try:
        cfg = client.load_config()
        cfg["endpoint"] = client.config.endpoint  # Include computed endpoint

        if ctx.obj["output"] == "json":
            output_result(ctx, cfg)
        else:
            console.print(f"[bold]Configuration file:[/bold] {client.config_path}\n")

            table = Table(title="Configuration")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")

            for key, value in cfg.items():
                # Mask token for security
                if key == "token" and value:
                    value = value[:10] + "..." if len(value) > 10 else "***"
                table.add_row(key, str(value))

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@config.command()
@click.confirmation_option(prompt="Are you sure you want to clear all configuration?")
@click.pass_context
def clear(ctx):
    """Clear all configuration."""
    client = ctx.obj["client"]
    try:
        client.config.clear()
        output_result(ctx, {}, "Configuration cleared")
    except Exception as e:
        handle_error(e, ctx)


@config.command("history")
@click.option("--limit", default=10, help="Number of recent operations to show")
@click.pass_context
def show_history(ctx, limit):
    """Show recent operation history."""
    client = ctx.obj["client"]
    try:
        history = client.config.get_history(limit)

        if ctx.obj["output"] == "json":
            output_result(ctx, history)
        else:
            if not history:
                console.print("[yellow]No operation history[/yellow]")
                return

            table = Table(title="Recent Operations")
            table.add_column("Time", style="blue")
            table.add_column("Operation", style="cyan")
            table.add_column("Details", style="green")

            for entry in history:
                timestamp = entry.get("timestamp", "")[:19]  # Trim milliseconds
                operation = entry.get("operation", "")
                details = entry.get("details", {})
                details_str = ", ".join(f"{k}={v}" for k, v in details.items())

                table.add_row(timestamp, operation, details_str)

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@config.command("clear-history")
@click.confirmation_option(prompt="Are you sure you want to clear operation history?")
@click.pass_context
def clear_history(ctx):
    """Clear operation history."""
    client = ctx.obj["client"]
    try:
        client.config.clear_history()
        output_result(ctx, {}, "Operation history cleared")
    except Exception as e:
        handle_error(e, ctx)


# ========== File Upload/Download Commands ==========


@repo_settings.command("upload")
@click.argument("repo_id")
@click.argument("local_path")
@click.option(
    "--path", "repo_path", help="Destination path in repo (default: same as local)"
)
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--branch", default="main", help="Target branch")
@click.option("--message", "-m", help="Commit message")
@click.pass_context
def upload_file(ctx, repo_id, local_path, repo_path, repo_type, branch, message):
    """Upload a file to repository.

    REPO_ID format: namespace/name
    LOCAL_PATH: Path to local file

    Examples:
    \b
        kohub-cli repo upload my-org/my-model model.safetensors
        kohub-cli repo upload my-org/my-model ./model.bin --path weights/model.bin
    """
    client = ctx.obj["client"]
    try:
        # Use local filename if repo_path not specified
        if not repo_path:
            from pathlib import Path

            repo_path = Path(local_path).name

        result = client.upload_file(
            repo_id,
            local_path=local_path,
            repo_path=repo_path,
            repo_type=repo_type,
            branch=branch,
            commit_message=message,
        )
        output_result(ctx, result, f"File uploaded: {repo_path}")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.command("download")
@click.argument("repo_id")
@click.argument("repo_path")
@click.option(
    "--output",
    "-o",
    "local_path",
    help="Local destination path (default: same as repo)",
)
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default="main", help="Branch or commit hash")
@click.pass_context
def download_file(ctx, repo_id, repo_path, local_path, repo_type, revision):
    """Download a file from repository.

    REPO_ID format: namespace/name
    REPO_PATH: Path to file in repository

    Examples:
    \b
        kohub-cli repo download my-org/my-model model.safetensors
        kohub-cli repo download my-org/my-model weights/model.bin -o ./model.bin
    """
    client = ctx.obj["client"]
    try:
        # Use repo filename if local_path not specified
        if not local_path:
            from pathlib import Path

            local_path = Path(repo_path).name

        result_path = client.download_file(
            repo_id,
            repo_path=repo_path,
            local_path=local_path,
            repo_type=repo_type,
            revision=revision,
        )
        output_result(ctx, {"path": result_path}, f"File downloaded: {result_path}")
    except Exception as e:
        handle_error(e, ctx)


# ========== Commit History Commands ==========


@repo_settings.command("commits")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--branch", default="main", help="Branch name")
@click.option("--limit", default=20, help="Maximum number of commits")
@click.pass_context
def list_repo_commits(ctx, repo_id, repo_type, branch, limit):
    """List commit history for a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.list_commits(
            repo_id, branch=branch, repo_type=repo_type, limit=limit
        )

        commits = result.get("commits", [])

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            if not commits:
                console.print("[yellow]No commits found[/yellow]")
                return

            table = Table(title=f"Commits for {repo_id} ({branch})")
            table.add_column("SHA", style="yellow", no_wrap=True)
            table.add_column("Message", style="cyan")
            table.add_column("Author", style="green")
            table.add_column("Date", style="blue")

            for c in commits:
                sha_short = c.get("oid", "")[:8]
                message = c.get("title", c.get("message", ""))
                # Truncate long messages
                if len(message) > 60:
                    message = message[:57] + "..."
                author = c.get("author", "unknown")
                date = c.get("date", "")

                table.add_row(sha_short, message, author, date)

            console.print(table)

            if result.get("hasMore"):
                console.print(
                    f"\n[dim]Showing {len(commits)} commits. Use --limit to see more.[/dim]"
                )
            else:
                console.print(f"\n[dim]Total: {len(commits)} commits[/dim]")
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.command("commit")
@click.argument("repo_id")
@click.argument("commit_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.pass_context
def get_commit_info(ctx, repo_id, commit_id, repo_type):
    """Show detailed information about a specific commit.

    REPO_ID format: namespace/name
    COMMIT_ID: Full or short commit SHA
    """
    client = ctx.obj["client"]
    try:
        commit = client.get_commit_detail(repo_id, commit_id, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, commit)
        else:
            from rich.panel import Panel
            from rich.text import Text

            info_text = Text()

            # Commit header
            info_text.append(
                f"Commit {commit.get('oid', commit_id)}\n", style="bold yellow"
            )
            info_text.append("─" * 60 + "\n", style="dim")

            # Commit info
            info_text.append("Author:  ", style="bold")
            info_text.append(f"{commit.get('author', 'unknown')}\n")

            info_text.append("Date:    ", style="bold")
            info_text.append(f"{commit.get('date', 'N/A')}\n")

            if commit.get("parents"):
                info_text.append("Parents: ", style="bold")
                parents_str = ", ".join([p[:8] for p in commit["parents"]])
                info_text.append(f"{parents_str}\n")

            # Message
            info_text.append("\n", style="bold")
            info_text.append(commit.get("message", "No message") + "\n")

            # Description if available
            if commit.get("description"):
                info_text.append("\n")
                info_text.append(commit["description"] + "\n", style="dim")

            # Metadata
            if commit.get("metadata"):
                info_text.append("\n")
                info_text.append("Metadata:\n", style="bold")
                for key, value in commit["metadata"].items():
                    info_text.append(f"  {key}: {value}\n", style="dim")

            panel = Panel(
                info_text,
                title=f"[bold]Commit Details[/bold]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
    except Exception as e:
        handle_error(e, ctx)


@repo_settings.command("commit-diff")
@click.argument("repo_id")
@click.argument("commit_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--show-diff", is_flag=True, help="Show actual diff content")
@click.pass_context
def get_commit_diff_cmd(ctx, repo_id, commit_id, repo_type, show_diff):
    """Show files changed in a commit.

    REPO_ID format: namespace/name
    COMMIT_ID: Full or short commit SHA
    """
    client = ctx.obj["client"]
    try:
        diff_result = client.get_commit_diff(repo_id, commit_id, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, diff_result)
        else:
            # Header
            console.print(
                f"\n[bold]Commit:[/bold] {diff_result.get('commit_id', commit_id)}"
            )
            console.print(
                f"[bold]Author:[/bold] {diff_result.get('author', 'unknown')}"
            )
            console.print(f"[bold]Date:[/bold] {diff_result.get('date', 'N/A')}")
            console.print(f"[bold]Message:[/bold] {diff_result.get('message', '')}\n")

            files = diff_result.get("files", [])
            if not files:
                console.print("[yellow]No files changed[/yellow]")
                return

            # Summary table
            table = Table(title="Files Changed")
            table.add_column("Type", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Size", style="yellow")
            table.add_column("LFS", style="magenta")

            for file_info in files:
                change_type = file_info.get("type", "unknown")
                path = file_info.get("path", "")
                size = file_info.get("size_bytes", 0)
                is_lfs = file_info.get("is_lfs", False)

                # Format size (decimal: 1KB = 1000 bytes)
                if size < 1000:
                    size_str = f"{size} B"
                elif size < 1000 * 1000:
                    size_str = f"{size / 1000:.1f} KB"
                else:
                    size_str = f"{size / (1000 * 1000):.1f} MB"

                # Change type icon
                type_icon = {
                    "added": "+ ",
                    "removed": "- ",
                    "changed": "M ",
                }.get(change_type, "  ")

                table.add_row(
                    type_icon + change_type,
                    path,
                    size_str,
                    "Yes" if is_lfs else "No",
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(files)} file(s) changed[/dim]")

            # Show diffs if requested
            if show_diff:
                console.print("\n[bold]Diffs:[/bold]\n")
                for file_info in files:
                    if file_info.get("diff"):
                        console.print(f"[cyan]File:[/cyan] {file_info['path']}")
                        console.print(file_info["diff"])
                        console.print()
    except Exception as e:
        handle_error(e, ctx)


# ========== Health Check Command ==========


@cli.command()
@click.pass_context
def health(ctx):
    """Check health of KohakuHub services."""
    client = ctx.obj["client"]

    try:
        health_info = client.health_check()

        if ctx.obj["output"] == "json":
            output_result(ctx, health_info)
        else:
            console.print("[bold]KohakuHub Health Check[/bold]\n")

            # API Status
            api_status = health_info.get("api", {})
            status = api_status.get("status", "unknown")

            if status == "healthy":
                console.print("✓ API: [bold green]Healthy[/bold green]")
                site_name = api_status.get("site_name", "KohakuHub")
                version = api_status.get("version", "unknown")
                console.print(f"  Site: {site_name}")
                console.print(f"  Version: {version}")
            elif status == "unreachable":
                console.print("✗ API: [bold red]Unreachable[/bold red]")
                if api_status.get("error"):
                    console.print(f"  Error: {api_status.get('error')}")
            else:
                console.print(f"? API: [yellow]{status}[/yellow]")

            console.print(f"  Endpoint: {api_status.get('endpoint')}")

            # Authentication Status
            console.print()
            if health_info.get("authenticated"):
                user = health_info.get("user", "unknown")
                console.print(
                    f"✓ Auth: [bold green]Authenticated as {user}[/bold green]"
                )
            else:
                console.print("✗ Auth: [yellow]Not authenticated[/yellow]")
                console.print("  [dim]Tip: Login with 'kohub-cli auth login'[/dim]")

    except Exception as e:
        handle_error(e, ctx)


# ========== Transfer Command ==========

def should_skip_file(file_path):
    """Check if file should be skipped during transfer."""
    skip_patterns = {'.git', '.cache', '__pycache__', '.pytest_cache', 
                    'node_modules', '.huggingface', '.DS_Store'}
    return (
        file_path.name.startswith('.') or
        any(pattern in file_path.parts for pattern in skip_patterns) or
        file_path.name.endswith(('.lock', '.tmp', '.temp'))
    )

def format_file_size(size_bytes):
    """Format file size consistently."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def check_huggingface_hub_available(ctx):
    """Check if huggingface_hub is available and show helpful error if not."""
    try:
        import huggingface_hub
        return True
    except ImportError:
        console = ctx.obj["console"]
        if ctx.obj.get("output", "text") == "json":
            # For JSON output, use standard error handling
            error = ImportError("huggingface_hub is required for HuggingFace Hub operations. Install with: pip install huggingface_hub")
            handle_error(error, ctx)
        else:
            # For text output, show helpful installation instructions
            console.print("[bold red]Error:[/bold red] huggingface_hub is required for HuggingFace Hub operations")
            console.print("")
            console.print("[yellow]To install huggingface_hub:[/yellow]")
            console.print("  pip install huggingface_hub")
            console.print("")
            console.print("Or install with all optional dependencies:")
            console.print("  pip install 'kohub-cli[transfer]'")
            sys.exit(1)
        return False


@cli.command()
@click.argument("source_repo_id")
@click.argument("dest_repo_id")
@click.option(
    "--repo-type",
    type=click.Choice(["model", "dataset", "auto"]),
    default="auto",
    help="Repository type (auto-detect if not specified)",
)
@click.option(
    "--include-lfs",
    is_flag=True,
    default=True,
    help="Include LFS files in transfer",
)
@click.option(
    "--private",
    is_flag=True,
    default=False,
    help="Create private repository",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing repository",
)
@click.option(
    "--token",
    help="Target hub API token (overrides HF_TOKEN env var). Used for both source and target if specific tokens not provided.",
)
@click.option(
    "--hf-token",
    help="HuggingFace Hub token for private repositories",
)
@click.option(
    "--src-token",
    help="Source hub API token (overrides --token for source hub)",
)
@click.option(
    "--target-token",
    help="Target hub API token (overrides --token for target hub)",
)
@click.option(
    "--src-endpoint",
    default="hf",
    help="Source hub (hf for HuggingFace Hub, or custom URL like https://hub.example.com)",
)
@click.option(
    "--target-endpoint",
    help="Target hub (hf for HuggingFace Hub, or custom URL like https://hub.example.com). Defaults to current endpoint.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed transfer progress",
)
@click.pass_context
def transfer(ctx, source_repo_id, dest_repo_id, repo_type, include_lfs, private, force, token, hf_token, src_token, target_token, src_endpoint, target_endpoint, verbose):
    """Transfer a repository between different hubs (HuggingFace, KohakuHub, or custom hubs).
    
    Examples:
    
    \b
    # Transfer from HuggingFace to current KohakuHub endpoint
    kohub-cli transfer deepseek-ai/DeepSeek-OCR user/DeepSeek-OCR
    
    \b
    # Transfer from custom hub to HuggingFace
    kohub-cli transfer user/model user/model --src-endpoint https://my-hub.com --target-endpoint hf
    
    \b
    # Transfer between two custom hubs
    kohub-cli transfer user/model user/model --src-endpoint https://hub1.com --target-endpoint https://hub2.com
    
    \b
    # Transfer a dataset with custom tokens
    kohub-cli transfer squad_v2 user/squad_v2 --repo-type dataset --hf-token <hf-token>
    
    \b
    # Transfer between hubs with different tokens
    kohub-cli transfer user/model user/model --src-endpoint https://hub1.com --target-endpoint https://hub2.com --src-token <token1> --target-token <token2>
    """
    import tempfile
    from pathlib import Path
    
    try:
        client = ctx.obj["client"]
        console = ctx.obj["console"]
        show_progress = ctx.obj.get("output", "text") == "text" and verbose
        
        # Determine source and target endpoints
        source_endpoint = "https://huggingface.co" if src_endpoint == "hf" else src_endpoint
        
        if target_endpoint:
            target_endpoint = "https://huggingface.co" if target_endpoint == "hf" else target_endpoint
        else:
            # Default to current client endpoint
            target_endpoint = client.endpoint
        
        if show_progress:
            console.print(f"🔄 Starting transfer from {source_endpoint} to {target_endpoint}")
        
        # Determine tokens for source and target
        if src_token:
            final_source_token = src_token
        elif source_endpoint == "https://huggingface.co":
            final_source_token = hf_token
        else:
            final_source_token = token
            
        if target_token:
            final_target_token = target_token
        elif target_endpoint == "https://huggingface.co":
            final_target_token = hf_token
        else:
            final_target_token = token
        
        # Set up target client
        if target_endpoint != client.endpoint:
            from .client import KohubClient
            from .config import Config
            target_client = KohubClient(endpoint=target_endpoint, token=final_target_token, config=Config())
        else:
            target_client = client
            if final_target_token:
                target_client.token = final_target_token
        
        # Auto-detect repository type if needed
        detected_repo_type = repo_type
        if repo_type == "auto":
            if show_progress:
                console.print(f"🔍 Detecting repository type...")
            
            if source_endpoint == "https://huggingface.co":
                # Check if huggingface_hub is available for HuggingFace operations
                if not check_huggingface_hub_available(ctx):
                    return
                
                from huggingface_hub import repo_info
                from huggingface_hub.utils import RepositoryNotFoundError
                
                try:
                    repo_info(source_repo_id, repo_type="model", token=final_source_token)
                    detected_repo_type = "model"
                except RepositoryNotFoundError:
                    try:
                        repo_info(source_repo_id, repo_type="dataset", token=final_source_token)
                        detected_repo_type = "dataset"
                    except RepositoryNotFoundError:
                        raise NotFoundError(f"Repository '{source_repo_id}' not found on {source_endpoint}")
            else:
                from .client import KohubClient
                from .config import Config
                source_client = KohubClient(endpoint=source_endpoint, token=final_source_token, config=Config())
                try:
                    source_client.repo_info(source_repo_id, repo_type="model")
                    detected_repo_type = "model"
                except NotFoundError:
                    try:
                        source_client.repo_info(source_repo_id, repo_type="dataset")
                        detected_repo_type = "dataset"
                    except NotFoundError:
                        raise NotFoundError(f"Repository '{source_repo_id}' not found on {source_endpoint}")
            
            if show_progress:
                console.print(f"✓ Detected as {detected_repo_type}")
        else:
            # Verify the repository exists with specified type
            if source_endpoint == "https://huggingface.co":
                # Check if huggingface_hub is available for HuggingFace operations
                if not check_huggingface_hub_available(ctx):
                    return
                
                from huggingface_hub import repo_info
                from huggingface_hub.utils import RepositoryNotFoundError
                
                try:
                    repo_info(source_repo_id, repo_type=detected_repo_type, token=final_source_token)
                except RepositoryNotFoundError:
                    raise NotFoundError(f"Repository '{source_repo_id}' not found as {detected_repo_type} on {source_endpoint}")
            else:
                from .client import KohubClient
                from .config import Config
                source_client = KohubClient(endpoint=source_endpoint, token=final_source_token, config=Config())
                try:
                    source_client.repo_info(source_repo_id, repo_type=detected_repo_type)
                except NotFoundError:
                    raise NotFoundError(f"Repository '{source_repo_id}' not found as {detected_repo_type} on {source_endpoint}")
        
        # Check if destination repository exists
        if "/" not in dest_repo_id:
            raise ValueError("Destination repo_id must be in format 'namespace/name'")
        
        try:
            target_client.repo_info(dest_repo_id, repo_type=detected_repo_type)
            if not force:
                raise AlreadyExistsError(f"Repository '{dest_repo_id}' already exists. Use --force to overwrite.")
            if show_progress:
                console.print(f"⚠️  Repository exists, overwriting due to --force")
        except NotFoundError:
            pass
        
        # Download from source hub
        with tempfile.TemporaryDirectory() as temp_dir:
            if show_progress:
                console.print(f"📥 Downloading from source...")
            
            if source_endpoint == "https://huggingface.co":
                # Check if huggingface_hub is available for HuggingFace operations
                if not check_huggingface_hub_available(ctx):
                    return
                
                from huggingface_hub import snapshot_download
                
                try:
                    local_dir = snapshot_download(
                        repo_id=source_repo_id,
                        repo_type=detected_repo_type,
                        local_dir=temp_dir,
                        local_dir_use_symlinks=False,
                        ignore_patterns=[] if include_lfs else ["*.bin", "*.safetensors", "*.gguf", "*.h5", "*.onnx"],
                        token=final_source_token,
                    )
                except Exception as e:
                    raise NetworkError(f"Failed to download from {source_endpoint}: {e}")
            else:
                # For custom hubs (like KohakuHub), use native KohubClient download
                from .client import KohubClient
                from .config import Config
                source_client = KohubClient(endpoint=source_endpoint, token=final_source_token, config=Config())
                
                try:
                    # Get list of all files in the repository
                    if show_progress:
                        console.print(f"  📋 Getting file list from {source_repo_id}...")
                    
                    files = source_client.list_repo_tree(
                        source_repo_id,
                        repo_type=detected_repo_type,
                        revision="main",
                        recursive=True
                    )
                    
                    # Filter out directories and files to skip
                    files_to_download = []
                    for f in files:
                        if f.get("type") == "directory":
                            continue
                        file_path = f.get("path", "")
                        if file_path and not should_skip_file(Path(file_path)):
                            files_to_download.append(f)
                    
                    if not include_lfs:
                        # Filter out large binary files if LFS is disabled
                        lfs_extensions = {".bin", ".safetensors", ".gguf", ".h5", ".onnx"}
                        files_to_download = [
                            f for f in files_to_download
                            if not any(f.get("path", "").lower().endswith(ext) for ext in lfs_extensions)
                        ]
                    
                    if show_progress:
                        console.print(f"  📦 Downloading {len(files_to_download)} files...")
                    
                    # Download each file
                    local_dir = temp_dir
                    for file_info in files_to_download:
                        file_path = file_info.get("path", "")
                        if not file_path:
                            continue
                            
                        local_file_path = Path(temp_dir) / file_path
                        
                        # Create parent directories
                        local_file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        if show_progress:
                            file_size = file_info.get("size", 0)
                            size_str = format_file_size(file_size)
                            console.print(f"    📄 {file_path} ({size_str})")
                        
                        # Download the file
                        source_client.download_file(
                            repo_id=source_repo_id,
                            repo_path=file_path,
                            local_path=str(local_file_path),
                            repo_type=detected_repo_type,
                            revision="main"
                        )
                    
                except Exception as e:
                    raise NetworkError(f"Failed to download from {source_endpoint}: {e}")
            
            # Create repository on target hub if it doesn't exist
            try:
                target_client.repo_info(dest_repo_id, repo_type=detected_repo_type)
            except NotFoundError:
                if show_progress:
                    console.print(f"📝 Creating repository...")
                target_client.create_repo(
                    repo_id=dest_repo_id,
                    repo_type=detected_repo_type,
                    private=private,
                )
            
            # Upload all files to target hub
            if show_progress:
                console.print(f"📤 Uploading files...")
            
            local_path = Path(local_dir)
            uploaded_count = 0
            skipped_count = 0
            failed_files = []
            
            for file_path in local_path.rglob("*"):
                if file_path.is_file() and not should_skip_file(file_path):
                    repo_path = str(file_path.relative_to(local_path))
                    
                    try:
                        if show_progress:
                            size_str = format_file_size(file_path.stat().st_size)
                            console.print(f"  📄 {repo_path} ({size_str})")
                        
                        target_client.upload_file(
                            repo_id=dest_repo_id,
                            local_path=str(file_path),
                            repo_path=repo_path,
                            repo_type=detected_repo_type,
                            commit_message=f"Transfer {repo_path}"
                        )
                        uploaded_count += 1
                        
                    except Exception as e:
                        failed_files.append({"file": repo_path, "error": str(e)})
                        if show_progress:
                            console.print(f"  ⚠️  Failed: {repo_path} - {e}")
                elif file_path.is_file():
                    skipped_count += 1
            
            # Standard result output
            source_hub_name = "HuggingFace Hub" if source_endpoint == "https://huggingface.co" else source_endpoint
            target_hub_name = "HuggingFace Hub" if target_endpoint == "https://huggingface.co" else target_endpoint
            
            result_data = {
                "source_repo": source_repo_id,
                "dest_repo": dest_repo_id,
                "repo_type": detected_repo_type,
                "files_uploaded": uploaded_count,
                "files_skipped": skipped_count,
                "files_failed": len(failed_files),
                "source_endpoint": source_hub_name,
                "target_endpoint": target_hub_name,
                "failed_files": failed_files
            }
            
            if failed_files:
                success_message = f"Transfer completed with {len(failed_files)} failures - {dest_repo_id} ({uploaded_count} files uploaded)"
            else:
                success_message = f"Successfully transferred {dest_repo_id} ({uploaded_count} files)"
            
            output_result(ctx, result_data, success_message)
    
    except Exception as e:
        handle_error(e, ctx)


# ========== Interactive Mode ==========


@cli.command()
@click.pass_context
def interactive(ctx):
    """Launch interactive TUI mode.

    This provides a menu-driven interface for managing
    KohakuHub resources interactively.
    """
    # Import the interactive mode from main
    from .main import InteractiveState, main_menu

    # Create state (will use endpoint/token from context if provided)
    state = InteractiveState()

    # Override with any provided options
    if ctx.obj.get("client"):
        client = ctx.obj["client"]
        if client.endpoint != "http://localhost:28080":
            state.client.endpoint = client.endpoint
        if client.token:
            state.client.token = client.token
            # Refresh username
            try:
                user_info = state.client.whoami()
                state.username = user_info.get("username")
            except Exception:
                pass

    # Launch interactive menu
    main_menu(state)
