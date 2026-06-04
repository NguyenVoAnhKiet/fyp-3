"""Unit tests for AIPipeline orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from attendance_system.services.ai_pipeline import (
    AIPipeline,
    LivenessChecker,
    FaceRecognizer,
    LivenessResult,
    RecognitionResult,
)
from attendance_system.services.exceptions import LivenessInferenceError, PoseInferenceError
from attendance_system.services.pipeline_result import PipelineResult


def _make_face_row() -> np.ndarray:
    """15-element YuNet face row: x, y, w, h, landmarks (5 pts), confidence."""
    return np.array(
        [100, 100, 160, 160, 120, 140, 180, 140, 150, 160, 130, 180, 170, 180, 0.99],
        dtype=np.float32,
    )


# ==============================================================================
# run_attendance tests
# ==============================================================================


class TestRunAttendance:
    """Test AIPipeline.run_attendance() — liveness → temporal smoothing → recognition."""

    def test_spoof_result(self) -> None:
        """Liveness tracker returns SPOOF → result_type is 'spoof'."""
        liveness = MagicMock(spec=LivenessChecker)
        # Raw score below T_HIGH (0.65) → tracker starts as SPOOF
        liveness.check.return_value = LivenessResult(is_real=False, score=0.2)
        recognizer = MagicMock(spec=FaceRecognizer)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 1)

        assert result.result_type == "spoof"
        assert result.frame_counter == 1
        assert result.liveness_score is not None
        assert result.user_id is None
        recognizer.identify.assert_not_called()

    def test_unrecognized_result(self) -> None:
        """Liveness passes but no recognition match → 'unrecognized'."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.return_value = LivenessResult(is_real=True, score=0.9)
        recognizer = MagicMock(spec=FaceRecognizer)
        recognizer.identify.return_value = None

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 5)

        assert result.result_type == "unrecognized"
        assert result.frame_counter == 5
        assert result.liveness_score == pytest.approx(0.9)

    def test_success_result(self) -> None:
        """Liveness passes and recognition matches → 'success'."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.return_value = LivenessResult(is_real=True, score=0.9)
        recognizer = MagicMock(spec=FaceRecognizer)
        recognizer.identify.return_value = RecognitionResult(
            user_id=42,
            full_name="Alice",
            student_id="SV001",
            similarity=0.92,
            matched_pose_label="center",
        )

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 10)

        assert result.result_type == "success"
        assert result.user_id == 42
        assert result.full_name == "Alice"
        assert result.student_id == "SV001"
        assert result.similarity == 0.92
        assert result.matched_pose_label == "center"

    def test_liveness_error_propagates(self) -> None:
        """LivenessInferenceError from checker propagates to caller."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.side_effect = LivenessInferenceError("ONNX failed")
        recognizer = MagicMock(spec=FaceRecognizer)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        with pytest.raises(LivenessInferenceError):
            pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 1)

    def test_tracker_state_persists_across_frames(self) -> None:
        """LivenessTracker EMA carries over between consecutive run_attendance calls."""
        liveness = MagicMock(spec=LivenessChecker)
        recognizer = MagicMock(spec=FaceRecognizer)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        # Frame 1: low score (SPOOF)
        liveness.check.return_value = LivenessResult(is_real=False, score=0.1)
        r1 = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 1)
        assert r1.result_type == "spoof"

        # Frame 2: same face, score still low but slightly higher
        liveness.check.return_value = LivenessResult(is_real=False, score=0.3)
        r2 = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 2)
        # Should still be spoof because EMA hasn't crossed T_HIGH
        assert r2.result_type == "spoof"

    def test_reset_tracker(self) -> None:
        """reset_tracker() clears tracker state."""
        liveness = MagicMock(spec=LivenessChecker)
        recognizer = MagicMock(spec=FaceRecognizer)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        # Create a track
        liveness.check.return_value = LivenessResult(is_real=True, score=0.9)
        pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 1)
        assert len(pipeline._liveness_tracker.tracks) > 0

        # Reset
        pipeline.reset_tracker()
        assert len(pipeline._liveness_tracker.tracks) == 0


# ==============================================================================
# run_enrollment tests
# ==============================================================================


