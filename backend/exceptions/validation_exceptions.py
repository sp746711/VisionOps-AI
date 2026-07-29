"""VisionOps AI — Validation exception classes.

These exceptions cover input validation, format checking, and constraint enforcement.
"""


class ValidationError(Exception):
    """Base exception for all validation errors."""

    def __init__(self, message: str = "Validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class FileValidationError(ValidationError):
    """Raised when a file path or directory path fails validation."""

    def __init__(self, message: str = "File validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class UUIDValidationError(ValidationError):
    """Raised when a UUID string is invalid or malformed."""

    def __init__(self, message: str = "UUID validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class EmailValidationError(ValidationError):
    """Raised when an email address is invalid."""

    def __init__(self, message: str = "Email validation failed") -> None:
        self.message = message
        super().__init__(self.message)


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
        details = f"value={value}, range=[{min_val}, {max_val}]"
        super().__init__(f"{message} ({details})")


class RequiredFieldError(ValidationError):
    """Raised when a required field or key is missing."""

    def __init__(
        self, message: str = "Required field missing", field: str | None = None
    ) -> None:
        self.field = field
        detail = f" — missing: {field}" if field else ""
        super().__init__(f"{message}{detail}")


class FilenameValidationError(ValidationError):
    """Raised when a filename fails validation."""

    def __init__(self, message: str = "Filename validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class ExtensionValidationError(ValidationError):
    """Raised when a file extension is invalid."""

    def __init__(self, message: str = "Extension validation failed") -> None:
        self.message = message
        super().__init__(self.message)
