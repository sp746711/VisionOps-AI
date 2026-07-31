"""VisionOps AI — Unit tests for the ``utils`` package.

Covers all public functions in:
- csv_utils
- date_utils
- file_utils
- id_generator
- json_utils
- math_utils
- timer
- validation
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# csv_utils tests
# ---------------------------------------------------------------------------


class TestCSVUtils:
    """Tests for :mod:`backend.utils.csv_utils`."""

    def test_read_csv(self, sample_csv_path: Path, sample_csv_rows: list[dict[str, str]]):
        """Read a valid CSV and verify contents."""
        from backend.utils.csv_utils import read_csv

        rows = read_csv(sample_csv_path)
        assert rows == sample_csv_rows

    def test_read_csv_file_not_found(self):
        """Reading a non-existent CSV raises FileNotFoundError."""
        from backend.utils.csv_utils import read_csv

        with pytest.raises(FileNotFoundError):
            read_csv("/nonexistent/path.csv")

    def test_read_csv_empty(self, empty_csv_path: Path):
        """Reading an empty CSV raises ValueError."""
        from backend.utils.csv_utils import read_csv

        with pytest.raises(ValueError, match="empty"):
            read_csv(empty_csv_path)

    def test_read_csv_custom_delimiter(self, tsv_path: Path):
        """Reading a TSV with explicit delimiter works."""
        from backend.utils.csv_utils import read_csv

        rows = read_csv(tsv_path, delimiter="\t")
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"

    def test_write_csv(self, tmp_data_dir: Path, sample_csv_rows: list[dict[str, str]]):
        """Write a CSV and verify it can be read back."""
        from backend.utils.csv_utils import write_csv, read_csv

        out = tmp_data_dir / "out.csv"
        result = write_csv(out, sample_csv_rows)
        assert result == out.resolve()

        rows = read_csv(out)
        assert rows == sample_csv_rows

    def test_write_csv_empty_data_raises(self, tmp_data_dir: Path):
        """Writing with no data and no fieldnames raises ValueError."""
        from backend.utils.csv_utils import write_csv

        with pytest.raises(ValueError, match="no data"):
            write_csv(tmp_data_dir / "out.csv", [])

    def test_write_csv_with_fieldnames(self, tmp_data_dir: Path):
        """Writing with explicit fieldnames works even with empty data."""
        from backend.utils.csv_utils import write_csv, read_csv

        out = tmp_data_dir / "out.csv"
        write_csv(out, [], fieldnames=["a", "b"])
        rows = read_csv(out)
        assert rows == []

    def test_append_rows(self, sample_csv_path: Path):
        """Appending rows to an existing CSV works."""
        from backend.utils.csv_utils import append_rows, read_csv

        new_rows = [{"id": "4", "name": "Diana", "role": "Designer"}]
        result = append_rows(sample_csv_path, new_rows)
        assert result == sample_csv_path.resolve()

        rows = read_csv(sample_csv_path)
        assert len(rows) == 4
        assert rows[-1]["name"] == "Diana"

    def test_append_rows_file_not_found(self, tmp_data_dir: Path):
        """Appending to a non-existent file raises ValueError."""
        from backend.utils.csv_utils import append_rows

        with pytest.raises(ValueError, match="not found"):
            append_rows(tmp_data_dir / "missing.csv", [{"a": "1"}])

    def test_update_rows(self, sample_csv_path: Path):
        """Updating matching rows works."""
        from backend.utils.csv_utils import update_rows, read_csv

        updated = update_rows(
            sample_csv_path,
            match_fn=lambda r: r["name"] == "Bob",
            update_fn=lambda r: {**r, "role": "Senior Manager"},
        )
        assert updated == 1

        rows = read_csv(sample_csv_path)
        assert rows[1]["role"] == "Senior Manager"

    def test_update_rows_no_match(self, sample_csv_path: Path):
        """Updating with no matching rows returns 0 and does not modify file."""
        from backend.utils.csv_utils import update_rows, read_csv

        original = read_csv(sample_csv_path)
        updated = update_rows(
            sample_csv_path,
            match_fn=lambda r: r["name"] == "Zoe",
            update_fn=lambda r: {**r, "role": "CEO"},
        )
        assert updated == 0

        rows = read_csv(sample_csv_path)
        assert rows == original

    def test_validate_csv_valid(self, sample_csv_path: Path):
        """Validating a well-formed CSV returns True."""
        from backend.utils.csv_utils import validate_csv

        assert validate_csv(sample_csv_path) is True

    def test_validate_csv_with_expected_headers(self, sample_csv_path: Path):
        """Validating with expected headers passes."""
        from backend.utils.csv_utils import validate_csv

        assert validate_csv(sample_csv_path, expected_headers=["id", "name"]) is True

    def test_validate_csv_missing_headers(self, sample_csv_path: Path):
        """Validating with missing expected headers raises ValueError."""
        from backend.utils.csv_utils import validate_csv

        with pytest.raises(ValueError, match="Missing expected headers"):
            validate_csv(sample_csv_path, expected_headers=["missing_col"])

    def test_validate_csv_empty(self, empty_csv_path: Path):
        """Validating an empty CSV raises ValueError."""
        from backend.utils.csv_utils import validate_csv

        with pytest.raises(ValueError, match="empty"):
            validate_csv(empty_csv_path)

    def test_check_headers_present(self, sample_csv_path: Path):
        """Checking present headers returns True."""
        from backend.utils.csv_utils import check_headers

        assert check_headers(sample_csv_path, ["id", "name", "role"]) is True

    def test_check_headers_missing(self, sample_csv_path: Path):
        """Checking missing headers returns False."""
        from backend.utils.csv_utils import check_headers

        assert check_headers(sample_csv_path, ["nonexistent"]) is False

    def test_check_headers_file_not_found(self):
        """Checking headers on missing file raises FileNotFoundError."""
        from backend.utils.csv_utils import check_headers

        with pytest.raises(FileNotFoundError):
            check_headers("/nonexistent.csv", ["id"])

    def test_detect_delimiter_comma(self, sample_csv_path: Path):
        """Detecting delimiter on a comma-separated file returns ','."""
        from backend.utils.csv_utils import detect_delimiter

        assert detect_delimiter(sample_csv_path) == ","

    def test_detect_delimiter_tab(self, tsv_path: Path):
        """Detecting delimiter on a tab-separated file returns '\\t'."""
        from backend.utils.csv_utils import detect_delimiter

        assert detect_delimiter(tsv_path) == "\t"

    def test_detect_delimiter_file_not_found(self):
        """Detecting delimiter on missing file raises FileNotFoundError."""
        from backend.utils.csv_utils import detect_delimiter

        with pytest.raises(FileNotFoundError):
            detect_delimiter("/nonexistent.csv")

    def test_export_csv(self, tmp_data_dir: Path, sample_csv_rows: list[dict[str, str]]):
        """Exporting data to CSV works."""
        from backend.utils.csv_utils import export_csv, read_csv

        out = tmp_data_dir / "export.csv"
        result = export_csv(sample_csv_rows, out)
        assert result == out.resolve()

        rows = read_csv(out)
        assert rows == sample_csv_rows

    def test_backup_csv(self, sample_csv_path: Path, tmp_data_dir: Path):
        """Backing up a CSV creates a timestamped copy."""
        from backend.utils.csv_utils import backup_csv

        backup = backup_csv(sample_csv_path, backup_dir=tmp_data_dir)
        assert backup.exists()
        assert backup.suffix == ".csv"
        assert ".bak" in backup.stem

    def test_backup_csv_file_not_found(self):
        """Backing up a missing file raises FileNotFoundError."""
        from backend.utils.csv_utils import backup_csv

        with pytest.raises(FileNotFoundError):
            backup_csv("/nonexistent.csv")

    def test_csv_exists_true(self, sample_csv_path: Path):
        """csv_exists returns True for an existing CSV."""
        from backend.utils.csv_utils import csv_exists

        assert csv_exists(sample_csv_path) is True

    def test_csv_exists_false_not_csv(self, sample_text_path: Path):
        """csv_exists returns False for a non-CSV file."""
        from backend.utils.csv_utils import csv_exists

        assert csv_exists(sample_text_path) is False

    def test_csv_exists_false_missing(self):
        """csv_exists returns False for a missing file."""
        from backend.utils.csv_utils import csv_exists

        assert csv_exists("/nonexistent.csv") is False


# ---------------------------------------------------------------------------
# date_utils tests
# ---------------------------------------------------------------------------


class TestDateUtils:
    """Tests for :mod:`backend.utils.date_utils`."""

    def test_now_utc(self):
        """now_utc returns a timezone-aware UTC datetime."""
        from backend.utils.date_utils import now_utc

        dt = now_utc()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_now_local(self):
        """now_local returns a timezone-aware local datetime."""
        from backend.utils.date_utils import now_local

        dt = now_local()
        assert dt.tzinfo is not None

    def test_timestamp_to_datetime_seconds(self):
        """Convert Unix timestamp in seconds to datetime."""
        from backend.utils.date_utils import timestamp_to_datetime

        dt = timestamp_to_datetime(1736933400)
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.tzinfo == timezone.utc

    def test_timestamp_to_datetime_milliseconds(self):
        """Convert Unix timestamp in milliseconds to datetime."""
        from backend.utils.date_utils import timestamp_to_datetime

        dt = timestamp_to_datetime(1736933400000, unit="ms")
        assert dt.year == 2025

    def test_timestamp_to_datetime_microseconds(self):
        """Convert Unix timestamp in microseconds to datetime."""
        from backend.utils.date_utils import timestamp_to_datetime

        dt = timestamp_to_datetime(1736933400000000, unit="us")
        assert dt.year == 2025

    def test_timestamp_to_datetime_invalid_unit(self):
        """Invalid unit raises ValueError."""
        from backend.utils.date_utils import timestamp_to_datetime

        with pytest.raises(ValueError, match="Unsupported timestamp unit"):
            timestamp_to_datetime(100, unit="invalid")

    def test_datetime_to_timestamp_seconds(self):
        """Convert datetime to Unix timestamp in seconds."""
        from backend.utils.date_utils import datetime_to_timestamp

        dt = datetime(2025, 1, 15, tzinfo=timezone.utc)
        ts = datetime_to_timestamp(dt)
        assert ts == 1736899200.0

    def test_datetime_to_timestamp_milliseconds(self):
        """Convert datetime to Unix timestamp in milliseconds."""
        from backend.utils.date_utils import datetime_to_timestamp

        dt = datetime(2025, 1, 15, tzinfo=timezone.utc)
        ts = datetime_to_timestamp(dt, unit="ms")
        assert ts == 1736899200000.0

    def test_datetime_to_timestamp_naive(self):
        """Naive datetime is treated as UTC."""
        from backend.utils.date_utils import datetime_to_timestamp

        dt = datetime(2025, 1, 15)
        ts = datetime_to_timestamp(dt)
        assert ts == 1736899200.0

    def test_datetime_to_timestamp_invalid_unit(self):
        """Invalid unit raises ValueError."""
        from backend.utils.date_utils import datetime_to_timestamp

        with pytest.raises(ValueError, match="Unsupported timestamp unit"):
            datetime_to_timestamp(datetime.now(), unit="invalid")

    def test_format_iso_default(self):
        """format_iso returns a valid ISO 8601 string."""
        from backend.utils.date_utils import format_iso

        iso = format_iso()
        assert "T" in iso
        assert iso.endswith("+00:00")

    def test_format_iso_custom_sep(self):
        """format_iso with custom separator."""
        from backend.utils.date_utils import format_iso

        dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        iso = format_iso(dt, sep=" ")
        assert " " in iso

    def test_format_duration_full(self):
        """format_duration with all components and explicit granularity."""
        from backend.utils.date_utils import format_duration

        result = format_duration(90061, granularity=4)
        assert result == "1d 1h 1m 1s"

    def test_format_duration_granularity(self):
        """format_duration with limited granularity."""
        from backend.utils.date_utils import format_duration

        result = format_duration(3661, granularity=2)
        assert result == "1h 1m"

    def test_format_duration_zero(self):
        """format_duration with zero seconds."""
        from backend.utils.date_utils import format_duration

        assert format_duration(0) == "0s"

    def test_format_duration_negative(self):
        """format_duration with negative seconds."""
        from backend.utils.date_utils import format_duration

        result = format_duration(-100)
        # Should handle gracefully
        assert isinstance(result, str)

    def test_time_difference(self):
        """time_difference between two datetimes."""
        from backend.utils.date_utils import time_difference

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        diff = time_difference(start, end)
        assert diff == 86400.0

    def test_time_difference_milliseconds(self):
        """time_difference in milliseconds."""
        from backend.utils.date_utils import time_difference

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        diff = time_difference(start, end, unit="ms")
        assert diff == 1000.0

    def test_time_difference_invalid_unit(self):
        """Invalid unit raises ValueError."""
        from backend.utils.date_utils import time_difference

        with pytest.raises(ValueError, match="Unsupported unit"):
            time_difference(datetime.now(), datetime.now(), unit="invalid")

    def test_utc_to_local(self):
        """Convert UTC datetime to local timezone."""
        from backend.utils.date_utils import utc_to_local

        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        local = utc_to_local(dt)
        assert local.tzinfo is not None
        assert local.utcoffset() != timedelta(0)

    def test_utc_to_local_naive(self):
        """Naive datetime is treated as UTC."""
        from backend.utils.date_utils import utc_to_local

        dt = datetime(2025, 1, 15, 12, 0, 0)
        local = utc_to_local(dt)
        assert local.tzinfo is not None

    def test_local_to_utc(self):
        """Convert local datetime to UTC."""
        from backend.utils.date_utils import local_to_utc

        dt = datetime(2025, 1, 15, 7, 0, 0)
        utc = local_to_utc(dt)
        assert utc.tzinfo == timezone.utc

    def test_local_to_utc_aware(self):
        """Aware local datetime is converted correctly."""
        from backend.utils.date_utils import local_to_utc

        dt = datetime(2025, 1, 15, 7, 0, 0, tzinfo=timezone.utc)
        utc = local_to_utc(dt)
        assert utc.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# file_utils tests
# ---------------------------------------------------------------------------


class TestFileUtils:
    """Tests for :mod:`backend.utils.file_utils`."""

    def test_create_directory(self, tmp_data_dir: Path):
        """Create a new directory."""
        from backend.utils.file_utils import create_directory

        new_dir = tmp_data_dir / "new_dir"
        result = create_directory(new_dir)
        assert result == new_dir.resolve()
        assert new_dir.exists()

    def test_create_directory_existing(self, tmp_data_dir: Path):
        """Creating an existing directory with exist_ok=True succeeds."""
        from backend.utils.file_utils import create_directory

        result = create_directory(tmp_data_dir)
        assert result == tmp_data_dir.resolve()

    def test_ensure_directory(self, tmp_data_dir: Path):
        """Ensure a nested directory is created."""
        from backend.utils.file_utils import ensure_directory

        nested = tmp_data_dir / "a" / "b" / "c"
        result = ensure_directory(nested)
        assert result == nested.resolve()
        assert nested.exists()

    def test_delete_file(self, sample_text_path: Path):
        """Delete an existing file."""
        from backend.utils.file_utils import delete_file

        delete_file(sample_text_path)
        assert not sample_text_path.exists()

    def test_delete_file_missing_ok(self, tmp_data_dir: Path):
        """Delete a missing file with missing_ok=True does not raise."""
        from backend.utils.file_utils import delete_file

        delete_file(tmp_data_dir / "missing.txt")  # should not raise

    def test_delete_file_missing_not_ok(self, tmp_data_dir: Path):
        """Delete a missing file with missing_ok=False raises FileNotFoundError."""
        from backend.utils.file_utils import delete_file

        with pytest.raises(FileNotFoundError):
            delete_file(tmp_data_dir / "missing.txt", missing_ok=False)

    def test_delete_file_is_directory(self, tmp_data_dir: Path):
        """Deleting a directory with delete_file raises IsADirectoryError."""
        from backend.utils.file_utils import delete_file

        with pytest.raises(IsADirectoryError):
            delete_file(tmp_data_dir)

    def test_copy_file(self, sample_text_path: Path, tmp_data_dir: Path):
        """Copy a file to a new location."""
        from backend.utils.file_utils import copy_file

        dst = tmp_data_dir / "copy.txt"
        result = copy_file(sample_text_path, dst)
        assert result == dst.resolve()
        assert dst.exists()
        assert dst.read_text() == sample_text_path.read_text()

    def test_copy_file_overwrite_false(self, sample_text_path: Path, tmp_data_dir: Path):
        """Copying to existing destination without overwrite raises FileExistsError."""
        from backend.utils.file_utils import copy_file

        dst = tmp_data_dir / "existing.txt"
        dst.write_text("existing")
        with pytest.raises(FileExistsError):
            copy_file(sample_text_path, dst, overwrite=False)

    def test_copy_file_overwrite_true(self, sample_text_path: Path, tmp_data_dir: Path):
        """Copying with overwrite=True succeeds."""
        from backend.utils.file_utils import copy_file

        dst = tmp_data_dir / "existing.txt"
        dst.write_text("existing")
        result = copy_file(sample_text_path, dst, overwrite=True)
        assert result == dst.resolve()
        assert dst.read_text() == "Hello, VisionOps!"

    def test_copy_file_source_not_found(self, tmp_data_dir: Path):
        """Copying a missing source raises FileNotFoundError."""
        from backend.utils.file_utils import copy_file

        with pytest.raises(FileNotFoundError):
            copy_file(tmp_data_dir / "missing.txt", tmp_data_dir / "out.txt")

    def test_copy_file_source_is_directory(self, tmp_data_dir: Path):
        """Copying a directory as source raises IsADirectoryError."""
        from backend.utils.file_utils import copy_file

        with pytest.raises(IsADirectoryError):
            copy_file(tmp_data_dir, tmp_data_dir / "out.txt")

    def test_move_file(self, sample_text_path: Path, tmp_data_dir: Path):
        """Move a file to a new location."""
        from backend.utils.file_utils import move_file

        dst = tmp_data_dir / "moved.txt"
        result = move_file(sample_text_path, dst)
        assert result == dst.resolve()
        assert dst.exists()
        assert not sample_text_path.exists()

    def test_move_file_overwrite_false(self, sample_text_path: Path, tmp_data_dir: Path):
        """Moving to existing destination without overwrite raises FileExistsError."""
        from backend.utils.file_utils import move_file

        dst = tmp_data_dir / "existing.txt"
        dst.write_text("existing")
        with pytest.raises(FileExistsError):
            move_file(sample_text_path, dst, overwrite=False)

    def test_rename_file(self, sample_text_path: Path):
        """Rename a file within the same directory."""
        from backend.utils.file_utils import rename_file

        result = rename_file(sample_text_path, "renamed.txt")
        assert result == sample_text_path.with_name("renamed.txt").resolve()
        assert result.exists()
        assert not sample_text_path.exists()

    def test_rename_file_overwrite_false(self, sample_text_path: Path, tmp_data_dir: Path):
        """Renaming to existing name without overwrite raises FileExistsError."""
        from backend.utils.file_utils import rename_file

        other = tmp_data_dir / "other.txt"
        other.write_text("other")
        with pytest.raises(FileExistsError):
            rename_file(sample_text_path, "other.txt", overwrite=False)

    def test_file_exists_true(self, sample_text_path: Path):
        """file_exists returns True for an existing file."""
        from backend.utils.file_utils import file_exists

        assert file_exists(sample_text_path) is True

    def test_file_exists_false(self, tmp_data_dir: Path):
        """file_exists returns False for a missing file."""
        from backend.utils.file_utils import file_exists

        assert file_exists(tmp_data_dir / "missing.txt") is False

    def test_file_exists_directory(self, tmp_data_dir: Path):
        """file_exists returns False for a directory."""
        from backend.utils.file_utils import file_exists

        assert file_exists(tmp_data_dir) is False

    def test_file_size_bytes(self, sample_text_path: Path):
        """file_size returns size in bytes."""
        from backend.utils.file_utils import file_size

        size = file_size(sample_text_path)
        assert isinstance(size, int)
        assert size > 0

    def test_file_size_kb(self, sample_text_path: Path):
        """file_size returns size in KB."""
        from backend.utils.file_utils import file_size

        size = file_size(sample_text_path, unit="KB")
        assert isinstance(size, float)

    def test_file_size_file_not_found(self, tmp_data_dir: Path):
        """file_size on missing file raises FileNotFoundError."""
        from backend.utils.file_utils import file_size

        with pytest.raises(FileNotFoundError):
            file_size(tmp_data_dir / "missing.txt")

    def test_file_size_is_directory(self, tmp_data_dir: Path):
        """file_size on a directory raises IsADirectoryError."""
        from backend.utils.file_utils import file_size

        with pytest.raises(IsADirectoryError):
            file_size(tmp_data_dir)

    def test_directory_size(self, tmp_data_dir: Path):
        """directory_size returns total bytes."""
        from backend.utils.file_utils import directory_size

        (tmp_data_dir / "a.txt").write_text("hello")
        (tmp_data_dir / "b.txt").write_text("world")
        size = directory_size(tmp_data_dir)
        assert size > 0

    def test_directory_size_not_found(self, tmp_data_dir: Path):
        """directory_size on missing path raises FileNotFoundError."""
        from backend.utils.file_utils import directory_size

        with pytest.raises(FileNotFoundError):
            directory_size(tmp_data_dir / "missing")

    def test_directory_size_not_directory(self, sample_text_path: Path):
        """directory_size on a file raises NotADirectoryError."""
        from backend.utils.file_utils import directory_size

        with pytest.raises(NotADirectoryError):
            directory_size(sample_text_path)

    def test_safe_path_within_base(self, tmp_data_dir: Path):
        """safe_path returns resolved path within base_dir."""
        from backend.utils.file_utils import safe_path

        nested = tmp_data_dir / "sub" / "file.txt"
        nested.parent.mkdir(parents=True)
        nested.write_text("data")
        result = safe_path(nested, base_dir=tmp_data_dir)
        assert result == nested.resolve()

    def test_safe_path_traversal(self, tmp_data_dir: Path):
        """safe_path raises ValueError on path traversal."""
        from backend.utils.file_utils import safe_path

        with pytest.raises(ValueError, match="Path traversal"):
            safe_path(tmp_data_dir / ".." / ".." / "etc" / "passwd", base_dir=tmp_data_dir)

    def test_safe_path_no_base(self, tmp_data_dir: Path):
        """safe_path without base_dir just resolves."""
        from backend.utils.file_utils import safe_path

        result = safe_path(tmp_data_dir)
        assert result == tmp_data_dir.resolve()

    def test_temporary_file(self):
        """temporary_file context manager creates and cleans up."""
        from backend.utils.file_utils import temporary_file

        with temporary_file(suffix=".csv") as tmp:
            assert Path(tmp.name).exists()
            tmp.write(b"data")
        assert not Path(tmp.name).exists()

    def test_list_files(self, tmp_data_dir: Path):
        """list_files returns sorted file paths."""
        from backend.utils.file_utils import list_files

        (tmp_data_dir / "b.txt").write_text("b")
        (tmp_data_dir / "a.txt").write_text("a")
        files = list_files(tmp_data_dir)
        assert len(files) == 2
        assert files[0].name == "a.txt"
        assert files[1].name == "b.txt"

    def test_list_files_with_pattern(self, tmp_data_dir: Path):
        """list_files with glob pattern filters results."""
        from backend.utils.file_utils import list_files

        (tmp_data_dir / "data.csv").write_text("a,b")
        (tmp_data_dir / "data.txt").write_text("hello")
        files = list_files(tmp_data_dir, pattern="*.csv")
        assert len(files) == 1
        assert files[0].suffix == ".csv"

    def test_list_files_recursive(self, tmp_data_dir: Path):
        """list_files recursive finds files in subdirectories."""
        from backend.utils.file_utils import list_files

        sub = tmp_data_dir / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_text("deep")
        files = list_files(tmp_data_dir, recursive=True)
        assert any(f.name == "deep.txt" for f in files)

    def test_list_files_not_found(self):
        """list_files on missing directory raises FileNotFoundError."""
        from backend.utils.file_utils import list_files

        with pytest.raises(FileNotFoundError):
            list_files("/nonexistent_dir")

    def test_list_files_not_directory(self, sample_text_path: Path):
        """list_files on a file raises NotADirectoryError."""
        from backend.utils.file_utils import list_files

        with pytest.raises(NotADirectoryError):
            list_files(sample_text_path)

    def test_list_directories(self, tmp_data_dir: Path):
        """list_directories returns sorted subdirectory paths."""
        from backend.utils.file_utils import list_directories

        (tmp_data_dir / "z_dir").mkdir()
        (tmp_data_dir / "a_dir").mkdir()
        dirs = list_directories(tmp_data_dir)
        assert len(dirs) == 2
        assert dirs[0].name == "a_dir"
        assert dirs[1].name == "z_dir"

    def test_list_directories_with_pattern(self, tmp_data_dir: Path):
        """list_directories with glob pattern."""
        from backend.utils.file_utils import list_directories

        (tmp_data_dir / "data_01").mkdir()
        (tmp_data_dir / "logs").mkdir()
        dirs = list_directories(tmp_data_dir, pattern="data_*")
        assert len(dirs) == 1
        assert dirs[0].name == "data_01"

    def test_is_empty_directory_true(self, tmp_data_dir: Path):
        """is_empty_directory returns True for empty dir."""
        from backend.utils.file_utils import is_empty_directory

        assert is_empty_directory(tmp_data_dir) is True

    def test_is_empty_directory_false(self, tmp_data_dir: Path):
        """is_empty_directory returns False for non-empty dir."""
        from backend.utils.file_utils import is_empty_directory

        (tmp_data_dir / "file.txt").write_text("data")
        assert is_empty_directory(tmp_data_dir) is False

    def test_is_empty_directory_not_found(self, tmp_data_dir: Path):
        """is_empty_directory returns True for non-existent path."""
        from backend.utils.file_utils import is_empty_directory

        assert is_empty_directory(tmp_data_dir / "missing") is True

    def test_is_empty_directory_not_directory(self, sample_text_path: Path):
        """is_empty_directory on a file raises NotADirectoryError."""
        from backend.utils.file_utils import is_empty_directory

        with pytest.raises(NotADirectoryError):
            is_empty_directory(sample_text_path)

    def test_file_hash_sha256(self, sample_binary_path: Path):
        """file_hash computes SHA-256 digest."""
        from backend.utils.file_utils import file_hash

        digest = file_hash(sample_binary_path)
        assert isinstance(digest, str)
        assert len(digest) == 64  # SHA-256 hex length

    def test_file_hash_md5(self, sample_binary_path: Path):
        """file_hash computes MD5 digest."""
        from backend.utils.file_utils import file_hash

        digest = file_hash(sample_binary_path, algorithm="md5")
        assert len(digest) == 32

    def test_file_hash_file_not_found(self, tmp_data_dir: Path):
        """file_hash on missing file raises FileNotFoundError."""
        from backend.utils.file_utils import file_hash

        with pytest.raises(FileNotFoundError):
            file_hash(tmp_data_dir / "missing.bin")

    def test_file_hash_is_directory(self, tmp_data_dir: Path):
        """file_hash on a directory raises IsADirectoryError."""
        from backend.utils.file_utils import file_hash

        with pytest.raises(IsADirectoryError):
            file_hash(tmp_data_dir)

    def test_file_hash_invalid_algorithm(self, sample_binary_path: Path):
        """file_hash with unsupported algorithm raises ValueError."""
        from backend.utils.file_utils import file_hash

        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            file_hash(sample_binary_path, algorithm="invalid_algo")

    def test_directory_hash(self, tmp_data_dir: Path):
        """directory_hash returns a consistent hash."""
        from backend.utils.file_utils import directory_hash

        (tmp_data_dir / "a.txt").write_text("hello")
        (tmp_data_dir / "b.txt").write_text("world")
        digest = directory_hash(tmp_data_dir)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_directory_hash_empty(self, tmp_data_dir: Path):
        """directory_hash on empty directory returns a hash."""
        from backend.utils.file_utils import directory_hash

        digest = directory_hash(tmp_data_dir)
        assert isinstance(digest, str)

    def test_directory_hash_not_found(self, tmp_data_dir: Path):
        """directory_hash on missing path raises FileNotFoundError."""
        from backend.utils.file_utils import directory_hash

        with pytest.raises(FileNotFoundError):
            directory_hash(tmp_data_dir / "missing")

    def test_directory_hash_not_directory(self, sample_text_path: Path):
        """directory_hash on a file raises NotADirectoryError."""
        from backend.utils.file_utils import directory_hash

        with pytest.raises(NotADirectoryError):
            directory_hash(sample_text_path)


# ---------------------------------------------------------------------------
# id_generator tests
# ---------------------------------------------------------------------------


class TestIDGenerator:
    """Tests for :mod:`backend.utils.id_generator`."""

    def test_generate_uuid4_format(self):
        """generate_uuid4 returns a valid UUID v4 string."""
        from backend.utils.id_generator import generate_uuid4

        uid = generate_uuid4()
        assert isinstance(uid, str)
        assert len(uid) == 36
        assert uid.count("-") == 4

    def test_generate_uuid4_unique(self):
        """generate_uuid4 returns unique values."""
        from backend.utils.id_generator import generate_uuid4

        assert generate_uuid4() != generate_uuid4()

    def test_generate_job_id_format(self):
        """generate_job_id starts with 'job_'."""
        from backend.utils.id_generator import generate_job_id

        jid = generate_job_id()
        assert jid.startswith("job_")
        assert len(jid) > 10

    def test_generate_worker_id_format(self):
        """generate_worker_id starts with 'worker_'."""
        from backend.utils.id_generator import generate_worker_id

        wid = generate_worker_id()
        assert wid.startswith("worker_")

    def test_generate_report_id_format(self):
        """generate_report_id starts with 'rpt_'."""
        from backend.utils.id_generator import generate_report_id

        rid = generate_report_id()
        assert rid.startswith("rpt_")

    def test_generate_session_id_format(self):
        """generate_session_id starts with 'sess_'."""
        from backend.utils.id_generator import generate_session_id

        sid = generate_session_id()
        assert sid.startswith("sess_")

    def test_generate_timestamp_id_default(self):
        """generate_timestamp_id with default prefix."""
        from backend.utils.id_generator import generate_timestamp_id

        tid = generate_timestamp_id()
        assert tid.startswith("id_")

    def test_generate_timestamp_id_custom_prefix(self):
        """generate_timestamp_id with custom prefix."""
        from backend.utils.id_generator import generate_timestamp_id

        tid = generate_timestamp_id(prefix="task")
        assert tid.startswith("task_")

    def test_generate_tracking_id_format(self):
        """generate_tracking_id starts with 'trk_'."""
        from backend.utils.id_generator import generate_tracking_id

        trk = generate_tracking_id()
        assert trk.startswith("trk_")

    def test_generate_trace_id_format(self):
        """generate_trace_id starts with 'trace_'."""
        from backend.utils.id_generator import generate_trace_id

        trc = generate_trace_id()
        assert trc.startswith("trace_")

    def test_generate_correlation_id_format(self):
        """generate_correlation_id starts with 'corr_'."""
        from backend.utils.id_generator import generate_correlation_id

        cid = generate_correlation_id()
        assert cid.startswith("corr_")

    def test_all_ids_unique(self):
        """All ID generators produce unique values."""
        from backend.utils.id_generator import (
            generate_uuid4,
            generate_job_id,
            generate_worker_id,
            generate_report_id,
            generate_session_id,
            generate_tracking_id,
            generate_trace_id,
            generate_correlation_id,
        )

        ids = {
            generate_uuid4(),
            generate_job_id(),
            generate_worker_id(),
            generate_report_id(),
            generate_session_id(),
            generate_tracking_id(),
            generate_trace_id(),
            generate_correlation_id(),
        }
        assert len(ids) == 8


# ---------------------------------------------------------------------------
# json_utils tests
# ---------------------------------------------------------------------------


class TestJSONUtils:
    """Tests for :mod:`backend.utils.json_utils`."""

    def test_read_json(self, sample_json_path: Path, sample_json_data: dict[str, Any]):
        """Read a valid JSON file."""
        from backend.utils.json_utils import read_json

        data = read_json(sample_json_path)
        assert data == sample_json_data

    def test_read_json_file_not_found(self):
        """Reading a non-existent JSON raises FileNotFoundError."""
        from backend.utils.json_utils import read_json

        with pytest.raises(FileNotFoundError):
            read_json("/nonexistent.json")

    def test_read_json_malformed(self, malformed_json_path: Path):
        """Reading malformed JSON raises ValueError."""
        from backend.utils.json_utils import read_json

        with pytest.raises(ValueError, match="Malformed JSON"):
            read_json(malformed_json_path)

    def test_write_json(self, tmp_data_dir: Path, sample_json_data: dict[str, Any]):
        """Write JSON and verify it can be read back."""
        from backend.utils.json_utils import write_json, read_json

        out = tmp_data_dir / "out.json"
        result = write_json(out, sample_json_data)
        assert result == out.resolve()

        data = read_json(out)
        assert data == sample_json_data

    def test_write_json_compact(self, tmp_data_dir: Path):
        """Write JSON with compact output (indent=None)."""
        from backend.utils.json_utils import write_json

        out = tmp_data_dir / "compact.json"
        write_json(out, {"key": "value"}, indent=None)
        content = out.read_text()
        assert "\n" not in content

    def test_write_json_sort_keys(self, tmp_data_dir: Path):
        """Write JSON with sorted keys."""
        from backend.utils.json_utils import write_json

        out = tmp_data_dir / "sorted.json"
        write_json(out, {"z": 1, "a": 2}, sort_keys=True)
        content = out.read_text()
        assert content.index("a") < content.index("z")

    def test_pretty_print(self, sample_json_data: dict[str, Any]):
        """pretty_print returns a formatted JSON string."""
        from backend.utils.json_utils import pretty_print

        formatted = pretty_print(sample_json_data)
        assert isinstance(formatted, str)
        assert "\n" in formatted

    def test_pretty_print_non_serializable(self):
        """pretty_print on non-serializable data raises ValueError."""
        from backend.utils.json_utils import pretty_print

        with pytest.raises(ValueError, match="Cannot pretty-print"):
            pretty_print(object())

    def test_validate_json_valid_string(self):
        """validate_json returns True for valid JSON string."""
        from backend.utils.json_utils import validate_json

        assert validate_json('{"key": "value"}') is True

    def test_validate_json_invalid_string(self):
        """validate_json returns False for invalid JSON string."""
        from backend.utils.json_utils import validate_json

        assert validate_json("{invalid}") is False

    def test_validate_json_valid_file(self, sample_json_path: Path):
        """validate_json returns True for valid JSON file."""
        from backend.utils.json_utils import validate_json

        assert validate_json(str(sample_json_path)) is True

    def test_validate_json_invalid_file(self, malformed_json_path: Path):
        """validate_json returns False for invalid JSON file."""
        from backend.utils.json_utils import validate_json

        assert validate_json(str(malformed_json_path)) is False

    def test_safe_serialize(self):
        """safe_serialize handles non-serializable types."""
        from backend.utils.json_utils import safe_serialize

        result = safe_serialize({"value": object()})
        assert isinstance(result, str)
        assert "value" in result

    def test_safe_serialize_custom_handler(self):
        """safe_serialize with custom default handler."""
        from backend.utils.json_utils import safe_serialize

        result = safe_serialize({"value": object()}, default_handler=lambda o: "custom")
        assert "custom" in result

    def test_safe_deserialize_valid(self):
        """safe_deserialize returns parsed data for valid JSON."""
        from backend.utils.json_utils import safe_deserialize

        result = safe_deserialize('{"key": "value"}')
        assert result == {"key": "value"}

    def test_safe_deserialize_invalid(self):
        """safe_deserialize returns default for invalid JSON."""
        from backend.utils.json_utils import safe_deserialize

        result = safe_deserialize("{invalid}", default={})
        assert result == {}

    def test_safe_deserialize_invalid_no_default(self):
        """safe_deserialize returns None for invalid JSON without default."""
        from backend.utils.json_utils import safe_deserialize

        result = safe_deserialize("{invalid}")
        assert result is None

    def test_handle_malformed_json_valid(self, sample_json_path: Path):
        """handle_malformed_json works on valid JSON."""
        from backend.utils.json_utils import handle_malformed_json

        data = handle_malformed_json(sample_json_path)
        assert data["app"] == "VisionOps"

    def test_handle_malformed_json_repairable(self, tmp_data_dir: Path):
        """handle_malformed_json repairs and returns data."""
        from backend.utils.json_utils import handle_malformed_json

        path = tmp_data_dir / "repairable.json"
        path.write_text('"key": "value"', encoding="utf-8")
        data = handle_malformed_json(path)
        assert data == {"key": "value"}

    def test_handle_malformed_json_no_repair(self, malformed_json_path: Path):
        """handle_malformed_json with repair_attempts=False raises ValueError."""
        from backend.utils.json_utils import handle_malformed_json

        with pytest.raises(ValueError, match="repair not attempted"):
            handle_malformed_json(malformed_json_path, repair_attempts=False)

    def test_handle_malformed_json_unrepairable(self, tmp_data_dir: Path):
        """handle_malformed_json raises ValueError when repair fails."""
        from backend.utils.json_utils import handle_malformed_json

        path = tmp_data_dir / "unrepairable.json"
        path.write_text("{{{{ totally broken }}}}", encoding="utf-8")
        with pytest.raises(ValueError, match="Could not repair"):
            handle_malformed_json(path)

    def test_merge_json_shallow(self):
        """merge_json shallow merge."""
        from backend.utils.json_utils import merge_json

        base = {"a": 1, "b": {"nested": 1}}
        override = {"b": 2}
        result = merge_json(base, override, deep=False)
        assert result == {"a": 1, "b": 2}

    def test_merge_json_deep(self):
        """merge_json deep merge."""
        from backend.utils.json_utils import merge_json

        base = {"a": 1, "b": {"nested": 1, "keep": 2}}
        override = {"b": {"nested": 99}}
        result = merge_json(base, override, deep=True)
        assert result == {"a": 1, "b": {"nested": 99, "keep": 2}}

    def test_deep_update(self):
        """deep_update modifies target in-place."""
        from backend.utils.json_utils import deep_update

        target = {"a": 1, "b": {"nested": 1}}
        source = {"b": {"nested": 99, "new": 2}}
        result = deep_update(target, source)
        assert result is target
        assert target["b"]["nested"] == 99
        assert target["b"]["new"] == 2


# ---------------------------------------------------------------------------
# math_utils tests
# ---------------------------------------------------------------------------


class TestMathUtils:
    """Tests for :mod:`backend.utils.math_utils`."""

    def test_clamp_within_range(self):
        """clamp returns value when within range."""
        from backend.utils.math_utils import clamp

        assert clamp(5, 0, 10) == 5

    def test_clamp_below_min(self):
        """clamp returns min when value below range."""
        from backend.utils.math_utils import clamp

        assert clamp(-5, 0, 10) == 0

    def test_clamp_above_max(self):
        """clamp returns max when value above range."""
        from backend.utils.math_utils import clamp

        assert clamp(15, 0, 10) == 10

    def test_clamp_invalid_range(self):
        """clamp raises ValueError when min > max."""
        from backend.utils.math_utils import clamp

        with pytest.raises(ValueError, match="min_val"):
            clamp(5, 10, 0)

    def test_percentage(self):
        """percentage calculates correctly."""
        from backend.utils.math_utils import percentage

        assert percentage(25, 200) == 12.5

    def test_percentage_zero_total(self):
        """percentage raises ZeroDivisionError when total is zero."""
        from backend.utils.math_utils import percentage

        with pytest.raises(ZeroDivisionError):
            percentage(10, 0)

    def test_average_simple(self):
        """average of a sequence."""
        from backend.utils.math_utils import average

        assert average([1, 2, 3, 4, 5]) == 3.0

    def test_average_weighted(self):
        """weighted average."""
        from backend.utils.math_utils import average

        assert average([1, 2, 3], weights=[1, 1, 2]) == 2.25

    def test_average_empty(self):
        """average of empty sequence raises ValueError."""
        from backend.utils.math_utils import average

        with pytest.raises(ValueError, match="empty"):
            average([])

    def test_average_weight_mismatch(self):
        """average with mismatched weights raises ValueError."""
        from backend.utils.math_utils import average

        with pytest.raises(ValueError, match="length"):
            average([1, 2], weights=[1])

    def test_average_zero_weight_sum(self):
        """average with zero total weight raises ValueError."""
        from backend.utils.math_utils import average

        with pytest.raises(ValueError, match="zero"):
            average([1, 2], weights=[0, 0])

    def test_min_max(self):
        """min_max returns (min, max)."""
        from backend.utils.math_utils import min_max

        assert min_max([3, 1, 4, 1, 5]) == (1, 5)

    def test_min_max_empty(self):
        """min_max of empty sequence raises ValueError."""
        from backend.utils.math_utils import min_max

        with pytest.raises(ValueError, match="empty"):
            min_max([])

    def test_distance(self):
        """Euclidean distance between two points."""
        from backend.utils.math_utils import distance

        assert distance(0, 0, 3, 4) == 5.0

    def test_normalize(self):
        """normalize value from one range to another."""
        from backend.utils.math_utils import normalize

        result = normalize(5, 0, 10, 0, 100)
        assert result == 50.0

    def test_normalize_zero_range(self):
        """normalize raises ZeroDivisionError when min == max."""
        from backend.utils.math_utils import normalize

        with pytest.raises(ZeroDivisionError):
            normalize(5, 10, 10)

    def test_safe_division(self):
        """safe_division returns correct result."""
        from backend.utils.math_utils import safe_division

        assert safe_division(10, 3) == 10.0 / 3.0

    def test_safe_division_by_zero_with_default(self):
        """safe_division returns default on zero division."""
        from backend.utils.math_utils import safe_division

        assert safe_division(10, 0, default=0.0) == 0.0

    def test_safe_division_by_zero_no_default(self):
        """safe_division raises ZeroDivisionError when no default."""
        from backend.utils.math_utils import safe_division

        with pytest.raises(ZeroDivisionError):
            safe_division(10, 0)

    def test_round_to_standard(self):
        """round_to with standard method."""
        from backend.utils.math_utils import round_to

        assert round_to(3.14159, 2) == 3.14

    def test_round_to_floor(self):
        """round_to with floor method."""
        from backend.utils.math_utils import round_to

        assert round_to(3.14159, 2, method="floor") == 3.14

    def test_round_to_ceil(self):
        """round_to with ceil method."""
        from backend.utils.math_utils import round_to

        assert round_to(3.14159, 2, method="ceil") == 3.15

    def test_round_to_invalid_method(self):
        """round_to with unknown method raises ValueError."""
        from backend.utils.math_utils import round_to

        with pytest.raises(ValueError, match="Unknown rounding method"):
            round_to(3.14, 2, method="invalid")

    def test_median_odd(self):
        """median of odd-length sequence."""
        from backend.utils.math_utils import median

        assert median([1, 3, 5]) == 3.0

    def test_median_even(self):
        """median of even-length sequence."""
        from backend.utils.math_utils import median

        assert median([1, 2, 3, 4]) == 2.5

    def test_median_empty(self):
        """median of empty sequence raises ValueError."""
        from backend.utils.math_utils import median

        with pytest.raises(ValueError, match="empty"):
            median([])

    def test_variance_population(self):
        """variance with ddof=0 (population)."""
        from backend.utils.math_utils import variance

        assert variance([1, 2, 3, 4, 5], ddof=0) == 2.0

    def test_variance_sample(self):
        """variance with ddof=1 (sample)."""
        from backend.utils.math_utils import variance

        result = variance([1, 2, 3, 4, 5], ddof=1)
        assert result == 2.5

    def test_variance_empty(self):
        """variance of empty sequence raises ValueError."""
        from backend.utils.math_utils import variance

        with pytest.raises(ValueError, match="empty"):
            variance([])

    def test_standard_deviation_population(self):
        """standard_deviation with ddof=0."""
        from backend.utils.math_utils import standard_deviation

        result = standard_deviation([1, 2, 3, 4, 5], ddof=0)
        assert result == 2.0 ** 0.5

    def test_standard_deviation_sample(self):
        """standard_deviation with ddof=1."""
        from backend.utils.math_utils import standard_deviation

        result = standard_deviation([1, 2, 3, 4, 5], ddof=1)
        assert result == 2.5 ** 0.5

    def test_standard_deviation_empty(self):
        """standard_deviation of empty sequence raises ValueError."""
        from backend.utils.math_utils import standard_deviation

        with pytest.raises(ValueError, match="empty"):
            standard_deviation([])


# ---------------------------------------------------------------------------
# timer tests
# ---------------------------------------------------------------------------


class TestTimer:
    """Tests for :mod:`backend.utils.timer`."""

    def test_timer_start_stop(self):
        """Timer start/stop returns elapsed time."""
        from backend.utils.timer import Timer

        t = Timer()
        t.start()
        time.sleep(0.01)
        elapsed = t.stop()
        assert elapsed > 0.0

    def test_timer_context_manager(self):
        """Timer as context manager."""
        from backend.utils.timer import Timer

        with Timer() as t:
            time.sleep(0.01)
        assert t.elapsed > 0.0

    def test_timer_elapsed_while_running(self):
        """Timer.elapsed returns time since start while running."""
        from backend.utils.timer import Timer

        t = Timer()
        t.start()
        time.sleep(0.01)
        assert t.elapsed > 0.0
        t.stop()

    def test_timer_elapsed_not_started(self):
        """Timer.elapsed returns 0.0 when never started."""
        from backend.utils.timer import Timer

        t = Timer()
        assert t.elapsed == 0.0

    def test_timer_is_running(self):
        """Timer.is_running reflects state."""
        from backend.utils.timer import Timer

        t = Timer()
        assert t.is_running is False
        t.start()
        assert t.is_running is True
        t.stop()
        assert t.is_running is False

    def test_timer_double_start_raises(self):
        """Starting an already running timer raises RuntimeError."""
        from backend.utils.timer import Timer

        t = Timer()
        t.start()
        with pytest.raises(RuntimeError, match="already running"):
            t.start()

    def test_timer_stop_not_started_raises(self):
        """Stopping a timer that was never started raises RuntimeError."""
        from backend.utils.timer import Timer

        t = Timer()
        with pytest.raises(RuntimeError, match="not started"):
            t.stop()

    def test_timer_reset(self):
        """Timer.reset clears state."""
        from backend.utils.timer import Timer

        t = Timer()
        t.start()
        time.sleep(0.01)
        t.stop()
        t.reset()
        assert t.elapsed == 0.0
        assert t.is_running is False

    def test_timer_format_elapsed_seconds(self):
        """format_elapsed returns seconds for >1s."""
        from backend.utils.timer import Timer

        t = Timer()
        t._elapsed = 1.2345
        assert "s" in t.format_elapsed()

    def test_timer_format_elapsed_milliseconds(self):
        """format_elapsed returns ms for <1s."""
        from backend.utils.timer import Timer

        t = Timer()
        t._elapsed = 0.042
        assert "ms" in t.format_elapsed()

    def test_timer_format_elapsed_microseconds(self):
        """format_elapsed returns us for <0.001s."""
        from backend.utils.timer import Timer

        t = Timer()
        t._elapsed = 0.000042
        assert "us" in t.format_elapsed()

    def test_async_timer(self):
        """AsyncTimer works as async context manager."""
        from backend.utils.timer import AsyncTimer

        async def run():
            async with AsyncTimer() as t:
                await asyncio.sleep(0.01)
            return t.elapsed

        elapsed = asyncio.run(run())
        assert elapsed > 0.0

    def test_async_timer_start_stop(self):
        """AsyncTimer start/stop works."""
        from backend.utils.timer import AsyncTimer

        async def run():
            t = AsyncTimer()
            await t.start()
            await asyncio.sleep(0.01)
            elapsed = await t.stop()
            return elapsed

        elapsed = asyncio.run(run())
        assert elapsed > 0.0

    def test_async_timer_reset(self):
        """AsyncTimer.reset clears state."""
        from backend.utils.timer import AsyncTimer

        t = AsyncTimer()
        t._timer._elapsed = 5.0
        t.reset()
        assert t.elapsed == 0.0

    def test_async_timer_is_running(self):
        """AsyncTimer.is_running reflects state."""
        from backend.utils.timer import AsyncTimer

        async def run():
            t = AsyncTimer()
            assert t.is_running is False
            await t.start()
            assert t.is_running is True
            await t.stop()
            assert t.is_running is False

        asyncio.run(run())

    def test_timeit_sync(self):
        """timeit decorator works on sync functions."""
        from backend.utils.timer import timeit

        @timeit
        def sync_func():
            return 42

        assert sync_func() == 42

    def test_timeit_async(self):
        """timeit decorator works on async functions."""
        from backend.utils.timer import timeit

        @timeit
        async def async_func():
            await asyncio.sleep(0.01)
            return 99

        result = asyncio.run(async_func())
        assert result == 99


# ---------------------------------------------------------------------------
# validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Tests for :mod:`backend.utils.validation`."""

    # --- validate_file_path ---

    def test_validate_file_path_exists(self, sample_text_path: Path):
        """validate_file_path returns resolved path for existing file."""
        from backend.utils.validation import validate_file_path

        result = validate_file_path(sample_text_path)
        assert result == sample_text_path.resolve()

    def test_validate_file_path_not_exists(self, tmp_data_dir: Path):
        """validate_file_path with must_exist=True raises FileNotFoundError."""
        from backend.utils.validation import validate_file_path

        with pytest.raises(FileNotFoundError):
            validate_file_path(tmp_data_dir / "missing.txt")

    def test_validate_file_path_not_exists_ok(self, tmp_data_dir: Path):
        """validate_file_path with must_exist=False returns resolved path."""
        from backend.utils.validation import validate_file_path

        result = validate_file_path(tmp_data_dir / "new.txt", must_exist=False)
        assert result == (tmp_data_dir / "new.txt").resolve()

    def test_validate_file_path_is_directory(self, tmp_data_dir: Path):
        """validate_file_path on a directory raises IsADirectoryError."""
        from backend.utils.validation import validate_file_path

        with pytest.raises(IsADirectoryError):
            validate_file_path(tmp_data_dir)

    def test_validate_file_path_empty(self):
        """validate_file_path with empty path raises ValueError."""
        from backend.utils.validation import validate_file_path

        with pytest.raises(ValueError, match="empty"):
            validate_file_path("")

    def test_validate_file_path_invalid_type(self):
        """validate_file_path with non-str/Path raises TypeError."""
        from backend.utils.validation import validate_file_path

        with pytest.raises(TypeError):
            validate_file_path(123)

    # --- validate_directory ---

    def test_validate_directory_exists(self, tmp_data_dir: Path):
        """validate_directory returns resolved path for existing dir."""
        from backend.utils.validation import validate_directory

        result = validate_directory(tmp_data_dir)
        assert result == tmp_data_dir.resolve()

    def test_validate_directory_not_exists(self, tmp_data_dir: Path):
        """validate_directory with must_exist=True raises FileNotFoundError."""
        from backend.utils.validation import validate_directory

        with pytest.raises(FileNotFoundError):
            validate_directory(tmp_data_dir / "missing")

    def test_validate_directory_not_exists_ok(self, tmp_data_dir: Path):
        """validate_directory with must_exist=False returns resolved path."""
        from backend.utils.validation import validate_directory

        result = validate_directory(tmp_data_dir / "new_dir", must_exist=False)
        assert result == (tmp_data_dir / "new_dir").resolve()

    def test_validate_directory_is_file(self, sample_text_path: Path):
        """validate_directory on a file raises NotADirectoryError."""
        from backend.utils.validation import validate_directory

        with pytest.raises(NotADirectoryError):
            validate_directory(sample_text_path)

    def test_validate_directory_empty(self):
        """validate_directory with empty path raises ValueError."""
        from backend.utils.validation import validate_directory

        with pytest.raises(ValueError, match="empty"):
            validate_directory("")

    # --- validate_uuid ---

    def test_validate_uuid_valid_v4(self):
        """validate_uuid returns True for valid UUID v4."""
        from backend.utils.validation import validate_uuid

        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_validate_uuid_invalid(self):
        """validate_uuid returns False for invalid string."""
        from backend.utils.validation import validate_uuid

        assert validate_uuid("not-a-uuid") is False

    def test_validate_uuid_empty(self):
        """validate_uuid returns False for empty string."""
        from backend.utils.validation import validate_uuid

        assert validate_uuid("") is False

    def test_validate_uuid_wrong_version(self):
        """validate_uuid returns False for wrong version."""
        from backend.utils.validation import validate_uuid

        # UUID v1
        assert validate_uuid("550e8400-e29b-11d4-a716-446655440000", version=4) is False

    def test_validate_uuid_invalid_version(self):
        """validate_uuid with unsupported version raises ValueError."""
        from backend.utils.validation import validate_uuid

        with pytest.raises(ValueError, match="Unsupported UUID version"):
            validate_uuid("550e8400-e29b-41d4-a716-446655440000", version=6)

    def test_validate_uuid_non_string(self):
        """validate_uuid returns False for non-string input."""
        from backend.utils.validation import validate_uuid

        assert validate_uuid(12345) is False

    # --- validate_email ---

    def test_validate_email_valid(self):
        """validate_email returns True for valid email."""
        from backend.utils.validation import validate_email

        assert validate_email("user@example.com") is True

    def test_validate_email_invalid(self):
        """validate_email returns False for invalid email."""
        from backend.utils.validation import validate_email

        assert validate_email("not-an-email") is False

    def test_validate_email_empty(self):
        """validate_email returns False for empty string."""
        from backend.utils.validation import validate_email

        assert validate_email("") is False

    def test_validate_email_non_string(self):
        """validate_email returns False for non-string."""
        from backend.utils.validation import validate_email

        assert validate_email(123) is False

    def test_validate_email_subdomain(self):
        """validate_email with subdomain."""
        from backend.utils.validation import validate_email

        assert validate_email("user@sub.example.com") is True

    # --- validate_numeric_range ---

    def test_validate_numeric_range_within(self):
        """validate_numeric_range returns True for value within range."""
        from backend.utils.validation import validate_numeric_range

        assert validate_numeric_range(5, 0, 10) is True

    def test_validate_numeric_range_below(self):
        """validate_numeric_range returns False for value below min."""
        from backend.utils.validation import validate_numeric_range

        assert validate_numeric_range(-1, 0, 10) is False

    def test_validate_numeric_range_above(self):
        """validate_numeric_range returns False for value above max."""
        from backend.utils.validation import validate_numeric_range

        assert validate_numeric_range(11, 0, 10) is False

    def test_validate_numeric_range_no_bounds(self):
        """validate_numeric_range with no bounds returns True."""
        from backend.utils.validation import validate_numeric_range

        assert validate_numeric_range(42) is True

    def test_validate_numeric_range_exclusive(self):
        """validate_numeric_range with inclusive=False."""
        from backend.utils.validation import validate_numeric_range

        assert validate_numeric_range(0, 0, 10, inclusive=False) is False
        assert validate_numeric_range(10, 0, 10, inclusive=False) is False
        assert validate_numeric_range(5, 0, 10, inclusive=False) is True

    def test_validate_numeric_range_non_numeric(self):
        """validate_numeric_range with non-numeric raises TypeError."""
        from backend.utils.validation import validate_numeric_range

        with pytest.raises(TypeError):
            validate_numeric_range("abc")

    # --- validate_required_values ---

    def test_validate_required_values_all_present(self):
        """validate_required_values returns True when all keys present."""
        from backend.utils.validation import validate_required_values

        assert validate_required_values({"a": 1, "b": 2}, ["a", "b"]) is True

    def test_validate_required_values_missing(self):
        """validate_required_values raises ValueError for missing keys."""
        from backend.utils.validation import validate_required_values

        with pytest.raises(ValueError, match="Missing required keys"):
            validate_required_values({"a": 1}, ["a", "b"])

    def test_validate_required_values_none_value(self):
        """validate_required_values treats None as missing."""
        from backend.utils.validation import validate_required_values

        with pytest.raises(ValueError, match="Missing required keys"):
            validate_required_values({"a": None}, ["a"])

    # --- validate_filename ---

    def test_validate_filename_valid(self):
        """validate_filename returns True for valid filename."""
        from backend.utils.validation import validate_filename

        assert validate_filename("report_2025.csv") is True

    def test_validate_filename_empty(self):
        """validate_filename raises ValueError for empty filename."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="empty"):
            validate_filename("")

    def test_validate_filename_too_long(self):
        """validate_filename raises ValueError for too long filename."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="exceeds max length"):
            validate_filename("a" * 300)

    def test_validate_filename_path_separator(self):
        """validate_filename raises ValueError for path separator."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="path separator"):
            validate_filename("a/b.txt")

    def test_validate_filename_reserved_name(self):
        """validate_filename raises ValueError for reserved names."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="reserved name"):
            validate_filename("CON.txt")

    def test_validate_filename_disallowed_chars(self):
        """validate_filename raises ValueError for disallowed chars."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="disallowed characters"):
            validate_filename("file@name!.txt")

    def test_validate_filename_non_string(self):
        """validate_filename raises ValueError for non-string."""
        from backend.utils.validation import validate_filename

        with pytest.raises(ValueError, match="empty"):
            validate_filename(123)

    # --- validate_extension ---

    def test_validate_extension_allowed(self):
        """validate_extension returns True for allowed extension."""
        from backend.utils.validation import validate_extension

        assert validate_extension("data.csv", [".csv", ".json"]) is True

    def test_validate_extension_not_allowed(self):
        """validate_extension raises ValueError for disallowed extension."""
        from backend.utils.validation import validate_extension

        with pytest.raises(ValueError, match="not allowed"):
            validate_extension("data.exe", [".csv", ".json"])

    def test_validate_extension_no_extension(self):
        """validate_extension raises ValueError for no extension."""
        from backend.utils.validation import validate_extension

        with pytest.raises(ValueError, match="no extension"):
            validate_extension("data", [".csv"])

    def test_validate_extension_case_insensitive(self):
        """validate_extension is case-insensitive by default."""
        from backend.utils.validation import validate_extension

        assert validate_extension("data.CSV", [".csv"]) is True

    def test_validate_extension_case_sensitive(self):
        """validate_extension with case_sensitive=True."""
        from backend.utils.validation import validate_extension

        with pytest.raises(ValueError, match="not allowed"):
            validate_extension("data.CSV", [".csv"], case_sensitive=True)

    def test_validate_extension_without_dot(self):
        """validate_extension handles extensions without leading dot."""
        from backend.utils.validation import validate_extension

        assert validate_extension("data.csv", ["csv"]) is True

    # --- validate_url ---

    def test_validate_url_valid_http(self):
        """validate_url returns True for valid HTTP URL."""
        from backend.utils.validation import validate_url

        assert validate_url("http://example.com") is True

    def test_validate_url_valid_https(self):
        """validate_url returns True for valid HTTPS URL."""
        from backend.utils.validation import validate_url

        assert validate_url("https://example.com/api/v1") is True

    def test_validate_url_invalid(self):
        """validate_url returns False for invalid URL."""
        from backend.utils.validation import validate_url

        assert validate_url("not-a-url") is False

    def test_validate_url_empty(self):
        """validate_url returns False for empty string."""
        from backend.utils.validation import validate_url

        assert validate_url("") is False

    def test_validate_url_non_string(self):
        """validate_url returns False for non-string."""
        from backend.utils.validation import validate_url

        assert validate_url(123) is False

    # --- validate_ip ---

    def test_validate_ip_v4(self):
        """validate_ip returns True for valid IPv4."""
        from backend.utils.validation import validate_ip

        assert validate_ip("192.168.1.1") is True

    def test_validate_ip_v6(self):
        """validate_ip returns True for valid IPv6."""
        from backend.utils.validation import validate_ip

        assert validate_ip("::1") is True

    def test_validate_ip_invalid(self):
        """validate_ip returns False for invalid IP."""
        from backend.utils.validation import validate_ip

        assert validate_ip("999.999.999.999") is False

    def test_validate_ip_empty(self):
        """validate_ip returns False for empty string."""
        from backend.utils.validation import validate_ip

        assert validate_ip("") is False

    def test_validate_ip_non_string(self):
        """validate_ip returns False for non-string."""
        from backend.utils.validation import validate_ip

        assert validate_ip(123) is False

    # --- validate_port ---

    def test_validate_port_valid(self):
        """validate_port returns True for valid port."""
        from backend.utils.validation import validate_port

        assert validate_port(8080) is True
        assert validate_port(1) is True
        assert validate_port(65535) is True

    def test_validate_port_invalid(self):
        """validate_port returns False for invalid port."""
        from backend.utils.validation import validate_port

        assert validate_port(0) is False
        assert validate_port(65536) is False
        assert validate_port(-1) is False

    def test_validate_port_non_int(self):
        """validate_port with non-int raises TypeError."""
        from backend.utils.validation import validate_port

        with pytest.raises(TypeError):
            validate_port("8080")

