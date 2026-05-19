"""Face processing utilities for detection, cropping, and utility functions."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _crop_face(
    frame: np.ndarray, bbox: tuple[int, int, int, int], scale: float = 1.5
) -> np.ndarray:
    """Return a padded crop of the face region specified by *bbox*."""
    x, y, w, h = bbox
    cx, cy = x + w // 2, y + h // 2
    side = int(max(w, h) * scale)
    half = side // 2
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, cx - half), max(0, cy - half)
    x2, y2 = min(fw, cx + half), min(fh, cy + half)
    return frame[y1:y2, x1:x2]


def _create_face_detector(
    model_path: Path | str,
    input_size: tuple[int, int] = (640, 480),
    score_threshold: float = 0.8,
    nms_threshold: float = 0.3,
) -> cv2.FaceDetectorYN:
    """Create and return a YuNet face detector.

    Parameters
    ----------
    model_path : Path | str
        Path to the YuNet ONNX model file.
    input_size : tuple[int, int]
        Input resolution for the detector (width, height).
    score_threshold : float
        Minimum face confidence score.
    nms_threshold : float
        Non-maximum suppression IoU threshold.

    Returns
    -------
    cv2.FaceDetectorYN
        Initialized face detector ready for detection.
    """
    return cv2.FaceDetectorYN.create(
        str(model_path), "", input_size, score_threshold, nms_threshold
    )
