"""Unit tests for LivenessTracker — EMA smoothing, IoU tracking, multi-face."""

from __future__ import annotations

import math

import pytest

from attendance_system.services.liveness_tracker import (
    ALPHA,
    IOU_THRESHOLD,
    MAX_MISSES,
    LivenessTracker,
    TrackedFace,
    compute_iou,
)


# ── compute_iou ──────────────────────────────────────────────────────────────


class TestComputeIoU:
    def test_perfect_overlap(self) -> None:
        bbox = (10.0, 20.0, 100.0, 200.0)
        assert compute_iou(bbox, bbox) == pytest.approx(1.0)

    def test_no_overlap(self) -> None:
        bbox1 = (0.0, 0.0, 10.0, 10.0)
        bbox2 = (20.0, 20.0, 10.0, 10.0)
        assert compute_iou(bbox1, bbox2) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        # Two 10×10 boxes overlapping by 5×5 = 25 px²
        # area1 = 100, area2 = 100, inter = 25, union = 175 → IoU = 25/175 ≈ 0.1429
        bbox1 = (0.0, 0.0, 10.0, 10.0)
        bbox2 = (5.0, 5.0, 10.0, 10.0)
        expected = 25.0 / 175.0
        assert compute_iou(bbox1, bbox2) == pytest.approx(expected)

    def test_contained(self) -> None:
        # One box fully inside the other
        bbox1 = (0.0, 0.0, 100.0, 100.0)
        bbox2 = (10.0, 10.0, 20.0, 20.0)
        # inter = 20*20 = 400, union = 10000 + 400 - 400 = 10000 → IoU = 400/10000 = 0.04
        assert compute_iou(bbox1, bbox2) == pytest.approx(0.04)

    def test_zero_area_bbox(self) -> None:
        bbox1 = (0.0, 0.0, 0.0, 10.0)
        bbox2 = (0.0, 0.0, 10.0, 10.0)
        assert compute_iou(bbox1, bbox2) == pytest.approx(0.0)

    def test_int_coordinates(self) -> None:
        iou = compute_iou((0, 0, 10, 10), (5, 5, 10, 10))
        expected = 25.0 / 175.0
        assert iou == pytest.approx(expected)


# ── LivenessTracker ──────────────────────────────────────────────────────────


class TestLivenessTrackerEmptyUpdate:
    def test_empty_update_returns_empty(self) -> None:
        tracker = LivenessTracker()
        result = tracker.update([], [])
        assert result == []

    def test_empty_update_prunes_stale_tracks(self) -> None:
        tracker = LivenessTracker()
        # Add a track manually
        tracker.tracks[0] = TrackedFace((0, 0, 50, 50), 0.5)
        tracker.tracks[0].misses = MAX_MISSES + 1
        result = tracker.update([], [])
        assert result == []
        assert len(tracker.tracks) == 0


class TestLivenessTrackerSingleFace:
    def test_first_detection_creates_track(self) -> None:
        tracker = LivenessTracker()
        result = tracker.update([(10, 10, 100, 100)], [0.8])
        assert len(result) == 1
        bbox, score, tid = result[0]
        assert bbox == (10.0, 10.0, 100.0, 100.0)
        assert score == pytest.approx(0.8)

    def test_ema_smoothing(self) -> None:
        """EMA: ema = ALPHA * new + (1-ALPHA) * ema"""
        tracker = LivenessTracker()
        # First update: ema = 0.6
        tracker.update([(0, 0, 50, 50)], [0.6])
        # Second update with same bbox: ema = 0.4 * 0.9 + 0.6 * 0.6 = 0.36 + 0.36 = 0.72
        result = tracker.update([(0, 0, 50, 50)], [0.9])
        _, score, _ = result[0]
        expected = ALPHA * 0.9 + (1.0 - ALPHA) * 0.6
        assert score == pytest.approx(expected)

    def test_face_disappears_then_reappears(self) -> None:
        """Track is maintained for MAX_MISSES frames, then deleted."""
        tracker = LivenessTracker()
        # Start track
        tracker.update([(0, 0, 50, 50)], [0.8])
        assert len(tracker.tracks) == 1

        # Face disappears for MAX_MISSES frames
        for i in range(MAX_MISSES):
            result = tracker.update([], [])
            assert len(result) == 1  # still alive
            assert list(tracker.tracks.values())[0].misses == i + 1

        # One more miss → track deleted
        result = tracker.update([], [])
        assert len(result) == 0
        assert len(tracker.tracks) == 0

    def test_face_reappears_before_deletion(self) -> None:
        """Track resumes when face reappears within MAX_MISSES."""
        tracker = LivenessTracker()
        tracker.update([(0, 0, 50, 50)], [0.8])
        # Miss 2 frames
        tracker.update([], [])
        tracker.update([], [])
        assert list(tracker.tracks.values())[0].misses == 2

        # Reappear → misses reset
        tracker.update([(0, 0, 50, 50)], [0.9])
        assert list(tracker.tracks.values())[0].misses == 0


