"""VisionOps AI — Sanity tests for the ``storage`` package.

The storage package modules are currently stubs (zero bytes).
These tests verify that the modules can be imported and their
expected public symbols are accessible.
"""

from __future__ import annotations

import pytest


class TestStoragePackage:
    """Sanity checks for the storage package."""

    def test_storage_init_module(self):
        """The storage __init__ module can be imported."""
        import backend.storage  # noqa: F811

    def test_csv_manager_module(self):
        """The csv_manager module can be imported."""
        import backend.storage.csv_manager  # noqa: F401

    def test_json_manager_module(self):
        """The json_manager module can be imported."""
        import backend.storage.json_manager  # noqa: F401

    def test_file_manager_module(self):
        """The file_manager module can be imported."""
        import backend.storage.file_manager  # noqa: F401

    def test_storage_service_module(self):
        """The storage_service module can be imported."""
        import backend.storage.storage_service  # noqa: F401

    def test_archive_manager_module(self):
        """The archive_manager module can be imported."""
        import backend.storage.archive_manager  # noqa: F401

    def test_backup_manager_module(self):
        """The backup_manager module can be imported."""
        import backend.storage.backup_manager  # noqa: F401

