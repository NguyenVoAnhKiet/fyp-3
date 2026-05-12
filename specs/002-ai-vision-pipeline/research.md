# Research: AI Engine & Vision Pipeline

## Decisions

### Language and runtime
- Decision: Use Python 3.11+.
- Rationale: The repository already targets Python 3.11+ and the current codebase uses modern typing and dataclass patterns.
- Alternatives considered: A newer runtime or a rewrite in another language. Rejected because it would not align with the existing desktop application stack.

### Vision and inference stack
- Decision: Use a local camera/vision stack with OpenCV-style capture and preprocessing, plus local inference components for liveness and embeddings.
- Rationale: The feature needs real-time frame handling, deterministic local execution, and offline operation.
- Alternatives considered: Cloud inference. Rejected because offline operation is a constitutional requirement.

### Concurrency model
- Decision: Use one dedicated worker thread with bounded queues for frame input and event output.
- Rationale: The repo already separates persistence into service/repository layers, and a single worker keeps UI responsiveness predictable for a single camera.
- Alternatives considered: A thread pool or process pool. Rejected because the feature scope is single-camera and the extra coordination would add complexity without clear benefit.

### Storage and event persistence
- Decision: Reuse the existing SQLite schema, especially `recognition_events`, `attendance_records`, and session threshold snapshots.
- Rationale: The repository already models attendance and recognition events in the database, so the new module should publish normalized events into that contract.
- Alternatives considered: A new event store or file-based logging. Rejected because it would duplicate state and complicate attendance auditing.

### Testing strategy
- Decision: Use pytest with unit tests for pipeline decisions and integration tests for end-to-end event emission and attendance updates.
- Rationale: The repo already has pytest fixtures and a split between unit and integration coverage.
- Alternatives considered: Manual-only validation. Rejected because the feature contains timing, threshold, and contract requirements that need repeatable checks.

## Findings

- The existing `AttendanceService` already provides a safe boundary for session start/end and event recording.
- The current schema already stores threshold snapshots at session start, which supports deterministic behavior.
- The `recognition_events` table already carries the score fields needed for liveness and similarity metadata.
- The attendance layer enforces `(session_id, user_id)` uniqueness, so the vision module should emit evidence rather than manage attendance deduplication itself.

## Implications

- The new module should act as a producer of normalized vision events, not as a direct writer of attendance state.
- Thresholds should be read once per session and then reused for the lifetime of that session.
- Any raw frame handling should remain transient unless a separate audit flow is explicitly added later.
