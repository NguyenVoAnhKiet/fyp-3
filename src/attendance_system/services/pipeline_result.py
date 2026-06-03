"""PipelineResult: structured output of a single frame through the AI pipeline.

This module provides the `PipelineResult` dataclass that encapsulates all
possible outputs from the `AIPipeline` orchestrator. Callers use the
`result_type` discriminator to determine which fields are populated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["PipelineResult"]


@dataclass(slots=True)
class PipelineResult:
    """Structured output of a single frame through the AI pipeline.

    Fields are optional — only populated for the relevant pipeline mode:

    **Attendance pipeline** (``run_attendance``):
        ``result_type`` is ``"success"``, ``"spoof"``, or ``"unrecognized"``.
        Always sets ``liveness_score``. ``"success"`` also sets ``user_id``,
        ``full_name``, ``student_id``, ``similarity``, and
        ``matched_pose_label``.

    **Enrollment pipeline** (``run_enrollment``):
        ``result_type`` is ``"pose_only"``, ``"capture_success"``, or
        ``"capture_fail"``. Always sets ``pitch``, ``yaw``, ``roll``.
        ``"capture_success"`` also sets ``liveness_score`` and ``embedding``.

    Attributes:
        result_type: Discriminator string. One of ``"success"``,
            ``"spoof"``, ``"unrecognized"``, ``"pose_only"``,
            ``"capture_success"``, or ``"capture_fail"``.
        frame_counter: Frame number from the camera loop (metadata).
        liveness_score: EMA-smoothed liveness score (``None`` if liveness
            was not run or failed).
        user_id: Matched user ID (``None`` if no recognition match).
        full_name: Matched user's full name (``None`` if no match).
        student_id: Matched user's student ID (``None`` if no match).
        similarity: Cosine similarity score (``None`` if no match).
        matched_pose_label: Pose label of the matched reference
            (``None`` if no match).
        pitch: Head-pose pitch in degrees (``None`` if not estimated).
        yaw: Head-pose yaw in degrees (``None`` if not estimated).
        roll: Head-pose roll in degrees (``None`` if not estimated).
        embedding: Extracted face embedding vector (``None`` if not
            extracted or extraction failed).
    """

    # ── Required fields ────────────────────────────────────────────────
    result_type: str
    frame_counter: int

    # ── Liveness output ────────────────────────────────────────────────
    liveness_score: float | None = None

    # ── Recognition output (attendance pipeline) ──────────────────────
    user_id: int | None = None
    full_name: str | None = None
    student_id: str | None = None
    similarity: float | None = None
    matched_pose_label: str | None = None

    # ── Head-pose output (enrollment pipeline) ────────────────────────
    pitch: float | None = None
    yaw: float | None = None
    roll: float | None = None

    # ── Embedding output (enrollment pipeline) ────────────────────────
    embedding: np.ndarray | None = None
