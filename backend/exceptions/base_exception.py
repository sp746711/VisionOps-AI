"""VisionOps AI — Base exception class.

This module defines the root exception for all VisionOps-specific errors.
"""


class VisionOpsError(Exception):
    """Base exception for all VisionOps AI errors."""

    def __init__(self, message: str = "A VisionOps error occurred") -> None:
        self.message = message
        super().__init__(self.message)

