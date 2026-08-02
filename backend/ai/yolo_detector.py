"""VisionOps AI — YOLO object detection adapter.

This module provides the low-level object-detection adapter around an
Ultralytics YOLO model.

Responsibilities
----------------
* Lazy, reusable model loading (never during import, never per-frame).
* Configurable model path, confidence threshold, IoU threshold, max
  detections, and inference device (from ``backend.core.config.settings``).
* Single-frame and batch inference.
* Normalization of third-party model output into the **existing project
  detection contract** consumed by
  :meth:`AnalysisService.run_detection
  <backend.services.analysis_service.AnalysisService.run_detection>`::

      {"class_name": str, "confidence": float, "bbox": [x, y, w, h], "track_id": None}

* Model readiness/status reporting and explicit model unload.

Dependency handling
-------------------
Ultralytics/Torch are optional dependencies.  They are imported lazily
when real inference is requested.  If they are unavailable, a clear
:class:`~backend.exceptions.AIError` is raised **only** when inference is
actually requested — never at import time.

Mock mode
---------
``use_mock=True`` is a **test-only** convenience that avoids loading any
model.  Mock mode does **not** fabricate detections, confidence scores, or
bounding boxes; :meth:`detect` simply returns an empty list.  Real
inference must be provided by an actual installed/available Ultralytics
installation.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Sequence

from backend.core.config import settings
from backend.exceptions import AIError, ValidationError
from backend.ai.utils.image_utils import validate_image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_DEVICES: frozenset[str] = frozenset({"cpu", "cuda", "mps", "auto"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _as_finite_float(value: object, *, name: str) -> float:
    """Convert *value* to a finite float, rejecting non-numeric values.

    Args:
        value: Value to convert (NumPy scalars accepted).
        name: Field name for error messages.

    Returns:
        Finite float.

    Raises:
        ValidationError: If the value is not a finite real number.
    """
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a number, got bool.")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{name} must be a number, got {value!r}."
        ) from exc
    if not math.isfinite(number):
        raise ValidationError(f"{name} must be finite, got {value!r}.")
    return number


def _normalize_coordinate(value: object, *, name: str) -> float:
    """Convert a coordinate to a finite non-negative float.

    Args:
        value: Raw coordinate value.
        name: Field name for error messages.

    Returns:
        Finite non-negative float.

    Raises:
        ValidationError: If the coordinate is invalid or negative.
    """
    number = _as_finite_float(value, name=name)
    if number < 0.0:
        raise ValidationError(f"{name} must be non-negative, got {number}.")
    return number


def _normalize_confidence(value: object) -> float:
    """Convert a raw confidence to a finite float in ``[0.0, 1.0]``.

    Args:
        value: Raw confidence value.

    Returns:
        Finite confidence in ``[0.0, 1.0]``.

    Raises:
        ValidationError: If the confidence is out of range.
    """
    number = _as_finite_float(value, name="confidence")
    if not (0.0 <= number <= 1.0):
        raise ValidationError(
            f"confidence must be in [0.0, 1.0], got {number}."
        )
    return number


# ---------------------------------------------------------------------------
# YOLODetector
# ---------------------------------------------------------------------------


class YOLODetector:
    """YOLO object-detection adapter (lazy, config-aware).

    The model is loaded on first inference via
    :meth:`_ensure_model_loaded`.  Subsequent calls reuse the same loaded
    model instance.  Call :meth:`unload_model` to free the model and force
    a reload on the next inference.

    Args:
        model_path: Path to the YOLO weights file.  If ``None``, the
            configured ``settings.YOLO_MODEL_PATH`` is used.
        confidence_threshold: Confidence threshold for detections.  If
            ``None``, ``settings.CONFIDENCE_THRESHOLD`` is used.
        iou_threshold: IoU threshold for NMS.  If ``None``,
            ``settings.IOU_THRESHOLD`` is used.
        max_detections: Maximum number of detections per frame.  If
            ``None``, ``settings.MAX_DETECTIONS`` is used.
        device: Inference device (``cpu``, ``cuda``, ``mps``, or
            ``auto``).  If ``None``, ``settings.DEVICE`` is used.
        use_mock: Test-only flag.  When ``True``, no model is loaded and
            :meth:`detect` returns an empty list.  Defaults to ``False``.
    """

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
        max_detections: int | None = None,
        device: str | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialise the YOLO detector (no model is loaded here)."""
        self._model_path: str = model_path or settings.YOLO_MODEL_PATH
        self._confidence_threshold: float = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.CONFIDENCE_THRESHOLD
        )
        self._iou_threshold: float = (
            iou_threshold if iou_threshold is not None else settings.IOU_THRESHOLD
        )
        self._max_detections: int = (
            max_detections if max_detections is not None else settings.MAX_DETECTIONS
        )
        self._device: str = device or settings.DEVICE
        self._use_mock: bool = bool(use_mock)

        self._model: Any | None = None
        self._names: dict[int, str] | None = None
        self._loaded: bool = False

        self._validate_config()

        if self._use_mock:
            logger.debug(
                "YOLODetector initialised in mock mode — real inference "
                "is disabled."
            )

    # ------------------------------------------------------------------
    # Configuration validation
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Validate the detector configuration at construction time.

        Raises:
            ValidationError: If any threshold/device/model-path value is
                invalid.
        """
        self.validate_model_path(self._model_path)

        self._confidence_threshold = _normalize_confidence(
            self._confidence_threshold
        )
        self._iou_threshold = _normalize_confidence(self._iou_threshold)

        if (
            isinstance(self._max_detections, bool)
            or not isinstance(self._max_detections, int)
            or self._max_detections < 1
        ):
            raise ValidationError(
                "max_detections must be a positive integer, got "
                f"{self._max_detections!r}."
            )

        if not isinstance(self._device, str) or not self._device.strip():
            raise ValidationError("device must be a non-empty string.")
        self._device = self._device.strip().lower()
        if self._device not in _VALID_DEVICES:
            raise ValidationError(
                f"Invalid device '{self._device}'. "
                f"Valid devices: {', '.join(sorted(_VALID_DEVICES))}."
            )

    @staticmethod
    def validate_model_path(model_path: str) -> str:
        """Validate a YOLO model path.

        Args:
            model_path: Model path string.

        Returns:
            The stripped, non-empty model path.

        Raises:
            ValidationError: If the path is empty/blank.
        """
        if not isinstance(model_path, str) or not model_path.strip():
            raise ValidationError("Model path must not be empty.")
        return model_path.strip()

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _resolve_device(self) -> str:
        """Resolve the effective inference device.

        ``auto`` is resolved by asking Torch (when available) which
        accelerator is present, falling back to ``cpu``.  CPU remains a
        supported baseline.

        Returns:
            One of ``cpu``, ``cuda``, or ``mps``.
        """
        if self._device == "auto":
            try:
                import torch  # lazy
            except ImportError:
                return "cpu"
            try:
                if torch.cuda.is_available():
                    return "cuda"
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    return "mps"
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Device auto-detection failed: %s", exc)
            return "cpu"
        return self._device

    def _ensure_model_loaded(self) -> None:
        """Load the YOLO model lazily (once).

        Raises:
            AIError: If Ultralytics/Torch is unavailable or the model
                fails to load.
            ValidationError: If the model path is empty.
        """
        if self._loaded and self._model is not None:
            return

        if self._use_mock:
            raise AIError(
                "YOLODetector is running in mock mode and cannot load a "
                "real model. Construct with use_mock=False for real "
                "inference."
            )

        self.validate_model_path(self._model_path)

        try:
            from ultralytics import YOLO  # lazy import
        except ImportError as exc:
            raise AIError(
                "Ultralytics (ultralytics) is required for YOLO inference "
                "but is not installed. Install 'ultralytics' to enable "
                "real object detection."
            ) from exc

        device = self._resolve_device()
        logger.info(
            "Loading YOLO model from '%s' on device '%s'...",
            self._model_path,
            device,
        )

        try:
            model = YOLO(self._model_path)
            if device != "auto":
                model.to(device)
            self._model = model
            self._names = getattr(model, "names", None)
            self._device = device
            self._loaded = True
        except Exception as exc:
            self._model = None
            self._loaded = False
            raise AIError(
                f"Failed to load YOLO model from '{self._model_path}' "
                f"on device '{device}': {exc}"
            ) from exc

        logger.info(
            "YOLO model loaded successfully from '%s' on '%s'.",
            self._model_path,
            device,
        )

    def unload_model(self) -> None:
        """Unload the model and free associated resources.

        The next call to :meth:`detect` reloads the model lazily.
        """
        model = self._model
        self._model = None
        self._names = None
        self._loaded = False
        if model is not None:
            logger.debug("YOLO model unloaded.")
        else:
            logger.debug("YOLO model unload requested (none loaded).")

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return ``True`` if the model is currently loaded."""
        return self._loaded and self._model is not None

    def get_model_info(self) -> dict[str, Any]:
        """Return metadata about the detector and model.

        Returns:
            Dictionary with keys ``model_path``, ``device``,
            ``confidence_threshold``, ``iou_threshold``,
            ``max_detections``, ``use_mock``, and ``loaded``.
        """
        return {
            "model_path": self._model_path,
            "device": self._device,
            "confidence_threshold": self._confidence_threshold,
            "iou_threshold": self._iou_threshold,
            "max_detections": self._max_detections,
            "use_mock": self._use_mock,
            "loaded": self.is_loaded(),
        }

    @property
    def names(self) -> dict[int, str] | None:
        """Return the model's class-name mapping (if loaded)."""
        return self._names

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def detect(self, frame: Any) -> list[dict[str, Any]]:
        """Run YOLO detection on a single frame.

        Args:
            frame: Image frame (BGR, ``HxWx3`` uint8 array).

        Returns:
            List of normalized detection dicts in the project contract::

                {
                    "class_name": str,
                    "confidence": float,
                    "bbox": [x, y, width, height],
                    "track_id": None,
                }

            In mock mode an empty list is returned (no fabricated
            detections).

        Raises:
            AIError: If inference fails or Ultralytics is unavailable.
            ValidationError: If the frame is invalid.
        """
        if self._use_mock:
            logger.debug("YOLO mock mode — returning no detections.")
            return []

        validate_image(frame)
        self._ensure_model_loaded()

        try:
            results = self._model(frame, verbose=False)
        except Exception as exc:
            raise AIError(f"YOLO inference failed: {exc}") from exc

        return self._parse_results(results)

    def detect_batch(self, frames: Sequence[Any]) -> list[list[dict[str, Any]]]:
        """Run YOLO detection on a batch of frames.

        Args:
            frames: Sequence of image frames.

        Returns:
            List of detection-dict lists (one per input frame).

        Raises:
            AIError: If inference fails or Ultralytics is unavailable.
            ValidationError: If any frame is invalid.
        """
        if self._use_mock:
            return [[] for _ in frames]

        if not isinstance(frames, (list, tuple)):
            raise ValidationError(
                f"frames must be a list/tuple, got {type(frames).__name__}."
            )

        for frame in frames:
            validate_image(frame)

        self._ensure_model_loaded()
        try:
            results = self._model(frames, verbose=False)
        except Exception as exc:
            raise AIError(f"YOLO batch inference failed: {exc}") from exc

        return [self._parse_results([r]) for r in results]

    # ------------------------------------------------------------------
    # Output normalization
    # ------------------------------------------------------------------

    def _parse_results(self, results: Any) -> list[dict[str, Any]]:
        """Normalize Ultralytics results into the project contract.

        Args:
            results: Output of ``model(frame)`` (a list of
                :class:`ultralytics.engine.results.Results`).

        Returns:
            List of normalized detection dicts.

        Raises:
            AIError: If the result format cannot be parsed.
        """
        if not results:
            return []

        first = results[0]
        boxes = getattr(first, "boxes", None)
        if boxes is None:
            return []

        names = self._names or {}
        detections: list[dict[str, Any]] = []

        try:
            xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy.numpy()
            confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else boxes.conf.numpy()
            cls_ids = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else boxes.cls.numpy()
        except Exception as exc:
            raise AIError(f"Failed to parse YOLO output: {exc}") from exc

        for box, conf, cls_id in zip(xyxy, confs, cls_ids):
            confidence = _normalize_confidence(float(conf))
            if confidence < self._confidence_threshold:
                continue

            class_index = int(cls_id)
            class_name = names.get(class_index, str(class_index))

            x1 = _normalize_coordinate(float(box[0]), name="bbox x1")
            y1 = _normalize_coordinate(float(box[1]), name="bbox y1")
            x2 = _normalize_coordinate(float(box[2]), name="bbox x2")
            y2 = _normalize_coordinate(float(box[3]), name="bbox y2")

            if x2 <= x1 or y2 <= y1:
                logger.debug(
                    "Skipping degenerate YOLO box: (%s, %s, %s, %s).",
                    x1, y1, x2, y2,
                )
                continue

            detections.append(
                {
                    "class_name": class_name,
                    "confidence": round(confidence, 6),
                    "bbox": [
                        round(x1, 2),
                        round(y1, 2),
                        round(x2 - x1, 2),
                        round(y2 - y1, 2),
                    ],
                    "track_id": None,
                }
            )

            if len(detections) >= self._max_detections:
                break

        return detections

    def __repr__(self) -> str:
        return (
            f"YOLODetector(model={self._model_path!r}, "
            f"device={self._device!r}, mock={self._use_mock}, "
            f"loaded={self.is_loaded()})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["YOLODetector"]

