# Research: Database & Storage Core

## Decision 1: Python 3.11+ with SQLite-backed local persistence

Rationale: The project context already targets a Python desktop app, and Python 3.11+ gives modern typing and stable SQLite integration while remaining compatible with the offline, Windows-based deployment model.

Alternatives considered: Older Python versions. Rejected because the workspace conventions already favor newer typing and there is no benefit to constraining the feature to an older runtime.

## Decision 2: SQLite transactional storage with foreign keys and WAL

Rationale: The feature is explicitly offline-first and local-only, so SQLite is the simplest durable store that still supports atomic writes, referential integrity, and lightweight concurrency improvements through WAL mode.

Alternatives considered: Flat files or an external database server. Rejected because they add operational complexity without improving the feature’s core requirements.

## Decision 3: Separate authentication material from user profile data

Rationale: Admin credentials should be hashed and isolated from operational profile records so the system minimizes the chance of accidental plaintext exposure and keeps the security boundary clear.

Alternatives considered: Storing admin password material in the user table. Rejected because it weakens the privacy boundary and complicates auditability.

## Decision 4: Store face references as derived biometric data only

Rationale: The constitution requires privacy by design, so persisted enrollment data should be limited to embeddings and associated metadata. Raw enrollment images should be discarded after feature extraction.

Alternatives considered: Persisting original enrollment images for reprocessing. Rejected because it conflicts with privacy requirements and increases risk.

## Decision 5: Enforce duplicate prevention at the database boundary

Rationale: Attendance integrity is strongest when the database itself prevents duplicate final records through uniqueness constraints and transactions, not only the UI or service layer.

Alternatives considered: Checking duplicates only in application logic. Rejected because concurrent writes could still create duplicates.

## Decision 6: Capture session-time configuration snapshots

Rationale: Thresholds and other settings can change over time, so session records should preserve the values used when decisions were made. This supports reproducibility and audit trails.

Alternatives considered: Reading current settings only at report time. Rejected because it makes historical decisions hard to explain.

## Decision 7: Validate with focused persistence and privacy tests

Rationale: The most important proof points for this feature are initialization, restart durability, duplicate blocking, privacy retention, and fast local CRUD. These are all measurable with automated tests.

Alternatives considered: Broad manual smoke testing only. Rejected because the feature needs repeatable validation evidence.