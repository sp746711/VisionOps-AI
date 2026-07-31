"""VisionOps AI — Pytest shared fixtures and configuration.

Provides reusable fixtures for all test modules:
- Temporary directories for file I/O tests
- Sample CSV, JSON, and detection data
- Mocked storage service and managers
- Mocked service instances
- Sample video metadata, alerts, events, KPIs
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, create_autospec

import pytest

from backend.core.config import Settings


# ===========================================================================
# Temporary directory fixtures
# ===========================================================================


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create and yield a temporary directory for test data files.

    Uses pytest's built-in ``tmp_path`` fixture for automatic cleanup.
    """
    return tmp_path


@pytest.fixture
def tmp_nested_dir(tmp_data_dir: Path) -> Path:
    """Create a nested subdirectory structure inside *tmp_data_dir*.

    Returns:
        Path to ``tmp_data_dir / sub / nested``.
    """
    nested = tmp_data_dir / "sub" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    return nested


# ===========================================================================
# Sample CSV data
# ===========================================================================


@pytest.fixture
def sample_csv_headers() -> list[str]:
    """Return the expected header list for CSV test data."""
    return ["id", "name", "role"]


@pytest.fixture
def sample_csv_rows() -> list[dict[str, str]]:
    """Return a small list of dicts representing CSV rows."""
    return [
        {"id": "1", "name": "Alice", "role": "Engineer"},
        {"id": "2", "name": "Bob", "role": "Manager"},
        {"id": "3", "name": "Charlie", "role": "Analyst"},
    ]


@pytest.fixture
def sample_csv_path(
    tmp_data_dir: Path,
    sample_csv_rows: list[dict[str, str]],
    sample_csv_headers: list[str],
) -> Path:
    """Create a real CSV file on disk and return its path."""
    path = tmp_data_dir / "test_data.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_headers)
        writer.writeheader()
        writer.writerows(sample_csv_rows)
    return path


@pytest.fixture
def empty_csv_path(tmp_data_dir: Path) -> Path:
    """Create an empty CSV file (zero bytes)."""
    path = tmp_data_dir / "empty.csv"
    path.touch()
    return path


@pytest.fixture
def header_only_csv_path(
    tmp_data_dir: Path,
    sample_csv_headers: list[str],
) -> Path:
    """Create a CSV file with headers but no data rows."""
    path = tmp_data_dir / "header_only.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_headers)
        writer.writeheader()
    return path


@pytest.fixture
def tsv_path(tmp_data_dir: Path) -> Path:
    """Create a tab-separated file for delimiter detection tests."""
    path = tmp_data_dir / "test_data.tsv"
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("id\tname\trole\n")
        f.write("1\tAlice\tEngineer\n")
        f.write("2\tBob\tManager\n")
    return path


# ===========================================================================
# Sample JSON data
# ===========================================================================


@pytest.fixture
def sample_json_data() -> dict[str, Any]:
    """Return a sample JSON-serialisable dictionary."""
    return {
        "app": "VisionOps",
        "version": "1.0.0",
        "features": {"detection": True, "tracking": True},
        "count": 42,
    }


@pytest.fixture
def sample_json_path(
    tmp_data_dir: Path,
    sample_json_data: dict[str, Any],
) -> Path:
    """Create a real JSON file on disk and return its path."""
    path = tmp_data_dir / "test_config.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(sample_json_data, f, indent=2)
    return path


@pytest.fixture
def malformed_json_path(tmp_data_dir: Path) -> Path:
    """Create a JSON file with malformed content."""
    path = tmp_data_dir / "malformed.json"
    path.write_text('{"key": "value" "extra": 1}', encoding="utf-8")
    return path


# ===========================================================================
# Sample file paths
# ===========================================================================


@pytest.fixture
def sample_text_path(tmp_data_dir: Path) -> Path:
    """Create a small text file for file I/O tests."""
    path = tmp_data_dir / "hello.txt"
    path.write_text("Hello, VisionOps!", encoding="utf-8")
    return path


@pytest.fixture
def sample_binary_path(tmp_data_dir: Path) -> Path:
    """Create a small binary file for hashing tests."""
    path = tmp_data_dir / "data.bin"
    path.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd\xfc")
    return path


# ===========================================================================
# Sample detection, event, alert, KPI data
# ===========================================================================


@pytest.fixture
def sample_detection_rows() -> list[dict[str, str]]:
    """Return sample detection records."""
    return [
        {"detection_id": "det_001", "video_id": "vid_001", "class_name": "person",
         "confidence": "0.95", "bbox_x": "100", "bbox_y": "200",
         "bbox_w": "50", "bbox_h": "100", "frame_number": "1",
         "created_at": "2025-01-15T10:00:00"},
        {"detection_id": "det_002", "video_id": "vid_001", "class_name": "forklift",
         "confidence": "0.85", "bbox_x": "300", "bbox_y": "400",
         "bbox_w": "80", "bbox_h": "60", "frame_number": "1",
         "created_at": "2025-01-15T10:00:01"},
        {"detection_id": "det_003", "video_id": "vid_002", "class_name": "pallet",
         "confidence": "0.72", "bbox_x": "50", "bbox_y": "50",
         "bbox_w": "100", "bbox_h": "100", "frame_number": "5",
         "created_at": "2025-01-15T11:00:00"},
    ]


