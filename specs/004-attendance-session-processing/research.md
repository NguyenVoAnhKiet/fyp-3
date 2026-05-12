# Research: Attendance Session Processing

## Decisions

### Keep session lifecycle as the gate for event intake
- Decision: Only process attendance outcomes when exactly one session is in ACTIVE state.
- Rationale: Session-gated intake keeps attendance scoped to one class and prevents cross-session ambiguity.
- Alternatives considered: Accepting events without checking session status. Rejected because events could be written to the wrong class context.

### Enforce duplicate prevention at persistence boundary
- Decision: Apply duplicate checks using session and student identity before writing successful attendance records.
- Rationale: Duplicate prevention must remain correct even if upstream event bursts repeat the same identity.
- Alternatives considered: Deduplicate only in UI memory. Rejected because process restarts or concurrent producers could bypass in-memory guards.

### Persist spoof outcomes as warning history, not attendance success
- Decision: Store spoof-detected events as warning outcomes in session history while never counting them as present attendance.
- Rationale: This preserves audit transparency and upholds attendance integrity.
- Alternatives considered: Dropping spoof events entirely. Rejected because instructors need traceability for suspicious attempts.

### Validate malformed AI payloads and continue processing
- Decision: Reject malformed outcome payloads (missing identity or outcome type) and log validation rejects without stopping the active session pipeline.
- Rationale: Real-time systems should degrade safely and keep valid traffic flowing.
- Alternatives considered: Fail-fast and stop processing on first malformed event. Rejected because one bad event should not interrupt a running class.

### Preserve deterministic event order with a single consumer path
- Decision: Keep a single ordered consumer path from vision events to attendance persistence for each active session.
- Rationale: Ordered processing simplifies duplicate checks and makes auditing reproducible.
- Alternatives considered: Parallel writes for higher throughput. Rejected because ordering conflicts can create race conditions and duplicate writes.

### Keep operations fully local for offline-first behavior
- Decision: Use local SQLite persistence only for session start, event handling, and history updates.
- Rationale: Classroom operations must continue without internet access.
- Alternatives considered: Remote sync as a hard dependency. Rejected because network loss would block attendance.

## Resolved Clarifications

- Technical stack, storage model, and test framework are already defined in the repository standards: Python 3.11+, SQLite3 (WAL), and pytest.
- Performance gate aligns with the constitution and spec success criteria: event outcomes should be persisted within 2 seconds under normal load.
- No unresolved NEEDS CLARIFICATION items remain for this feature.
