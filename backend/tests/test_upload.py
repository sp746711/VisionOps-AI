"""VisionOps AI — Unit tests for the upload functionality.

Tests:
- VideoProcessingService upload initiation
- File validation (extension, size, path traversal)
- Metadata creation, storage integration, cleanup
- Edge cases: large files, duplicate files, invalid extensions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.exceptions import (
    FileValidationError,
    StorageError,
    ValidationError,
)


# ===========================================================================
# Upload API Module Imports
# ===========================================================================


class TestUploadImports:
    """Verify upload-related modules are importable."""

    def test_videos_api_module(self):
        """The videos API module can be imported."""
        import backend.api.videos  # noqa: F401

    def test_video_schemas_module(self):
        """The video schema module can be imported."""
        import backend.schemas.video  # noqa: F401

    def test_video_service_module(self):
        """The video_service module can be imported."""
        import backend.services.video_service  # noqa: F401

    def test_video_model_module(self):
        """The video model module can be imported."""
        import backend.models.video  # noqa: F401

    def test_file_manager_module(self):
        """The file_manager module can be imported."""
        import backend.storage.file_manager  # noqa: F401

    def test_storage_service_module(self):
        """The storage_service module can be imported."""
        import backend.storage.storage_service  # noqa: F401


# ===========================================================================
# Upload Schemas
# ===========================================================================


class TestUploadSchemas:
    """Tests for upload-related Pydantic schemas."""

    def test_upload_request_schema(self):
        """UploadRequest schema exists."""
        from backend.schemas.video import UploadRequest
        assert UploadRequest is not None

    def test_video_response_schema(self):
        """VideoResponse schema exists."""
        from backend.schemas.video import VideoResponse
        assert VideoResponse is not None


# ===========================================================================
# VideoProcessingService — Upload Initiation
# ===========================================================================


class TestVideoProcessingServiceUpload:
    """Tests for VideoProcessingService upload initiation."""

    def test_initiate_upload_success(self, mock_storage_service: MagicMock):
        """initiate_upload returns video metadata for valid input."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        result = service.initiate_upload(
            filename="test_video.mp4", file_size=1024, content_type="video/mp4",
        )
        assert result["video_id"].startswith("vid_")
        assert result["filename"] == "test_video.mp4"
        assert result["status"] == "uploaded"

    def test_initiate_upload_creates_unique_id(self, mock_storage_service: MagicMock):
        """initiate_upload generates unique video IDs."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        result1 = service.initiate_upload("vid1.mp4", 100)
        result2 = service.initiate_upload("vid2.mp4", 200)
        assert result1["video_id"] != result2["video_id"]

    def test_initiate_upload_persists_metadata(self, mock_storage_service: MagicMock):
        """initiate_upload persists video metadata to storage."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        service.initiate_upload("test.mp4", 1024)
        mock_storage_service.append_csv_store.assert_called_once()

    def test_initiate_upload_storage_error(self, mock_storage_service: MagicMock):
        """initiate_upload propagates storage errors."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.append_csv_store.side_effect = StorageError("Write failed")
        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(StorageError, match="Failed to initiate upload"):
            service.initiate_upload(filename="test.mp4", file_size=1024)


# ===========================================================================
# VideoProcessingService — File Validation
# ===========================================================================


class TestVideoProcessingServiceFileValidation:
    """Tests for VideoProcessingService file validation."""

    def test_empty_filename_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for empty filename."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Filename must not be empty"):
            service.initiate_upload(filename="", file_size=1024)

    def test_invalid_extension_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for disallowed extension."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Extension"):
            service.initiate_upload(filename="test.exe", file_size=1024)

    def test_no_extension_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for file with no extension."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="no extension"):
            service.initiate_upload(filename="test", file_size=1024)

    def test_zero_file_size_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for zero file size."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="positive"):
            service.initiate_upload(filename="test.mp4", file_size=0)

    def test_negative_file_size_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for negative file size."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="positive"):
            service.initiate_upload(filename="test.mp4", file_size=-100)

    def test_path_separator_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for filename with path separator."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="path separator"):
            service.initiate_upload(filename="../test.mp4", file_size=1024)

    def test_unicode_filename(self, mock_storage_service: MagicMock):
        """initiate_upload accepts unicode filenames."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        result = service.initiate_upload(filename="\u89c6\u9891_test.mp4", file_size=1024)
        assert result["filename"] == "\u89c6\u9891_test.mp4"


# ===========================================================================
# VideoProcessingService — Duplicate & Cleanup
# ===========================================================================


class TestVideoProcessingServiceDuplicateAndCleanup:
    """Tests for duplicate detection and cleanup."""

    def test_duplicate_filename_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for duplicate filename."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "filename": "existing.mp4"},
        ]
        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="already exists"):
            service.initiate_upload(filename="existing.mp4", file_size=1024)

    def test_cleanup_upload(self, mock_storage_service: MagicMock):
        """cleanup_upload removes a failed upload record."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.csv_manager.update_rows.return_value = 1
        service = VideoProcessingService(storage=mock_storage_service)
        result = service.cleanup_upload(video_id="vid_001")
        assert result["video_id"] == "vid_001"
        assert result["status"] == "cleaned"
