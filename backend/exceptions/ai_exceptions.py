"""VisionOps AI — AI / ML exception classes.

These exceptions cover model inference, object detection, tracking,
frame extraction, and other AI/ML operations.
"""

from .base_exception import VisionOpsError


class AIError(VisionOpsError):
    """Base exception for all AI / ML operations."""

