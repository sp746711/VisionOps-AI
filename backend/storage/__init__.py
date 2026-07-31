"""VisionOps AI — Storage package.

Provides a config-aware, production-ready storage layer built on top of
the low-level utilities in ``backend.utils``.

The package is organised into five manager classes and one unified
facade:

* :class:`CSVManager`        — CRUD for CSV data stores
* :class:`JSONManager`       — CRUD for JSON data files
* :class:`FileManager`       — High-level file operations
* :class:`ArchiveManager`    — Archival of data directories
* :class:`BackupManager`     — Backup / restore operations
* :class:`StorageService`    — Unified facade over all managers

Usage::

    from backend.storage import StorageService

    storage = StorageService()
    storage.initialize()
"""

from __future__ import annotations

from backend.storage.archive_manager import ArchiveManager
from backend.storage.backup_manager import BackupManager
from backend.storage.csv_manager import CSVManager
from backend.storage.file_manager import FileManager
from backend.storage.json_manager import JSONManager
from backend.storage.storage_service import StorageService

__all__ = [
    "ArchiveManager",
    "BackupManager",
    "CSVManager",
    "FileManager",
    "JSONManager",
    "StorageService",
]

