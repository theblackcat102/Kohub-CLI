"""Centralized constants for kohub-cli interactive TUI.

This module contains UI strings, prompts, and style constants
to reduce duplication and maintain consistency.
"""

# Style constants
STYLE_SUCCESS = "bold green"
STYLE_ERROR = "bold red"
STYLE_WARNING = "bold yellow"
STYLE_INFO = "bold cyan"
STYLE_HIGHLIGHT = "bold cyan"

# UI strings
UI_BACK = "⬅️  Back"
UI_CANCEL = "⬅️  Cancel"
UI_CANCELLED = "[yellow]Cancelled[/yellow]"
UI_PRESS_ENTER = "\nPress Enter to continue..."

# Icons/prefixes
ICON_PRIVATE = "🔒 Private"
ICON_PUBLIC = "🌐 Public"

# Prompts
PROMPT_REPO_TYPE = "Repository type:"
PROMPT_REPO_ID = "Repository ID (namespace/name):"
PROMPT_REPO_ID_NEW = "New repository ID (namespace/name):"
PROMPT_ORG_NAME = "Organization name:"

# Validation messages
VALIDATION_REPO_ID_FORMAT = "Format: namespace/name"

# Section headers
SECTION_SUGGESTIONS = "\n💡 Suggestions:\n"

# Field labels
LABEL_CREATED = "Created: "

# Error message (already defined in client.py but referenced here for completeness)
# See: src/kohub_cli/client.py:16
# _ERR_INVALID_REPO_ID = "repo_id must be in format 'namespace/name'"
