"""VisionOps AI — Unit tests for the ``services`` package.

Tests all service classes:
- AuthService
- VideoProcessingService
- AnalysisService
- AnalyticsService
- DashboardService
- ReportService
- NotificationService
- SettingsService

Covers success paths, failure modes, and edge cases.
All external dependencies are mocked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.exceptions import (
    AuthenticationError,
    RequiredFieldError,
    ValidationError,
    StorageError,
    FileValidationError,
    AnalyticsError,
)


# ===========================================================================
# AuthService Tests
# ===========================================================================


class TestAuthService:
    """Tests for :class:`backend.services.auth_service.AuthService`."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """AuthService can be instantiated with injected storage."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        assert service is not None

    def test_initialisation_default_storage(self):
        """AuthService creates a default StorageService when none injected."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        assert service is not None
        assert service._storage is not None

    # --- authenticate_user ---

    def test_authenticate_user_success(self, mock_storage_service: MagicMock):
        """authenticate_user returns token data for valid credentials."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "username": "admin", "password": "admin123",
             "role": "admin"},
        ]
        service = AuthService(storage=mock_storage_service)

        result = service.authenticate_user(username="admin", password="admin123")
        assert result["access_token"] is not None
        assert result["token_type"] == "bearer"
        assert result["username"] == "admin"
        assert result["role"] == "admin"

    def test_authenticate_user_empty_username_raises(self, mock_storage_service: MagicMock):
        """authenticate_user raises RequiredFieldError for empty username."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Username"):
            service.authenticate_user(username="", password="admin123")

    def test_authenticate_user_empty_password_raises(self, mock_storage_service: MagicMock):
        """authenticate_user raises RequiredFieldError for empty password."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Password"):
            service.authenticate_user(username="admin", password="")

    def test_authenticate_user_invalid_credentials(self, mock_storage_service: MagicMock):
        """authenticate_user raises AuthenticationError for invalid credentials."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "username": "admin", "password": "admin123",
             "role": "admin"},
        ]
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            service.authenticate_user(username="admin", password="wrongpass")

    def test_authenticate_user_user_not_found(self, mock_storage_service: MagicMock):
        """authenticate_user raises AuthenticationError when user not found."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "username": "existing", "password": "pass",
             "role": "operator"},
        ]
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            service.authenticate_user(username="unknown_user", password="pass")

    def test_authenticate_user_storage_fallback(self, mock_storage_service: MagicMock):
        """authenticate_user falls back to default users when storage fails."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.side_effect = StorageError("Store missing")
        service = AuthService(storage=mock_storage_service)

        # Should fall back to default admin user
        result = service.authenticate_user(username="admin", password="admin123")
        assert result["username"] == "admin"

    # --- create_access_token ---

    def test_create_access_token_success(self, mock_storage_service: MagicMock):
        """create_access_token returns a valid token string."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_access_token_empty_user_id_raises(self, mock_storage_service: MagicMock):
        """create_access_token raises RequiredFieldError for empty user_id."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="user_id"):
            service.create_access_token(user_id="", username="admin")

    def test_create_access_token_empty_username_raises(self, mock_storage_service: MagicMock):
        """create_access_token raises RequiredFieldError for empty username."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="username"):
            service.create_access_token(user_id="u1", username="")

    # --- verify_token ---

    def test_verify_token_success(self, mock_storage_service: MagicMock):
        """verify_token returns a payload dict for a valid token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        payload = service.verify_token(token)
        assert isinstance(payload, dict)
        assert "user_id" in payload

    def test_verify_token_empty_raises(self, mock_storage_service: MagicMock):
        """verify_token raises RequiredFieldError for empty token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Token"):
            service.verify_token("")

    def test_verify_token_invalid_format(self, mock_storage_service: MagicMock):
        """verify_token raises AuthenticationError for malformed token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(AuthenticationError, match="Invalid token format"):
            service.verify_token("invalid-token")

    # --- refresh_token ---

    def test_refresh_token_success(self, mock_storage_service: MagicMock):
        """refresh_token returns a new token for a valid token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        result = service.refresh_token(token)
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] > 0

    def test_refresh_token_empty_raises(self, mock_storage_service: MagicMock):
        """refresh_token raises RequiredFieldError for empty token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Token"):
            service.refresh_token("")

    # --- change_password ---

    def test_change_password_success(self, mock_storage_service: MagicMock):
        """change_password updates password for valid credentials."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "username": "admin", "password": "oldpass",
             "role": "admin"},
        ]
        service = AuthService(storage=mock_storage_service)

        result = service.change_password(
            user_id="u1", current_password="oldpass", new_password="newpass123",
        )
        assert result["message"] == "Password changed successfully."

    def test_change_password_invalid_current(self, mock_storage_service: MagicMock):
        """change_password raises AuthenticationError for wrong current password."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "username": "admin", "password": "oldpass",
             "role": "admin"},
        ]
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(AuthenticationError, match="Current password is incorrect"):
            service.change_password(
                user_id="u1", current_password="wrongpass", new_password="newpass123",
            )

    def test_change_password_empty_fields_raises(self, mock_storage_service: MagicMock):
        """change_password raises RequiredFieldError for empty fields."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)

        with pytest.raises(RequiredFieldError, match="user_id"):
            service.change_password(user_id="", current_password="old", new_password="new")

        with pytest.raises(RequiredFieldError, match="current_password"):
            service.change_password(user_id="u1", current_password="", new_password="new")

        with pytest.raises(RequiredFieldError, match="new_password"):
            service.change_password(user_id="u1", current_password="old", new_password="")


