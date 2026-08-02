"""VisionOps AI — Object classifier / class normalization.

This module provides lightweight **class normalization and mapping** for
detection output.  It does **not** implement a second neural-network
model; the underlying detector already emits class labels.  Its role is
to:

* Normalize arbitrary/raw class names (from a detector) into the project's
  canonical :class:`~backend.schemas.common.DetectionClass` vocabulary.
* Map class names to human-readable labels and display colors (useful for
  drawing utilities and downstream consumers).
* Preserve unknown classes as-is (lowercased) when they are not part of
  the canonical vocabulary.

The normalization is deterministic and dependency-free: no model, no
download, no random values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.schemas.common import DetectionClass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical label/color mapping for known classes (BGR colors are stored
#: as ``(b, g, r)`` since OpenCV draws in BGR).
_CLASS_STYLE: dict[str, tuple[str, tuple[int, int, int]]] = {
    "person": ("Person", (255, 0, 0)),
    "forklift": ("Forklift", (0, 255, 0)),
    "pallet": ("Pallet", (0, 255, 255)),
    "truck": ("Truck", (255, 0, 0)),
    "dock": ("Dock", (255, 255, 0)),
    "product": ("Product", (255, 0, 255)),
    "spoiled_food": ("Spoiled Food", (0, 0, 255)),
}

#: Aliases that map to canonical class names.
_CLASS_ALIASES: dict[str, str] = {
    "person": "person",
    "people": "person",
    "forklift": "forklift",
    "forklifts": "forklift",
    "pallet": "pallet",
    "pallets": "pallet",
    "truck": "truck",
    "trucks": "truck",
    "dock": "dock",
    "loading_dock": "dock",
    "product": "product",
    "products": "product",
    "spoiled_food": "spoiled_food",
    "spoiled": "spoiled_food",
    "spoilage": "spoiled_food",
}


@dataclass(frozen=True)
class ClassInfo:
    """Metadata for a detected object class.

    Attributes:
        name: Canonical class name (lowercase).
        label: Human-readable display label.
        color: BGR ``(b, g, r)`` tuple for drawing annotations.
        is_known: ``True`` if the class is part of the project's canonical
            vocabulary.
    """

    name: str
    label: str
    color: tuple[int, int, int]
    is_known: bool


# ---------------------------------------------------------------------------
# ObjectClassifier
# ---------------------------------------------------------------------------


class ObjectClassifier:
    """Deterministic class normalization/mapping utility.

    Converts raw detector class names into the project's canonical
    vocabulary and resolves human-readable labels and colors.

    Args:
        labels: Optional mapping of class name -> human-readable label.
            When ``None``, the built-in canonical labels are used.
        colors: Optional mapping of class name -> BGR color tuple.
            When ``None``, the built-in canonical colors are used.
    """

    def __init__(
        self,
        labels: dict[str, str] | None = None,
        colors: dict[str, tuple[int, int, int]] | None = None,
    ) -> None:
        """Initialise the classifier with optional override mappings."""
        self._labels: dict[str, str] = {
            name: label for name, (label, _) in _CLASS_STYLE.items()
        }
        self._colors: dict[str, tuple[int, int, int]] = {
            name: color for name, (_, color) in _CLASS_STYLE.items()
        }
        if labels:
            self._labels.update(labels)
        if colors:
            self._colors.update(colors)

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_class_name(raw: str) -> str:
        """Normalize a raw class name.

        Aliases are resolved to canonical names, and the result is
        lowercased/stripped.

        Args:
            raw: Raw class name.

        Returns:
            The normalized class name (lowercase).

        Raises:
            ValueError: If *raw* is not a non-empty string.
        """
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"class_name must be a non-empty string, got {raw!r}.")
        normalized = raw.strip().lower()
        return _CLASS_ALIASES.get(normalized, normalized)

    def get_class_info(self, class_name: str, label: str | None = None) -> ClassInfo:
        """Return rich metadata for a class name.

        Args:
            class_name: Raw class name.
            label: Optional override label.

        Returns:
            A :class:`ClassInfo` record.
        """
        normalized = self.normalize_class_name(class_name)
        is_known = normalized in self._labels
        resolved_label = label or self._labels.get(normalized, normalized.title())
        color = self._colors.get(normalized, (0, 255, 0))
        return ClassInfo(
            name=normalized,
            label=resolved_label,
            color=color,
            is_known=is_known,
        )

    # ------------------------------------------------------------------
    # Detection classification
    # ------------------------------------------------------------------

    def classify(
        self,
        detections: list[dict[str, Any]],
        use_mock: bool = False,
    ) -> list[dict[str, Any]]:
        """Normalize a list of detection dicts in place (returns new dicts).

        Each detection dict is expected to contain a ``class_name`` key.
        The produced output preserves all existing keys and adds:

        * ``class_name`` — normalized canonical name (aliases resolved).
        * ``label`` — human-readable display label.
        * ``class_color`` — BGR ``(b, g, r)`` color for drawing.

        Args:
            detections: List of raw detection dicts.
            use_mock: Test-only flag.  When ``True``, the same
                normalization is applied (no model).  Kept for API parity
                with the rest of the package.

        Returns:
            List of normalized detection dicts.  Entries that are not
            dicts or lack a valid ``class_name`` are dropped (logged).

        Raises:
            ValueError: If *detections* is not a list.
        """
        del use_mock  # normalization is deterministic; no mock branch needed
        if not isinstance(detections, list):
            raise ValueError(
                f"detections must be a list, got {type(detections).__name__}."
            )

        result: list[dict[str, Any]] = []
        for idx, det in enumerate(detections):
            if not isinstance(det, dict):
                logger.debug(
                    "Classification: detection at index %d is not a dict, skipping.",
                    idx,
                )
                continue
            raw_class = det.get("class_name")
            if not isinstance(raw_class, str) or not raw_class.strip():
                logger.debug(
                    "Classification: detection at index %d missing valid "
                    "class_name, skipping.",
                    idx,
                )
                continue

            try:
                info = self.get_class_info(raw_class)
            except ValueError:
                logger.debug(
                    "Classification: detection at index %d has invalid class, "
                    "skipping.",
                    idx,
                )
                continue

            entry = dict(det)
            entry["class_name"] = info.name
            entry["label"] = info.label
            entry["class_color"] = list(info.color)
            result.append(entry)

        return result

    def classify_single(self, detection: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize a single detection dict.

        Args:
            detection: Raw detection dict.

        Returns:
            The normalized dict (preserving all keys and adding ``label``/
            ``class_color``), or ``None`` if the dict is invalid.
        """
        return self.classify([detection])[0] if self.classify([detection]) else None

    # ------------------------------------------------------------------
    # Class labels
    # ------------------------------------------------------------------

    def get_class_labels(self) -> list[str]:
        """Return the list of canonical class labels.

        Returns:
            Sorted list of known canonical class names.
        """
        return sorted(self._labels)

    def is_known_class(self, class_name: str) -> bool:
        """Check whether a class name is part of the canonical vocabulary.

        Args:
            class_name: Raw class name.

        Returns:
            ``True`` if the normalized name is known.
        """
        return self.normalize_class_name(class_name) in self._labels

    def __repr__(self) -> str:
        return f"ObjectClassifier(classes={len(self._labels)}, aliases={len(_CLASS_ALIASES)})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["ObjectClassifier", "ClassInfo"]

