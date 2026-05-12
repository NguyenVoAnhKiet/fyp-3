# Quickstart: Attendance Session Processing

## Purpose

Use this checklist to validate Module 4 attendance-session behavior after implementation.

## Setup

1. Activate the repository Python 3.11+ environment.
2. Ensure the local SQLite database is initialized for the workspace.
3. Confirm the application can run in offline mode.

## Validation Steps

1. Run focused attendance and pipeline tests:

```bash
python -m pytest tests/unit/test_attendance_service.py tests/unit/test_vision_event_adapter.py tests/integration/test_attendance_history.py tests/integration/test_attendance_audit.py tests/integration/test_vision_pipeline_flow.py tests/integration/test_offline_behavior.py
```

2. Run contract validation:

```bash
python -m pytest tests/contract/test_vision_event_contract.py
```

3. Start a new attendance session with valid course and class metadata and verify status becomes ACTIVE.
4. Send one valid `success` outcome for a student and verify one attendance record is created.
5. Send the same `success` outcome again and verify no duplicate attendance record is created while history captures duplicate blocking.
6. Send a `spoof_warning` outcome and verify warning history is recorded without marking attendance success.
7. Send an invalid payload (for example, missing required fields) and verify it is logged as invalid without interrupting subsequent valid processing.
8. End the session and verify new outcomes are no longer accepted for attendance persistence.

## Expected Outcomes

- Session activation requires complete metadata and transitions to ACTIVE immediately.
- Successful attendance is recorded once per student per session.
- Spoof and invalid outcomes are retained as auditable history entries.
- Valid operations continue in offline mode without internet dependency.
- Closed sessions reject additional event persistence.

## Troubleshooting

- If duplicates are still stored, verify session-scoped duplicate checks in attendance write path.
- If spoof attempts count as attendance, inspect outcome mapping from event adapter to persistence.
- If events are accepted after session close, check ACTIVE-state gating before persistence.
