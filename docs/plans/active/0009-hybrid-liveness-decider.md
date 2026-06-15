# 0009 — Hybrid Liveness Decider

## Status

**Draft** (revised after oracle review)

## Context

The face attendance system has two critical accuracy problems:

1. **Liveness (anti-spoof) false rejects**: MiniFASNet V2 SE is a 2D texture classifier that rejects ~90% of real faces in poor lighting and ~80% in good lighting. This is a model limitation — 2D texture info degrades under poor lighting.

2. **Recognition instability**: When liveness does pass, face recognition similarity scores are borderline (0.6–0.8), causing only 1 frame to match in 3–5 seconds of camera runtime. The combination of liveness failures + borderline recognition + 3-second cooldown means the system barely works.

**Root cause chain**:
```
Liveness fails → recognition never runs → no attendance recorded
   OR
Liveness passes (rarely) → recognition borderline → match flickers → 1 success then nothing
```

**Architecture context** (from oracle review):
- `LivenessChecker.check()` returns **logit_diff** (unbounded, can be negative), NOT probability (0–1)
- `LivenessTracker` already has EMA + hysteresis + IoU tracking — adding another temporal filter creates conflict
- Current code only processes the **largest face** per frame (single-face limitation)

## Goals

1. Reduce real-face-as-spoof rejection rate from 80–90% to < 20% across lighting conditions
2. Increase recognition stability from 1 match per 3–5s to consistent matching every frame
3. Maintain anti-spoof effectiveness — spoof detection should not degrade
4. Clean architecture: single temporal authority, no redundant filters

## Non-Goals

- Replacing the MiniFASNet ONNX model (out of scope — model upgrade is a separate effort)
- Changing the SFace recognition model or embedding dimensions
- Modifying enrollment pipeline (enrollment uses LivenessChecker directly, not hybrid decider)
- Camera/resolution changes
- Database schema changes
- Multi-face support (current limitation — only largest face processed)

## Design Decisions

| # | Decision | Options Considered | Final Choice | Rationale |
|---|----------|-------------------|--------------|-----------|
| D1 | Score space | Logit space / Probability space | **Probability space** | Add `sigmoid(logit_diff)` in LivenessChecker. All downstream logic uses 0–1 probabilities. Avoids threshold confusion. |
| D2 | Temporal authority | Keep LivenessTracker + add decider / Replace hysteresis with decider / Decider consumes tracker output | **Replace hysteresis with decider; tracker keeps IoU only** | Single temporal authority. Tracker becomes pure face-tracking (IoU matching). Decider owns all temporal decisions. |
| D3 | Voting window size | 3 / 5 / 7–10 frames | **5 frames** | ~167ms at 30fps — balances responsiveness and accuracy |
| D4 | Voting mechanism | Majority / Weighted / EMA-only | **Majority vote (≥3/5 agree)** | Simple, interpretable, robust to outlier frames |
| D5 | Recognition role | Tiebreaker / Periodic only / Both | **Periodic only (every 5 AI-frames)** | Decoupled from liveness. Recognition runs independently for identity. No circular dependency. |
| D6 | Recognition frequency | Every 3 / 5 / 10 AI-frames | **Every 5 AI-frames (~2 Hz)** | Balances compute and identity availability. Profile SFace latency to confirm. |
| D7 | Buffer reset | Every frame / On face loss / On track change | **On face loss (integrated with tracker)** | Reset when LivenessTracker deletes track (MAX_MISSES=3). No independent reset logic. |
| D8 | Per-face state | Per-track buffer / Single buffer + document limitation | **Single buffer + document limitation** | Current code only processes largest face. Multi-face support is future work. |
| D9 | Frame counter | Use CameraThread frame_counter / Local ai_frame_counter | **Local ai_frame_counter in AIWorker** | frame_counter jumps by 3 (AI_FRAME_SKIP). Local counter increments per processed frame. |
| D10 | Thread architecture | Keep 2 threads / Split into 3 threads | **Keep 2 threads (CameraThread + AIWorker)** | Simpler, less risk, existing backpressure mechanism works |
| D11 | Bypass mode | Skip decider / Always return REAL | **Always return REAL when model disabled** | LivenessChecker already returns score=1.0 when model_path=None. Decider passes through. |
| D12 | Unrecognized in voting | Neutral / Spoof vote / Skip vote | **Neutral (not counted)** | Recognition failure ≠ spoof. Only count explicit liveness scores in voting. |
| D13 | Cooldown | Keep 3s / Reduce to 1s / Remove | **Reduce to 1.5s** | More frequent recognition attempts → shorter cooldown prevents flooding while allowing re-identification. |
| D14 | Config exposure | Hardcoded / Partial config / Full SystemConfig | **Full SystemConfig** | All params (voting_window, boost, offsets, recognition_interval) configurable via env/DB/settings UI. |

