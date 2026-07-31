"""VisionOps AI — API exception classes.

These exceptions cover API-layer operations including authentication,
authorization, request validation, routing, and HTTP-related errors.
"""

from .base_exception import VisionOpsError


class APIError(VisionOpsError):
    """Base exception for all API-layer errors."""


class AuthenticationError(APIError):
    """Raised when user authentication fails."""


class AuthorizationError(APIError):
    """Raised when a user lacks permission to perform an action."""


class BadRequestError(APIError):
    """Raised when an invalid client request is received."""


class ResourceNotFoundError(APIError):
    """Raised when a requested resource cannot be found."""


class ConflictError(APIError):
    """Raised when a request conflicts with the current resource state."""


class RateLimitError(APIError):
    """Raised when the API rate limit has been exceeded."""


class ServiceUnavailableError(APIError):
    """Raised when a required service is temporarily unavailable."""


class InternalAPIError(APIError):
    """Raised when an unexpected API-layer error occurs."""