"""VisionOps AI — ID Generator Utilities.

Reusable helpers for generating unique identifiers: UUIDs, job IDs,
worker IDs, report IDs, session IDs, tracking IDs, trace IDs, and
correlation IDs. Shared across the entire backend.

Usage:
    from backend.utils.id_generator import generate_uuid4, generate_job_id
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("visionops.utils.id_generator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_RANDOM_LENGTH: int = 8


def _random_suffix(length: int = _DEFAULT_RANDOM_LENGTH) -> str:
    """Generate a short random suffix from a UUID hex string."""
    return uuid.uuid4().hex[:length]


def _timestamp_prefix() -> str:
    """Return a compact timestamp string (YYYYMMDDHHMMSS)."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_uuid4() -> str:
    """Generate a UUID v4 string.

    Returns:
        A UUID v4 string, e.g. ``"550e8400-e29b-41d4-a716-446655440000"``.

    Example:
        >>> generate_uuid4()
        '550e8400-e29b-41d4-a716-446655440000'
    """
    return str(uuid.uuid4())


def generate_job_id() -> str:
    """Generate a unique job identifier.

    Format: ``job_<random>_<timestamp>``

    Returns:
        Job ID string.
    """
    return f"job_{_random_suffix()}_{_timestamp_prefix()}"


def generate_worker_id() -> str:
    """Generate a unique worker identifier.

    Format: ``worker_<random>_<timestamp>``

    Returns:
        Worker ID string.
    """
    return f"worker_{_random_suffix()}_{_timestamp_prefix()}"


def generate_report_id() -> str:
    """Generate a unique report identifier.

    Format: ``rpt_<random>_<timestamp>``

    Returns:
        Report ID string.
    """
    return f"rpt_{_random_suffix()}_{_timestamp_prefix()}"


def generate_session_id() -> str:
    """Generate a unique session identifier.

    Format: ``sess_<random>_<timestamp>``

    Returns:
        Session ID string.
    """
    return f"sess_{_random_suffix()}_{_timestamp_prefix()}"


def generate_timestamp_id(prefix: str = "id") -> str:
    """Generate a timestamp-based ID with a custom prefix.

    Format: ``<prefix>_<timestamp>_<random>``

    Args:
        prefix: Custom prefix (default: ``"id"``).

    Returns:
        Timestamp-based ID string.

    Example:
        >>> generate_timestamp_id("task")
        'task_20250115_123000_a1b2c3d4'
    """
    return f"{prefix}_{_timestamp_prefix()}_{_random_suffix()}"


def generate_tracking_id() -> str:
    """Generate a unique tracking identifier.

    Format: ``trk_<uuid4>``

    Returns:
        Tracking ID string.
    """
    return f"trk_{uuid.uuid4()}"


def generate_trace_id() -> str:
    """Generate a unique trace identifier (UUID4-based).

    Format: ``trace_<uuid4>``

    Returns:
        Trace ID string.
    """
    return f"trace_{uuid.uuid4()}"


def generate_correlation_id() -> str:
    """Generate a unique correlation identifier (UUID4-based).

    Format: ``corr_<uuid4>``

    Returns:
        Correlation ID string.
    """
    return f"corr_{uuid.uuid4()}"
