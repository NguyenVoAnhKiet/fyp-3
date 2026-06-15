# 0010: Hybrid Liveness Mode + Recognition Consensus

## Status
Proposed

## Context
Under good lighting, face recognition flickers between "unrecognized" and "success" — 4/5 frames fail, 1 succeeds. Root cause: SFace alignCrop() is sensitive to YuNet landmark jitter, causing cosine similarity to oscillate around the threshold boundary (0.5).

Current system runs in Legacy mode with ~10 Hz recognition frequency and no temporal smoothing for recognition results.

## Goals
1. Enable hybrid liveness mode via .env configuration
2. Add recognition consensus mechanism to stabilize UI display
3. Reduce recognition flicker from ~10 Hz to ~3.3 Hz

## Non-Goals
- Landmark smoothing (deferred to future work)
- Embedding averaging (deferred to future work)
- Modifying SFace or YuNet models
- Changing enrollment process

## Design Decisions

### 1. Hybrid Liveness Mode
- Enable via `HYBRID_LIVENESS_ENABLED=true` in `.env`
- `voting_window = 5` (default — 5-frame majority voting for liveness)
- `boost_amount = 0.10` (reduced from 0.15 — lighter boost)
- `recognition_interval = 5` (default — recognition every ~0.5s)

### 2. Recognition Consensus
- Window: 3 recognition frames
- Threshold: 2/3 user identity agreement
- Buffer: `[(user_id, timestamp)]`
- Face loss → reset buffer
- No buffer expiry (window=3 already limits entries)
- Each voting session independently determines result

### 3. Cooldown
- Keep existing `_COOLDOWN_SECONDS = 1.5` (prevents duplicate DB records)
- Consensus handles UI stability (different purpose)

## Implementation

### Step 1: Enable Hybrid Mode (.env)
Add to `.env`:
```
HYBRID_LIVENESS_ENABLED=true
```

### Step 2: Update CameraThread (camera_thread.py)
Add hybrid parameters to `CameraThread.__init__`:
- `hybrid_liveness_enabled: bool`
- `hybrid_voting_window: int`
- `hybrid_boost_amount: float`
- `recognition_interval: int`

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

### Step 4: Add Consensus Logic (AIWorker in camera_thread.py)
Add to `AIWorker` class:
- `_consensus_buffer: list[tuple[int, float]]` — circular buffer of (user_id, timestamp)
- `_consensus_window = 3`
- `_consensus_threshold = 2`

In `_process_frame()`:
1. After pipeline result, extract `user_id` (0 if unrecognized)
2. Append `(user_id, timestamp)` to buffer
3. If buffer length >= window, check majority:
   - Count occurrences of each user_id in buffer
   - If any user_id >= threshold → emit that user
   - Otherwise → emit "unrecognized"
4. On face loss (no detection), reset buffer

## Testing
1. Enable hybrid mode, verify liveness uses 5-frame voting
2. Verify recognition runs at ~2 Hz (every 0.5s)
3. Test consensus: sit still, verify UI shows consistent name without flicker
4. Test face loss: cover camera, verify buffer resets
5. Test edge case: multiple people in frame
6. Run existing unit tests to ensure no regression

## Risks
- Consensus adds ~500ms latency (3 frames × ~170ms each)
- boost_amount=0.10 may be too light for borderline liveness scores
- Hybrid mode recognition at 2 Hz may feel slower than legacy 10 Hz