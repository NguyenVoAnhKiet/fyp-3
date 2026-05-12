# Data Model: Attendance Session Processing

## Attendance Session

Represents one lecturer-started attendance window for a specific course and class.

Fields:
- `id`: unique session identifier
- `course_name`: course label entered at session start
- `class_code`: class/group identifier
- `status`: `active`, `ended`, or `cancelled`
- `started_at`: ISO 8601 timestamp when session becomes active
- `ended_at`: ISO 8601 timestamp when session closes (null while active)
- `created_by`: lecturer/admin identifier

Validation rules:
- `course_name` and `class_code` are required to activate a session.
- Only one session can be `active` at a time in this module scope.

State transitions:
- `created` -> `active` when start validation succeeds
- `active` -> `ended` when lecturer ends session normally
- `active` -> `cancelled` when session is aborted

## Recognition Outcome Event

Represents one finalized AI output consumed by attendance processing.

Fields:
- `session_id`: target attendance session identifier
- `event_time`: ISO 8601 timestamp
- `student_id`: recognized identity or null for non-identity outcomes
- `outcome_type`: `success`, `spoof_warning`, `unrecognized`, or `invalid`
- `liveness_score`: numeric score or null
- `similarity_score`: numeric score or null
- `details`: optional diagnostic text

Validation rules:
- Events are accepted only when target session is `active`.
- `success` requires a non-null `student_id`.
- `spoof_warning` must not be treated as successful attendance.

## Attendance Record

Represents one successful attendance confirmation for a student in a session.

Fields:
- `id`: unique record identifier
- `session_id`: linked attendance session
- `student_id`: attendee identity
- `recorded_at`: ISO 8601 timestamp
- `source_event_time`: original event timestamp

Relationships:
- Many attendance records belong to one attendance session.
- At most one successful attendance record exists per `(session_id, student_id)`.

Validation rules:
- Duplicate successful records for the same student in one session are blocked.

## Session History Entry

Represents immutable audit history for every processed attendance-related outcome.

Fields:
- `id`: unique history identifier
- `session_id`: linked attendance session
- `student_id`: optional identity (nullable for malformed/unrecognized outcomes)
- `history_type`: `success`, `spoof_warning`, `duplicate_blocked`, `invalid_event`, or `unrecognized`
- `occurred_at`: ISO 8601 timestamp
- `message`: optional operator/audit detail

Relationships:
- Many history entries belong to one attendance session.

Validation rules:
- Every processed event produces at most one history entry with a deterministic `history_type`.
- History entries are append-only and remain queryable after session close.

## Consistency Notes

- Attendance records are a strict subset of history outcomes (`history_type=success`).
- Spoof warnings and invalid events are preserved for audit but never imply presence.
- All persisted timestamps use ISO 8601 format to align with repository constraints.