@pytest.fixture
def sample_event_rows() -> list[dict[str, str]]:
    """Return sample event records."""
    return [
        {"event_id": "evt_001", "video_id": "vid_001", "event_type": "dwell",
         "severity": "medium", "created_at": "2025-01-15T10:05:00"},
        {"event_id": "evt_002", "video_id": "vid_001", "event_type": "movement",
         "severity": "low", "created_at": "2025-01-15T10:10:00"},
    ]


@pytest.fixture
def sample_alert_rows() -> list[dict[str, str]]:
    """Return sample alert records."""
    return [
        {"alert_id": "alert_001", "video_id": "vid_001", "severity": "high",
         "message": "Unauthorized personnel detected",
         "acknowledged": "false", "created_at": "2025-01-15T10:00:00"},
        {"alert_id": "alert_002", "video_id": "vid_001", "severity": "medium",
         "message": "Spoilage risk detected",
         "acknowledged": "true", "created_at": "2025-01-15T10:05:00"},
    ]


@pytest.fixture
def sample_kpi_rows() -> list[dict[str, str]]:
    """Return sample KPI records."""
    return [
        {"kpi_id": "kpi_001", "video_id": "vid_001", "metric": "total_detections",
         "value": "150", "unit": "count", "timestamp": "2025-01-15T10:00:00"},
        {"kpi_id": "kpi_002", "video_id": "vid_001", "metric": "average_confidence",
         "value": "0.85", "unit": "score", "timestamp": "2025-01-15T10:00:00"},
    ]


@pytest.fixture
def sample_video_rows() -> list[dict[str, str]]:
    """Return sample video metadata records."""
    return [
        {"video_id": "vid_001", "filename": "warehouse_1.mp4", "file_size": "1048576",
         "status": "completed", "created_at": "2025-01-15T09:00:00",
         "updated_at": "2025-01-15T09:30:00"},
        {"video_id": "vid_002", "filename": "warehouse_2.mp4", "file_size": "2097152",
         "status": "processing", "created_at": "2025-01-15T10:00:00",
         "updated_at": "2025-01-15T10:15:00"},
    ]


# ===========================================================================
# Mocked StorageService
# ===========================================================================


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Create a fully mocked StorageService with all sub-managers mocked.

    Returns:
        MagicMock configured with mocked csv_manager, json_manager,
        file_manager, archive_manager, and backup_manager.
    """
    mock = MagicMock()

    # Set up sub-manager mocks
    mock.csv_manager = MagicMock()
    mock.json_manager = MagicMock()
    mock.file_manager = MagicMock()
    mock.archive_manager = MagicMock()
    mock.backup_manager = MagicMock()

    return mock


@pytest.fixture
def mock_csv_manager() -> MagicMock:
    """Create a mocked CSVManager."""
    return MagicMock()


@pytest.fixture
def mock_json_manager() -> MagicMock:
    """Create a mocked JSONManager."""
    return MagicMock()


@pytest.fixture
def mock_file_manager() -> MagicMock:
    """Create a mocked FileManager."""
    return MagicMock()


@pytest.fixture
def mock_storage_with_csv_data(
    mock_storage_service: MagicMock,
    sample_detection_rows: list[dict[str, str]],
    sample_event_rows: list[dict[str, str]],
    sample_alert_rows: list[dict[str, str]],
    sample_kpi_rows: list[dict[str, str]],
    sample_video_rows: list[dict[str, str]],
) -> MagicMock:
    """Configure a mocked StorageService to return sample CSV data.

    Configures ``read_csv_store`` to return appropriate data based on
    the store name argument.
    """
    store_data: dict[str, list[dict[str, str]]] = {
        "videos": sample_video_rows,
        "detections": sample_detection_rows,
        "events": sample_event_rows,
        "alerts": sample_alert_rows,
        "kpis": sample_kpi_rows,
    }

    def read_csv_side_effect(store_name: str) -> list[dict[str, str]]:
        return store_data.get(store_name, [])

    mock_storage_service.read_csv_store.side_effect = read_csv_side_effect
    mock_storage_service.csv_manager.read_store.side_effect = read_csv_side_effect

    return mock_storage_service


# ===========================================================================
# Mocked Services
# ===========================================================================


@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Create a mocked AuthService."""
    mock = MagicMock()
    mock.authenticate_user.return_value = {
        "access_token": "mock_token",
        "token_type": "bearer",
        "expires_in": 3600,
        "user_id": "user_001",
        "username": "admin",
        "role": "admin",
    }
    return mock


