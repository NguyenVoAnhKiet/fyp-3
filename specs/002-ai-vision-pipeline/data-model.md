# Data Model: AI Engine & Vision Pipeline

## Existing Persistent Entities

### Attendance Session
Represents the active attendance run that the vision pipeline serves.

Fields:
- `id`: unique identifier
- `subject_name`: class subject
- `class_name`: class identifier
- `status`: `active`, `closed`, or `interrupted`
- `start_time`: ISO 8601 session start time
- `end_time`: ISO 8601 session end time or null
- `liveness_threshold_snapshot`: threshold in effect for the session
- `similarity_threshold_snapshot`: threshold in effect for the session

Validation rules:
- A session must be active before vision events are consumed for attendance.
- Threshold snapshots must be present when a session becomes active.

### Recognition Event
Represents the normalized event emitted by the vision pipeline.

Fields:
- `id`: unique identifier
- `session_id`: related session
- `user_id`: matched user or null for spoof/unknown/no-face outcomes
- `event_time`: ISO 8601 event timestamp
- `result`: `success`, `duplicate`, `spoof_warning`, or `unrecognized`
- `liveness_score`: score from the anti-spoof stage or null
- `similarity_score`: score from the recognition stage or null
- `details`: optional diagnostic note

Relationships:
- Each event belongs to one session.
- A successful match may be linked to one user.

Validation rules:
- `result` must use an approved value.
- `event_time` must be present for every event.

### Attendance Record
Represents the final attendance outcome stored by the attendance layer.

Fields:
- `id`: unique identifier
- `session_id`: related session
- `user_id`: related user
- `status`: `success`, `duplicate`, `spoof_warning`, or `unrecognized`
- `recorded_at`: ISO 8601 timestamp

Validation rules:
- `(session_id, user_id)` must remain unique.
- Attendance records are only written after the downstream attendance service accepts a matching event.

## Module 2 Runtime Entities

### Frame Processing Task
Internal unit of work for a captured frame.

Fields:
- `session_id`: active session identifier
- `frame_id`: monotonic sequence number
- `captured_at`: ISO 8601 frame capture time
- `frame_data`: transient image payload

Validation rules:
- Frame data is transient and must not be persisted in the normal flow.

### Liveness Decision
Intermediate decision from the anti-spoof stage.

Fields:
- `frame_id`: source frame identifier
- `score`: liveness score
- `threshold`: active threshold snapshot
- `passed`: boolean decision

Validation rules:
- A recognition attempt can only follow a passing decision.

### Recognition Decision
Intermediate identity matching result for a live face.

Fields:
- `frame_id`: source frame identifier
- `user_id`: matched user or null
- `score`: similarity score
- `threshold`: active threshold snapshot
- `passed`: boolean decision

Validation rules:
- A recognition event must be emitted after this decision is resolved.

### Vision Pipeline State
Runtime worker state for the background processing thread.

Fields:
- `status`: `idle`, `running`, `recovering`, `degraded`, or `stopped`
- `active_session_id`: current session or null
- `queue_depth`: number of queued frames
- `last_event_time`: ISO 8601 timestamp or null

State transitions:
- `idle` -> `running`
- `running` -> `degraded`
- `running` -> `recovering`
- `recovering` -> `running`
- any active state -> `stopped`
