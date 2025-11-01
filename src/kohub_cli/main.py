"""Interactive TUI mode for KohakuHub CLI - Refactored version."""

import os
import sys
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .client import KohubClient
from .config import Config
from .constants import (
    ICON_PRIVATE,
    ICON_PUBLIC,
    LABEL_CREATED,
    PROMPT_ORG_NAME,
    PROMPT_REPO_ID,
    PROMPT_REPO_TYPE,
    SECTION_SUGGESTIONS,
    STYLE_ERROR,
    STYLE_HIGHLIGHT,
    STYLE_WARNING,
    UI_BACK,
    UI_CANCEL,
    UI_CANCELLED,
    UI_PRESS_ENTER,
    VALIDATION_REPO_ID_FORMAT,
)
from .errors import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    KohubError,
    NetworkError,
    NotFoundError,
)

# UI Styles
_STYLE_SUCCESS = "bold green"


class UserCancelled(Exception):
    """Exception raised when user cancels an operation (Ctrl+C)."""

    pass


def safe_ask(question, default_on_cancel=None):
    """Wrapper for questionary that catches Ctrl+C and returns to menu.

    Args:
        question: Questionary question object
        default_on_cancel: Value to return on cancellation (None means raise UserCancelled)

    Returns:
        User's answer or default_on_cancel

    Raises:
        UserCancelled: If user pressed Ctrl+C and default_on_cancel is None
    """
    try:
        result = question.ask()
        # If user cancels (Ctrl+C), result is None
        if result is None:
            if default_on_cancel is not None:
                return default_on_cancel
            raise UserCancelled()
        return result
    except KeyboardInterrupt:
        if default_on_cancel is not None:
            return default_on_cancel
        raise UserCancelled()


class InteractiveState:
    """State management for interactive CLI mode with context navigation."""

    def __init__(self):
        """Initialize interactive state with KohubClient."""
        self.console = Console()
        self.config = Config()

        # Initialize client
        endpoint = os.environ.get("HF_ENDPOINT") or self.config.endpoint
        token = os.environ.get("HF_TOKEN") or self.config.token

        self.client = KohubClient(endpoint=endpoint, token=token, config=self.config)
        self.username = None

        # Context tracking (website-like navigation)
        self.current_context = None  # "repo", "user", "org", or None
        self.current_repo = None  # {repo_id, repo_type, info}
        self.current_user = None  # {username, info}
        self.current_org = None  # {org_name, info}

        # Try to get current user if token exists
        if token:
            try:
                user_info = self.client.whoami()
                self.username = user_info.get("username")
            except Exception:
                # Token might be invalid, clear it
                self.console.print(
                    "[yellow]Stored token is invalid, please login again[/yellow]"
                )

    def get_breadcrumb(self) -> str:
        """Get breadcrumb navigation string."""
        parts = ["KohakuHub"]

        if self.current_context == "repo" and self.current_repo:
            parts.append(self.current_repo["repo_type"].capitalize() + "s")
            parts.append(self.current_repo["repo_id"])
        elif self.current_context == "user" and self.current_user:
            parts.append("Users")
            parts.append(self.current_user["username"])
        elif self.current_context == "org" and self.current_org:
            parts.append("Organizations")
            parts.append(self.current_org["org_name"])

        return " > ".join(parts)

    def enter_repo_context(self, repo_id: str, repo_type: str = "model"):
        """Enter repository context for operations."""
        self.current_context = "repo"
        self.current_repo = {
            "repo_id": repo_id,
            "repo_type": repo_type,
            "info": None,  # Will be fetched on demand
        }

    def enter_user_context(self, username: str):
        """Enter user profile context."""
        self.current_context = "user"
        self.current_user = {
            "username": username,
            "info": None,
        }

    def enter_org_context(self, org_name: str):
        """Enter organization context."""
        self.current_context = "org"
        self.current_org = {
            "org_name": org_name,
            "info": None,
        }

    def exit_context(self):
        """Exit current context and return to main menu."""
        self.current_context = None
        self.current_repo = None
        self.current_user = None
        self.current_org = None

    def render_header(self):
        """Render status header showing connection, user info, and navigation breadcrumb."""
        # Breadcrumb navigation
        breadcrumb = self.get_breadcrumb()

        # Connection status
        conn_text = Text()
        conn_text.append("🌐 ", style="bold blue")
        conn_text.append(self.client.endpoint)

        # User status
        user_text = Text()
        if self.username:
            user_text.append("👤 ", style=_STYLE_SUCCESS)
            user_text.append(self.username, style=_STYLE_SUCCESS)
        else:
            user_text.append("👤 ", style=STYLE_ERROR)
            user_text.append("Not logged in", style=STYLE_ERROR)

        # Combine in panel
        from rich.columns import Columns

        status = Columns([conn_text, user_text], equal=True, expand=True)

        panel = Panel(
            status,
            title=f"[bold]{breadcrumb}[/bold]",
            border_style="blue",
            padding=(0, 2),
        )

        self.console.print(panel)
        self.console.print()

    def handle_error(self, e: Exception, operation: str = "Operation"):
        """Display error with helpful context.

        Args:
            e: Exception that occurred
            operation: Name of the operation that failed
        """
        error_text = Text()
        error_text.append("❌ ", style="bold red")
        error_text.append(f"{operation} failed\n\n", style="bold red")
        error_text.append(f"{str(e)}\n", style="red")

        # Add suggestions based on error type
        match e:
            case AuthenticationError():
                error_text.append(SECTION_SUGGESTIONS, style=STYLE_WARNING)
                error_text.append("  • Login: Select 'Login' from User Management\n")
                error_text.append("  • Or create an API token and add to config\n")

            case NotFoundError():
                error_text.append(SECTION_SUGGESTIONS, style=STYLE_WARNING)
                error_text.append("  • Check the resource name spelling\n")
                error_text.append("  • Verify the resource exists\n")

            case NetworkError():
                error_text.append(SECTION_SUGGESTIONS, style=STYLE_WARNING)
                error_text.append(f"  • Check endpoint: {self.client.endpoint}\n")
                error_text.append("  • Verify server is running\n")
                error_text.append("  • Check your network connection\n")

        panel = Panel(
            error_text, title="[bold red]Error[/bold red]", border_style="red"
        )
        self.console.print(panel)
        input(UI_PRESS_ENTER)


def main_menu(state: InteractiveState):
    """Main menu with improved UX."""
    while True:
        state.console.clear()
        state.render_header()

        # Show tip about Ctrl+C
        state.console.print(
            "[dim]💡 Tip: Press Ctrl+C at any prompt to go back[/dim]\n"
        )

        try:
            choice = safe_ask(
                questionary.select(
                    "What would you like to do?",
                    choices=[
                        questionary.Choice("🔐 Authentication & User", value="auth"),
                        questionary.Choice("📦 Repositories", value="repo"),
                        questionary.Choice("👥 Organizations", value="org"),
                        questionary.Choice("⚙️  Settings", value="settings"),
                        questionary.Separator(),
                        questionary.Choice("🚪 Exit", value="exit"),
                    ],
                )
            )
        except UserCancelled:
            # Ctrl+C on main menu = exit
            break

        match choice:
            case "auth":
                auth_menu(state)
            case "repo":
                repo_menu(state)
            case "org":
                org_menu(state)
            case "settings":
                settings_menu(state)
            case "exit":
                break


