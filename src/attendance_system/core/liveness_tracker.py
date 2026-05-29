"""Temporal smoothing of liveness scores using EMA + Hysteresis + IoU tracking.

This module provides frame-to-frame tracking of detected faces with
exponential moving average (EMA) smoothing of liveness scores and a
hysteresis state machine to prevent rapid SPOOF ↔ REAL transitions.

Algorithm (per frame):
  1. Greedy IoU match each detection → existing track.
  2. Matched tracks: update bbox, apply EMA, apply hysteresis.
  3. Unmatched detections → create new tracks.
  4. Unmatched existing tracks → increment miss counter.
  5. Prune tracks with misses > MAX_MISSES.
"""

from __future__ import annotations



# ── Constants ────────────────────────────────────────────────────────────────

ALPHA = 0.4
"""
EMA smoothing factor.

Higher values give more weight to the current observation, making the
smoothed score respond faster to changes but more susceptible to noise.
Lower values produce a smoother but more lagging estimate.
``ema = ALPHA * new_score + (1 - ALPHA) * previous_ema``
"""

T_HIGH = 0.65
"""Threshold to transition SPOOF → REAL (must reach or exceed this value)."""

T_LOW = 0.45
"""Threshold to transition REAL → SPOOF (must drop below this value)."""

MAX_MISSES = 3
"""
Number of consecutive frames a track can be unmatched before deletion.
Tolerates occasional missed detections (e.g. blinking, fast head turn).
"""

IOU_THRESHOLD = 0.5
"""Minimum Intersection-over-Union to consider two detections the same face."""


# ── Helpers ──────────────────────────────────────────────────────────────────


def compute_iou(
    bbox1: tuple[float, float, float, float],
    bbox2: tuple[float, float, float, float],
) -> float:
    """Compute Intersection over Union of two bounding boxes in (x, y, w, h) format.

    Args:
        bbox1: First bounding box ``(x, y, w, h)``.
        bbox2: Second bounding box ``(x, y, w, h)``.

    Returns:
        IoU in [0, 1].  Returns 0.0 if there is no overlap.
    """
    # Convert from (x, y, w, h) → (x1, y1, x2, y2)
    ax1, ay1 = bbox1[0], bbox1[1]
    ax2, ay2 = bbox1[0] + bbox1[2], bbox1[1] + bbox1[3]
    bx1, by1 = bbox2[0], bbox2[1]
    bx2, by2 = bbox2[0] + bbox2[2], bbox2[1] + bbox2[3]

    # Intersection rectangle
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0

    # Union = area(A) + area(B) - intersection
    area1 = bbox1[2] * bbox1[3]
    area2 = bbox2[2] * bbox2[3]
    union = area1 + area2 - inter
    if union <= 0.0:
        return 0.0

    return inter / union


# ── Classes ──────────────────────────────────────────────────────────────────


class TrackedFace:
    """A single tracked face with EMA-smoothed liveness score and hysteresis state.

    Hysteresis prevents rapid state flipping at boundary values:
      - SPOOF → REAL transition requires ``ema_score >= T_HIGH``.
      - REAL → SPOOF transition requires ``ema_score < T_LOW``.
    """

    __slots__ = ("bbox", "ema_score", "state", "misses")

    def __init__(
        self,
        bbox: tuple[float, float, float, float],
        initial_score: float,
    ) -> None:
        self.bbox: tuple[float, float, float, float] = bbox
        self.ema_score: float = initial_score
        # Initial state: SPOOF unless the score is already above the high bar
        self.state: str = "SPOOF" if initial_score < T_HIGH else "REAL"
        self.misses: int = 0


class LivenessTracker:
    """Tracks faces across frames via IoU matching with EMA + hysteresis.

    Usage::

        tracker = LivenessTracker()
        while capturing:
            bboxes = [(x1, y1, w1, h1), ...]   # from face detector
            scores = [0.82, 0.31, ...]          # from liveness model
            results = tracker.update(bboxes, scores)
            for bbox, state, ema_score in results:
                if state == "REAL":
                    ...  # proceed with recognition
    """

    def __init__(self) -> None:
        self.tracks: dict[int, TrackedFace] = {}
        """Active tracks keyed by a monotonic integer ID."""
        self.next_id: int = 0
        """Next available track ID."""

    def update(
        self,
        bboxes: list[tuple[float, float, float, float]],
        raw_scores: list[float],
    ) -> list[tuple[tuple[float, float, float, float], str, float]]:
        """Update tracker with one frame of detections.

        Args:
            bboxes: List of bounding boxes in ``(x, y, w, h)`` format.
            raw_scores: List of raw liveness scores (logit_diff from
                :class:`~attendance_system.services.ai_pipeline.LivenessChecker`).

        Returns:
            List of ``(bbox, state, ema_score)`` tuples for **all** currently
            active tracks.  Callers should match their own detections to the
            returned bboxes via :func:`compute_iou` to get the per-face result.
        """
        matched_ids: set[int] = set()

        for bbox, raw_score in zip(bboxes, raw_scores):
            bbox = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

            # ── Greedy IoU matching ──────────────────────────────────────
            # Find the best-matching unused track (highest IoU > IOU_THRESHOLD)
            best_id: int | None = None
            best_iou = IOU_THRESHOLD  # must be strictly greater than this

            for tid, track in self.tracks.items():
                if tid in matched_ids:
                    continue
                iou_val = compute_iou(bbox, track.bbox)
                if iou_val > best_iou:
                    best_iou = iou_val
                    best_id = tid

            if best_id is not None:
                # ── Update existing track ────────────────────────────────
                track = self.tracks[best_id]

                # EMA smoothing: ema = α · new + (1 − α) · ema
                track.ema_score = ALPHA * raw_score + (1.0 - ALPHA) * track.ema_score
                track.bbox = bbox
                track.misses = 0

                # Hysteresis state machine:
                #   SPOOF → REAL only when ema_score ≥ T_HIGH
                #   REAL → SPOOF only when ema_score < T_LOW
                #   Otherwise stay in current state (avoids boundary flicker)
                if track.state == "SPOOF" and track.ema_score >= T_HIGH:
                    track.state = "REAL"
                elif track.state == "REAL" and track.ema_score < T_LOW:
                    track.state = "SPOOF"

                matched_ids.add(best_id)
            else:
                # ── Create new track ─────────────────────────────────────
                self.tracks[self.next_id] = TrackedFace(bbox, raw_score)
                matched_ids.add(self.next_id)
                self.next_id += 1

        # ── Increment misses for unmatched tracks, prune stale ones ────
        for tid in list(self.tracks.keys()):
            if tid not in matched_ids:
                self.tracks[tid].misses += 1
                if self.tracks[tid].misses > MAX_MISSES:
                    del self.tracks[tid]

        # ── Build return list ───────────────────────────────────────────
        return [
            (track.bbox, track.state, track.ema_score)
            for track in self.tracks.values()
        ]