# ===========================================================================
# VideoProcessingService Tests
# ===========================================================================


class TestVideoProcessingService:
    """Tests for :class:`backend.services.video_service.VideoProcessingService`."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """VideoProcessingService can be instantiated with injected storage."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        assert service is not None

    # --- initiate_upload ---

    def test_initiate_upload_success(self, mock_storage_service: MagicMock):
        """initiate_upload returns video metadata for valid input."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.append_csv_store.return_value = Path("/tmp/videos.csv")
        service = VideoProcessingService(storage=mock_storage_service)

        result = service.initiate_upload(
            filename="test_video.mp4",
            file_size=1024,
            content_type="video/mp4",
        )
        assert result["video_id"].startswith("vid_")
        assert result["filename"] == "test_video.mp4"
        assert result["file_size"] == 1024
        assert result["status"] == "uploaded"

    def test_initiate_upload_empty_filename_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for empty filename."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Filename must not be empty"):
            service.initiate_upload(filename="", file_size=1024)

    def test_initiate_upload_invalid_extension(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for disallowed extension."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Extension"):
            service.initiate_upload(filename="test.exe", file_size=1024)

    def test_initiate_upload_zero_size_raises(self, mock_storage_service: MagicMock):
        """initiate_upload raises ValidationError for zero file size."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="positive"):
            service.initiate_upload(filename="test.mp4", file_size=0)

    def test_initiate_upload_storage_error(self, mock_storage_service: MagicMock):
        """initiate_upload propagates storage errors."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.append_csv_store.side_effect = StorageError("Write failed")
        service = VideoProcessingService(storage=mock_storage_service)

        with pytest.raises(StorageError, match="Failed to initiate upload"):
            service.initiate_upload(filename="test.mp4", file_size=1024)

    # --- process_video ---

    @pytest.mark.asyncio
    async def test_process_video_success(self, mock_storage_service: MagicMock):
        """process_video returns processing result for valid video."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "status": "uploaded"},
        ]
        service = VideoProcessingService(storage=mock_storage_service)

        result = await service.process_video(video_id="vid_001")
        assert result["video_id"] == "vid_001"
        assert result["status"] == "processing"

    @pytest.mark.asyncio
    async def test_process_video_invalid_id_raises(self, mock_storage_service: MagicMock):
        """process_video raises ValidationError for invalid video_id prefix."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid video_id"):
            await service.process_video(video_id="invalid_id")

    @pytest.mark.asyncio
    async def test_process_video_not_found(self, mock_storage_service: MagicMock):
        """process_video raises FileValidationError for missing video."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = []
        service = VideoProcessingService(storage=mock_storage_service)

        with pytest.raises(FileValidationError, match="Video not found"):
            await service.process_video(video_id="vid_nonexistent")

    @pytest.mark.asyncio
    async def test_process_video_already_processing(self, mock_storage_service: MagicMock):
        """process_video raises ValidationError if already processing."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "status": "processing"},
        ]
        service = VideoProcessingService(storage=mock_storage_service)

        with pytest.raises(ValidationError, match="already being processed"):
            await service.process_video(video_id="vid_001")

    # --- mark_completed ---

    def test_mark_completed(self, mock_storage_service: MagicMock):
        """mark_completed updates video status to completed."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.csv_manager.update_rows.return_value = 1
        service = VideoProcessingService(storage=mock_storage_service)

        with patch.object(service, "_update_video_record", return_value={"status": "completed"}):
            result = service.mark_completed(video_id="vid_001")
            assert result["status"] == "completed"

    # --- mark_failed ---

    def test_mark_failed(self, mock_storage_service: MagicMock):
        """mark_failed updates video status to failed."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)

        with patch.object(service, "_update_video_record", return_value={"status": "failed"}):
            result = service.mark_failed(video_id="vid_001", error_message="Processing error")
            assert result["status"] == "failed"

    # --- get_video_metadata ---

    def test_get_video_metadata_success(self, mock_storage_service: MagicMock):
        """get_video_metadata returns video record for valid ID."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "filename": "test.mp4", "status": "completed"},
        ]
        service = VideoProcessingService(storage=mock_storage_service)

        result = service.get_video_metadata(video_id="vid_001")
        assert result["video_id"] == "vid_001"
        assert result["filename"] == "test.mp4"

    def test_get_video_metadata_not_found(self, mock_storage_service: MagicMock):
        """get_video_metadata raises FileValidationError for missing video."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = []
        service = VideoProcessingService(storage=mock_storage_service)

        with pytest.raises(FileValidationError, match="Video not found"):
            service.get_video_metadata(video_id="vid_nonexistent")

    def test_get_video_metadata_empty_id_raises(self, mock_storage_service: MagicMock):
        """get_video_metadata raises ValidationError for empty video_id."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            service.get_video_metadata(video_id="")

    # --- list_videos ---

    def test_list_videos(self, mock_storage_service: MagicMock):
        """list_videos returns filtered and paginated video list."""
        from backend.services.video_service import VideoProcessingService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "status": "completed"},
            {"video_id": "vid_002", "status": "processing"},
            {"video_id": "vid_003", "status": "completed"},
        ]
        service = VideoProcessingService(storage=mock_storage_service)

        # Filter by status
        result = service.list_videos(status="completed")
        assert len(result) == 2

        # Pagination
        result = service.list_videos(limit=1, offset=0)
        assert len(result) == 1

    def test_list_videos_invalid_status(self, mock_storage_service: MagicMock):
        """list_videos raises ValidationError for invalid status."""
        from backend.services.video_service import VideoProcessingService

        service = VideoProcessingService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid status"):
            service.list_videos(status="invalid_status")