class TestRunEnrollment:
    """Test AIPipeline.run_enrollment() — head-pose → liveness → embedding."""

    def test_pose_only_result(self) -> None:
        """do_capture=False → only head-pose estimated."""
        liveness = MagicMock(spec=LivenessChecker)
        recognizer = MagicMock(spec=FaceRecognizer)
        head_pose = MagicMock()
        head_pose.estimate.return_value = (10.0, 20.0, 5.0)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_enrollment(frame_bgr, face_row, 1, do_capture=False)

        assert result.result_type == "pose_only"
        assert result.pitch == 10.0
        assert result.yaw == 20.0
        assert result.roll == 5.0
        assert result.embedding is None
        liveness.check.assert_not_called()
        recognizer.get_embedding.assert_not_called()

    def test_capture_success(self) -> None:
        """do_capture=True, liveness real, embedding extracted → 'capture_success'."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.return_value = LivenessResult(is_real=True, score=0.95)
        recognizer = MagicMock(spec=FaceRecognizer)
        expected_emb = np.ones(128, dtype=np.float32)
        recognizer.get_embedding.return_value = expected_emb
        head_pose = MagicMock()
        head_pose.estimate.return_value = (0.0, 0.0, 0.0)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_enrollment(frame_bgr, face_row, 3, do_capture=True)

        assert result.result_type == "capture_success"
        assert result.liveness_score == pytest.approx(0.95)
        assert np.array_equal(result.embedding, expected_emb)
        assert result.pitch == 0.0

    def test_capture_fail_spoof(self) -> None:
        """do_capture=True, liveness spoof → 'capture_fail'."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.return_value = LivenessResult(is_real=False, score=0.2)
        recognizer = MagicMock(spec=FaceRecognizer)
        head_pose = MagicMock()
        head_pose.estimate.return_value = (0.0, 0.0, 0.0)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_enrollment(frame_bgr, face_row, 3, do_capture=True)

        assert result.result_type == "capture_fail"
        assert result.liveness_score == pytest.approx(0.2)
        assert result.embedding is None
        recognizer.get_embedding.assert_not_called()

    def test_capture_fail_no_embedding(self) -> None:
        """do_capture=True, liveness real, but embedding returns None → 'capture_fail'."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.return_value = LivenessResult(is_real=True, score=0.95)
        recognizer = MagicMock(spec=FaceRecognizer)
        recognizer.get_embedding.return_value = None
        head_pose = MagicMock()
        head_pose.estimate.return_value = (0.0, 0.0, 0.0)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        result = pipeline.run_enrollment(frame_bgr, face_row, 3, do_capture=True)

        assert result.result_type == "capture_fail"
        assert result.embedding is None

    def test_pose_error_propagates(self) -> None:
        """PoseInferenceError from head_pose_estimator propagates."""
        liveness = MagicMock(spec=LivenessChecker)
        recognizer = MagicMock(spec=FaceRecognizer)
        head_pose = MagicMock()
        head_pose.estimate.side_effect = PoseInferenceError("model error")

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        with pytest.raises(PoseInferenceError):
            pipeline.run_enrollment(frame_bgr, face_row, 1)

    def test_no_head_pose_estimator_raises(self) -> None:
        """run_enrollment() without head_pose_estimator raises RuntimeError."""
        liveness = MagicMock(spec=LivenessChecker)
        recognizer = MagicMock(spec=FaceRecognizer)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=None,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        with pytest.raises(RuntimeError, match="HeadPoseEstimator required"):
            pipeline.run_enrollment(frame_bgr, face_row, 1)

    def test_liveness_error_during_capture_propagates(self) -> None:
        """LivenessInferenceError during capture step propagates."""
        liveness = MagicMock(spec=LivenessChecker)
        liveness.check.side_effect = LivenessInferenceError("ONNX error")
        recognizer = MagicMock(spec=FaceRecognizer)
        head_pose = MagicMock()
        head_pose.estimate.return_value = (0.0, 0.0, 0.0)

        pipeline = AIPipeline(
            liveness_checker=liveness,
            face_recognizer=recognizer,
            head_pose_estimator=head_pose,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )

        frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        face_row = _make_face_row()

        with pytest.raises(LivenessInferenceError):
            pipeline.run_enrollment(frame_bgr, face_row, 1, do_capture=True)


# ==============================================================================
# Dependency injection tests
# ==============================================================================


class TestDependencyInjection:
    """Test that AIPipeline correctly composes dependencies."""

    def test_thresholds_are_required(self) -> None:
        """Plan 0005: thresholds are required (no defaults) — callers must
        thread them from the resolved :class:`SystemConfig`."""
        with pytest.raises(TypeError):
            AIPipeline(
                liveness_checker=MagicMock(spec=LivenessChecker),
                face_recognizer=MagicMock(spec=FaceRecognizer),
            )

    def test_custom_thresholds(self) -> None:
        """Custom thresholds are respected."""
        pipeline = AIPipeline(
            liveness_checker=MagicMock(spec=LivenessChecker),
            face_recognizer=MagicMock(spec=FaceRecognizer),
            liveness_threshold=0.5,
            similarity_threshold=0.8,
        )
        assert pipeline._liveness_threshold == 0.5
        assert pipeline._similarity_threshold == 0.8

    def test_each_instance_has_own_tracker(self) -> None:
        """Each AIPipeline instance has its own LivenessTracker."""
        p1 = AIPipeline(
            liveness_checker=MagicMock(spec=LivenessChecker),
            face_recognizer=MagicMock(spec=FaceRecognizer),
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )
        p2 = AIPipeline(
            liveness_checker=MagicMock(spec=LivenessChecker),
            face_recognizer=MagicMock(spec=FaceRecognizer),
            liveness_threshold=0.5,
            similarity_threshold=0.6,
        )
        assert p1._liveness_tracker is not p2._liveness_tracker
