"""KohakuHub CLI - Python API and command-line tool for KohakuHub.

Example:
    Using the Python API:

    ```python
    from kohub_cli import KohubClient

    # Initialize client
    client = KohubClient(endpoint="http://localhost:28080")

    # Login
    client.login(username="alice", password="secret")

    # Create repository
    client.create_repo("my-org/my-model", repo_type="model")

    # List files
    files = client.list_repo_tree("my-org/my-model")
    ```

    Using the CLI:

    ```bash
    # Login
    kohub-cli auth login

    # Create repository
    kohub-cli repo create my-org/my-model --type model

    # List repositories
    kohub-cli repo list --type model --author my-org
    ```
"""

from .client import KohubClient
from .config import Config
from .errors import (
    KohubError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
    ServerError,
    NetworkError,
)

__version__ = "0.1.0"

__all__ = [
    "KohubClient",
    "Config",
    "KohubError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "AlreadyExistsError",
    "ValidationError",
    "ServerError",
    "NetworkError",
]
