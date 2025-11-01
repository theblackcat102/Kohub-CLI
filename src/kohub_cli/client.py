"""Python API client for KohakuHub."""

import requests
from typing import Any, Literal, Optional

from .config import Config
from .errors import (
    handle_response_error,
    NetworkError,
)


RepoType = Literal["model", "dataset", "space"]

# Error messages
_ERR_INVALID_REPO_ID = "repo_id must be in format 'namespace/name'"


class KohubClient:
    """Python API client for KohakuHub.

    Example:
        ```python
        from kohub_cli import KohubClient

        # Initialize client
        client = KohubClient(endpoint="http://localhost:28080")

        # Login
        client.login(username="alice", password="secret")

        # Create a repository
        client.create_repo("my-org/my-model", repo_type="model")
        ```
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """Initialize KohubClient.

        Args:
            endpoint: KohakuHub endpoint URL. If None, uses HF_ENDPOINT env var or config.
            token: API token. If None, uses HF_TOKEN env var or config.
            config: Config object. If None, creates a new one.
        """
        self.config = config or Config()
        self.endpoint = (endpoint or self.config.endpoint).rstrip("/")
        self.session = requests.Session()

        # Set token if provided
        if token:
            self.token = token
        elif self.config.token:
            self.token = self.config.token

    @property
    def token(self) -> Optional[str]:
        """Get current API token."""
        auth = self.session.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    @token.setter
    def token(self, value: Optional[str]):
        """Set API token for authentication."""
        if value:
            self.session.headers["Authorization"] = f"Bearer {value}"
        else:
            self.session.headers.pop("Authorization", None)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request to KohakuHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (will be appended to endpoint)
            **kwargs: Additional arguments passed to requests

        Returns:
            requests.Response object

        Raises:
            NetworkError: If network request fails
            KohubError: If API returns an error
        """
        url = f"{self.endpoint}{path}"
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"Network request failed: {e}")

        # Raise appropriate error if not successful
        if not response.ok:
            handle_response_error(response)

        return response

    # ========== Authentication ==========

    def register(
        self,
        username: str,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Register a new user.

        Args:
            username: Username
            email: Email address
            password: Password

        Returns:
            Registration response with success message

        Raises:
            AlreadyExistsError: If username or email already exists
            ValidationError: If input validation fails
        """
        response = self._request(
            "POST",
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        return response.json()

    def login(
        self,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        """Login and create a session.

        Args:
            username: Username
            password: Password

        Returns:
            Login response with session info

        Raises:
            AuthenticationError: If login fails
        """
        response = self._request(
            "POST",
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        return response.json()

    def logout(self) -> dict[str, Any]:
        """Logout and destroy current session.

        Returns:
            Logout response

        Raises:
            AuthenticationError: If not logged in
        """
        response = self._request("POST", "/api/auth/logout")
        return response.json()

    def whoami(self) -> dict[str, Any]:
        """Get current user information.

        Returns:
            User information (username, email, etc.)

        Raises:
            AuthenticationError: If not authenticated
        """
        response = self._request("GET", "/api/auth/me")
        return response.json()

    # ========== Token Management ==========

    def create_token(self, name: str) -> dict[str, Any]:
        """Create a new API token.

        Args:
            name: Token name/description

        Returns:
            Token information including the token string (only shown once!)

        Raises:
            AuthenticationError: If not authenticated
        """
        response = self._request(
            "POST",
            "/api/auth/tokens/create",
            json={"name": name},
        )
        return response.json()

    def list_tokens(self) -> list[dict[str, Any]]:
        """List all API tokens for current user.

        Returns:
            List of token information (without the token strings)

        Raises:
            AuthenticationError: If not authenticated
        """
        response = self._request("GET", "/api/auth/tokens")
        data = response.json()
        return data.get("tokens", [])

    def revoke_token(self, token_id: int) -> dict[str, Any]:
        """Revoke an API token.

        Args:
            token_id: Token ID to revoke

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            NotFoundError: If token not found
        """
        response = self._request("DELETE", f"/api/auth/tokens/{token_id}")
        return response.json()

    # ========== External Token Operations ==========

    def list_available_sources(self) -> list[dict[str, Any]]:
        """List available fallback sources.

        Returns:
            List of available sources with url, name, source_type
        """
        response = self._request("GET", "/api/fallback-sources/available")
        return response.json()

    def list_external_tokens(self, username: str) -> list[dict[str, Any]]:
        """List user's external fallback tokens.

        Args:
            username: Username

        Returns:
            List of external tokens (tokens are masked)
        """
        response = self._request("GET", f"/api/users/{username}/external-tokens")
        return response.json()

    def add_external_token(self, username: str, url: str, token: str) -> dict[str, Any]:
        """Add or update external token for a source.

        Args:
            username: Username
            url: Source URL (e.g., "https://huggingface.co")
            token: Token for this source

        Returns:
            Success message
        """
        from urllib.parse import quote

        response = self._request(
            "POST",
            f"/api/users/{username}/external-tokens",
            json={"url": url, "token": token},
        )
        return response.json()

    def delete_external_token(self, username: str, url: str) -> dict[str, Any]:
        """Delete external token for a source.

        Args:
            username: Username
            url: Source URL

        Returns:
            Success message
        """
        from urllib.parse import quote

        response = self._request(
            "DELETE", f"/api/users/{username}/external-tokens/{quote(url, safe='')}"
        )
        return response.json()

    # ========== Organization Operations ==========

    def create_organization(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new organization.

        Args:
            name: Organization name
            description: Organization description

        Returns:
            Organization information

        Raises:
            AuthenticationError: If not authenticated
            AlreadyExistsError: If organization already exists
        """
        response = self._request(
            "POST",
            "/org/create",
            json={"name": name, "description": description},
        )
        return response.json()

    def get_organization(self, org_name: str) -> dict[str, Any]:
        """Get organization information.

        Args:
            org_name: Organization name

        Returns:
            Organization details

        Raises:
            NotFoundError: If organization not found
        """
        response = self._request("GET", f"/org/{org_name}")
        return response.json()

    def list_user_organizations(
        self,
        username: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List organizations for a user.

        Args:
            username: Username (if None, uses current user)

        Returns:
            List of organizations with roles

        Raises:
            AuthenticationError: If username is None and not authenticated
            NotFoundError: If user not found
        """
        if username is None:
            # Get current user
            user_info = self.whoami()
            username = user_info["username"]

        response = self._request("GET", f"/org/users/{username}/orgs")
        data = response.json()
        return data.get("organizations", [])

    def add_organization_member(
        self,
        org_name: str,
        username: str,
        role: str = "member",
    ) -> dict[str, Any]:
        """Add a member to an organization.

        Args:
            org_name: Organization name
            username: Username to add
            role: Member role (member, admin, super-admin)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized to add members
            NotFoundError: If organization or user not found
        """
        response = self._request(
            "POST",
            f"/org/{org_name}/members",
            json={"username": username, "role": role},
        )
        return response.json()

    def remove_organization_member(
        self,
        org_name: str,
        username: str,
    ) -> dict[str, Any]:
        """Remove a member from an organization.

        Args:
            org_name: Organization name
            username: Username to remove

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized to remove members
            NotFoundError: If organization or user not found
        """
        response = self._request("DELETE", f"/org/{org_name}/members/{username}")
        return response.json()

    def update_organization_member(
        self,
        org_name: str,
        username: str,
        role: str,
    ) -> dict[str, Any]:
        """Update a member's role in an organization.

        Args:
            org_name: Organization name
            username: Username
            role: New role (member, admin, super-admin)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized to update roles
            NotFoundError: If organization or user not found
        """
        response = self._request(
            "PUT",
            f"/org/{org_name}/members/{username}",
            json={"role": role},
        )
        return response.json()

    # ========== Repository Operations ==========

    def create_repo(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        private: bool = False,
    ) -> dict[str, Any]:
        """Create a new repository.

        Args:
            repo_id: Repository ID (format: "namespace/name" or just "name")
            repo_type: Repository type (model, dataset, space)
            private: Whether the repository is private

        Returns:
            Repository information

        Raises:
            AuthenticationError: If not authenticated
            AlreadyExistsError: If repository already exists
            ValidationError: If repo_id format is invalid
        """
        # Parse repo_id
        if "/" in repo_id:
            organization, name = repo_id.split("/", 1)
        else:
            organization = None
            name = repo_id

        response = self._request(
            "POST",
            "/api/repos/create",
            json={
                "type": repo_type,
                "name": name,
                "organization": organization,
                "private": private,
            },
        )
        return response.json()

    def delete_repo(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Delete a repository.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized to delete
            NotFoundError: If repository not found
        """
        # Parse repo_id
        if "/" in repo_id:
            organization, name = repo_id.split("/", 1)
        else:
            organization = None
            name = repo_id

        response = self._request(
            "DELETE",
            "/api/repos/delete",
            json={
                "type": repo_type,
                "name": name,
                "organization": organization,
            },
        )
        return response.json()

    def squash_repo(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Squash repository to clear all commit history.

        This operation removes all commit history while preserving the current
        state of the repository. This can help reduce storage usage.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        response = self._request(
            "POST",
            "/api/repos/squash",
            json={
                "repo": repo_id,
                "type": repo_type,
            },
        )
        return response.json()

    def repo_info(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get repository information.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)
            revision: Specific revision/branch (optional)

        Returns:
            Repository metadata

        Raises:
            NotFoundError: If repository not found
        """
        # Parse repo_id
        if "/" in repo_id:
            namespace, name = repo_id.split("/", 1)
        else:
            raise ValueError(_ERR_INVALID_REPO_ID)

        if revision:
            path = f"/api/{repo_type}s/{namespace}/{name}/revision/{revision}"
        else:
            path = f"/api/{repo_type}s/{namespace}/{name}"

        response = self._request("GET", path)
        return response.json()

    def list_repos(
        self,
        repo_type: RepoType = "model",
        author: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List repositories.

        Args:
            repo_type: Repository type (model, dataset, space)
            author: Filter by author/namespace
            limit: Maximum number of results

        Returns:
            List of repositories

        Raises:
            ValidationError: If invalid parameters
        """
        params = {"limit": limit}
        if author:
            params["author"] = author

        response = self._request("GET", f"/api/{repo_type}s", params=params)
        return response.json()

    def list_namespace_repos(
        self,
        namespace: str,
        repo_type: Optional[RepoType] = None,
    ) -> list[dict[str, Any]]:
        """List all repositories under a namespace (user or organization).

        Args:
            namespace: Namespace (username or organization name)
            repo_type: Optional filter by repository type

        Returns:
            List of repositories grouped by type

        Raises:
            NotFoundError: If namespace not found
        """
        # Use the dedicated endpoint if available
        try:
            response = self._request("GET", f"/api/users/{namespace}/repos")
            data = response.json()

            # If repo_type specified, filter the results
            if repo_type:
                key = repo_type + "s"
                repos = data.get(key, [])
                for repo in repos:
                    repo["repo_type"] = repo_type
                return repos

            # Otherwise return all
            all_repos = []
            for rtype in ["model", "dataset", "space"]:
                key = rtype + "s"
                repos = data.get(key, [])
                for repo in repos:
                    repo["repo_type"] = rtype
                all_repos.extend(repos)

            return all_repos

        except Exception:
            # Fallback to old method if endpoint doesn't exist
            all_repos = []

            if repo_type:
                repos = self.list_repos(
                    repo_type=repo_type, author=namespace, limit=1000
                )
                return repos

            for rtype in ["model", "dataset", "space"]:
                repos = self.list_repos(repo_type=rtype, author=namespace, limit=1000)
                for repo in repos:
                    repo["repo_type"] = rtype
                all_repos.extend(repos)

            return all_repos

    def list_repo_tree(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str = "main",
        path: str = "",
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        """List files in a repository.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)
            revision: Branch or commit hash
            path: Path within repository
            recursive: List files recursively

        Returns:
            List of files and directories

        Raises:
            NotFoundError: If repository or path not found
        """
        # Parse repo_id
        if "/" in repo_id:
            namespace, name = repo_id.split("/", 1)
        else:
            raise ValueError(_ERR_INVALID_REPO_ID)

        api_path = (
            f"/api/{repo_type}s/{namespace}/{name}/tree/{revision}/{path}".rstrip("/")
        )
        params = {"recursive": str(recursive).lower()}

        response = self._request("GET", api_path, params=params)
        return response.json()

    # ========== Settings API ==========

    def whoami_v2(self) -> dict[str, Any]:
        """Get current user information with organizations (HuggingFace compatible).

        Returns:
            User information including organizations

        Raises:
            AuthenticationError: If not authenticated
        """
        response = self._request("GET", "/api/whoami-v2")
        return response.json()

    def update_user_settings(
        self,
        username: str,
        email: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update user settings.

        Args:
            username: Username to update
            email: New email address

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
        """
        data = {}
        if email is not None:
            data["email"] = email

        response = self._request("PUT", f"/api/users/{username}/settings", json=data)
        return response.json()

    def update_repo_settings(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        private: Optional[bool] = None,
        gated: Optional[str] = None,
        lfs_threshold_bytes: Optional[int] = None,
        lfs_keep_versions: Optional[int] = None,
        lfs_suffix_rules: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Update repository settings.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)
            private: Whether the repository is private
            gated: Gating mode ("auto", "manual", or None)
            lfs_threshold_bytes: LFS threshold in bytes (None = use server default)
            lfs_keep_versions: Number of LFS versions to keep (None = use server default)
            lfs_suffix_rules: List of file suffixes to always use LFS (None = no rules)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        data = {}
        if private is not None:
            data["private"] = private
        if gated is not None:
            data["gated"] = gated
        if lfs_threshold_bytes is not None:
            data["lfs_threshold_bytes"] = lfs_threshold_bytes
        if lfs_keep_versions is not None:
            data["lfs_keep_versions"] = lfs_keep_versions
        if lfs_suffix_rules is not None:
            data["lfs_suffix_rules"] = lfs_suffix_rules

        response = self._request(
            "PUT",
            f"/api/{repo_type}s/{namespace}/{name}/settings",
            json=data,
        )
        return response.json()

    def get_repo_lfs_settings(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Get repository LFS settings.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)

        Returns:
            LFS settings with configured and effective values

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        response = self._request(
            "GET",
            f"/api/{repo_type}s/{namespace}/{name}/settings/lfs",
        )
        return response.json()

    def move_repo(
        self,
        from_repo: str,
        to_repo: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Move/rename a repository.

        Args:
            from_repo: Source repository ID (format: "namespace/name")
            to_repo: Destination repository ID (format: "namespace/name")
            repo_type: Repository type (model, dataset, space)

        Returns:
            New repository URL

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If source repository not found
            AlreadyExistsError: If destination repository already exists
        """
        response = self._request(
            "POST",
            "/api/repos/move",
            json={
                "fromRepo": from_repo,
                "toRepo": to_repo,
                "type": repo_type,
            },
        )
        return response.json()

    def create_branch(
        self,
        repo_id: str,
        branch: str,
        repo_type: RepoType = "model",
        revision: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new branch.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            branch: Branch name to create
            repo_type: Repository type (model, dataset, space)
            revision: Source revision (defaults to main)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        data = {"branch": branch}
        if revision:
            data["revision"] = revision

        response = self._request(
            "POST",
            f"/api/{repo_type}s/{namespace}/{name}/branch",
            json=data,
        )
        return response.json()

    def delete_branch(
        self,
        repo_id: str,
        branch: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Delete a branch.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            branch: Branch name to delete
            repo_type: Repository type (model, dataset, space)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository or branch not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        response = self._request(
            "DELETE",
            f"/api/{repo_type}s/{namespace}/{name}/branch/{branch}",
        )
        return response.json()

    def create_tag(
        self,
        repo_id: str,
        tag: str,
        repo_type: RepoType = "model",
        revision: Optional[str] = None,
        message: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new tag.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            tag: Tag name to create
            repo_type: Repository type (model, dataset, space)
            revision: Source revision (defaults to main)
            message: Tag message

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        data = {"tag": tag}
        if revision:
            data["revision"] = revision
        if message:
            data["message"] = message

        response = self._request(
            "POST",
            f"/api/{repo_type}s/{namespace}/{name}/tag",
            json=data,
        )
        return response.json()

    def delete_tag(
        self,
        repo_id: str,
        tag: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Delete a tag.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            tag: Tag name to delete
            repo_type: Repository type (model, dataset, space)

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If repository or tag not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        response = self._request(
            "DELETE",
            f"/api/{repo_type}s/{namespace}/{name}/tag/{tag}",
        )
        return response.json()

    def update_organization_settings(
        self,
        org_name: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update organization settings.

        Args:
            org_name: Organization name
            description: New description

        Returns:
            Success message

        Raises:
            AuthenticationError: If not authenticated
            AuthorizationError: If not authorized
            NotFoundError: If organization not found
        """
        data = {}
        if description is not None:
            data["description"] = description

        response = self._request(
            "PUT",
            f"/api/organizations/{org_name}/settings",
            json=data,
        )
        return response.json()

    def list_organization_members(
        self,
        org_name: str,
    ) -> list[dict[str, Any]]:
        """List organization members.

        Args:
            org_name: Organization name

        Returns:
            List of members with roles

        Raises:
            NotFoundError: If organization not found
        """
        response = self._request("GET", f"/org/{org_name}/members")
        data = response.json()
        return data.get("members", [])

    # ========== Commit History ==========

    def list_commits(
        self,
        repo_id: str,
        branch: str = "main",
        repo_type: RepoType = "model",
        limit: int = 20,
        after: Optional[str] = None,
    ) -> dict[str, Any]:
        """List commits for a repository branch.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            branch: Branch name (default: main)
            repo_type: Repository type (model, dataset, space)
            limit: Maximum number of commits (default: 20, max: 100)
            after: Pagination cursor (commit ID to start after)

        Returns:
            Dict with 'commits', 'hasMore', 'nextCursor'

        Raises:
            NotFoundError: If repository or branch not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        params = {"limit": limit}
        if after:
            params["after"] = after

        response = self._request(
            "GET",
            f"/api/{repo_type}s/{namespace}/{name}/commits/{branch}",
            params=params,
        )
        return response.json()

    def get_commit_detail(
        self,
        repo_id: str,
        commit_id: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Get detailed information about a specific commit.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            commit_id: Commit ID (SHA)
            repo_type: Repository type (model, dataset, space)

        Returns:
            Commit details including author, message, metadata

        Raises:
            NotFoundError: If repository or commit not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        response = self._request(
            "GET",
            f"/api/{repo_type}s/{namespace}/{name}/commit/{commit_id}",
        )
        return response.json()

    def get_commit_diff(
        self,
        repo_id: str,
        commit_id: str,
        repo_type: RepoType = "model",
    ) -> dict[str, Any]:
        """Get diff of files changed in a commit.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            commit_id: Commit ID (SHA)
            repo_type: Repository type (model, dataset, space)

        Returns:
            Dict with commit info and list of files changed with diffs

        Raises:
            NotFoundError: If repository or commit not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        response = self._request(
            "GET",
            f"/api/{repo_type}s/{namespace}/{name}/commit/{commit_id}/diff",
        )
        return response.json()

    # ========== File Operations ==========

    def upload_file(
        self,
        repo_id: str,
        local_path: str,
        repo_path: str,
        repo_type: RepoType = "model",
        branch: str = "main",
        commit_message: Optional[str] = None,
    ) -> dict[str, Any]:
        """Upload a file to repository.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            local_path: Local file path to upload
            repo_path: Destination path in repository
            repo_type: Repository type (model, dataset, space)
            branch: Target branch (default: main)
            commit_message: Commit message (default: auto-generated)

        Returns:
            Commit result

        Raises:
            FileNotFoundError: If local file doesn't exist
            AuthenticationError: If not authenticated
            NotFoundError: If repository not found
        """
        import base64
        from pathlib import Path

        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        # Read file content
        with open(local_file, "rb") as f:
            content = f.read()

        # Encode as base64
        content_b64 = base64.b64encode(content).decode("utf-8")

        # Build NDJSON commit payload
        import json

        ndjson_lines = []

        # Header
        message = commit_message or f"Upload {repo_path}"
        ndjson_lines.append(
            json.dumps(
                {"key": "header", "value": {"summary": message, "description": ""}}
            )
        )

        # File
        ndjson_lines.append(
            json.dumps(
                {
                    "key": "file",
                    "value": {
                        "path": repo_path,
                        "content": content_b64,
                        "encoding": "base64",
                    },
                }
            )
        )

        ndjson_payload = "\n".join(ndjson_lines)

        # Send commit
        response = self._request(
            "POST",
            f"/api/{repo_type}s/{namespace}/{name}/commit/{branch}",
            data=ndjson_payload,
            headers={"Content-Type": "application/x-ndjson"},
        )

        return response.json()

    def download_file(
        self,
        repo_id: str,
        repo_path: str,
        local_path: str,
        repo_type: RepoType = "model",
        revision: str = "main",
    ) -> str:
        """Download a file from repository.

        Args:
            repo_id: Repository ID (format: "namespace/name")
            repo_path: File path in repository
            local_path: Local destination path
            repo_type: Repository type (model, dataset, space)
            revision: Branch or commit hash (default: main)

        Returns:
            Local file path

        Raises:
            NotFoundError: If file not found
        """
        if "/" not in repo_id:
            raise ValueError("repo_id must be in format 'namespace/name'")

        namespace, name = repo_id.split("/", 1)

        # Use resolve endpoint
        url = f"{self.endpoint}/{repo_type}s/{namespace}/{name}/resolve/{revision}/{repo_path}"

        try:
            response = self.session.get(url, allow_redirects=True)
            if not response.ok:
                handle_response_error(response)

            # Save to file
            with open(local_path, "wb") as f:
                f.write(response.content)

            return local_path
        except requests.RequestException as e:
            raise NetworkError(f"Download failed: {e}")

    # ========== Health Check ==========

    def health_check(self) -> dict[str, Any]:
        """Check health of KohakuHub services.

        Returns:
            Dict with status of various components

        Raises:
            NetworkError: If cannot connect to server
        """
        health_info = {
            "api": {"status": "unknown", "endpoint": self.endpoint},
            "authenticated": False,
            "user": None,
        }

        # Check API using /api/version endpoint
        try:
            response = self.session.get(f"{self.endpoint}/api/version", timeout=5)
            if response.ok:
                data = response.json()
                health_info["api"]["status"] = "healthy"
                health_info["api"]["version"] = data.get("version", "unknown")
                health_info["api"]["site_name"] = data.get("name", "KohakuHub")
                health_info["api"]["api"] = data.get("api", "kohakuhub")
            else:
                health_info["api"]["status"] = f"error (HTTP {response.status_code})"
        except requests.RequestException as e:
            health_info["api"]["status"] = "unreachable"
            health_info["api"]["error"] = str(e)

        # Check auth
        try:
            user_info = self.whoami()
            health_info["authenticated"] = True
            health_info["user"] = user_info.get("username")
        except Exception:
            health_info["authenticated"] = False

        return health_info

    # ========== Configuration ==========

    def save_config(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """Save configuration to config file.

        Args:
            endpoint: Endpoint URL to save
            token: API token to save
        """
        if endpoint is not None:
            self.config.endpoint = endpoint
        if token is not None:
            self.config.token = token

    def load_config(self) -> dict[str, Any]:
        """Load all configuration values.

        Returns:
            Dictionary of configuration values
        """
        return self.config.all()

    @property
    def config_path(self) -> str:
        """Get configuration file path.

        Returns:
            Path to configuration file
        """
        return str(self.config.config_file)
