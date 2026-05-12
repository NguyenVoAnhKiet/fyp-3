# Data Model: Database & Storage Core

## User Account

Represents an enrolled person in the attendance system.

Fields:
- `id`: unique identifier
- `student_id`: external enrollment identifier
- `full_name`: display name
- `is_active`: whether the account is usable
- `created_at`: creation timestamp
- `updated_at`: last update timestamp

Validation rules:
- `student_id` must be unique.
- `full_name` must not be empty.
- Deactivated users remain in storage for auditability.

## Face Reference

Represents the derived biometric reference for a user.

Fields:
- `id`: unique identifier
- `user_id`: linked user account
- `embedding`: serialized vector data
- `model_name`: embedding model used
- `vector_length`: number of values in the embedding
- `created_at`: creation timestamp

Relationships:
- One user has at most one active face reference.

Validation rules:
- The embedding must be stored only in derived form.
- The linked user must exist.

## Attendance Session

Represents a class meeting or attendance run.

Fields:
- `id`: unique identifier
- `subject_name`: course or subject name
- `class_name`: class/group name
- `status`: planned, active, closed, or interrupted
- `start_time`: session start timestamp
- `end_time`: session end timestamp
- `liveness_threshold_snapshot`: threshold value in effect when the session started
- `similarity_threshold_snapshot`: threshold value in effect when the session started

Validation rules:
- A session must have a start time when it becomes active.
- End time must not precede start time.

State transitions:
- `planned` -> `active` -> `closed`
- `active` -> `interrupted`

## Recognition Event

Represents an individual recognition attempt recorded during a session.

Fields:
- `id`: unique identifier
- `session_id`: linked session
- `user_id`: matched user, if any
- `event_time`: time of the attempt
- `result`: success, duplicate, spoof_warning, or unrecognized
- `liveness_score`: score produced by the liveness step
- `similarity_score`: score produced by the recognition step
- `details`: optional audit notes

Relationships:
- Each recognition event belongs to exactly one session.
- A recognition event may be linked to a user when a match is found.

Validation rules:
- `result` must be one of the approved status values.
- The event timestamp must fall within the session lifecycle window.

## Attendance Record

Represents the final attendance outcome for a learner in a session.

Fields:
- `id`: unique identifier
- `session_id`: linked session
- `user_id`: linked user
- `status`: success, duplicate, spoof_warning, or unrecognized
- `recorded_at`: timestamp

Relationships:
- A session can contain many attendance records.
- A user can have at most one final attendance record per session.

Validation rules:
- `(session_id, user_id)` must be unique.
- Committed records should be treated as immutable except through controlled correction workflows.

## System Setting

Represents a configurable operational value.

Fields:
- `setting_key`: unique key
- `setting_value`: stored value
- `value_type`: optional type marker
- `updated_at`: last update timestamp

Validation rules:
- Setting keys must be unique.
- Invalid values must be rejected or replaced with safe defaults.

## Security/Operational Notes

- Admin credential data is not stored in the core attendance tables.
- Raw enrollment images are never part of the persistent model.
- Threshold values in a session should be treated as snapshots, not live references.