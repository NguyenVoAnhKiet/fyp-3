## 1. Data Recording — AttendanceService (P0)

- [x] 1.1 Verify transaction atomicity: confirm `INSERT INTO recognition_events` rolls back if `INSERT INTO attendance_records` fails
- [x] 1.2 Verify `SessionClosedError` is raised in `record_duplicate()` when session is closed
- [x] 1.3 Verify threshold snapshots are frozen at session creation and do not change when settings update
- [x] 1.4 Verify `get_records_with_users()` uses `LEFT JOIN` to include NULL-user records after user deletion
- [x] 1.5 Verify CSV export properly escapes commas, double quotes, and Unicode in student names
- [x] 1.6 Write unit test for export with special characters in names
- [x] 1.7 Write integration test verifying `ON DELETE SET NULL` leaves attendance records intact

## 2. Face Recognition — SFace + FaceReferenceRepository (P0)

- [x] 2.1 Review `get_embedding()` — verify `alignCrop` + `feature` receive correct YuNet format
- [x] 2.2 Verify `_face_refs.get_all()` cache is invalidated on every write path (add, update, delete face reference)
- [x] 2.3 Write unit test: `identify()` with corrupt embedding bytes in DB — must skip gracefully, not crash
- [x] 2.4 Write unit test: cache invalidation after upsert/deletion
- [x] 2.5 Run benchmark: `identify()` with 1000+ users × 5 poses — measure end-to-end latency per frame

## 3. Liveness Detection — MiniFASNet + LivenessChecker (P1)

- [x] 3.1 Review `_preprocess()` with various aspect ratios (1:1, 2:1, 1:2, 3:4) — confirm output is always 128×128
- [x] 3.2 Write unit test: `check()` handles NaN/Inf model output gracefully
- [x] 3.3 Verify circuit breaker: `_consecutive_failures` resets on successful inference
- [x] 3.4 Verify bypass mode: `model_path=None` produces `score=1.0` and `is_real=True`

## 4. Camera Pipeline — AIWorker + CameraThread (P1)

- [x] 4.1 Review `submit_task()` frame copy depth — confirm `.copy()` is deep copy for numpy arrays
- [x] 4.2 Review sentinel termination — verify queue drain + sentinel push + clean worker exit
- [x] 4.3 Review signal disconnect safety — confirm `TypeError` catch on all disconnect paths
- [x] 4.4 Write unit test: `_retry_read()` releases old cap before creating new one
- [x] 4.5 Review `cap.release()` is called in all exit paths (including exception paths)

## 5. Face Detection — YuNet (P2)

- [x] 5.1 Review `_crop_face()` clamping: verify bbox at frame edges does not cause out-of-bounds access
- [x] 5.2 Verify pipeline handles empty face detection result (no faces) — no crash, continues loop
- [x] 5.3 Verify detector `score_threshold=0.8` is appropriate for camera quality 640×480

## 6. UI Integration — UserModeView (P2)

- [x] 6.1 Verify `_recognized_users` is cleared on both `_end_session()` and `_start_session()`
- [x] 6.2 Verify stats counters: `_stats_total` always increments; `_stats_success` only on first recognition per user
- [x] 6.3 Verify `_on_recognition_result` handles `_session_id = None` (session ended mid-callback)
- [x] 6.4 Verify UTC→local time conversion in sidebar display produces correct timezone offset

## 7. Temporal Smoothing — LivenessTracker (P3)

- [x] 7.1 Verify `AIWorker.stop()` clears `LivenessTracker.tracks` (ensure clean state on restart)
- [x] 7.2 Review IoU with extreme coordinates (negative, zero, very large) — verify no crash

## 8. Final Validation

- [x] 8.1 Run full test suite: `pytest tests/ -v` — all tests pass
- [x] 8.2 Run linter: `ruff check src/` — clean
- [x] 8.3 Confirm no `[DEBUG-...]` instrumentation left in code
- [ ] 8.4 Commit and push all review changes
