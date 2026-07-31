"""VisionOps AI — Unit tests for the ``exceptions.validation_exceptions`` module.

Tests cover all validation exception classes defined in the exceptions package.
"""

from __future__ import annotations

import pytest


class TestValidationExceptions:
    """Tests for :mod:`backend.exceptions.validation_exceptions`."""

    # ------------------------------------------------------------------
    # ValidationError
    # ------------------------------------------------------------------

    def test_validation_error_default_message(self):
        """ValidationError has a sensible default message."""
        from backend.exceptions.validation_exceptions import ValidationError

        exc = ValidationError()
        assert str(exc) == "Validation failed"

    def test_validation_error_custom_message(self):
        """ValidationError accepts a custom message."""
        from backend.exceptions.validation_exceptions import ValidationError

        exc = ValidationError("Custom error")
        assert str(exc) == "Custom error"

    def test_validation_error_is_visionops_error(self):
        """ValidationError inherits from VisionOpsError."""
        from backend.exceptions.validation_exceptions import ValidationError
        from backend.exceptions.base_exception import VisionOpsError

        assert issubclass(ValidationError, VisionOpsError)

    # ------------------------------------------------------------------
    # FileValidationError
    # ------------------------------------------------------------------

    def test_file_validation_error_default(self):
        """FileValidationError has a sensible default."""
        from backend.exceptions.validation_exceptions import FileValidationError

        exc = FileValidationError()
        assert str(exc) == "File validation failed"

    def test_file_validation_error_is_validation_error(self):
        """FileValidationError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            FileValidationError,
            ValidationError,
        )

        assert issubclass(FileValidationError, ValidationError)

    # ------------------------------------------------------------------
    # UUIDValidationError
    # ------------------------------------------------------------------

    def test_uuid_validation_error_default(self):
        """UUIDValidationError has a sensible default."""
        from backend.exceptions.validation_exceptions import UUIDValidationError

        exc = UUIDValidationError()
        assert str(exc) == "UUID validation failed"

    def test_uuid_validation_error_inheritance(self):
        """UUIDValidationError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            UUIDValidationError,
            ValidationError,
        )

        assert issubclass(UUIDValidationError, ValidationError)

    # ------------------------------------------------------------------
    # EmailValidationError
    # ------------------------------------------------------------------

    def test_email_validation_error_default(self):
        """EmailValidationError has a sensible default."""
        from backend.exceptions.validation_exceptions import EmailValidationError

        exc = EmailValidationError()
        assert str(exc) == "Email validation failed"

    def test_email_validation_error_inheritance(self):
        """EmailValidationError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            EmailValidationError,
            ValidationError,
        )

        assert issubclass(EmailValidationError, ValidationError)

    # ------------------------------------------------------------------
    # NumericRangeError
    # ------------------------------------------------------------------

    def test_numeric_range_error_default(self):
        """NumericRangeError has a sensible default."""
        from backend.exceptions.validation_exceptions import NumericRangeError

        exc = NumericRangeError()
        assert str(exc) == "Numeric value out of range"

    def test_numeric_range_error_with_value(self):
        """NumericRangeError includes value in message."""
        from backend.exceptions.validation_exceptions import NumericRangeError

        exc = NumericRangeError(value=42.5)
        assert "value=42.5" in str(exc)

    def test_numeric_range_error_with_bounds(self):
        """NumericRangeError includes bounds in message."""
        from backend.exceptions.validation_exceptions import NumericRangeError

        exc = NumericRangeError(value=5, min_val=0, max_val=10)
        msg = str(exc)
        assert "value=5" in msg
        assert "min=0" in msg
        assert "max=10" in msg

    def test_numeric_range_error_attributes(self):
        """NumericRangeError stores value, min_val, max_val."""
        from backend.exceptions.validation_exceptions import NumericRangeError

        exc = NumericRangeError(value=5, min_val=0, max_val=10)
        assert exc.value == 5
        assert exc.min_val == 0
        assert exc.max_val == 10

    def test_numeric_range_error_inheritance(self):
        """NumericRangeError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            NumericRangeError,
            ValidationError,
        )

        assert issubclass(NumericRangeError, ValidationError)

    # ------------------------------------------------------------------
    # RequiredFieldError
    # ------------------------------------------------------------------

    def test_required_field_error_default(self):
        """RequiredFieldError has a sensible default."""
        from backend.exceptions.validation_exceptions import RequiredFieldError

        exc = RequiredFieldError()
        assert str(exc) == "Required field missing"

    def test_required_field_error_with_field(self):
        """RequiredFieldError includes field name in message."""
        from backend.exceptions.validation_exceptions import RequiredFieldError

        exc = RequiredFieldError(field="email")
        assert "email" in str(exc)
        assert "missing field" in str(exc)

    def test_required_field_error_attribute(self):
        """RequiredFieldError stores the field name."""
        from backend.exceptions.validation_exceptions import RequiredFieldError

        exc = RequiredFieldError(field="email")
        assert exc.field == "email"

    def test_required_field_error_no_field(self):
        """RequiredFieldError without field is None."""
        from backend.exceptions.validation_exceptions import RequiredFieldError

        exc = RequiredFieldError()
        assert exc.field is None

    def test_required_field_error_inheritance(self):
        """RequiredFieldError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            RequiredFieldError,
            ValidationError,
        )

        assert issubclass(RequiredFieldError, ValidationError)

    # ------------------------------------------------------------------
    # FilenameValidationError
    # ------------------------------------------------------------------

    def test_filename_validation_error_default(self):
        """FilenameValidationError has a sensible default."""
        from backend.exceptions.validation_exceptions import FilenameValidationError

        exc = FilenameValidationError()
        assert str(exc) == "Filename validation failed"

    def test_filename_validation_error_inheritance(self):
        """FilenameValidationError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            FilenameValidationError,
            ValidationError,
        )

        assert issubclass(FilenameValidationError, ValidationError)

    # ------------------------------------------------------------------
    # ExtensionValidationError
    # ------------------------------------------------------------------

    def test_extension_validation_error_default(self):
        """ExtensionValidationError has a sensible default."""
        from backend.exceptions.validation_exceptions import ExtensionValidationError

        exc = ExtensionValidationError()
        assert str(exc) == "Extension validation failed"

    def test_extension_validation_error_inheritance(self):
        """ExtensionValidationError inherits from ValidationError."""
        from backend.exceptions.validation_exceptions import (
            ExtensionValidationError,
            ValidationError,
        )

        assert issubclass(ExtensionValidationError, ValidationError)

    # ------------------------------------------------------------------
    # Cross-reference: utils.validation integration
    # ------------------------------------------------------------------

    def test_validation_utils_importable(self):
        """The validation utils module can be imported."""
        import backend.utils.validation  # noqa: F401

    def test_validation_exceptions_importable(self):
        """All validation exception types are importable from the package."""
        from backend.exceptions import (
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

