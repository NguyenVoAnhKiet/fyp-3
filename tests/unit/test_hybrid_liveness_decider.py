"""Unit tests for HybridLivenessDecider — majority voting, recognition boost, reset."""

from __future__ import annotations

import pytest

from attendance_system.services.hybrid_liveness_decider import (
    HybridDecision,
    HybridLivenessDecider,
)


class TestHybridLivenessDeciderInit:
    def test_default_params(self) -> None:
        d = HybridLivenessDecider()
        assert d._threshold == 0.5
        assert d._voting_window == 5
        assert d._boost_amount == 0.15
        assert d._min_frames == 3
        assert d.buffer_size == 0

    def test_custom_params(self) -> None:
        d = HybridLivenessDecider(
            liveness_threshold=0.6,
            voting_window=7,
            boost_amount=0.2,
        )
        assert d._threshold == 0.6
        assert d._voting_window == 7
        assert d._min_frames == 5  # 7 - 2
        assert d._boost_amount == 0.2

    def test_invalid_voting_window_raises(self) -> None:
        with pytest.raises(ValueError, match="voting_window"):
            HybridLivenessDecider(voting_window=0)

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="liveness_threshold"):
            HybridLivenessDecider(liveness_threshold=1.5)

    def test_invalid_boost_raises(self) -> None:
        with pytest.raises(ValueError, match="boost_amount"):
            HybridLivenessDecider(boost_amount=-0.1)


class TestHybridLivenessDeciderVoting:
    def test_majority_vote_real(self) -> None:
        """3/5 frames above threshold → REAL."""
        d = HybridLivenessDecider()
        # Add 3 above-threshold, 2 below-threshold frames
        for score in [0.8, 0.7, 0.9, 0.3, 0.2]:
            result = d.update(score)
        assert result.state == "REAL"
        assert result.voting_ratio == pytest.approx(3.0 / 5.0)
        assert result.frames_in_buffer == 5

    def test_majority_vote_spoof(self) -> None:
        """2/5 frames above threshold → SPOOF."""
        d = HybridLivenessDecider()
        for score in [0.8, 0.3, 0.9, 0.2, 0.1]:
            result = d.update(score)
        assert result.state == "SPOOF"
        assert result.voting_ratio == pytest.approx(2.0 / 5.0)

    def test_exact_threshold_boundary(self) -> None:
        """Score exactly at threshold counts as real vote."""
        d = HybridLivenessDecider(liveness_threshold=0.5)
        # 3 frames at exactly 0.5 → should be REAL
        for score in [0.5, 0.5, 0.5, 0.4, 0.3]:
            result = d.update(score)
        assert result.state == "REAL"

    def test_all_spoof_scores(self) -> None:
        """All frames below threshold → SPOOF."""
        d = HybridLivenessDecider()
        for score in [0.1, 0.2, 0.1, 0.3, 0.2]:
            result = d.update(score)
        assert result.state == "SPOOF"
        assert result.voting_ratio == pytest.approx(0.0)

    def test_all_real_scores(self) -> None:
        """All frames ≥ 1.0 (bypass mode) → REAL."""
        d = HybridLivenessDecider()
        for _ in range(5):
            result = d.update(1.0)
        assert result.state == "REAL"
        assert result.voting_ratio == pytest.approx(1.0)


class TestHybridLivenessDeciderMinimumFrames:
    def test_minimum_frames_required(self) -> None:
        """< 3 frames (default min) → SPOOF even with all scores above threshold."""
        d = HybridLivenessDecider()
        r1 = d.update(0.9)  # 1 frame
        assert r1.state == "SPOOF"
        r2 = d.update(0.9)  # 2 frames
        assert r2.state == "SPOOF"

    def test_minimum_frames_reached(self) -> None:
        """3 frames all above threshold → REAL."""
        d = HybridLivenessDecider()
        for score in [0.9, 0.8, 0.7]:
            result = d.update(score)
        assert result.state == "REAL"

    def test_min_frames_small_window(self) -> None:
        """Small window (3) → min_frames = 1."""
        d = HybridLivenessDecider(voting_window=3)
        assert d._min_frames == 1
        # Single high-scoring frame should be REAL
        result = d.update(0.9)
        assert result.state == "REAL"


