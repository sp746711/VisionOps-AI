"""VisionOps AI — Scripts Package.

Standalone executable utilities for project initialization, data backup,
output cleanup, default file creation, and full project reset.

Each script is a CLI entry point that orchestrates existing services
from ``backend.storage``, ``backend.core``, ``backend.utils``, and
``backend.exceptions``.

Usage:
    python -m backend.scripts.initialize_project
    python -m backend.scripts.create_default_files
    python -m backend.scripts.backup_data
    python -m backend.scripts.clean_outputs
    python -m backend.scripts.reset_project
"""

from __future__ import annotations

__all__: list[str] = []