class TestLivenessTrackerMultiFace:
    def test_two_faces_tracked_independently(self) -> None:
        tracker = LivenessTracker()
        bboxes = [(10, 10, 50, 50), (200, 200, 60, 60)]
        scores = [0.9, 0.2]
        result = tracker.update(bboxes, scores)
        assert len(result) == 2
        # Each result is (bbox, score, track_id)
        scores_list = [r[1] for r in result]
        assert any(s >= 0.9 for s in scores_list)  # face 1 high
        assert any(s <= 0.2 for s in scores_list)  # face 2 low

    def test_two_faces_ema_independent(self) -> None:
        tracker = LivenessTracker()
        # First frame
        tracker.update([(10, 10, 50, 50), (200, 200, 60, 60)], [0.9, 0.2])

        # Second frame — face 1 gets high score, face 2 gets low score
        result = tracker.update([(10, 10, 50, 50), (200, 200, 60, 60)], [0.95, 0.15])
        assert len(result) == 2

        # Sort by x coordinate
        sorted_results = sorted(result, key=lambda r: r[0][0])
        # Face 1 (left): starts 0.9, ema = 0.4*0.95 + 0.6*0.9 = 0.92
        assert sorted_results[0][1] == pytest.approx(ALPHA * 0.95 + (1 - ALPHA) * 0.9)
        # Face 2 (right): starts 0.2, ema = 0.4*0.15 + 0.6*0.2 = 0.18
        assert sorted_results[1][1] == pytest.approx(ALPHA * 0.15 + (1 - ALPHA) * 0.2)

    def test_face_swap_maintains_tracks(self) -> None:
        """When two faces swap positions, tracks should follow by IoU."""
        tracker = LivenessTracker()
        # Frame 1: face A at (0,0), face B at (100,0)
        tracker.update([(0, 0, 50, 50), (100, 0, 50, 50)], [0.9, 0.1])

        # Frame 2: faces slightly moved — tracks follow by IoU
        result = tracker.update([(2, 2, 50, 50), (102, 2, 50, 50)], [0.85, 0.15])
        assert len(result) == 2
        sorted_by_x = sorted(result, key=lambda r: r[0][0])
        # Left face should have higher EMA score (from initial 0.9)
        assert sorted_by_x[0][1] > sorted_by_x[1][1]

    def test_new_face_appears_old_disappears(self) -> None:
        """New face creates new track; old face track gets pruned after misses."""
        tracker = LivenessTracker()
        # Frame 1: face A
        tracker.update([(0, 0, 50, 50)], [0.9])
        assert len(tracker.tracks) == 1

        # Frame 2: face A disappears, face B appears far away
        tracker.update([(300, 300, 50, 50)], [0.9])
        # Two tracks: A (misses=1), B (new)
        assert len(tracker.tracks) == 2

        # Frame 3+: face B continues, face A misses accumulate
        for _ in range(MAX_MISSES):
            tracker.update([(300, 300, 50, 50)], [0.9])

        # After MAX_MISSES misses, track A should be gone
        assert len(tracker.tracks) == 1
        bbox = list(tracker.tracks.values())[0].bbox
        assert bbox == (300.0, 300.0, 50.0, 50.0)


class TestLivenessTrackerEdgeCases:
    def test_bbox_converted_to_float(self) -> None:
        tracker = LivenessTracker()
        result = tracker.update([(10, 10, 50, 50)], [0.5])
        bbox = result[0][0]
        assert all(isinstance(v, float) for v in bbox)

    def test_negative_coordinates(self) -> None:
        tracker = LivenessTracker()
        # Should not crash with negative bbox coords
        result = tracker.update([(-10, -10, 50, 50)], [0.5])
        assert len(result) == 1

    def test_track_id_monotonic(self) -> None:
        tracker = LivenessTracker()
        tracker.update([(0, 0, 10, 10)], [0.5])
        assert tracker.next_id == 1
        tracker.update([(10, 10, 10, 10)], [0.5])  # low IoU → new track
        assert tracker.next_id == 2

    def test_clear_tracks(self) -> None:
        tracker = LivenessTracker()
        tracker.update([(0, 0, 10, 10)], [0.5])
        assert len(tracker.tracks) == 1
        tracker.tracks.clear()
        assert len(tracker.tracks) == 0


class TestLivenessTrackerIoUMatching:
    def test_low_iou_creates_new_track(self) -> None:
        """Two detections with IoU < threshold should be different tracks."""
        tracker = LivenessTracker()
        # Frame 1
        tracker.update([(0, 0, 50, 50)], [0.9])
        # Frame 2: face moved far away
        result = tracker.update([(200, 200, 50, 50)], [0.9])
        assert len(tracker.tracks) == 2

    def test_high_iou_updates_same_track(self) -> None:
        """Two detections with IoU >= threshold should be same track."""
        tracker = LivenessTracker()
        tracker.update([(0, 0, 50, 50)], [0.9])
        result = tracker.update([(5, 5, 50, 50)], [0.8])
        assert len(tracker.tracks) == 1