class TestHybridLivenessDeciderRecognitionBoost:
    def test_recognition_boost_applied(self) -> None:
        """Recognition match adds boost to probability."""
        d = HybridLivenessDecider(boost_amount=0.15)
        # A score of 0.4 is below threshold 0.5
        # With +0.15 boost → 0.55, which IS above threshold
        result = d.update(0.4, recognition_match=True)
        assert result.recognition_boosted is True
        # Check buffer has boosted probability
        assert d._buffer[-1].probability == pytest.approx(0.55)

    def test_recognition_no_boost_no_match(self) -> None:
        """Recognition no match → neutral, no boost."""
        d = HybridLivenessDecider()
        result = d.update(0.4, recognition_match=False)
        # Should be treated as no recognition ran (recognition_match defaults to False)
        assert d._buffer[-1].probability == pytest.approx(0.4)
        assert d._buffer[-1].recognition_match is False

    def test_recognition_boost_no_match_on_different_frame(self) -> None:
        """Only the frame with recognition match gets boosted."""
        d = HybridLivenessDecider()
        d.update(0.4)  # no boost
        d.update(0.4, recognition_match=True)  # boosted
        assert d._buffer[0].recognition_match is False
        assert d._buffer[0].probability == pytest.approx(0.4)
        assert d._buffer[1].recognition_match is True
        assert d._buffer[1].probability == pytest.approx(0.55)

    def test_boost_clamped_to_one(self) -> None:
        """Boost does not push probability above 1.0."""
        d = HybridLivenessDecider(boost_amount=0.5)
        result = d.update(0.8, recognition_match=True)
        assert d._buffer[-1].probability == pytest.approx(1.0)

    def test_boost_turns_spoof_vote_to_real(self) -> None:
        """Boost can flip a single frame's vote from SPOOF to REAL."""
        d = HybridLivenessDecider(boost_amount=0.2)
        # Without boost: 0.4 < 0.5 → SPOOF
        # With boost: 0.6 >= 0.5 → REAL
        # 3 frames at 0.6 (boosted from 0.4) → REAL
        for _ in range(3):
            result = d.update(0.4, recognition_match=True)
        assert result.state == "REAL"


class TestHybridLivenessDeciderBufferReset:
    def test_reset_clears_buffer(self) -> None:
        d = HybridLivenessDecider()
        d.update(0.8)
        d.update(0.8)
        assert d.buffer_size == 2
        d.reset()
        assert d.buffer_size == 0

    def test_reset_then_update_starts_fresh(self) -> None:
        d = HybridLivenessDecider()
        d.update(0.8)
        d.reset()
        result = d.update(0.8)
        assert d.buffer_size == 1
        assert result.frames_in_buffer == 1
        assert result.state == "SPOOF"  # < 3 frames


class TestHybridLivenessDeciderProbabilitySpace:
    def test_scores_are_zero_to_one(self) -> None:
        """Scores are probabilities in [0, 1], not logit values."""
        d = HybridLivenessDecider()
        d.update(0.5)
        d.update(0.9)
        d.update(0.0)
        assert all(
            0.0 <= f.probability <= 1.0 for f in d._buffer
        )

    def test_zero_probability(self) -> None:
        """Probability = 0.0 → SPOOF vote."""
        d = HybridLivenessDecider()
        result = d.update(0.0)
        assert d._buffer[-1].probability == pytest.approx(0.0)


class TestHybridLivenessDeciderBypassMode:
    def test_probability_one_is_real(self) -> None:
        """Probability = 1.0 (model disabled) → always REAL."""
        d = HybridLivenessDecider()
        for _ in range(3):
            result = d.update(1.0)
        assert result.state == "REAL"
        assert result.voting_ratio == pytest.approx(1.0)

    def test_probability_one_does_not_need_boost(self) -> None:
        """No boost applied when already at 1.0, but recognition_ran still tracked."""
        d = HybridLivenessDecider()
        result = d.update(1.0, recognition_match=True)
        assert d._buffer[-1].probability == pytest.approx(1.0)


class TestHybridLivenessDeciderEdgeCases:
    def test_boundary_threshold_and_probability(self) -> None:
        """Threshold exactly at 0.5, probabilities at boundaries."""
        d = HybridLivenessDecider(liveness_threshold=0.5)
        # 0.5 is exact threshold
        d.update(0.5)  # real vote
        d.update(0.5)  # real vote
        d.update(0.5)  # real vote → REAL
        d.update(0.49)  # spoof vote
        d.update(0.49)  # spoof vote
        assert d.buffer_size == 5

    def test_continuous_updates_buffer_wraps(self) -> None:
        """Buffer wraps around after window_size updates."""
        d = HybridLivenessDecider(voting_window=3)
        for i in range(10):
            d.update(0.9)
        assert d.buffer_size == 3  # only 3 newest frames

    def test_negative_probability_clamped(self) -> None:
        """Negative probability is clamped to 0."""
        d = HybridLivenessDecider()
        result = d.update(-0.5)
        assert d._buffer[-1].probability == pytest.approx(0.0)