## Tasks

| # | Task | Agent | Depends On | Status |
|---|------|-------|------------|--------|
| T1 | Add `sigmoid()` conversion in `LivenessChecker.check()` — return probability instead of logit_diff | @fixer | — | Pending |
| T2 | Simplify `LivenessTracker` — remove hysteresis (T_HIGH/T_LOW), keep IoU tracking + EMA only | @fixer | — | Pending |
| T3 | Create `HybridLivenessDecider` class: circular buffer, majority voting, recognition boost, config from SystemConfig | @fixer | T1 | Pending |
| T4 | Add `ai_frame_counter` to AIWorker — local counter per processed frame | @fixer | — | Pending |
| T5 | Wire HybridLivenessDecider into `AIPipeline.run_attendance()` — recognition every 5 AI-frames, independent of liveness | @fixer | T3, T4 | Pending |
| T6 | Add config entries to SystemConfig + defaults for all hybrid decider params | @fixer | — | Pending |
| T7 | Write unit tests for HybridLivenessDecider | @fixer | T3 | Pending |
| T8 | Manual smoke test with camera | human | T5 | Pending |

## Implementation

### Step 1: Fix score space (T1)

**File**: `src/attendance_system/services/ai_pipeline.py` — `LivenessChecker.check()`

```python
import math

class LivenessChecker:
    def check(self, face_rgb, threshold):
        # ... existing ONNX inference ...
        logit_diff = float(output[0][0] - output[0][1])

        # Convert logit → probability (0–1)
        probability = 1.0 / (1.0 + math.exp(-logit_diff))

        # Threshold comparison now in probability space
        is_real = probability >= threshold

        return LivenessResult(
            is_real=is_real,
            score=probability,  # ← CHANGED: was logit_diff, now probability
            raw_logit=logit_diff,  # ← NEW: keep raw logit for debugging
        )
```

**Impact**: All downstream code (LivenessTracker, AIPipeline, HybridLivenessDecider) now receives probabilities. Existing thresholds (T_HIGH=0.65, T_LOW=0.45) need recalibration to probability space.

### Step 2: Simplify LivenessTracker (T2)

**File**: `src/attendance_system/services/liveness_tracker.py`

Remove hysteresis state machine. Keep:
- EMA smoothing (α=0.4) — still useful for noise reduction
- IoU tracking — still needed for multi-face association
- Track lifecycle (MAX_MISSES) — still needed

Remove:
- `T_HIGH`, `T_LOW` constants
- SPOOF/REAL state transitions
- State-based decision logic

```python
class LivenessTracker:
    """Pure IoU face tracker with EMA smoothing. No temporal decisions."""

    def update(self, bboxes, scores):
        # IoU matching + EMA smoothing only
        # Returns: [(bbox, ema_score, track_id), ...]
        # NO state (SPOOF/REAL) — that's HybridLivenessDecider's job
```

### Step 3: Create HybridLivenessDecider (T3)

**New file**: `src/attendance_system/services/hybrid_liveness_decider.py`

