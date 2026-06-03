"""Unit tests for PipelineResult dataclass."""

from __future__ import annotations

import numpy as np
import pytest

from attendance_system.services.pipeline_result import PipelineResult


class TestPipelineResultBasics:
    """Test dataclass fundamentals: construction, defaults, equality."""

    def test_minimal_construction(self) -> None:
        """PipelineResult requires result_type and frame_counter."""
        pr = PipelineResult(result_type="success", frame_counter=42)
        assert pr.result_type == "success"
        assert pr.frame_counter == 42

    def test_optional_fields_default_none(self) -> None:
        """All optional fields default to None."""
        pr = PipelineResult(result_type="spoof", frame_counter=0)
        assert pr.liveness_score is None
        assert pr.user_id is None
        assert pr.full_name is None
        assert pr.student_id is None
        assert pr.similarity is None
        assert pr.matched_pose_label is None
        assert pr.pitch is None
        assert pr.yaw is None
        assert pr.roll is None
        assert pr.embedding is None

    def test_full_construction(self) -> None:
        """All fields can be set at construction time."""
        emb = np.array([1.0, 0.0, 0.5], dtype=np.float32)
        pr = PipelineResult(
            result_type="success",
            frame_counter=10,
            liveness_score=0.85,
            user_id=42,
            full_name="Alice",
            student_id="SV001",
            similarity=0.92,
            matched_pose_label="center",
            pitch=1.5,
            yaw=-2.3,
            roll=0.1,
            embedding=emb,
        )
        assert pr.user_id == 42
        assert pr.full_name == "Alice"
        assert pr.similarity == 0.92
        assert np.array_equal(pr.embedding, emb)

    def test_equality(self) -> None:
        """Two PipelineResults with same fields are equal."""
        a = PipelineResult(result_type="success", frame_counter=1, user_id=10)
        b = PipelineResult(result_type="success", frame_counter=1, user_id=10)
        assert a == b

    def test_inequality(self) -> None:
        """PipelineResults with different fields are not equal."""
        a = PipelineResult(result_type="success", frame_counter=1)
        b = PipelineResult(result_type="spoof", frame_counter=1)
        assert a != b

    def test_slots(self) -> None:
        """PipelineResult uses __slots__ for memory efficiency."""
        pr = PipelineResult(result_type="x", frame_counter=0)
        assert hasattr(pr, "__slots__")
        # Should not be able to add arbitrary attributes
        with pytest.raises(AttributeError):
            pr.nonexistent_field = "test"  # type: ignore[attr-defined]


class TestPipelineResultAttendance:
    """Test PipelineResult for attendance pipeline use cases."""

    def test_spoof_result(self) -> None:
        pr = PipelineResult(
            result_type="spoof",
            frame_counter=5,
            liveness_score=0.32,
        )
        assert pr.result_type == "spoof"
        assert pr.liveness_score == 0.32
        assert pr.user_id is None

    def test_unrecognized_result(self) -> None:
        pr = PipelineResult(
            result_type="unrecognized",
            frame_counter=5,
            liveness_score=0.78,
        )
        assert pr.result_type == "unrecognized"
        assert pr.user_id is None

    def test_success_result(self) -> None:
        pr = PipelineResult(
            result_type="success",
            frame_counter=5,
            liveness_score=0.91,
            user_id=7,
            full_name="Bob",
            student_id="SV007",
            similarity=0.88,
            matched_pose_label="right",
        )
        assert pr.result_type == "success"
        assert pr.user_id == 7
        assert pr.full_name == "Bob"
        assert pr.similarity == 0.88


class TestPipelineResultEnrollment:
    """Test PipelineResult for enrollment pipeline use cases."""

    def test_pose_only_result(self) -> None:
        pr = PipelineResult(
            result_type="pose_only",
            frame_counter=3,
            pitch=10.5,
            yaw=-5.2,
            roll=1.0,
        )
        assert pr.result_type == "pose_only"
        assert pr.pitch == 10.5
        assert pr.embedding is None

    def test_capture_success_result(self) -> None:
        emb = np.ones(128, dtype=np.float32)
        pr = PipelineResult(
            result_type="capture_success",
            frame_counter=3,
            liveness_score=0.95,
            pitch=0.0,
            yaw=0.0,
            roll=0.0,
            embedding=emb,
        )
        assert pr.result_type == "capture_success"
        assert pr.liveness_score == 0.95
        assert np.array_equal(pr.embedding, emb)

    def test_capture_fail_result(self) -> None:
        pr = PipelineResult(
            result_type="capture_fail",
            frame_counter=3,
            liveness_score=0.2,
            pitch=5.0,
            yaw=3.0,
            roll=0.5,
        )
        assert pr.result_type == "capture_fail"
        assert pr.embedding is None

    def test_capture_fail_no_pose(self) -> None:
        """capture_fail can occur before pose is estimated (empty crop)."""
        pr = PipelineResult(
            result_type="capture_fail",
            frame_counter=3,
        )
        assert pr.pitch is None
        assert pr.embedding is None
