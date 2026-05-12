# Attendance Session Event Contract

This contract defines how the attendance-session module consumes normalized AI outcomes and maps them to persisted attendance and history records.

## Consumer Preconditions

- There is an ACTIVE attendance session.
- Incoming payload follows the required fields below.
- Event timestamps are ISO 8601.

## Accepted Outcome Types

- `success`: recognized real face that can count as attendance
- `spoof_warning`: liveness failed and must not count as attendance
- `unrecognized`: real face but no identity match
- `invalid`: malformed or rejected payload

## Required Fields

- `session_id`: integer session identifier
- `event_time`: ISO 8601 timestamp
- `outcome_type`: one of accepted outcome types
- `student_id`: string or integer for `success`, optional for other outcomes
- `liveness_score`: number or null
- `similarity_score`: number or null
- `details`: optional text

## Validation Rules

- Payloads for non-ACTIVE sessions are rejected from attendance processing.
- `success` must include `student_id`.
- Duplicate `success` for the same `(session_id, student_id)` must not create a second attendance record.
- `spoof_warning` must not create an attendance success record.
- Missing required fields map to `invalid` history handling.

## Persistence Mapping

- `success` (first occurrence) -> create one attendance record + create `success` history entry.
- `success` (duplicate) -> no new attendance record + create `duplicate_blocked` history entry.
- `spoof_warning` -> no attendance record + create `spoof_warning` history entry.
- `unrecognized` -> no attendance record + create `unrecognized` history entry.
- `invalid` -> no attendance record + create `invalid_event` history entry.

## Compatibility Notes

- Contract aligns with existing session, recognition-event, and attendance persistence boundaries.
- Contract is local-process and offline-safe; no remote dependency is required for acceptance.