```python
"""Hybrid liveness decider: multi-frame voting + periodic recognition.

Single temporal authority for liveness decisions. Replaces LivenessTracker's
hysteresis with majority voting over a 5-frame window. Recognition runs
periodically for identity, independent of liveness decision.
"""

from __future__ import annotations

import collections
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    """Result of a single frame's liveness check."""
    probability: float  # 0.0–1.0 (sigmoid-converted)
    recognition_match: bool = False


@dataclass
class HybridDecision:
    """Final hybrid liveness decision."""
    state: str  # "REAL" or "SPOOF"
    confidence: float  # 0.0–1.0 (voting ratio)
    voting_ratio: float  # real_votes / total_votes
    frames_in_buffer: int
    recognition_boosted: bool


class HybridLivenessDecider:
    """Multi-frame voting for liveness decisions.

    Architecture:
        - Circular buffer of 5 FrameResult entries (probability space)
        - Majority voting: >= 3/5 frames agree → REAL
        - Recognition runs periodically (every N AI-frames), NOT as tiebreaker
        - Recognition match → additive boost (+0.15) to probability
        - Buffer resets when face is lost (integrated with LivenessTracker)

    Note: Single-face only. Current attendance mode processes largest face.
    Multi-face support requires per-track buffers (future work).
    """

    def __init__(
        self,
        liveness_threshold: float = 0.5,
        voting_window: int = 5,
        boost_amount: float = 0.15,
        min_frames_for_decision: int = 3,
    ) -> None:
        self._threshold = liveness_threshold
        self._voting_window = voting_window
        self._boost_amount = boost_amount
        self._min_frames = min_frames_for_decision

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
            probability: Liveness probability (0.0=definitely spoof, 1.0=definitely real)
            recognition_match: True if periodic recognition found a match

        Returns:
            HybridDecision with voting result
        """
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

        # Decision: need minimum frames + majority
        if total >= self._min_frames and real_votes >= (total // 2 + 1):
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
            confidence=voting_ratio,
            voting_score=voting_ratio,
            frames_in_buffer=total,
            recognition_boosted=recognition_boosted,
        )

    def reset(self) -> None:
        """Reset buffer state."""
        self._buffer.clear()

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
```

### Step 4: Add local frame counter (T4)

**File**: `src/attendance_system/ui/camera_thread.py` — `AIWorker`

```python
class AIWorker(AIWorkerBase):
    def __init__(self, pipeline, parent=None):
        super().__init__(pipeline, parent)
        self._last_recognized: dict[int, float] = {}
        self._ai_frame_counter: int = 0  # ← NEW: local counter per processed frame

    def _process_frame(self, task):
        self._ai_frame_counter += 1  # ← NEW
        frame_bgr, frame_rgb, face_row, frame_counter = task

        result = self._pipeline.run_attendance(
            frame_bgr, frame_rgb, face_row, self._ai_frame_counter  # ← pass local counter
        )
        # ... rest unchanged ...
```

### Step 5: Wire into AIPipeline (T5)

**File**: `src/attendance_system/services/ai_pipeline.py` — `AIPipeline.run_attendance()`