# ========== Authentication Menu ==========


def auth_menu(state: InteractiveState):
    """Authentication and user management menu."""
    while True:
        state.console.clear()
        state.render_header()

        # Show quick stats
        if state.username:
            state.console.print(f"[dim]Logged in as {state.username}[/dim]\n")

        try:
            choice = safe_ask(
                questionary.select(
                    "Authentication & User Management",
                    choices=[
                        questionary.Choice("🔑 Login", value="login"),
                        questionary.Choice("📝 Register", value="register"),
                        questionary.Choice("ℹ️  Who Am I", value="whoami"),
                        questionary.Separator("─── API Tokens ───"),
                        questionary.Choice("➕ Create Token", value="create_token"),
                        questionary.Choice("📋 List Tokens", value="list_tokens"),
                        questionary.Choice("🗑️  Delete Token", value="delete_token"),
                        questionary.Separator("─── Organizations ───"),
                        questionary.Choice("👥 My Organizations", value="my_orgs"),
                        questionary.Separator(),
                        questionary.Choice("🚪 Logout", value="logout"),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "login":
                login(state)
            case "register":
                register(state)
            case "whoami":
                whoami(state)
            case "create_token":
                create_token(state)
            case "list_tokens":
                list_tokens(state)
            case "delete_token":
                delete_token(state)
            case "my_orgs":
                my_orgs(state)
            case "logout":
                logout(state)
            case "back":
                break


def login(state: InteractiveState):
    """Login with improved UX."""
    state.console.print("[bold]Login to KohakuHub[/bold]\n")

    try:
        username = safe_ask(
            questionary.text(
                "Username (or Ctrl+C to cancel):",
                validate=lambda x: len(x) > 0 or "Username required",
            )
        )

        password = safe_ask(
            questionary.password(
                "Password (or Ctrl+C to cancel):",
                validate=lambda x: len(x) > 0 or "Password required",
            )
        )
    except UserCancelled:
        state.console.print("\n[yellow]Login cancelled[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Login with progress
    with state.console.status(f"[{_STYLE_SUCCESS}]Logging in..."):
        try:
            result = state.client.login(username, password)
            state.username = username
        except Exception as e:
            state.handle_error(e, "Login")
            return

    state.console.print(f"\n✓ Logged in as {username}", style=_STYLE_SUCCESS)

    # Offer to create and save token
    try:
        if safe_ask(
            questionary.confirm(
                "\nCreate API token for future use? (Recommended)", default=True
            )
        ):
            token_name = safe_ask(
                questionary.text(
                    "Token name:",
                    default=f"cli-{os.uname().nodename if hasattr(os, 'uname') else 'windows'}",
                )
            )

            try:
                with state.console.status(f"[{_STYLE_SUCCESS}]Creating token..."):
                    token_result = state.client.create_token(token_name)

                token_value = token_result["token"]

                # Save token to config
                state.config.token = token_value
                state.client.token = token_value

                state.console.print(
                    "\n✓ Token created and saved to config", style=_STYLE_SUCCESS
                )
                state.console.print("[dim]You won't need to enter password again[/dim]")
            except Exception as e:
                state.console.print(f"\n[yellow]Token creation failed: {e}[/yellow]")
    except UserCancelled:
        pass

    input("\nPress Enter to continue...")


def register(state: InteractiveState):
    """Register new user with improved UX."""
    state.console.print("[bold]Register New Account[/bold]\n")

    username = questionary.text(
        "Username:",
        validate=lambda x: (
            len(x) >= 3 and len(x) <= 50 or "Username must be 3-50 characters"
        ),
    ).ask()

    email = questionary.text(
        "Email:", validate=lambda x: "@" in x or "Invalid email format"
    ).ask()

    password = questionary.password(
        "Password:",
        validate=lambda x: len(x) >= 6 or "Password must be at least 6 characters",
    ).ask()

    password_confirm = questionary.password("Confirm password:").ask()

    if password != password_confirm:
        state.console.print("\n✗ Passwords don't match", style="bold red")
        input(UI_PRESS_ENTER)
        return

    # Register with progress
    with state.console.status(f"[{_STYLE_SUCCESS}]Creating account..."):
        try:
            result = state.client.register(username, email, password)
        except AlreadyExistsError as e:
            state.handle_error(e, "Registration")
            return
        except Exception as e:
            state.handle_error(e, "Registration")
            return

    state.console.print(f"\n✓ Account created: {username}", style=_STYLE_SUCCESS)

    message = result.get("message", "")
    if message:
        state.console.print(f"[dim]{message}[/dim]")

    # Auto-login if email is verified
    if result.get("email_verified", False):
        if questionary.confirm("\nLogin now?", default=True).ask():
            try:
                with state.console.status(f"[{_STYLE_SUCCESS}]Logging in..."):
                    state.client.login(username, password)
                    state.username = username

                state.console.print("✓ Logged in", style=_STYLE_SUCCESS)

                # Create and save token
                if questionary.confirm(
                    "Create API token? (Recommended)", default=True
                ).ask():
                    try:
                        token_result = state.client.create_token(f"cli-auto")
                        state.config.token = token_result["token"]
                        state.client.token = token_result["token"]
                        state.console.print(
                            "✓ Token created and saved", style=_STYLE_SUCCESS
                        )
                    except Exception:
                        pass
            except Exception as e:
                state.console.print(f"\n[yellow]Auto-login failed: {e}[/yellow]")

    input("\nPress Enter to continue...")


def whoami(state: InteractiveState):
    """Show current user info."""
    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching user info..."):
        try:
            info = state.client.whoami()
        except Exception as e:
            state.handle_error(e, "Get user info")
            return

    state.username = info.get("username")

    # Display in panel
    user_text = Text()
    user_text.append("👤 ", style="bold")
    user_text.append(f"{info.get('username')}\n\n", style=STYLE_HIGHLIGHT)
    user_text.append("Email: ", style="bold")
    user_text.append(f"{info.get('email')}\n")
    user_text.append("Email Verified: ", style="bold")
    verified = "✓ Yes" if info.get("email_verified") else "✗ No"
    style = "green" if info.get("email_verified") else "yellow"
    user_text.append(f"{verified}\n", style=style)
    user_text.append("User ID: ", style="bold")
    user_text.append(f"{info.get('id')}\n")

    panel = Panel(
        user_text,
        title="[bold]Current User[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def create_token(state: InteractiveState):
    """Create API token with improved UX."""
    state.console.print("[bold]Create API Token[/bold]\n")
    state.console.print("[dim]Tokens allow programmatic access to KohakuHub[/dim]\n")

    name = questionary.text(
        "Token name (e.g., 'my-laptop', 'ci-server'):",
        validate=lambda x: len(x) > 0 or "Token name required",
    ).ask()

    # Create with progress
    with state.console.status("[bold green]Creating token..."):
        try:
            result = state.client.create_token(name)
        except Exception as e:
            state.handle_error(e, "Token creation")
            return

    token_value = result["token"]

    # Display token prominently
    token_display = Text()
    token_display.append("🔑 Your API Token:\n\n", style="bold yellow")
    token_display.append(token_value, style=_STYLE_SUCCESS)
    token_display.append(
        "\n\n⚠️  Save this token now - you won't see it again!", style="bold red"
    )

    panel = Panel(
        token_display,
        title="[bold]Token Created Successfully[/bold]",
        border_style="green",
        padding=(1, 2),
    )

    state.console.print(panel)

    # Offer to save
    if questionary.confirm("\nSave token to config?", default=True).ask():
        state.config.token = token_value
        state.client.token = token_value
        state.console.print("✓ Token saved to config", style=_STYLE_SUCCESS)

    state.console.print(f"\n[bold]To use this token:[/bold]")
    state.console.print(f"  export HF_TOKEN={token_value}")

    input("\nPress Enter to continue...")


def list_tokens(state: InteractiveState):
    """List all API tokens."""
    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching tokens..."):
        try:
            tokens = state.client.list_tokens()
        except Exception as e:
            state.handle_error(e, "List tokens")
            return

    if not tokens:
        state.console.print("[yellow]No tokens found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display in table
    from rich.table import Table

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

    state.console.print(table)
    input("\nPress Enter to continue...")


def delete_token(state: InteractiveState):
    """Delete an API token."""
    # First list tokens
    try:
        tokens = state.client.list_tokens()
    except Exception as e:
        state.handle_error(e, "List tokens")
        return

    if not tokens:
        state.console.print("[yellow]No tokens to delete[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Show tokens and let user select
    choices = []
    for t in tokens:
        label = f"{t['name']} (ID: {t['id']}, Created: {t.get('created_at', 'N/A')})"
        choices.append(questionary.Choice(label, value=t["id"]))
    choices.append(questionary.Choice(UI_CANCEL, value=None))

    token_id = questionary.select("Select token to delete:", choices=choices).ask()

    if token_id is None:
        return

    # Confirm deletion
    if not questionary.confirm(
        f"Delete token ID {token_id}? This cannot be undone.", default=False
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    # Delete with progress
    with state.console.status(f"[{_STYLE_SUCCESS}]Deleting token..."):
        try:
            state.client.revoke_token(token_id)
        except Exception as e:
            state.handle_error(e, "Token deletion")
            return

    state.console.print("\n✓ Token deleted successfully", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def my_orgs(state: InteractiveState):
    """Show user's organizations."""
    if not state.username:
        # Try to refresh
        try:
            info = state.client.whoami()
            state.username = info.get("username")
        except Exception:
            state.console.print("[bold red]Please login first[/bold red]")
            input(UI_PRESS_ENTER)
            return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching organizations..."):
        try:
            orgs = state.client.list_user_organizations()
        except Exception as e:
            state.handle_error(e, "List organizations")
            return

    if not orgs:
        state.console.print("[yellow]You are not in any organizations[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{state.username}'s Organizations")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Description", style="blue")

    for o in orgs:
        table.add_row(
            o.get("name", ""),
            o.get("role", ""),
            o.get("description", ""),
        )

    state.console.print(table)
    input("\nPress Enter to continue...")


def logout(state: InteractiveState):
    """Logout from KohakuHub."""
    if not state.username:
        state.console.print("[yellow]Not logged in[/yellow]")
        input(UI_PRESS_ENTER)
        return

    if not questionary.confirm(f"Logout from {state.username}?", default=True).ask():
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Logging out..."):
        try:
            state.client.logout()
        except Exception as e:
            # Logout might fail if token-based, that's ok
            pass

    state.username = None
    state.console.print("\n✓ Logged out", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


# ========== Organization Menu ==========


def org_menu(state: InteractiveState):
    """Organization management menu."""
    while True:
        state.console.clear()
        state.render_header()

        # Show quick stats
        if state.username:
            try:
                orgs = state.client.list_user_organizations()
                state.console.print(
                    f"[dim]You're in {len(orgs)} organization(s)[/dim]\n"
                )
            except Exception:
                pass

        try:
            choice = safe_ask(
                questionary.select(
                    "Organization Management",
                    choices=[
                        questionary.Choice("➕ Create Organization", value="create"),
                        questionary.Choice("📋 List My Organizations", value="list"),
                        questionary.Choice("ℹ️  Organization Info", value="info"),
                        questionary.Separator("─── Members ───"),
                        questionary.Choice("👥 List Members", value="list_members"),
                        questionary.Choice("➕ Add Member", value="add"),
                        questionary.Choice("➖ Remove Member", value="remove"),
                        questionary.Choice(
                            "🔄 Update Member Role", value="update_role"
                        ),
                        questionary.Separator(),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "create":
                create_organization(state)
            case "list":
                my_orgs(state)
            case "info":
                organization_info(state)
            case "list_members":
                list_org_members(state)
            case "add":
                add_member(state)
            case "remove":
                remove_member(state)
            case "update_role":
                update_member_role(state)
            case "back":
                break


def create_organization(state: InteractiveState):
    """Create organization with improved UX."""
    state.console.print("[bold]Create Organization[/bold]\n")

    name = questionary.text(
        PROMPT_ORG_NAME,
        validate=lambda x: (
            len(x) >= 3 and len(x) <= 50 or "Name must be 3-50 characters"
        ),
    ).ask()

    description = questionary.text("Description (optional):").ask()

    # Confirm
    state.console.print("\n[bold]Creating organization:[/bold]")
    state.console.print(f"  Name: {name}")
    if description:
        state.console.print(f"  Description: {description}")

    if not questionary.confirm("Proceed?", default=True).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    # Create with progress
    with state.console.status(f"[{_STYLE_SUCCESS}]Creating organization..."):
        try:
            result = state.client.create_organization(name, description=description)
        except AlreadyExistsError:
            state.console.print(
                f"\n✗ Organization '{name}' already exists", style="bold red"
            )
            input(UI_PRESS_ENTER)
            return
        except Exception as e:
            state.handle_error(e, "Organization creation")
            return

    state.console.print(
        f"\n✓ Organization '{name}' created successfully", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


def organization_info(state: InteractiveState):
    """Show organization information."""
    org_name = questionary.text("Organization name:").ask()

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching organization info..."):
        try:
            info = state.client.get_organization(org_name)
        except Exception as e:
            state.handle_error(e, "Get organization info")
            return

    # Display
    info_text = Text()
    info_text.append("👥 ", style="bold")
    info_text.append(f"{info.get('name')}\n\n", style="bold cyan")
    info_text.append("Description: ", style="bold")
    info_text.append(f"{info.get('description', 'N/A')}\n")
    info_text.append(LABEL_CREATED, style="bold")
    info_text.append(f"{info.get('created_at', 'N/A')}\n")

    panel = Panel(
        info_text,
        title="[bold]Organization Info[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def list_org_members(state: InteractiveState):
    """List organization members."""
    org_name = questionary.text("Organization name:").ask()

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching members..."):
        try:
            members = state.client.list_organization_members(org_name)
        except Exception as e:
            state.handle_error(e, "List members")
            return

    if not members:
        state.console.print("[yellow]No members found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{org_name} Members")
    table.add_column("Username", style="cyan")
    table.add_column("Role", style="green")

    for m in members:
        table.add_row(m.get("user", ""), m.get("role", ""))

    state.console.print(table)
    input("\nPress Enter to continue...")


def add_member(state: InteractiveState):
    """Add member to organization."""
    org_name = questionary.text("Organization name:").ask()
    username = questionary.text("Username to add:").ask()
    role = questionary.select(
        "Role:", choices=["member", "admin", "super-admin"], default="member"
    ).ask()

    # Confirm
    if not questionary.confirm(
        f"Add {username} to {org_name} as {role}?", default=True
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Adding member..."):
        try:
            state.client.add_organization_member(org_name, username, role=role)
        except Exception as e:
            state.handle_error(e, "Add member")
            return

    state.console.print(
        f"\n✓ Added {username} to {org_name} as {role}", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


def remove_member(state: InteractiveState):
    """Remove member from organization."""
    org_name = questionary.text("Organization name:").ask()

    # Try to list members first
    try:
        members = state.client.list_organization_members(org_name)
        if members:
            # Let user select from list
            choices = [m["user"] for m in members]
            choices.append("⬅️  Cancel")
            username = questionary.select(
                "Select member to remove:", choices=choices
            ).ask()

            if username == "⬅️  Cancel":
                return
        else:
            username = questionary.text("Username to remove:").ask()
    except Exception:
        username = questionary.text("Username to remove:").ask()

    # Confirm
    if not questionary.confirm(
        f"⚠️  Remove {username} from {org_name}?", default=False
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Removing member..."):
        try:
            state.client.remove_organization_member(org_name, username)
        except Exception as e:
            state.handle_error(e, "Remove member")
            return

    state.console.print(f"\n✓ Removed {username} from {org_name}", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def update_member_role(state: InteractiveState):
    """Update member role."""
    org_name = questionary.text("Organization name:").ask()
    username = questionary.text("Username:").ask()
    role = questionary.select(
        "New role:", choices=["member", "admin", "super-admin"]
    ).ask()

    # Confirm
    if not questionary.confirm(
        f"Update {username}'s role in {org_name} to {role}?", default=True
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Updating role..."):
        try:
            state.client.update_organization_member(org_name, username, role=role)
        except Exception as e:
            state.handle_error(e, "Update member role")
            return

    state.console.print(
        f"\n✓ Updated {username}'s role to {role}", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


# ========== Repository Menu ==========


def repo_menu(state: InteractiveState):
    """Repository management menu with navigation support."""
    while True:
        state.console.clear()
        state.render_header()

        try:
            choice = safe_ask(
                questionary.select(
                    "Repository Management",
                    choices=[
                        questionary.Choice(
                            "🔍 Browse & Select Repository", value="browse"
                        ),
                        questionary.Choice("➕ Create Repository", value="create"),
                        questionary.Separator("─── Quick Actions ───"),
                        questionary.Choice("📋 List Repositories", value="list"),
                        questionary.Choice("ℹ️  Quick Info Lookup", value="info"),
                        questionary.Choice("🔄 Move/Rename", value="move"),
                        questionary.Choice("🗑️  Delete Repository", value="delete"),
                        questionary.Separator(),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "browse":
                browse_and_select_repo(state)
            case "create":
                create_repo(state)
            case "list":
                list_repos(state)
            case "info":
                repo_info(state)
            case "move":
                move_repo(state)
            case "delete":
                delete_repo(state)
            case "back":
                break


def browse_and_select_repo(state: InteractiveState):
    """Browse repositories and select one to enter its context."""
    try:
        repo_type = safe_ask(
            questionary.select(
                PROMPT_REPO_TYPE,
                choices=["model", "dataset", "space"],
                default="model",
            )
        )

        author = safe_ask(
            questionary.text(
                "Filter by author (leave blank for all, or press Ctrl+C to cancel):",
                default=state.username or "",
            )
        )
    except UserCancelled:
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching repositories..."):
        try:
            repos = state.client.list_repos(
                repo_type=repo_type, author=author or None, limit=100
            )
        except Exception as e:
            state.handle_error(e, "List repositories")
            return

    if not repos:
        state.console.print("[yellow]No repositories found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Let user select a repository
    choices = []
    for r in repos:
        visibility = "🔒" if r.get("private") else "🌐"
        label = f"{visibility} {r.get('id')} [dim]({r.get('author')})[/dim]"
        choices.append(questionary.Choice(label, value=r.get("id")))

    choices.append(questionary.Choice(UI_CANCEL, value=None))

    try:
        selected = safe_ask(
            questionary.select(
                f"Select {repo_type} to view (or press Ctrl+C to cancel):",
                choices=choices,
                use_shortcuts=True,
            )
        )
    except UserCancelled:
        return

    if selected is None:
        return

    # Enter repository context
    state.enter_repo_context(selected, repo_type)
    repo_context_menu(state)


def repo_context_menu(state: InteractiveState):
    """Context menu for a specific repository - all operations on current repo."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    while True:
        state.console.clear()
        state.render_header()

        # Show quick repo info if available
        if state.current_repo.get("info"):
            info = state.current_repo["info"]
            visibility = ICON_PRIVATE if info.get("private") else ICON_PUBLIC
            state.console.print(
                f"[dim]{visibility} | Last modified: {info.get('lastModified', 'N/A')}[/dim]\n"
            )

        try:
            choice = safe_ask(
                questionary.select(
                    f"What would you like to do with {repo_id}?",
                    choices=[
                        questionary.Choice("ℹ️  View Repository Info", value="info"),
                        questionary.Choice("📂 Browse Files", value="files"),
                        questionary.Choice("📜 View Commits", value="commits"),
                        questionary.Choice(
                            "🔍 View Commit Details", value="commit_detail"
                        ),
                        questionary.Choice("📊 View Commit Diff", value="commit_diff"),
                        questionary.Separator("─── Management ───"),
                        questionary.Choice("⚙️  Repository Settings", value="settings"),
                        questionary.Choice("🌿 Branch Management", value="branch_mgmt"),
                        questionary.Choice("🏷️  Tag Management", value="tag_mgmt"),
                        questionary.Choice("🔄 Move/Rename", value="move"),
                        questionary.Choice("📦 Squash History", value="squash"),
                        questionary.Choice("🗑️  Delete Repository", value="delete"),
                        questionary.Separator(),
                        questionary.Choice("⬅️  Back to Repository List", value="back"),
                    ],
                )
            )
        except UserCancelled:
            # Ctrl+C in repo context = go back to repo menu
            break

        match choice:
            case "info":
                repo_info_context(state)
            case "files":
                repo_tree_context(state)
            case "commits":
                list_commits_context(state)
            case "commit_detail":
                view_commit_detail(state)
            case "commit_diff":
                view_commit_diff(state)
            case "settings":
                repo_settings_context(state)
            case "branch_mgmt":
                branch_management_menu(state)
            case "tag_mgmt":
                tag_management_menu(state)
            case "move":
                move_repo_context(state)
            case "squash":
                squash_repo_context(state)
            case "delete":
                if delete_repo_context(state):
                    # Repository deleted, exit context
                    break
            case "back":
                break

    # Exit context when leaving
    state.exit_context()


def repo_info_context(state: InteractiveState):
    """Show repository info (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching repository info..."):
        try:
            info = state.client.repo_info(repo_id, repo_type=repo_type)
            # Cache it
            state.current_repo["info"] = info
        except Exception as e:
            state.handle_error(e, "Get repository info")
            return

    # Display
    info_text = Text()
    info_text.append("📦 ", style="bold")
    info_text.append(f"{info.get('id')}\n\n", style="bold cyan")

    info_text.append("Author: ", style="bold")
    info_text.append(f"{info.get('author')}\n")

    info_text.append("Type: ", style="bold")
    info_text.append(f"{repo_type}\n")

    info_text.append("Visibility: ", style="bold")
    visibility = "🔒 Private" if info.get("private") else "🌐 Public"
    info_text.append(f"{visibility}\n")

    info_text.append(LABEL_CREATED, style="bold")
    info_text.append(f"{info.get('createdAt', 'N/A')}\n")

    if info.get("lastModified"):
        info_text.append("Last Modified: ", style="bold")
        info_text.append(f"{info.get('lastModified')}\n")

    if info.get("sha"):
        info_text.append("\nCommit SHA: ", style="bold")
        info_text.append(f"{info.get('sha')}\n", style="yellow")

    panel = Panel(
        info_text,
        title=f"[bold]{repo_type.capitalize()} Repository[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def repo_tree_context(state: InteractiveState):
    """Browse repository files (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    try:
        revision = safe_ask(
            questionary.text("Revision/branch (or Ctrl+C to cancel):", default="main")
        )
        path = safe_ask(questionary.text("Path (leave blank for root):", default=""))
        recursive = safe_ask(questionary.confirm("List recursively?", default=True))
    except UserCancelled:
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching file tree..."):
        try:
            files = state.client.list_repo_tree(
                repo_id,
                repo_type=repo_type,
                revision=revision,
                path=path,
                recursive=recursive,
            )
        except Exception as e:
            state.handle_error(e, "List files")
            return

    if not files:
        state.console.print("[yellow]No files found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display as tree
    from rich.tree import Tree

    def format_size(size_bytes):
        """Format size using decimal prefixes (1KB = 1000 bytes)."""
        if size_bytes < 1000:
            return f"{size_bytes} B"
        elif size_bytes < 1000 * 1000:
            return f"{size_bytes / 1000:.1f} KB"
        elif size_bytes < 1000 * 1000 * 1000:
            return f"{size_bytes / (1000 * 1000):.1f} MB"
        else:
            return f"{size_bytes / (1000 * 1000 * 1000):.1f} GB"

    tree_root = Tree(
        f"[bold cyan]{repo_id}[/bold cyan] [dim]({revision}/{path or 'root'})[/dim]",
        guide_style="blue",
    )

    for item in sorted(
        files, key=lambda x: (x.get("type") != "directory", x.get("path", ""))
    ):
        item_path = item.get("path", "")
        item_type = item.get("type", "")
        item_size = item.get("size", 0)

        if item_type == "directory":
            tree_root.add(f"[bold blue]📁 {item_path}[/bold blue]")
        else:
            size_str = format_size(item_size)
            lfs_indicator = " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
            tree_root.add(
                f"[green]📄 {item_path}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
            )

    state.console.print(tree_root)
    state.console.print(f"\n[dim]Total: {len(files)} items[/dim]")
    input("\nPress Enter to continue...")


def list_commits_context(state: InteractiveState):
    """List commits for current repository."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    try:
        branch = safe_ask(
            questionary.text("Branch name (or Ctrl+C to cancel):", default="main")
        )
        limit = safe_ask(questionary.text("Number of commits:", default="20"))

        try:
            limit = int(limit)
        except ValueError:
            limit = 20
    except UserCancelled:
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching commits..."):
        try:
            result = state.client.list_commits(
                repo_id, branch=branch, repo_type=repo_type, limit=limit
            )
        except Exception as e:
            state.handle_error(e, "List commits")
            return

    commits = result.get("commits", [])
    if not commits:
        state.console.print("[yellow]No commits found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"Commits for {repo_id} ({branch})")
    table.add_column("SHA", style="yellow", no_wrap=True)
    table.add_column("Message", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Date", style="blue")

    for c in commits:
        sha_short = c.get("oid", "")[:8]
        message = c.get("title", c.get("message", ""))
        if len(message) > 60:
            message = message[:57] + "..."
        author = c.get("author", "unknown")
        date = c.get("date", "")

        table.add_row(sha_short, message, author, date)

    state.console.print(table)

    if result.get("hasMore"):
        state.console.print(
            f"\n[dim]Showing {len(commits)} commits. Use larger limit to see more.[/dim]"
        )
    else:
        state.console.print(f"\n[dim]Total: {len(commits)} commits[/dim]")

    input("\nPress Enter to continue...")


def view_commit_detail(state: InteractiveState):
    """View specific commit detail (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    try:
        commit_id = safe_ask(
            questionary.text(
                "Commit ID (full or short SHA, or Ctrl+C to cancel):",
                validate=lambda x: len(x) >= 6 or "Commit ID too short",
            )
        )
    except UserCancelled:
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching commit details..."):
        try:
            commit = state.client.get_commit_detail(
                repo_id, commit_id, repo_type=repo_type
            )
        except Exception as e:
            state.handle_error(e, "Get commit detail")
            return

    # Display
    info_text = Text()
    info_text.append(f"Commit {commit.get('oid', commit_id)}\n", style="bold yellow")
    info_text.append("─" * 60 + "\n", style="dim")

    info_text.append("Author:  ", style="bold")
    info_text.append(f"{commit.get('author', 'unknown')}\n")

    info_text.append("Date:    ", style="bold")
    info_text.append(f"{commit.get('date', 'N/A')}\n")

    if commit.get("parents"):
        info_text.append("Parents: ", style="bold")
        parents_str = ", ".join([p[:8] for p in commit["parents"]])
        info_text.append(f"{parents_str}\n")

    info_text.append("\n", style="bold")
    info_text.append(commit.get("message", "No message") + "\n")

    if commit.get("description"):
        info_text.append("\n")
        info_text.append(commit["description"] + "\n", style="dim")

    panel = Panel(
        info_text,
        title="[bold]Commit Details[/bold]",
        border_style="blue",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def view_commit_diff(state: InteractiveState):
    """View commit diff (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    try:
        commit_id = safe_ask(
            questionary.text(
                "Commit ID (full or short SHA, or Ctrl+C to cancel):",
                validate=lambda x: len(x) >= 6 or "Commit ID too short",
            )
        )
    except UserCancelled:
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching commit diff..."):
        try:
            diff_result = state.client.get_commit_diff(
                repo_id, commit_id, repo_type=repo_type
            )
        except Exception as e:
            state.handle_error(e, "Get commit diff")
            return

    # Header
    state.console.print(
        f"\n[bold]Commit:[/bold] {diff_result.get('commit_id', commit_id)}"
    )
    state.console.print(f"[bold]Author:[/bold] {diff_result.get('author', 'unknown')}")
    state.console.print(f"[bold]Date:[/bold] {diff_result.get('date', 'N/A')}")
    state.console.print(f"[bold]Message:[/bold] {diff_result.get('message', '')}\n")

    files = diff_result.get("files", [])
    if not files:
        state.console.print("[yellow]No files changed[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Summary table
    from rich.table import Table

    table = Table(title="Files Changed")
    table.add_column("Type", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Size", style="yellow")

    for file_info in files:
        change_type = file_info.get("type", "unknown")
        path = file_info.get("path", "")
        size = file_info.get("size_bytes", 0)

        if size < 1000:
            size_str = f"{size} B"
        elif size < 1000 * 1000:
            size_str = f"{size / 1000:.1f} KB"
        else:
            size_str = f"{size / (1000 * 1000):.1f} MB"

        type_icon = {
            "added": "+ ",
            "removed": "- ",
            "changed": "M ",
        }.get(change_type, "  ")

        table.add_row(type_icon + change_type, path, size_str)

    state.console.print(table)
    state.console.print(f"\n[dim]Total: {len(files)} file(s) changed[/dim]")
    input("\nPress Enter to continue...")


def repo_settings_context(state: InteractiveState):
    """Update repository settings (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    # Get current settings
    try:
        info = state.client.repo_info(repo_id, repo_type=repo_type)
        current_private = info.get("private", False)
    except Exception:
        current_private = False

    state.console.print(
        f"\n[dim]Current visibility: {'Private' if current_private else 'Public'}[/dim]\n"
    )

    private = questionary.select(
        "Visibility:",
        choices=[
            questionary.Choice("🌐 Public", value=False),
            questionary.Choice("🔒 Private", value=True),
        ],
        default=current_private,
    ).ask()

    if not questionary.confirm("Update settings?", default=True).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Updating settings..."):
        try:
            state.client.update_repo_settings(
                repo_id, repo_type=repo_type, private=private
            )
            # Invalidate cached info
            state.current_repo["info"] = None
        except Exception as e:
            state.handle_error(e, "Update settings")
            return

    state.console.print("\n✓ Settings updated", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def move_repo_context(state: InteractiveState):
    """Move/rename repository (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    state.console.print(f"[bold]Move/Rename Repository[/bold]\n")
    state.console.print(f"[dim]Current: {repo_id}[/dim]\n")

    to_repo = questionary.text(
        "New repository ID (namespace/name):",
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    if not questionary.confirm(f"\nMove {repo_id} to {to_repo}?", default=False).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Moving repository..."):
        try:
            result = state.client.move_repo(
                from_repo=repo_id, to_repo=to_repo, repo_type=repo_type
            )
        except Exception as e:
            state.handle_error(e, "Move repository")
            return

    state.console.print(
        f"\n✓ Repository moved: {result.get('url')}", style=_STYLE_SUCCESS
    )

    # Update context to new repo ID
    state.current_repo["repo_id"] = to_repo
    state.current_repo["info"] = None

    input("\nPress Enter to continue...")


def squash_repo_context(state: InteractiveState):
    """Squash repository history (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    state.console.print(f"[bold yellow]Squash Repository History[/bold yellow]\n")
    state.console.print(f"[dim]Repository: {repo_id}[/dim]\n")
    state.console.print("[yellow]⚠️  This will clear ALL commit history![/yellow]")
    state.console.print("[dim]Only the current state will be preserved.[/dim]\n")

    if not questionary.confirm(
        "Are you sure you want to squash this repository?", default=False
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(
        "[yellow]Squashing repository (this may take a while)..."
    ):
        try:
            result = state.client.squash_repo(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Squash repository")
            return

    state.console.print(f"\n✓ Repository squashed successfully", style=_STYLE_SUCCESS)
    state.current_repo["info"] = None  # Invalidate cache
    input("\nPress Enter to continue...")


def delete_repo_context(state: InteractiveState) -> bool:
    """Delete repository (uses current context). Returns True if deleted."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    state.console.print("[bold red]Delete Repository[/bold red]\n")
    state.console.print(f"[dim]Repository: {repo_id}[/dim]\n")
    state.console.print("[yellow]⚠️  This action is IRREVERSIBLE![/yellow]\n")

    # Double confirmation
    if not questionary.confirm(
        f"⚠️  Delete {repo_id}? This CANNOT be undone!", default=False
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return False

    # Type repo name to confirm
    repo_name = repo_id.split("/")[1]
    confirmation = questionary.text(
        f"Type the repository name '{repo_name}' to confirm:",
    ).ask()

    if confirmation != repo_name:
        state.console.print(
            "\n✗ Repository name doesn't match. Deletion cancelled.",
            style="bold red",
        )
        input(UI_PRESS_ENTER)
        return False

    # Delete with progress
    with state.console.status("[bold red]Deleting repository..."):
        try:
            state.client.delete_repo(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Repository deletion")
            return False

    state.console.print(f"\n✓ Repository {repo_id} deleted", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")
    return True


def branch_management_menu(state: InteractiveState):
    """Branch management submenu (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    while True:
        state.console.clear()
        state.render_header()

        try:
            choice = safe_ask(
                questionary.select(
                    "Branch Management",
                    choices=[
                        questionary.Choice("➕ Create Branch", value="create"),
                        questionary.Choice("🗑️  Delete Branch", value="delete"),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "create":
                branch_name = questionary.text(
                    "New branch name:",
                    validate=lambda x: len(x) > 0 or "Branch name required",
                ).ask()

                revision = questionary.text(
                    "Source revision (leave blank for main):", default=""
                ).ask()

                with state.console.status(f"[{_STYLE_SUCCESS}]Creating branch..."):
                    try:
                        state.client.create_branch(
                            repo_id,
                            branch=branch_name,
                            repo_type=repo_type,
                            revision=revision or None,
                        )
                    except Exception as e:
                        state.handle_error(e, "Create branch")
                        continue

                state.console.print(
                    f"\n✓ Branch '{branch_name}' created", style=_STYLE_SUCCESS
                )
                input(UI_PRESS_ENTER)

            case "delete":
                branch_name = questionary.text(
                    "Branch name to delete:",
                    validate=lambda x: (
                        x != "main" and len(x) > 0 or "Cannot delete main branch"
                    ),
                ).ask()

                if not questionary.confirm(
                    f"Delete branch '{branch_name}'?", default=False
                ).ask():
                    continue

                with state.console.status(f"[{_STYLE_SUCCESS}]Deleting branch..."):
                    try:
                        state.client.delete_branch(
                            repo_id, branch=branch_name, repo_type=repo_type
                        )
                    except Exception as e:
                        state.handle_error(e, "Delete branch")
                        continue

                state.console.print(
                    f"\n✓ Branch '{branch_name}' deleted", style=_STYLE_SUCCESS
                )
                input(UI_PRESS_ENTER)

            case "back":
                break


def tag_management_menu(state: InteractiveState):
    """Tag management submenu (uses current context)."""
    repo_id = state.current_repo["repo_id"]
    repo_type = state.current_repo["repo_type"]

    while True:
        state.console.clear()
        state.render_header()

        try:
            choice = safe_ask(
                questionary.select(
                    "Tag Management",
                    choices=[
                        questionary.Choice("➕ Create Tag", value="create"),
                        questionary.Choice("🗑️  Delete Tag", value="delete"),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "create":
                tag_name = questionary.text(
                    "New tag name:",
                    validate=lambda x: len(x) > 0 or "Tag name required",
                ).ask()

                revision = questionary.text(
                    "Source revision (leave blank for main):", default=""
                ).ask()

                message = questionary.text("Tag message (optional):", default="").ask()

                with state.console.status(f"[{_STYLE_SUCCESS}]Creating tag..."):
                    try:
                        state.client.create_tag(
                            repo_id,
                            tag=tag_name,
                            repo_type=repo_type,
                            revision=revision or None,
                            message=message or None,
                        )
                    except Exception as e:
                        state.handle_error(e, "Create tag")
                        continue

                state.console.print(
                    f"\n✓ Tag '{tag_name}' created", style=_STYLE_SUCCESS
                )
                input(UI_PRESS_ENTER)

            case "delete":
                tag_name = questionary.text(
                    "Tag name to delete:",
                    validate=lambda x: len(x) > 0 or "Tag name required",
                ).ask()

                if not questionary.confirm(
                    f"Delete tag '{tag_name}'?", default=False
                ).ask():
                    continue

                with state.console.status(f"[{_STYLE_SUCCESS}]Deleting tag..."):
                    try:
                        state.client.delete_tag(
                            repo_id, tag=tag_name, repo_type=repo_type
                        )
                    except Exception as e:
                        state.handle_error(e, "Delete tag")
                        continue

                state.console.print(
                    f"\n✓ Tag '{tag_name}' deleted", style=_STYLE_SUCCESS
                )
                input(UI_PRESS_ENTER)

            case "back":
                break


def create_repo(state: InteractiveState):
    """Create repository with improved UX."""
    state.console.print("[bold]Create Repository[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    name = questionary.text(
        "Repository name:",
        validate=lambda x: (
            len(x) > 0 and len(x) < 100 or "Name must be 1-100 characters"
        ),
    ).ask()

    # Default to current user's namespace
    namespace = questionary.text(
        "Namespace (organization or username):", default=state.username or ""
    ).ask()

    private = questionary.confirm("Private repository?", default=False).ask()

    repo_id = f"{namespace}/{name}"

    # Show summary
    state.console.print("\n[bold]Creating repository:[/bold]")
    state.console.print(f"  Type: {repo_type}")
    state.console.print(f"  ID: {repo_id}")
    state.console.print(f"  Visibility: {'🔒 Private' if private else '🌐 Public'}")

    if not questionary.confirm("\nProceed?", default=True).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    # Create with progress
    with state.console.status(f"[{_STYLE_SUCCESS}]Creating repository..."):
        try:
            result = state.client.create_repo(
                repo_id, repo_type=repo_type, private=private
            )
        except AlreadyExistsError:
            state.console.print(
                f"\n✗ Repository {repo_id} already exists", style="bold red"
            )
            input(UI_PRESS_ENTER)
            return
        except Exception as e:
            state.handle_error(e, "Repository creation")
            return

    state.console.print(
        f"\n✓ Repository created: {result.get('url')}", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


def list_repos(state: InteractiveState):
    """List repositories."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    author = questionary.text("Filter by author (optional, leave blank for all):").ask()

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching repositories..."):
        try:
            repos = state.client.list_repos(
                repo_type=repo_type, author=author or None, limit=50
            )
        except Exception as e:
            state.handle_error(e, "List repositories")
            return

    if not repos:
        state.console.print("[yellow]No repositories found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{repo_type.capitalize()}s")
    table.add_column("Repository", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Visibility", style="yellow")
    table.add_column("Created", style="blue")

    for r in repos:
        visibility = "🔒 Private" if r.get("private") else "🌐 Public"
        table.add_row(
            r.get("id", ""),
            r.get("author", ""),
            visibility,
            r.get("createdAt", ""),
        )

    state.console.print(table)
    state.console.print(f"\n[dim]Total: {len(repos)} repositories[/dim]")
    input("\nPress Enter to continue...")


def repo_info(state: InteractiveState):
    """Show repository information."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        PROMPT_REPO_ID,
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching repository info..."):
        try:
            info = state.client.repo_info(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Get repository info")
            return

    # Display
    info_text = Text()
    info_text.append("📦 ", style="bold")
    info_text.append(f"{info.get('id')}\n\n", style="bold cyan")

    info_text.append("Author: ", style="bold")
    info_text.append(f"{info.get('author')}\n")

    info_text.append("Type: ", style="bold")
    info_text.append(f"{repo_type}\n")

    info_text.append("Visibility: ", style="bold")
    visibility = "🔒 Private" if info.get("private") else "🌐 Public"
    info_text.append(f"{visibility}\n")

    info_text.append(LABEL_CREATED, style="bold")
    info_text.append(f"{info.get('createdAt', 'N/A')}\n")

    if info.get("lastModified"):
        info_text.append("Last Modified: ", style="bold")
        info_text.append(f"{info.get('lastModified')}\n")

    if info.get("sha"):
        info_text.append("\nCommit SHA: ", style="bold")
        info_text.append(f"{info.get('sha')}\n", style="yellow")

    panel = Panel(
        info_text,
        title=f"[bold]{repo_type.capitalize()} Repository[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def repo_tree(state: InteractiveState):
    """Browse repository files with tree view."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        PROMPT_REPO_ID,
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    revision = questionary.text("Revision/branch:", default="main").ask()

    path = questionary.text("Path (leave blank for root):", default="").ask()

    recursive = questionary.confirm("List recursively?", default=False).ask()

    with state.console.status(f"[{_STYLE_SUCCESS}]Fetching file tree..."):
        try:
            files = state.client.list_repo_tree(
                repo_id,
                repo_type=repo_type,
                revision=revision,
                path=path,
                recursive=recursive,
            )
        except Exception as e:
            state.handle_error(e, "List files")
            return

    if not files:
        state.console.print("[yellow]No files found[/yellow]")
        input(UI_PRESS_ENTER)
        return

    # Display as tree
    from rich.tree import Tree

    def format_size(size_bytes):
        """Format file size using decimal prefixes (1KB = 1000 bytes)."""
        if size_bytes < 1000:
            return f"{size_bytes} B"
        elif size_bytes < 1000 * 1000:
            return f"{size_bytes / 1000:.1f} KB"
        elif size_bytes < 1000 * 1000 * 1000:
            return f"{size_bytes / (1000 * 1000):.1f} MB"
        else:
            return f"{size_bytes / (1000 * 1000 * 1000):.1f} GB"

    tree_root = Tree(
        f"[bold cyan]{repo_id}[/bold cyan] [dim]({revision})[/dim]",
        guide_style="blue",
    )

    for item in sorted(
        files, key=lambda x: (x.get("type") != "directory", x.get("path", ""))
    ):
        item_path = item.get("path", "")
        item_type = item.get("type", "")
        item_size = item.get("size", 0)

        if item_type == "directory":
            tree_root.add(f"[bold blue]📁 {item_path}[/bold blue]")
        else:
            size_str = format_size(item_size)
            lfs_indicator = " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
            tree_root.add(
                f"[green]📄 {item_path}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
            )

    state.console.print(tree_root)
    state.console.print(f"\n[dim]Total: {len(files)} items[/dim]")
    input("\nPress Enter to continue...")


def repo_settings(state: InteractiveState):
    """Update repository settings."""
    state.console.print("[bold]Repository Settings[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        PROMPT_REPO_ID,
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    # Get current settings
    try:
        info = state.client.repo_info(repo_id, repo_type=repo_type)
        current_private = info.get("private", False)
    except Exception:
        current_private = False

    state.console.print(
        f"\n[dim]Current visibility: {'Private' if current_private else 'Public'}[/dim]\n"
    )

    private = questionary.select(
        "Visibility:",
        choices=[
            questionary.Choice("🌐 Public", value=False),
            questionary.Choice("🔒 Private", value=True),
        ],
        default=current_private,
    ).ask()

    # Confirm
    if not questionary.confirm("Update settings?", default=True).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Updating settings..."):
        try:
            state.client.update_repo_settings(
                repo_id, repo_type=repo_type, private=private
            )
        except Exception as e:
            state.handle_error(e, "Update settings")
            return

    state.console.print("\n✓ Settings updated", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def move_repo(state: InteractiveState):
    """Move/rename repository."""
    state.console.print("[bold]Move/Rename Repository[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    from_repo = questionary.text(
        "Current repository ID (namespace/name):",
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    to_repo = questionary.text(
        "New repository ID (namespace/name):",
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    # Confirm
    state.console.print(f"\n[bold]Move repository:[/bold]")
    state.console.print(f"  From: {from_repo}")
    state.console.print(f"  To: {to_repo}")

    if not questionary.confirm("\n⚠️  Proceed?", default=False).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    with state.console.status(f"[{_STYLE_SUCCESS}]Moving repository..."):
        try:
            result = state.client.move_repo(
                from_repo=from_repo, to_repo=to_repo, repo_type=repo_type
            )
        except Exception as e:
            state.handle_error(e, "Move repository")
            return

    state.console.print(
        f"\n✓ Repository moved: {result.get('url')}", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


def delete_repo(state: InteractiveState):
    """Delete repository with improved confirmation."""
    state.console.print("[bold red]Delete Repository[/bold red]\n")
    state.console.print("[yellow]⚠️  This action is IRREVERSIBLE![/yellow]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        PROMPT_REPO_ID,
        validate=lambda x: "/" in x or VALIDATION_REPO_ID_FORMAT,
    ).ask()

    # Try to show repo info first
    try:
        info = state.client.repo_info(repo_id, repo_type=repo_type)
        state.console.print("[bold]Repository to delete:[/bold]")
        state.console.print(f"  ID: {info.get('id')}")
        state.console.print(f"  Type: {repo_type}")
        state.console.print(
            f"  Visibility: {'Private' if info.get('private') else 'Public'}"
        )
        if info.get("lastModified"):
            state.console.print(f"  Last Modified: {info.get('lastModified')}")
        state.console.print()
    except Exception:
        pass

    # Double confirmation
    if not questionary.confirm(
        f"⚠️  Delete {repo_id}? This CANNOT be undone!", default=False
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    # Type repo name to confirm
    repo_name = repo_id.split("/")[1]
    confirmation = questionary.text(
        f"Type the repository name '{repo_name}' to confirm:",
    ).ask()

    if confirmation != repo_name:
        state.console.print(
            "\n✗ Repository name doesn't match. Deletion cancelled.",
            style="bold red",
        )
        input(UI_PRESS_ENTER)
        return

    # Delete with progress
    with state.console.status("[bold red]Deleting repository..."):
        try:
            state.client.delete_repo(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Repository deletion")
            return

    state.console.print(f"\n✓ Repository {repo_id} deleted", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


# ========== Settings Menu ==========


def settings_menu(state: InteractiveState):
    """Settings and configuration menu."""
    while True:
        state.console.clear()
        state.render_header()

        state.console.print(f"[dim]Config: {state.client.config.config_file}[/dim]\n")

        try:
            choice = safe_ask(
                questionary.select(
                    "Settings & Configuration",
                    choices=[
                        questionary.Choice("🌐 Set Endpoint URL", value="endpoint"),
                        questionary.Choice("🔑 Set API Token", value="token"),
                        questionary.Choice("📋 Show All Config", value="show"),
                        questionary.Choice("🗑️  Clear Config", value="clear"),
                        questionary.Separator(),
                        questionary.Choice(UI_BACK, value="back"),
                    ],
                )
            )
        except UserCancelled:
            break

        match choice:
            case "endpoint":
                set_endpoint(state)
            case "token":
                set_token(state)
            case "show":
                show_config(state)
            case "clear":
                clear_config(state)
            case "back":
                break


def set_endpoint(state: InteractiveState):
    """Set endpoint URL."""
    current = state.client.endpoint
    state.console.print(f"[dim]Current endpoint: {current}[/dim]\n")

    endpoint = questionary.text(
        "Endpoint URL (e.g., http://localhost:48888):",
        default=current,
        validate=lambda x: x.startswith("http")
        or "Must start with http:// or https://",
    ).ask()

    endpoint = endpoint.rstrip("/")
    state.config.endpoint = endpoint
    state.client.endpoint = endpoint

    state.console.print(f"\n✓ Endpoint set to {endpoint}", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def set_token(state: InteractiveState):
    """Set API token."""
    state.console.print("[bold]Set API Token[/bold]\n")
    state.console.print("[dim]Token will be saved to config file[/dim]\n")

    token = questionary.password(
        "API Token:", validate=lambda x: len(x) > 0 or "Token required"
    ).ask()

    # Test token
    state.config.token = token
    state.client.token = token

    with state.console.status(f"[{_STYLE_SUCCESS}]Verifying token..."):
        try:
            user_info = state.client.whoami()
            state.username = user_info.get("username")
        except Exception as e:
            state.console.print(f"\n✗ Invalid token: {e}", style="bold red")
            input(UI_PRESS_ENTER)
            return

    state.console.print(
        f"\n✓ Token saved and verified (user: {state.username})", style=_STYLE_SUCCESS
    )
    input("\nPress Enter to continue...")


def show_config(state: InteractiveState):
    """Show all configuration."""
    cfg = state.client.load_config()
    cfg["endpoint"] = state.client.endpoint

    from rich.table import Table

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in cfg.items():
        # Mask token
        if key == "token" and value:
            value = value[:10] + "..." if len(value) > 10 else "***"
        table.add_row(key, str(value))

    state.console.print(table)
    state.console.print(f"\n[dim]Config file: {state.client.config.config_file}[/dim]")
    input("\nPress Enter to continue...")


def clear_config(state: InteractiveState):
    """Clear all configuration."""
    if not questionary.confirm(
        "⚠️  Clear all configuration? This will logout and remove saved token.",
        default=False,
    ).ask():
        state.console.print(UI_CANCELLED)
        input(UI_PRESS_ENTER)
        return

    state.client.config.clear()
    state.client.token = None
    state.username = None

    state.console.print("\n✓ Configuration cleared", style=_STYLE_SUCCESS)
    input("\nPress Enter to continue...")


def main():
    """Main entry point for interactive mode."""
    if len(sys.argv) == 1:
        state = InteractiveState()
        main_menu(state)
    else:
        # Use Click CLI
        from .cli import cli as click_cli

        click_cli()


if __name__ == "__main__":
    main()
