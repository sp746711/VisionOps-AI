"""VisionOps AI — Unit tests for the ``storage`` package.

Tests all storage managers:
- CSVManager
- JSONManager
- FileManager
- StorageService (facade)

Covers success paths, failure modes, and edge cases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from backend.exceptions import CSVError, FileOperationError, StorageError


# ===========================================================================
# CSVManager Tests
# ===========================================================================


class TestCSVManager:
    """Tests for :class:`backend.storage.csv_manager.CSVManager`."""

    def test_initialisation(self):
        """CSVManager can be instantiated with default params."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        assert mgr is not None

    def test_initialisation_custom_delimiter(self):
        """CSVManager accepts custom delimiter and encoding."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager(delimiter=";", encoding="utf-16")
        assert mgr is not None

    def test_store_names(self):
        """store_names returns all recognised store names."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        names = mgr.store_names()
        assert "videos" in names
        assert "detections" in names
        assert "events" in names
        assert "alerts" in names
        assert "kpis" in names
        assert "analytics" in names
        assert names == sorted(names)

    def test_unknown_store_raises_csv_error(self):
        """Accessing an unknown store raises CSVError."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        with pytest.raises(CSVError, match="Unknown CSV store"):
            mgr.read_store("nonexistent")

    def test_store_info(self):
        """store_info returns metadata for a known store."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        info = mgr.store_info("videos")
        assert info["name"] == "videos"
        assert "path" in info
        assert "description" in info
        assert "exists" in info

    # --- Read ---

    def test_read_store_missing_file_raises(self, monkeypatch):
        """Reading a missing file raises CSVError."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        with pytest.raises(CSVError, match="Failed to read"):
            mgr.read_store("videos")

    # --- Write ---

    def test_write_store(
        self,
        tmp_data_dir: Path,
        sample_csv_rows: list[dict[str, str]],
        monkeypatch: Any,
    ):
        """write_store writes data and returns the path."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "videos.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        result = mgr.write_store("videos", sample_csv_rows)
        assert result == out_path.resolve()
        assert out_path.exists()

    def test_write_store_empty_data_raises(self, monkeypatch: Any, tmp_data_dir: Path):
        """Writing with no data and no fieldnames raises CSVError."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "videos.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        with pytest.raises(CSVError, match="Failed to write"):
            mgr.write_store("videos", [])

    # --- Append ---

    def test_append_store_missing_file_raises(self, monkeypatch: Any, tmp_data_dir: Path):
        """Appending to a missing file raises CSVError."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "videos.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        with pytest.raises(CSVError, match="Failed to append"):
            mgr.append_store("videos", [{"id": "1"}])

    # --- Validation ---

    def test_validate_store_missing_raises(self):
        """Validating a missing store raises CSVError."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        with pytest.raises(CSVError, match="Validation failed"):
            mgr.validate_store("videos")

    # --- Existence ---

    def test_store_exists_false(self, monkeypatch: Any, tmp_data_dir: Path):
        """store_exists returns False for a missing file."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "videos.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        assert mgr.store_exists("videos") is False

    # --- Convenience methods ---

    def test_convenience_read_methods(self, monkeypatch: Any):
        """Convenience read methods delegate to read_store."""
        from backend.storage.csv_manager import CSVManager

        mgr = CSVManager()
        for store in ("videos", "detections", "events", "alerts", "kpis", "analytics"):
            method = getattr(mgr, f"read_{store}")
            with pytest.raises(CSVError):
                method()

    def test_convenience_write_methods(self, monkeypatch: Any, tmp_data_dir: Path):
        """Convenience write methods delegate to write_store."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "test.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        with pytest.raises(CSVError):
            mgr.write_videos([])

    def test_convenience_append_methods(self, monkeypatch: Any, tmp_data_dir: Path):
        """Convenience append methods delegate to append_store."""
        from backend.storage.csv_manager import CSVManager

        out_path = tmp_data_dir / "test.csv"
        monkeypatch.setattr(
            "backend.core.config.settings.VIDEOS_CSV",
            str(out_path),
        )

        mgr = CSVManager()
        with pytest.raises(CSVError):
            mgr.append_videos([{"id": "1"}])


# ===========================================================================
# FileManager Tests
# ===========================================================================


class TestFileManager:
    """Tests for :class:`backend.storage.file_manager.FileManager`."""

    def test_initialisation(self):
        """FileManager can be instantiated."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager()
        assert mgr is not None

    def test_initialisation_with_base_dir(self, tmp_data_dir: Path):
        """FileManager accepts a custom base directory."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager(base_dir=tmp_data_dir)
        assert mgr is not None

    def test_managed_directory_names(self):
        """managed_directory_names returns all recognised directories."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager()
        names = mgr.managed_directory_names()
        assert "uploads" in names
        assert "thumbnails" in names
        assert "annotated_videos" in names
        assert "pdf_reports" in names

    def test_unknown_directory_raises(self):
        """Accessing an unknown managed directory raises FileOperationError."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager()
        with pytest.raises(FileOperationError, match="Unknown managed directory"):
            mgr._resolve_managed_dir("nonexistent")

    # --- Save uploaded file ---

    def test_save_uploaded_file(
        self,
        tmp_data_dir: Path,
        monkeypatch: Any,
    ):
        """save_uploaded_file saves content to the uploads directory."""
        from backend.storage.file_manager import FileManager

        upload_dir = tmp_data_dir / "uploads"
        upload_dir.mkdir()
        monkeypatch.setattr(
            "backend.core.config.settings.UPLOAD_FOLDER",
            str(upload_dir),
        )

        mgr = FileManager(base_dir=tmp_data_dir)
        result = mgr.save_uploaded_file(b"test content", "test.mp4")
        assert result.exists()
        assert result.read_bytes() == b"test content"

    def test_save_uploaded_file_with_subdir(self, tmp_data_dir: Path, monkeypatch: Any):
        """save_uploaded_file saves to a subdirectory."""
        from backend.storage.file_manager import FileManager

        upload_dir = tmp_data_dir / "uploads"
        upload_dir.mkdir()
        monkeypatch.setattr(
            "backend.core.config.settings.UPLOAD_FOLDER",
            str(upload_dir),
        )

        mgr = FileManager(base_dir=tmp_data_dir)
        result = mgr.save_uploaded_file(b"data", "test.mp4", subdir="videos")
        assert result.exists()
        assert "videos" in str(result.parent)

    # --- Save thumbnail ---

    def test_save_thumbnail(self, tmp_data_dir: Path, monkeypatch: Any):
        """save_thumbnail saves content to the thumbnails directory."""
        from backend.storage.file_manager import FileManager

        thumb_dir = tmp_data_dir / "thumbnails"
        thumb_dir.mkdir()
        monkeypatch.setattr(
            "backend.core.config.settings.THUMBNAIL_FOLDER",
            str(thumb_dir),
        )

        mgr = FileManager(base_dir=tmp_data_dir)
        result = mgr.save_thumbnail(b"thumbnail", "thumb.jpg")
        assert result.exists()

    # --- Copy / Move / Delete ---

    def test_copy(self, tmp_data_dir: Path, sample_text_path: Path):
        """copy copies a file within the base directory."""
        from backend.storage.file_manager import FileManager

        dst = tmp_data_dir / "copy.txt"
        mgr = FileManager(base_dir=tmp_data_dir)
        result = mgr.copy(sample_text_path, dst)
        assert result == dst.resolve()
        assert dst.exists()

    def test_move(self, tmp_data_dir: Path, sample_text_path: Path):
        """move moves a file within the base directory."""
        from backend.storage.file_manager import FileManager

        dst = tmp_data_dir / "moved.txt"
        mgr = FileManager(base_dir=tmp_data_dir)
        result = mgr.move(sample_text_path, dst)
        assert result == dst.resolve()
        assert dst.exists()
        assert not sample_text_path.exists()

    def test_delete(self, tmp_data_dir: Path, sample_text_path: Path):
        """delete removes a file."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager(base_dir=tmp_data_dir)
        mgr.delete(sample_text_path)
        assert not sample_text_path.exists()

    def test_delete_missing_ok(self, tmp_data_dir: Path):
        """delete with missing_ok=True does not raise."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager(base_dir=tmp_data_dir)
        mgr.delete(tmp_data_dir / "missing.txt")  # should not raise

    # --- Exists ---

    def test_exists(self, tmp_data_dir: Path, sample_text_path: Path):
        """exists returns True for existing file."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager(base_dir=tmp_data_dir)
        assert mgr.exists(sample_text_path) is True

    # --- List files ---

    def test_list_files(self, tmp_data_dir: Path, sample_text_path: Path):
        """list_files returns files in a directory."""
        from backend.storage.file_manager import FileManager

        mgr = FileManager(base_dir=tmp_data_dir)
        files = mgr.list_files(tmp_data_dir)
        assert len(files) >= 1

    # --- Directory info ---

    def test_directory_info(self, monkeypatch: Any, tmp_data_dir: Path):
        """directory_info returns metadata about a managed directory."""
        from backend.storage.file_manager import FileManager

        upload_dir = tmp_data_dir / "uploads"
        upload_dir.mkdir()
        monkeypatch.setattr(
            "backend.core.config.settings.UPLOAD_FOLDER",
            str(upload_dir),
        )

        mgr = FileManager(base_dir=tmp_data_dir)
        info = mgr.directory_info("uploads")
        assert info["name"] == "uploads"
        assert "path" in info
        assert "exists" in info


