"""Hybrid liveness decider: multi-frame voting + periodic recognition.

Single temporal authority for liveness decisions. Replaces LivenessTracker's
hysteresis with majority voting over a configurable frame window. Recognition
runs periodically for identity, independent of liveness decision.

Architecture:
    - Circular buffer of FrameResult entries (probability space 0-1)
    - Majority voting: >= ceil(window/2)+1 frames agree → REAL
    - Recognition runs periodically (every N AI-frames), NOT as tiebreaker
    - Recognition match → additive boost (+boost_amount) to probability
    - Buffer resets when face is lost (integrated with LivenessTracker)
"""

from __future__ import annotations

import collections
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    """Result of a single frame's liveness check."""
    probability: float  # 0.0-1.0 (sigmoid-converted)
    recognition_match: bool = False


@dataclass
class HybridDecision:
    """Final hybrid liveness decision."""
    state: str  # "REAL" or "SPOOF"
    voting_ratio: float  # 0.0-1.0 (agreement ratio)
    frames_in_buffer: int
    recognition_boosted: bool


class HybridLivenessDecider:
    """Multi-frame voting for liveness decisions.

    Args:
        liveness_threshold: Probability threshold (0-1). A frame is "real"
            when its probability >= this value.
        voting_window: Number of frames in the circular buffer.
        boost_amount: Additive boost to probability when recognition matches.
            Clamped to [0, 1 - probability] so boosted probability never
            exceeds 1.0.
    """

    def __init__(
        self,
        liveness_threshold: float = 0.5,
        voting_window: int = 5,
        boost_amount: float = 0.15,
    ) -> None:
        if voting_window < 1:
            raise ValueError(f"voting_window must be >= 1, got {voting_window}")
        if not 0.0 <= liveness_threshold <= 1.0:
            raise ValueError(
                f"liveness_threshold must be in [0, 1], got {liveness_threshold}"
            )
        if not 0.0 <= boost_amount <= 1.0:
            raise ValueError(
                f"boost_amount must be in [0, 1], got {boost_amount}"
            )

        self._threshold = liveness_threshold
        self._voting_window = voting_window
        self._boost_amount = boost_amount

        #: Minimum frames needed before making a REAL decision.
        #: Derived as window_size - 2 so that for the default window of 5,
        #: min_frames = 3 = majority threshold (5//2 + 1). For smaller windows
        #: (e.g. 3) we floor at 1 to allow an early decision.
        self._min_frames = max(1, voting_window - 2)

        self._buffer: collections.deque[FrameResult] = collections.deque(
            maxlen=voting_window
        )

    def update(
        self,
        probability: float,
        recognition_match: bool = False,
    ) -> HybridDecision:
        """Process one frame's liveness result.

        Args:
            probability: Liveness probability (0.0=definitely spoof,
                1.0=definitely real). Must be in [0, 1].
            recognition_match: True if periodic recognition found a match
                on this frame.

        Returns:
            HybridDecision with voting result.
        """
        if not 0.0 <= probability <= 1.0:
            logger.warning(
                "HybridDecider: probability %.3f out of [0, 1], clamping",
                probability,
            )
            probability = max(0.0, min(1.0, probability))

        # Apply recognition boost if match
        boosted_prob = probability
        recognition_boosted = False
        if recognition_match:
            boosted_prob = min(1.0, probability + self._boost_amount)
            recognition_boosted = True

        # Append to buffer
        self._buffer.append(FrameResult(
            probability=boosted_prob,
            recognition_match=recognition_match,
        ))

        # Majority voting
        total = len(self._buffer)
        real_votes = sum(
            1 for f in self._buffer if f.probability >= self._threshold
        )
        voting_ratio = real_votes / total if total > 0 else 0.0

        # Decision: need minimum frames + > half of total votes
        majority = total // 2 + 1
        if total >= self._min_frames and real_votes >= majority:
            state = "REAL"
        else:
            state = "SPOOF"

        logger.debug(
            "HybridDecider: prob=%.3f boosted=%.3f match=%s "
            "buffer=%d/%d real_votes=%d ratio=%.2f → %s",
            probability, boosted_prob, recognition_match,
            total, self._voting_window, real_votes, voting_ratio, state,
        )

        return HybridDecision(
            state=state,
            voting_ratio=voting_ratio,
            frames_in_buffer=total,
            recognition_boosted=recognition_boosted,
        )

    def reset(self) -> None:
        """Reset buffer state. Call when face is lost (track deleted)."""
        self._buffer.clear()

    @property
    def buffer_size(self) -> int:
        """Number of frames currently in the buffer."""
        return len(self._buffer)