@pytest.fixture
def mock_video_service() -> MagicMock:
    """Create a mocked VideoProcessingService."""
    mock = MagicMock()
    mock.initiate_upload.return_value = {
        "video_id": "vid_mock_001",
        "filename": "test.mp4",
        "file_size": 1024,
        "status": "uploaded",
        "created_at": "2025-01-15T10:00:00",
    }
    return mock


@pytest.fixture
def mock_analysis_service() -> MagicMock:
    """Create a mocked AnalysisService."""
    mock = MagicMock()
    mock.aggregate_results.return_value = {
        "video_id": "vid_001",
        "total_detections": 10,
        "unique_classes": 3,
        "class_counts": {"person": 5, "forklift": 3, "pallet": 2},
        "average_confidence": 0.85,
        "class_avg_confidence": {"person": 0.9, "forklift": 0.8, "pallet": 0.75},
        "detections_per_frame": 2.5,
    }
    return mock


@pytest.fixture
def mock_analytics_service() -> MagicMock:
    """Create a mocked AnalyticsService."""
    mock = MagicMock()
    mock.calculate_kpis.return_value = [
        {"kpi_id": "kpi_001", "metric": "total_detections", "value": 150,
         "unit": "count", "timestamp": "2025-01-15T10:00:00"},
    ]
    return mock


@pytest.fixture
def mock_dashboard_service() -> MagicMock:
    """Create a mocked DashboardService."""
    mock = MagicMock()
    mock.get_summary.return_value = {
        "total_videos": 10,
        "total_detections": 1500,
        "total_events": 50,
        "total_alerts": 20,
        "total_kpis": 15,
        "videos_by_status": {"completed": 8, "processing": 2},
        "generated_at": "2025-01-15T10:00:00",
    }
    return mock


@pytest.fixture
def mock_report_service() -> MagicMock:
    """Create a mocked ReportService."""
    mock = MagicMock()
    mock.generate_report.return_value = {
        "report_id": "rpt_001",
        "format": "pdf",
        "file_path": "/tmp/reports/rpt_001.pdf",
        "file_size": 1024,
        "status": "generated",
        "generated_at": "2025-01-15T10:00:00",
    }
    return mock


@pytest.fixture
def mock_notification_service() -> MagicMock:
    """Create a mocked NotificationService."""
    mock = MagicMock()
    mock.dispatch_alerts.return_value = {
        "total_alerts": 2,
        "channels_used": ["dashboard"],
        "successful_dispatches": 2,
        "failed_dispatches": 0,
        "dispatch_results": [],
        "timestamp": "2025-01-15T10:00:00",
    }
    return mock


@pytest.fixture
def mock_settings_service() -> MagicMock:
    """Create a mocked SettingsService."""
    mock = MagicMock()
    mock.get_settings.return_value = {
        "PROJECT_NAME": "VisionOps AI",
        "VERSION": "1.0.0",
        "ENVIRONMENT": "testing",
        "DEBUG": True,
    }
    return mock


# ===========================================================================
# Settings fixture for isolated testing
# ===========================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Create a Settings instance configured for testing.

    Uses environment variables to override paths to temporary locations.
    The settings object is configured with TESTING environment to avoid
    side effects like directory creation.
    """
    return Settings(
        _env_file=None,
        ENVIRONMENT="testing",
        DEBUG=True,
        SECRET_KEY="test-secret-key-for-testing-only-32chars",
    )


# ===========================================================================
# Timestamp fixture
# ===========================================================================


@pytest.fixture
def utc_now() -> datetime:
    """Return the current UTC datetime.

    Useful for tests that need a consistent timestamp reference.
    """
    return datetime.now(timezone.utc)


# ===========================================================================
# Sample raw detection data (for AnalysisService tests)
# ===========================================================================


@pytest.fixture
def sample_raw_detections() -> list[dict[str, Any]]:
    """Return sample raw detection dictionaries as produced by AI inference."""
    return [
        {"class_name": "person", "confidence": 0.95, "bbox": [100, 200, 50, 100]},
        {"class_name": "forklift", "confidence": 0.85, "bbox": [300, 400, 80, 60]},
        {"class_name": "pallet", "confidence": 0.72, "bbox": [50, 50, 100, 100]},
        {"class_name": "person", "confidence": 0.45, "bbox": [200, 300, 60, 120]},
    ]


@pytest.fixture
def sample_invalid_detections() -> list[dict[str, Any]]:
    """Return sample invalid detection dictionaries for error-path testing."""
    return [
        {},  # Missing all fields
        {"class_name": "person"},  # Missing confidence and bbox
        {"class_name": "forklift", "confidence": "invalid", "bbox": [1, 2, 3, 4]},
        {"class_name": "pallet", "confidence": 0.5, "bbox": "not_a_list"},
        {"class_name": "truck", "confidence": 1.5, "bbox": [0, 0, 10, 10]},
        {"class_name": "dock", "confidence": -0.1, "bbox": [0, 0, 10, 10]},
    ]