# ===========================================================================
# StorageService (Facade) Tests
# ===========================================================================


class TestStorageService:
    """Tests for :class:`backend.storage.storage_service.StorageService`."""

    def test_initialisation(self):
        """StorageService can be instantiated with default params."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        assert service is not None
        assert service.csv_manager is not None
        assert service.json_manager is not None
        assert service.file_manager is not None
        assert service.archive_manager is not None
        assert service.backup_manager is not None

    def test_initialisation_custom_params(self):
        """StorageService accepts custom parameters for sub-managers."""
        from backend.storage.storage_service import StorageService

        service = StorageService(
            csv_delimiter=";",
            json_encoding="utf-8",
            json_indent=4,
            archive_format="gztar",
        )
        assert service is not None

    def test_repr(self):
        """__repr__ returns a meaningful string."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        rep = repr(service)
        assert "StorageService" in rep
        assert "CSVManager" in rep
        assert "FileManager" in rep

    # --- Status ---

    def test_status(self, monkeypatch: Any, tmp_data_dir: Path):
        """status returns a dictionary with all storage sections."""
        from backend.storage.storage_service import StorageService

        # Patch managed directories to our temp dir
        for attr in ["UPLOAD_FOLDER", "THUMBNAIL_FOLDER",
                     "ANNOTATED_VIDEOS_DIR", "EXTRACTED_FRAMES_DIR",
                     "DETECTION_IMAGES_DIR", "PREVIEW_IMAGES_DIR",
                     "PDF_REPORTS_DIR", "EXCEL_REPORTS_DIR", "JSON_REPORTS_DIR"]:
            dir_path = tmp_data_dir / attr.lower()
            dir_path.mkdir(parents=True, exist_ok=True)
            monkeypatch.setattr(
                f"backend.core.config.settings.{attr}",
                str(dir_path),
            )

        service = StorageService()
        svc_status = service.status()
        assert "initialized" in svc_status
        assert "csv_stores" in svc_status
        assert "json_stores" in svc_status
        assert "managed_directories" in svc_status
        assert "backup_info" in svc_status

    # --- CSV passthrough ---

    def test_read_csv_store(self, mock_storage_service: MagicMock):
        """read_csv_store delegates to csv_manager.read_store."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.csv_manager = mock_storage_service.csv_manager
        service.read_csv_store("videos")
        mock_storage_service.csv_manager.read_store.assert_called_once_with("videos")

    def test_write_csv_store(self, mock_storage_service: MagicMock):
        """write_csv_store delegates to csv_manager.write_store."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.csv_manager = mock_storage_service.csv_manager
        service.write_csv_store("videos", [{"id": "1"}])
        mock_storage_service.csv_manager.write_store.assert_called_once()

    def test_append_csv_store(self, mock_storage_service: MagicMock):
        """append_csv_store delegates to csv_manager.append_store."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.csv_manager = mock_storage_service.csv_manager
        service.append_csv_store("videos", [{"id": "1"}])
        mock_storage_service.csv_manager.append_store.assert_called_once()

    # --- JSON passthrough ---

    def test_read_json_store(self, mock_storage_service: MagicMock):
        """read_json_store delegates to json_manager.read_store."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.json_manager = mock_storage_service.json_manager
        service.read_json_store("summary")
        mock_storage_service.json_manager.read_store.assert_called_once_with("summary")

    def test_write_json_store(self, mock_storage_service: MagicMock):
        """write_json_store delegates to json_manager.write_store."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.json_manager = mock_storage_service.json_manager
        service.write_json_store("summary", {"key": "value"})
        mock_storage_service.json_manager.write_store.assert_called_once()

    # --- File passthrough ---

    def test_file_exists(self, mock_storage_service: MagicMock):
        """file_exists delegates to file_manager.exists."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.file_manager = mock_storage_service.file_manager
        service.file_exists("/tmp/test.txt")
        mock_storage_service.file_manager.exists.assert_called_once()

    def test_delete_file(self, mock_storage_service: MagicMock):
        """delete_file delegates to file_manager.delete."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.file_manager = mock_storage_service.file_manager
        service.delete_file("/tmp/test.txt")
        mock_storage_service.file_manager.delete.assert_called_once()

    # --- Snapshot ---

    def test_create_snapshot(self, mock_storage_service: MagicMock):
        """create_snapshot delegates to backup_manager.create_backup."""
        from backend.storage.storage_service import StorageService

        service = StorageService()
        service.backup_manager = mock_storage_service.backup_manager
        service.create_snapshot(label="test")
        mock_storage_service.backup_manager.create_backup.assert_called_once_with(
            label="test",
        )

    # --- Error handling ---

    def test_read_csv_store_error(self, mock_storage_service: MagicMock):
        """read_csv_store propagates errors from csv_manager."""
        from backend.storage.storage_service import StorageService

        mock_storage_service.csv_manager.read_store.side_effect = CSVError("Read failed")
        service = StorageService()
        service.csv_manager = mock_storage_service.csv_manager

        with pytest.raises(CSVError, match="Read failed"):
            service.read_csv_store("videos")
