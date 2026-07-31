"""VisionOps AI — Unit tests for the ``exceptions`` package.

Covers all custom exception classes defined across the exceptions modules:
- base_exception
- storage_exceptions
- validation_exceptions
- ai_exceptions
- analytics_exceptions
- api_exceptions
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# base_exception
# ---------------------------------------------------------------------------


class TestVisionOpsError:
    """Tests for :class:`backend.exceptions.base_exception.VisionOpsError`."""

    def test_default_message(self):
        """VisionOpsError has a sensible default message."""
        from backend.exceptions.base_exception import VisionOpsError

        exc = VisionOpsError()
        assert str(exc) == "A VisionOps error occurred"

    def test_custom_message(self):
        """VisionOpsError accepts a custom message."""
        from backend.exceptions.base_exception import VisionOpsError

        exc = VisionOpsError("Custom error message")
        assert str(exc) == "Custom error message"

    def test_is_exception(self):
        """VisionOpsError inherits from Exception."""
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(VisionOpsError, Exception)

    def test_message_attribute(self):
        """VisionOpsError stores the message as an attribute."""
        from backend.exceptions.base_exception import VisionOpsError

        exc = VisionOpsError("Test message")
        assert exc.message == "Test message"

    def test_raise_and_catch(self):
        """VisionOpsError can be raised and caught."""
        from backend.exceptions.base_exception import VisionOpsError

        with pytest.raises(VisionOpsError):
            raise VisionOpsError("Something went wrong")


# ---------------------------------------------------------------------------
# storage_exceptions
# ---------------------------------------------------------------------------


class TestStorageExceptions:
    """Tests for :mod:`backend.exceptions.storage_exceptions`."""

    def test_storage_error_default(self):
        """StorageError has a default message."""
        from backend.exceptions.storage_exceptions import StorageError

        exc = StorageError()
        assert str(exc) == "A storage error occurred"

    def test_storage_error_inheritance(self):
        """StorageError inherits from VisionOpsError."""
        from backend.exceptions.storage_exceptions import StorageError
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(StorageError, VisionOpsError)

    def test_csv_error_default(self):
        """CSVError has a default message."""
        from backend.exceptions.storage_exceptions import CSVError

        exc = CSVError()
        assert str(exc) == "CSV operation failed"

    def test_csv_error_inheritance(self):
        """CSVError inherits from StorageError."""
        from backend.exceptions.storage_exceptions import CSVError, StorageError

        assert issubclass(CSVError, StorageError)

    def test_json_error_default(self):
        """JSONError has a default message."""
        from backend.exceptions.storage_exceptions import JSONError

        exc = JSONError()
        assert str(exc) == "JSON operation failed"

    def test_json_error_inheritance(self):
        """JSONError inherits from StorageError."""
        from backend.exceptions.storage_exceptions import JSONError, StorageError

        assert issubclass(JSONError, StorageError)

    def test_file_operation_error_default(self):
        """FileOperationError has a default message."""
        from backend.exceptions.storage_exceptions import FileOperationError

        exc = FileOperationError()
        assert str(exc) == "File operation failed"

    def test_file_operation_error_with_path(self):
        """FileOperationError includes path in message when provided."""
        from backend.exceptions.storage_exceptions import FileOperationError

        exc = FileOperationError(path="/tmp/test.txt")
        msg = str(exc)
        assert "Path:" in msg
        assert "/tmp/test.txt" in msg

    def test_file_operation_error_without_path(self):
        """FileOperationError without path does not include path detail."""
        from backend.exceptions.storage_exceptions import FileOperationError

        exc = FileOperationError()
        assert "Path:" not in str(exc)

    def test_file_operation_error_attribute(self):
        """FileOperationError stores the path attribute."""
        from backend.exceptions.storage_exceptions import FileOperationError

        exc = FileOperationError(path="/data/file.csv")
        assert exc.path == "/data/file.csv"

    def test_file_operation_error_no_path_attribute(self):
        """FileOperationError without path has path as None."""
        from backend.exceptions.storage_exceptions import FileOperationError

        exc = FileOperationError()
        assert exc.path is None

    def test_file_operation_error_inheritance(self):
        """FileOperationError inherits from StorageError."""
        from backend.exceptions.storage_exceptions import FileOperationError, StorageError

        assert issubclass(FileOperationError, StorageError)


# ---------------------------------------------------------------------------
# validation_exceptions
# ---------------------------------------------------------------------------


class TestValidationExceptionsPackage:
    """Tests for :mod:`backend.exceptions.validation_exceptions`."""

    def test_all_exceptions_importable(self):
        """All validation exception types are importable."""
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

        assert ValidationError is not None
        assert FileValidationError is not None
        assert UUIDValidationError is not None
        assert EmailValidationError is not None
        assert NumericRangeError is not None
        assert RequiredFieldError is not None
        assert FilenameValidationError is not None
        assert ExtensionValidationError is not None

    def test_validation_error_superclass(self):
        """All validation exceptions inherit from ValidationError."""
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

        for exc in [
            FileValidationError,
            UUIDValidationError,
            EmailValidationError,
            NumericRangeError,
            RequiredFieldError,
            FilenameValidationError,
            ExtensionValidationError,
        ]:
            assert issubclass(exc, ValidationError)


# ---------------------------------------------------------------------------
# ai_exceptions
# ---------------------------------------------------------------------------


class TestAIExceptions:
    """Tests for :mod:`backend.exceptions.ai_exceptions`."""

    def test_ai_error_default(self):
        """AIError has no default message (inherits from VisionOpsError)."""
        from backend.exceptions.ai_exceptions import AIError

        exc = AIError()
        assert isinstance(str(exc), str)

    def test_ai_error_custom_message(self):
        """AIError accepts a custom message."""
        from backend.exceptions.ai_exceptions import AIError

        exc = AIError("AI inference failed")
        assert str(exc) == "AI inference failed"

    def test_ai_error_inheritance(self):
        """AIError inherits from VisionOpsError."""
        from backend.exceptions.ai_exceptions import AIError
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(AIError, VisionOpsError)

    def test_ai_error_raise_and_catch(self):
        """AIError can be raised and caught."""
        from backend.exceptions.ai_exceptions import AIError

        with pytest.raises(AIError):
            raise AIError("Model not loaded")


# ---------------------------------------------------------------------------
# analytics_exceptions
# ---------------------------------------------------------------------------


class TestAnalyticsExceptions:
    """Tests for :mod:`backend.exceptions.analytics_exceptions`."""

    def test_analytics_error_default(self):
        """AnalyticsError has no default message (inherits from VisionOpsError)."""
        from backend.exceptions.analytics_exceptions import AnalyticsError

        exc = AnalyticsError()
        assert isinstance(str(exc), str)

    def test_analytics_error_custom_message(self):
        """AnalyticsError accepts a custom message."""
        from backend.exceptions.analytics_exceptions import AnalyticsError

        exc = AnalyticsError("Aggregation failed")
        assert str(exc) == "Aggregation failed"

    def test_analytics_error_inheritance(self):
        """AnalyticsError inherits from VisionOpsError."""
        from backend.exceptions.analytics_exceptions import AnalyticsError
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(AnalyticsError, VisionOpsError)

    def test_analytics_error_raise_and_catch(self):
        """AnalyticsError can be raised and caught."""
        from backend.exceptions.analytics_exceptions import AnalyticsError

        with pytest.raises(AnalyticsError):
            raise AnalyticsError("Report generation failed")


# ---------------------------------------------------------------------------
# api_exceptions
# ---------------------------------------------------------------------------


class TestAPIExceptions:
    """Tests for :mod:`backend.exceptions.api_exceptions`."""

    def test_api_error_default(self):
        """APIError has no default message."""
        from backend.exceptions.api_exceptions import APIError

        exc = APIError()
        assert isinstance(str(exc), str)

    def test_api_error_custom_message(self):
        """APIError accepts a custom message."""
        from backend.exceptions.api_exceptions import APIError

        exc = APIError("Bad request")
        assert str(exc) == "Bad request"

    def test_api_error_inheritance(self):
        """APIError inherits from VisionOpsError."""
        from backend.exceptions.api_exceptions import APIError
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(APIError, VisionOpsError)

    def test_authentication_error_default(self):
        """AuthenticationError has no default message."""
        from backend.exceptions.api_exceptions import AuthenticationError

        exc = AuthenticationError()
        assert isinstance(str(exc), str)

    def test_authentication_error_custom_message(self):
        """AuthenticationError accepts a custom message."""
        from backend.exceptions.api_exceptions import AuthenticationError

        exc = AuthenticationError("Invalid token")
        assert str(exc) == "Invalid token"

    def test_authentication_error_inheritance(self):
        """AuthenticationError inherits from APIError."""
        from backend.exceptions.api_exceptions import AuthenticationError, APIError

        assert issubclass(AuthenticationError, APIError)

    def test_authorization_error_default(self):
        """AuthorizationError has no default message."""
        from backend.exceptions.api_exceptions import AuthorizationError

        exc = AuthorizationError()
        assert isinstance(str(exc), str)

    def test_authorization_error_inheritance(self):
        """AuthorizationError inherits from APIError."""
        from backend.exceptions.api_exceptions import AuthorizationError, APIError

        assert issubclass(AuthorizationError, APIError)

    def test_bad_request_error_default(self):
        """BadRequestError has no default message."""
        from backend.exceptions.api_exceptions import BadRequestError

        exc = BadRequestError()
        assert isinstance(str(exc), str)

    def test_bad_request_error_inheritance(self):
        """BadRequestError inherits from APIError."""
        from backend.exceptions.api_exceptions import BadRequestError, APIError

        assert issubclass(BadRequestError, APIError)

    def test_resource_not_found_error_default(self):
        """ResourceNotFoundError has no default message."""
        from backend.exceptions.api_exceptions import ResourceNotFoundError

        exc = ResourceNotFoundError()
        assert isinstance(str(exc), str)

    def test_resource_not_found_error_inheritance(self):
        """ResourceNotFoundError inherits from APIError."""
        from backend.exceptions.api_exceptions import (
            ResourceNotFoundError,
            APIError,
        )

        assert issubclass(ResourceNotFoundError, APIError)

    def test_conflict_error_default(self):
        """ConflictError has no default message."""
        from backend.exceptions.api_exceptions import ConflictError

        exc = ConflictError()
        assert isinstance(str(exc), str)

    def test_conflict_error_inheritance(self):
        """ConflictError inherits from APIError."""
        from backend.exceptions.api_exceptions import ConflictError, APIError

        assert issubclass(ConflictError, APIError)

    def test_rate_limit_error_default(self):
        """RateLimitError has no default message."""
        from backend.exceptions.api_exceptions import RateLimitError

        exc = RateLimitError()
        assert isinstance(str(exc), str)

    def test_rate_limit_error_inheritance(self):
        """RateLimitError inherits from APIError."""
        from backend.exceptions.api_exceptions import RateLimitError, APIError

        assert issubclass(RateLimitError, APIError)

    def test_service_unavailable_error_default(self):
        """ServiceUnavailableError has no default message."""
        from backend.exceptions.api_exceptions import ServiceUnavailableError

        exc = ServiceUnavailableError()
        assert isinstance(str(exc), str)

    def test_service_unavailable_error_inheritance(self):
        """ServiceUnavailableError inherits from APIError."""
        from backend.exceptions.api_exceptions import (
            ServiceUnavailableError,
            APIError,
        )

        assert issubclass(ServiceUnavailableError, APIError)

    def test_internal_api_error_default(self):
        """InternalAPIError has no default message."""
        from backend.exceptions.api_exceptions import InternalAPIError

        exc = InternalAPIError()
        assert isinstance(str(exc), str)

    def test_internal_api_error_inheritance(self):
        """InternalAPIError inherits from APIError."""
        from backend.exceptions.api_exceptions import InternalAPIError, APIError

        assert issubclass(InternalAPIError, APIError)


# ---------------------------------------------------------------------------
# Package-level __init__ exports
# ---------------------------------------------------------------------------


class TestExceptionsPackageInit:
    """Tests for :mod:`backend.exceptions.__init__` exports."""

    def test_all_exports_accessible(self):
        """All expected exception names are exported from the package."""
        import backend.exceptions

        expected = [
            "VisionOpsError",
            "CSVError",
            "JSONError",
            "FileOperationError",
            "StorageError",
            "ValidationError",
            "FileValidationError",
            "UUIDValidationError",
            "EmailValidationError",
            "NumericRangeError",
            "RequiredFieldError",
            "FilenameValidationError",
            "ExtensionValidationError",
            "AIError",
            "AnalyticsError",
            "APIError",
            "AuthenticationError",
        ]
        for name in expected:
            assert hasattr(backend.exceptions, name), f"Missing export: {name}"

    def test_all_exports_in_all(self):
        """All expected names appear in __all__."""
        from backend.exceptions import __all__

        expected = [
            "VisionOpsError",
            "CSVError",
            "JSONError",
            "FileOperationError",
            "StorageError",
            "ValidationError",
            "FileValidationError",
            "UUIDValidationError",
            "EmailValidationError",
            "NumericRangeError",
            "RequiredFieldError",
            "FilenameValidationError",
            "ExtensionValidationError",
            "AIError",
            "AnalyticsError",
            "APIError",
            "AuthenticationError",
        ]
        for name in expected:
            assert name in __all__, f"Missing from __all__: {name}"

    def test_unauthorized_name_not_exported(self):
        """AuthorizationError is not exported from package __init__."""
        import backend.exceptions

        assert not hasattr(backend.exceptions, "AuthorizationError")
        assert not hasattr(backend.exceptions, "BadRequestError")
        assert not hasattr(backend.exceptions, "ResourceNotFoundError")
        assert not hasattr(backend.exceptions, "ConflictError")
        assert not hasattr(backend.exceptions, "RateLimitError")
        assert not hasattr(backend.exceptions, "ServiceUnavailableError")
        assert not hasattr(backend.exceptions, "InternalAPIError")

