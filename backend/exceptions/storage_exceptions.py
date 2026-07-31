"""VisionOps AI — Storage exception classes.

These exceptions cover file I/O, CSV, JSON, and blob storage operations.
"""

from .base_exception import VisionOpsError


class StorageError(VisionOpsError):
    """Base exception for all storage-layer errors."""

    def __init__(self, message: str = "A storage error occurred") -> None:
        super().__init__(message)


class CSVError(StorageError):
    """Raised when a CSV operation fails (read, write, parse, validate)."""

    def __init__(self, message: str = "CSV operation failed") -> None:
        super().__init__(message)


class JSONError(StorageError):
    """Raised when a JSON operation fails (read, write, deserialize)."""

    def __init__(self, message: str = "JSON operation failed") -> None:
        super().__init__(message)


class FileOperationError(StorageError):
    """Raised when a general file operation fails (copy, move, delete)."""

    def __init__(
        self,
        message: str = "File operation failed",
        path: str | None = None,
    ) -> None:
        self.path = path
        detail = f" — Path: {path}" if path else ""
        super().__init__(f"{message}{detail}")