```python
class AIPipeline:
    def __init__(self, ..., recognition_interval: int = 5):
        # ... existing init ...
        self._recognition_interval = recognition_interval
        self._hybrid_decider = HybridLivenessDecider(
            liveness_threshold=liveness_threshold,
        )

    def run_attendance(self, frame_bgr, frame_rgb, face_row, ai_frame_counter):
        x, y, w, h = face_row[:4].astype(int)

        # Step 1: Liveness check (now returns probability 0–1)
        face_crop = _crop_face(frame_rgb, (x, y, w, h), scale=2.7)
        liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)

        # Step 2: IoU tracking (no temporal decisions — tracker is pure tracking)
        bbox_float = (float(x), float(y), float(w), float(h))
        tracked_faces = self._liveness_tracker.update(
            [bbox_float], [liveness.score]
        )

        # Step 3: Periodic recognition (every N AI-frames, independent of liveness)
        recognition_match = False
        match = None
        if ai_frame_counter % self._recognition_interval == 0:
            match = self._face_recognizer.identify(
                frame_bgr, face_row, self._similarity_threshold
            )
            recognition_match = match is not None

        # Step 4: Hybrid liveness decision (single temporal authority)
        hybrid_decision = self._hybrid_decider.update(
            liveness.score, recognition_match
        )

        if hybrid_decision.state == "SPOOF":
            return PipelineResult(
                result_type="spoof",
                frame_counter=ai_frame_counter,
                liveness_score=hybrid_decision.confidence,
            )

        # Step 5: Recognition for identity (reuse if already done)
        if match is None:
            match = self._face_recognizer.identify(
                frame_bgr, face_row, self._similarity_threshold
            )

        if match is None:
            return PipelineResult(
                result_type="unrecognized",
                frame_counter=ai_frame_counter,
                liveness_score=hybrid_decision.confidence,
            )

        return PipelineResult(
            result_type="success",
            frame_counter=ai_frame_counter,
            liveness_score=hybrid_decision.confidence,
            user_id=match.user_id,
            full_name=match.full_name,
            similarity=match.similarity,
            matched_pose_label=match.matched_pose_label,
        )
```

### Step 6: Config entries (T6)

**File**: `src/attendance_system/core/defaults.py`

```python
DEFAULT_LIVENESS_THRESHOLD = 0.5          # was 0.3 (logit space), now probability
DEFAULT_HYBRID_VOTING_WINDOW = 5
DEFAULT_HYBRID_BOOST_AMOUNT = 0.15
DEFAULT_HYBRID_MIN_FRAMES = 3
DEFAULT_RECOGNITION_INTERVAL = 5          # AI-frames between recognition runs
DEFAULT_COOLDOWN_SECONDS = 1.5            # was 3.0
```

**File**: `src/attendance_system/core/config.py` — add to `SystemConfig`

```python
# Hybrid liveness decider
hybrid_voting_window: int = 5
hybrid_boost_amount: float = 0.15
hybrid_min_frames: int = 3
recognition_interval: int = 5
cooldown_seconds: float = 1.5
```

## Testing

### Unit tests: `tests/unit/test_hybrid_liveness_decider.py`

| Test case | Description |
|-----------|-------------|
| `test_majority_vote_real` | 3/5 frames above threshold → REAL |
| `test_majority_vote_spoof` | 2/5 frames above threshold → SPOOF |
| `test_recognition_boost` | Recognition match → +0.15 to probability |
| `test_recognition_no_boost_no_match` | Recognition no match → neutral, no boost |
| `test_minimum_frames_required` | < 3 frames → SPOOF regardless of scores |
| `test_buffer_reset` | reset() clears buffer |
| `test_probability_space` | Scores are 0–1, not logit values |
| `test_bypass_mode` | Probability = 1.0 (model disabled) → always REAL |
| `test_boundary_values` | Threshold exactly at 0.5, probabilities at 0.0/1.0 |
| `test_multiple_faces_documented` | Single buffer, single face (documented limitation) |

### Unit tests: `tests/unit/test_liveness_checker_sigmoid.py`

| Test case | Description |
|-----------|-------------|
| `test_sigmoid_conversion` | logit_diff → probability via sigmoid |
| `test_threshold_comparison` | Probability >= threshold → is_real |
| `test_negative_logit` | Large negative logit → probability near 0 |
| `test_positive_logit` | Large positive logit → probability near 1 |

### Manual smoke test checklist

- [ ] Launch app with camera, enroll a face
- [ ] Verify green flash appears consistently (>80% of frames) in good lighting
- [ ] Verify green flash appears in poor lighting (>50% of frames)
- [ ] Verify spoof detection still works (hold up phone/photo)
- [ ] Verify cooldown (1.5s) prevents duplicate attendance records
- [ ] Check similarity scores are in healthy range (>0.6 consistently)
- [ ] Check debug logs show hybrid decision details (prob, boosted, ratio, state)
