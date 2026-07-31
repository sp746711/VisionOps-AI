"""VisionOps AI — Pytest shared fixtures and configuration.

Provides reusable fixtures for all test modules:
- Temporary directories for file I/O tests
- Sample CSV and JSON data
- Sample file paths
- Timer instances
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_data_dir() -> Generator[Path, None, None]:
    """Create and yield a temporary directory for test data files.

    The directory and all contents are automatically cleaned up after
    the test completes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_nested_dir(tmp_data_dir: Path) -> Path:
    """Create a nested subdirectory structure inside *tmp_data_dir*.

    Returns:
        Path to ``tmp_data_dir / sub / nested``.
    """
    nested = tmp_data_dir / "sub" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    return nested


# ---------------------------------------------------------------------------
# Sample CSV data
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv_rows() -> list[dict[str, str]]:
    """Return a small list of dicts representing CSV rows."""
    return [
        {"id": "1", "name": "Alice", "role": "Engineer"},
        {"id": "2", "name": "Bob", "role": "Manager"},
        {"id": "3", "name": "Charlie", "role": "Analyst"},
    ]


@pytest.fixture
def sample_csv_headers() -> list[str]:
    """Return the expected header list for *sample_csv_rows*."""
    return ["id", "name", "role"]


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


# ---------------------------------------------------------------------------
# Sample JSON data
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Sample file paths
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Timer fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def timer_instance():
    """Return a fresh :class:`backend.utils.timer.Timer` instance."""
    from backend.utils.timer import Timer

    return Timer()

