# Data Model: Admin User and Biometric Enrollment

## User Profile

Represents a person being enrolled for future attendance recognition.

Fields:
- `id`: unique identifier
- `student_id`: institutional identifier
- `full_name`: display name
- `is_active`: whether the person can be used in attendance flows
- `created_at`: creation timestamp
- `updated_at`: last update timestamp

Validation rules:
- `student_id` must be unique.
- `full_name` must not be empty.

## Biometric Reference

Represents the derived biometric output created after enrollment completes.

Fields:
- `id`: unique identifier
- `user_id`: linked user profile
- `embedding`: derived biometric vector data
- `model_name`: identifier of the derivation method used
- `vector_length`: number of values in the vector
- `created_at`: creation timestamp

Relationships:
- One user profile has at most one active biometric reference.

Validation rules:
- The stored data must be derived only and must not include raw face images.

## Enrollment Session

Represents one administrator-driven enrollment attempt.

Fields:
- `id`: unique identifier
- `user_id`: linked target user
- `admin_identifier`: acting administrator identity
- `status`: `active`, `completed`, `cancelled`, or `failed`
- `started_at`: session start timestamp
- `ended_at`: session end timestamp or null while active
- `accepted_sample_count`: number of accepted samples collected
- `minimum_required_samples`: required sample threshold for completion
- `failure_reason`: optional summary when the session does not complete

Relationships:
- A user profile can have multiple historical sessions but only one active session at a time.

Validation rules:
- Active sessions must be unique per target user.
- Completed sessions must have at least the required number of accepted samples.

## Enrollment Sample Assessment

Represents the decision for one captured sample during an enrollment session.

Fields:
- `id`: unique identifier
- `session_id`: linked enrollment session
- `sample_index`: capture sequence number
- `captured_at`: timestamp of capture
- `accepted`: whether the sample passed quality checks
- `rejection_reason`: optional reason when the sample is rejected

Validation rules:
- Rejected samples must include a reason that can be shown to the administrator.
- Sample assessments belong to exactly one enrollment session.

## Enrollment Audit Record

Represents the immutable record of an administrative action taken during enrollment.

Fields:
- `id`: unique identifier
- `session_id`: linked enrollment session
- `admin_identifier`: acting administrator identity
- `event_type`: `started`, `sample_accepted`, `sample_rejected`, `completed`, `cancelled`, or `failed`
- `occurred_at`: timestamp
- `details`: optional audit note

Validation rules:
- Each lifecycle event should be traceable to the responsible administrator.
- Audit records must remain available after the session closes.

## Security and Operational Notes

- Raw enrollment images are transient working data and are not part of the persistent model.
- The biometric reference is the only enrollment artifact intended for later attendance recognition.
- Session and audit records provide accountability without retaining unnecessary biometric source material.