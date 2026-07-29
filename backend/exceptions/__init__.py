"""VisionOps AI — Exception package.

This package defines all custom exception classes used across the backend.
Organized by domain layer to maintain clean architecture boundaries.
"""

from backend.exceptions.storage_exceptions import (
    CSVError,
    JSONError,
    FileOperationError,
    StorageError,
)
from backend.exceptions.validation_exceptions import (
    ValidationError,
    FileValidationError,
    UUIDValidationError,
    EmailValidationError,
    NumericRangeError,
    RequiredFieldError,
    FilenameValidationError,
    ExtensionValidationError,
)

__all__ = [
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
]