# ===========================================================================
# AnalysisService Tests
# ===========================================================================


class TestAnalysisService:
    """Tests for :class:`backend.services.analysis_service.AnalysisService`."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """AnalysisService can be instantiated with injected storage."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        assert service is not None

    # --- run_detection ---

    def test_run_detection_success(
        self,
        mock_storage_service: MagicMock,
        sample_raw_detections: list[dict[str, Any]],
    ):
        """run_detection validates, filters, enriches, and persists detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.run_detection(
            video_id="vid_001",
            detections=sample_raw_detections,
            source_frame=1,
        )
        assert len(result) == 3  # 4 input - 1 low confidence (0.45) removed
        assert all(d["detection_id"].startswith("det_") for d in result)
        assert all(d["video_id"] == "vid_001" for d in result)
        mock_storage_service.append_csv_store.assert_called_once()

    def test_run_detection_empty_video_id_raises(
        self,
        mock_storage_service: MagicMock,
    ):
        """run_detection raises ValidationError for empty video_id."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            service.run_detection(video_id="", detections=[])

    def test_run_detection_invalid_detections_type(
        self,
        mock_storage_service: MagicMock,
    ):
        """run_detection raises ValidationError for non-list detections."""
        from backend.services.analysis_service import AnalysisService

        service = Analys
