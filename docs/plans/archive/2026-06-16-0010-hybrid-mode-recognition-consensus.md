# 0010: Hybrid Liveness Mode + Recognition Consensus

## Status
Done (2026-06-16)

## Context
Under good lighting, face recognition flickers between "unrecognized" and "success" — 4/5 frames fail, 1 succeeds. Root cause: SFace `alignCrop()` is sensitive to YuNet landmark jitter, causing cosine similarity to oscillate around the threshold boundary (0.5).

Current system runs in Legacy mode with ~10 Hz recognition frequency and no temporal smoothing for recognition results.

## Goals
1. Enable hybrid liveness mode via .env configuration
2. Add recognition consensus mechanism to stabilize UI display
3. Reduce recognition flicker from ~10 Hz to ~2 Hz

## Non-Goals
- Landmark smoothing (deferred to future work)
- Embedding averaging (deferred to future work)
- Modifying SFace or YuNet models
- Changing enrollment process

## Design Decisions

### 1. Hybrid Liveness Mode
- Enable via `HYBRID_LIVENESS_ENABLED=true` in `.env`
- `voting_window = 5` (default — 5-frame majority voting for liveness)
- `boost_amount = 0.10` (update default from 0.15 in `defaults.py`)
- `recognition_interval = 5` (default — recognition every ~0.5s at 2 Hz)

### 2. Recognition Consensus
- Window: 3 recognition frames
- Threshold: 2/3 user identity agreement
- Buffer: `[(user_id, timestamp)]`
- Face loss → reset buffer
- No buffer expiry (window=3 already limits entries)
- Each voting session independently determines result
- **Consensus logic lives in CameraThread** (not AIWorker) — CameraThread has visibility of face presence/absence for proper buffer reset

### 3. Cooldown
- Keep existing `_COOLDOWN_SECONDS = 1.5` (prevents duplicate DB records)
- Consensus handles UI stability (different purpose)

## Implementation

### Step 0: Add `recognition_interval` to Config System

`recognition_interval` does not exist in the config system yet. Add it:

**`defaults.py`:**
```python
DEFAULT_RECOGNITION_INTERVAL: int = 5
```

**`config.py` — SystemConfig dataclass:**
```python
recognition_interval: int
```

**`config.py` — resolve chain (in `_ENV_MAP` or equivalent):**
```python
("RECOGNITION_INTERVAL", "recognition_interval", "int"),
```

Resolution: CLI arg > env var > DB > default (5)

### Step 1: Enable Hybrid Mode (.env)
Add to `.env`:
```
HYBRID_LIVENESS_ENABLED=true
```

### Step 2: Update CameraThread (camera_thread.py)
Add hybrid parameters to `CameraThread.__init__`:
- `hybrid_liveness_enabled: bool = False`
- `hybrid_voting_window: int = 5`
- `hybrid_boost_amount: float = 0.10`
- `recognition_interval: int = 5`

Forward to `AIPipeline(...)` constructor.

### Step 3: Update UserModeView (user_mode_view.py)
Read hybrid config from `SystemConfig` and pass to `CameraThread(...)`:
```python
self._camera_thread = CameraThread(
    ...,
    hybrid_liveness_enabled=self._config.hybrid_liveness_enabled,
    hybrid_voting_window=self._config.hybrid_voting_window,
    hybrid_boost_amount=self._config.hybrid_boost_amount,
    recognition_interval=self._config.recognition_interval,
)
```

### Step 4: Add Consensus Logic (CameraThread, not AIWorker)

**Why CameraThread instead of AIWorker?** `AIWorker._process_frame()` is only called when faces are detected (line 185: `if faces is not None and len(faces) > 0`). Face loss = no call = no opportunity to reset buffer. `CameraThread` runs every frame and has face presence visibility.

Add to `CameraThread`:
- `_consensus_buffer: list[tuple[int, float]]` — circular buffer of (user_id, timestamp)
- `_consensus_window = 3`
- `_consensus_threshold = 2`
- `_consensus_user_id: int | None` — last consensus-decided user_id

In `_on_recognition_result()`:
1. Extract `user_id` (0 if unrecognized)
2. Append `(user_id, timestamp.monotonic())` to buffer (keep last `_consensus_window` entries)
3. If buffer length >= `_consensus_window`, count occurrences of each user_id:
   - If any user_id (excluding 0) >= `_consensus_threshold` → set `_consensus_user_id = that_user_id`
   - Otherwise → set `_consensus_user_id = None` (unrecognized)
4. Emit consensus-decided result (not raw pipeline result)

In `_process_frame()`:
- When `faces is None or len(faces) == 0` → reset `_consensus_buffer` and `_consensus_user_id`

**Consensus vote logic (explicit):**
```
Buffer = [user_A, user_A, 0]        → 2/3 user_A >= 2 → emit user_A
Buffer = [user_A, user_B, 0]        → no majority     → emit "unrecognized"
Buffer = [0, 0, user_A]             → 2/3 for 0       → emit "unrecognized"
Buffer = [user_A, user_A, user_A]   → 3/3 user_A >= 2 → emit user_A
```

## Testing

### Unit Tests
1. `test_recognition_consensus_majority` — 2/3 same user → emit that user
2. `test_recognition_consensus_no_majority` — mixed users → emit unrecognized
3. `test_consensus_resets_on_face_loss` — buffer clears when no faces detected
4. `test_consensus_independent_sessions` — each window is independent
5. `test_hybrid_liveness_enabled` — AIPipeline receives hybrid params correctly
6. Run existing unit tests to ensure no regression

### Manual Tests
1. Enable hybrid mode, verify liveness uses 5-frame voting
2. Verify recognition runs at ~2 Hz (every 0.5s)
3. Test consensus: sit still, verify UI shows consistent name without flicker
4. Test face loss: cover camera, verify buffer resets
5. Test edge case: multiple people in frame

## Risks
- Consensus adds ~1.5s latency (3 recognition frames x 500ms each at 2 Hz)
- boost_amount=0.10 may be too light for borderline liveness scores
- Hybrid mode recognition at 2 Hz may feel slower than legacy 10 Hz

## Rollback
Set `HYBRID_LIVENESS_ENABLED=false` in `.env` → returns to legacy mode. No code rollback needed.
