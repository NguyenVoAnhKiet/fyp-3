# Quickstart: AI Engine & Vision Pipeline

## Goal

Verify the feature design against the existing attendance service and storage layer, then use the module in a classroom-style attendance session once the implementation is in place.

## Prerequisites

- Python 3.11+ environment
- Local SQLite database initialized by the existing storage module
- A camera device or test video source for frame input
- Registered users with stored face references

## Validation Workflow

1. Run the repository test suite:

```bash
PYTHONPATH=src pytest tests/
```

2. Run the lint check used by the project:

```bash
ruff check src/
```

3. Confirm the attendance service still records session and recognition events correctly by exercising the existing integration tests.

4. For the Module 2 implementation, verify these behaviors in order:
- a real face produces a success event
- a spoof face stops at liveness and produces a spoof warning
- a low-confidence but real face produces an unknown outcome
- the UI stays responsive during continuous processing

## Operational Flow

1. Start an attendance session and snapshot the active thresholds.
2. Start the vision worker on the configured camera source.
3. Feed frames through detect -> liveness -> recognize.
4. Emit normalized events to the attendance layer.
5. Stop the worker and close the session when the class ends.

## Acceptance Checkpoints

- No raw frame persistence in the normal processing path.
- Event payloads include session context, timestamp, result, and scores where applicable.
- Duplicate attendance remains blocked by the existing attendance uniqueness constraint.
- The pipeline keeps operating offline.
