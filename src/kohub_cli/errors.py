"""Error classes for KohakuHub CLI."""


class KohubError(Exception):
    """Base exception for KohakuHub CLI errors."""

    def __init__(self, message: str, status_code: int = None, response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(KohubError):
    """Raised when authentication fails or is required."""

    pass


class AuthorizationError(KohubError):
    """Raised when user doesn't have permission for an operation."""

    pass


class NotFoundError(KohubError):
    """Raised when a resource is not found."""

    pass


class AlreadyExistsError(KohubError):
    """Raised when trying to create a resource that already exists."""

    pass


class ValidationError(KohubError):
    """Raised when input validation fails."""

    pass


class ServerError(KohubError):
    """Raised when the server returns a 5xx error."""

    pass


class NetworkError(KohubError):
    """Raised when network communication fails."""

    pass


def handle_response_error(response):
    """Convert HTTP response to appropriate exception.

    Args:
        response: requests.Response object

    Raises:
        Appropriate KohubError subclass based on status code
    """
    status = response.status_code

    try:
        data = response.json()
        message = data.get("detail") or data.get("message") or response.text
    except Exception:
        message = response.text or f"HTTP {status}"

    if status == 401:
        raise AuthenticationError(message, status, response)
    elif status == 403:
        raise AuthorizationError(message, status, response)
    elif status == 404:
        raise NotFoundError(message, status, response)
    elif status == 400:
        # Check if it's an "already exists" error
        if "already exists" in message.lower() or "exists" in message.lower():
            raise AlreadyExistsError(message, status, response)
        else:
            raise ValidationError(message, status, response)
    elif status >= 500:
        raise ServerError(message, status, response)
    else:
        raise KohubError(message, status, response)
