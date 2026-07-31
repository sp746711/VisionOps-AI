"""VisionOps AI — Exception package.

This package defines all custom exception classes used across the backend.
Organized by domain layer to maintain clean architecture boundaries.
"""

from .base_exception import VisionOpsError
from .storage_exceptions import (
    CSVError,
    JSONError,
    FileOperationError,
    StorageError,
)
from .validation_exceptions import (
    ValidationError,
    FileValidationError,
    UUIDValidationError,
    EmailValidationError,
    NumericRangeError,
    RequiredFieldError,
    FilenameValidationError,
    ExtensionValidationError,
)
from .ai_exceptions import AIError
from .analytics_exceptions import AnalyticsError
from .api_exceptions import APIError, AuthenticationError

__all__ = [
    # Base exception
    "VisionOpsError",
    # Storage exceptions
    "CSVError",
    "JSONError",
    "FileOperationError",
    "StorageError",
    # Validation exceptions
    "ValidationError",
    "FileValidationError",
    "UUIDValidationError",
    "EmailValidationError",
    "NumericRangeError",
    "RequiredFieldError",
    "FilenameValidationError",
    "ExtensionValidationError",
    # AI exceptions
    "AIError",
    # Analytics exceptions
    "AnalyticsError",
    # API exceptions
    "APIError",
    "AuthenticationError",
]
