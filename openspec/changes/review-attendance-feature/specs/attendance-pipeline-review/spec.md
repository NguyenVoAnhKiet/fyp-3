## ADDED Requirements

### Requirement: Attendance pipeline review — Data Recording (AttendanceService)
The attendance recording service SHALL be reviewed for data integrity, transaction atomicity, and edge-case handling.

#### Scenario: Transaction rollback on failure
- **WHEN** `record_success()` is called and the `INSERT INTO attendance_records` fails
- **THEN** the corresponding `INSERT INTO recognition_events` SHALL also be rolled back

#### Scenario: Session status validation for all write paths
- **WHEN** `record_spoof_warning()`, `record_unrecognized()`, or `record_duplicate()` is called on a closed session
- **THEN** the system SHALL raise `SessionClosedError`

#### Scenario: Threshold snapshots are frozen at session creation
- **WHEN** a session is created with `liveness_threshold_snapshot` = X and `similarity_threshold_snapshot` = Y
- **THEN** the stored snapshot values SHALL persist unchanged even if the settings change later

#### Scenario: User deletion does not remove attendance records
- **WHEN** a user is hard-deleted from the `users` table
- **THEN** their existing attendance records SHALL remain with `user_id = NULL`
- **AND** `get_records_with_users()` SHALL use `LEFT JOIN` to include NULL-user records

#### Scenario: Export handles special characters in names
- **WHEN** a student's name contains commas, double quotes, or Unicode characters
- **THEN** the exported CSV SHALL properly escape these characters

#### Scenario: Export empty session produces valid file
- **WHEN** exporting a session with zero attendance records
- **THEN** the exported CSV SHALL contain column headers as the first row

### Requirement: Attendance pipeline review — Face Recognition (SFace)
The face recognition component SHALL be reviewed for embedding extraction correctness, similarity computation, and cache management.

#### Scenario: Embedding extraction from corrupt data
- **WHEN** `identify()` encounters a `face_references.embedding` blob with invalid float32 data
- **THEN** the system SHALL skip that reference gracefully without crashing

#### Scenario: Cache invalidation after upsert
- **WHEN** a new face reference is added or an existing one is deleted
- **THEN** the `FaceReferenceRepository._cache_all` SHALL be cleared
- **AND** the next `get_all()` call SHALL fetch fresh data from the database

#### Scenario: Cosine similarity with zero-vector reference
- **WHEN** a stored embedding is all zeros
- **THEN** `_cosine_similarity()` SHALL return -1.0 (no match)

#### Scenario: Average embeddings normalization
- **WHEN** `average_embeddings()` computes the mean of multiple embeddings
- **THEN** the result SHALL be L2-normalized to unit length

### Requirement: Attendance pipeline review — Liveness Detection (MiniFASNet)
The liveness detection component SHALL be reviewed for preprocessing correctness, numerical stability, and circuit breaker behavior.

#### Scenario: Preprocessing handles various aspect ratios
- **WHEN** a face crop has a 2:1 aspect ratio (wide) or 1:2 (tall)
- **THEN** `_preprocess()` SHALL produce a 128×128 tensor with reflect-padded borders

#### Scenario: Model output with NaN values
- **WHEN** the ONNX model returns NaN or Inf logits
- **THEN** the system SHALL not crash; the `logit_diff` SHALL propagate NaN upstream

#### Scenario: Circuit breaker resets on success
- **WHEN** a `LivenessInferenceError` occurs followed by a successful inference
- **THEN** the `_consecutive_failures` counter SHALL reset to zero

### Requirement: Attendance pipeline review — Camera Pipeline (AIWorker + CameraThread)
The camera and AI worker threading SHALL be reviewed for correctness of frame management, signal lifecycle, and resource cleanup.

#### Scenario: Frame copy prevents buffer overwriting
- **WHEN** a new camera frame arrives while the AI worker is still processing the previous one
- **THEN** the AI worker SHALL operate on a deep copy, not a view into the camera buffer

#### Scenario: Sentinel termination drains queue properly
- **WHEN** `AIWorker.stop()` is called
- **THEN** all pending items in the queue SHALL be drained
- **AND** the sentinel SHALL unblock `queue.get()` and cause a clean exit

#### Scenario: Signal disconnection is safe during shutdown
- **WHEN** `CameraThread.stop()` or `_on_ai_worker_camera_error()` runs
- **THEN** all signal disconnections SHALL catch `TypeError` if already disconnected

#### Scenario: Camera release on failure
- **WHEN** the main capture loop exits (either normally or via exception)
- **THEN** `cap.release()` SHALL always be called

### Requirement: Attendance pipeline review — Face Detection (YuNet)
The face detector SHALL be reviewed for parameter correctness and crop boundary safety.

#### Scenario: Crop at frame boundaries
- **WHEN** a detected face bounding box is at the edge of the frame
- **THEN** `_crop_face()` SHALL clamp coordinates to frame dimensions

#### Scenario: Zero faces detected
- **WHEN** no faces are found in a frame
- **THEN** the pipeline SHALL skip AI processing and continue the capture loop normally

### Requirement: Attendance pipeline review — UI Integration (UserModeView)
The UI integration SHALL be reviewed for session lifecycle management, stats consistency, and timezone handling.

#### Scenario: Recognized users set is cleared between sessions
- **WHEN** a session ends and a new session starts
- **THEN** the `_recognized_users` set SHALL be empty

#### Scenario: Stats counters are consistent with events
- **WHEN** a recognition event occurs
- **THEN** `_stats_total` SHALL always increment
- **AND** `_stats_success` SHALL only increment for the first recognition of each unique user

### Requirement: Attendance pipeline review — Temporal Smoothing (LivenessTracker)
The liveness tracker SHALL be reviewed for track lifecycle correctness.

#### Scenario: Tracks cleared on AIWorker restart
- **WHEN** `AIWorker.stop()` is called
- **THEN** all existing `LivenessTracker.tracks` SHALL be cleared
