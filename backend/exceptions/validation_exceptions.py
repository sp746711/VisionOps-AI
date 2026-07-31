"""VisionOps AI — Validation exception classes.

These exceptions cover input validation, format checking, and constraint enforcement.
"""

from .base_exception import VisionOpsError


class ValidationError(VisionOpsError):
    """Base exception for all validation errors."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message)


class FileValidationError(ValidationError):
    """Raised when a file path or directory path fails validation."""

    def __init__(self, message: str = "File validation failed") -> None:
        super().__init__(message)


class UUIDValidationError(ValidationError):
    """Raised when a UUID string is invalid or malformed."""

    def __init__(self, message: str = "UUID validation failed") -> None:
        super().__init__(message)


class EmailValidationError(ValidationError):
    """Raised when an email address is invalid."""

    def __init__(self, message: str = "Email validation failed") -> None:
        super().__init__(message)


class NumericRangeError(ValidationError):
    """Raised when a numeric value is outside the allowed range."""

    def __init__(
        self,
        message: str = "Numeric value out of range",
        value: float | None = None,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> None:
        self.value = value
        self.min_val = min_val
        self.max_val = max_val

        details = []

        if value is not None:
            details.append(f"value={value}")
        if min_val is not None:
            details.append(f"min={min_val}")
        if max_val is not None:
            details.append(f"max={max_val}")

        suffix = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{suffix}")


class RequiredFieldError(ValidationError):
    """Raised when a required field or key is missing."""

    def __init__(
        self,
        message: str = "Required field missing",
        field: str | None = None,
    ) -> None:
        self.field = field
        detail = f" — missing field: {field}" if field else ""
        super().__init__(f"{message}{detail}")


class FilenameValidationError(ValidationError):
    """Raised when a filename fails validation."""

    def __init__(self, message: str = "Filename validation failed") -> None:
        super().__init__(message)


class ExtensionValidationError(ValidationError):
    """Raised when a file extension is invalid."""

    def __init__(self, message: str = "Extension validation failed") -> None:
        super().__init__(message)