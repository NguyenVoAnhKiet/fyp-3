# Quickstart: Admin User and Biometric Enrollment

## Purpose

Use this checklist to verify the enrollment feature once it is implemented.

## Setup

1. Activate the Python 3.11+ environment used by the repository.
2. Install the project dependencies needed for the desktop application and test suite.
3. Confirm the local SQLite database can be initialized in the workspace.

## Validation Steps

1. Run the focused enrollment checks first:

```bash
PYTHONPATH=src pytest tests/unit/test_enrollment_service.py tests/integration/test_enrollment_flow.py tests/integration/test_enrollment_privacy.py tests/integration/test_enrollment_quality.py
```

2. Run the repository test suite:

```bash
PYTHONPATH=src pytest tests/
```

3. Run the repository lint check:

```bash
python -m ruff check src tests/unit/test_enrollment_service.py tests/integration/test_enrollment_flow.py tests/integration/test_enrollment_privacy.py tests/integration/test_enrollment_quality.py
```

4. Create a new user profile and start an enrollment session for that user.
5. Capture a rejected sample and then an accepted sample, and confirm progress updates while the audit trail records both outcomes.
6. Capture valid samples until enrollment completes and verify one derived biometric reference is stored.
7. Confirm all raw image artifacts from that session are deleted after completion.
8. Start a second enrollment session for the same user while the first is still active and confirm the duplicate start is blocked.
9. Cancel or fail an in-progress enrollment and confirm the raw image cleanup path still runs.

## Expected Outcomes

- Enrollment starts only for administrators with valid privileges.
- A completed enrollment produces exactly one derived biometric reference per user.
- Raw enrollment images are removed after completion, cancellation, or failure.
- Duplicate active enrollment sessions for the same user are prevented.
- Audit records remain available for the session lifecycle.

## Troubleshooting

- If enrollment completion fails, check the minimum-sample rules and quality rejection criteria.
- If raw images remain, inspect the cleanup path executed after feature extraction and cancellation.
- If duplicate sessions are created, verify the uniqueness rule on the active session state.