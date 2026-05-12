# Research: Admin User and Biometric Enrollment

## Decisions

### Reuse the existing identity and biometric foundations
- Decision: Keep `users` as the canonical enrolled-person table and `face_references` as the derived biometric store.
- Rationale: The repository already has stable CRUD and persistence for both entities, so the feature should extend the existing model instead of duplicating identity data.
- Alternatives considered: Introducing a separate enrollment identity table. Rejected because it would fragment the user record and complicate attendance lookup.

### Add enrollment-specific workflow records
- Decision: Introduce enrollment session and audit records to capture who enrolled whom, when the session started and ended, and whether the attempt completed, failed, or was cancelled.
- Rationale: The current schema does not preserve enrollment lifecycle detail, and the feature specification requires auditability plus a verifiable privacy cleanup path.
- Alternatives considered: Encoding the full workflow only in logs. Rejected because logs are harder to query and validate in automated tests.

### Keep raw images transient
- Decision: Treat raw enrollment images as temporary working data only and delete them immediately after the derived biometric reference is produced or the session ends.
- Rationale: The spec explicitly requires removal of raw image data for privacy.
- Alternatives considered: Retaining images for future reprocessing. Rejected because it violates the privacy requirement.

### Orchestrate enrollment in the service layer
- Decision: Implement enrollment as a service that coordinates repositories, validation, cleanup, and audit updates.
- Rationale: The existing codebase already separates persistence into repositories and business rules into services, which keeps the workflow testable.
- Alternatives considered: Putting session logic directly into repositories. Rejected because it would mix business rules with persistence concerns.

### Validate with automated tests
- Decision: Cover the feature with pytest unit and integration tests for session lifecycle, duplicate-session prevention, cleanup behavior, and persistence of derived references.
- Rationale: The repository already uses pytest and the feature has several behavioral guarantees that are easiest to verify automatically.
- Alternatives considered: Manual-only validation. Rejected because cleanup and concurrency rules need repeatable proof.

## Findings

- `EnrollmentService` already deletes a raw image path after persisting a derived embedding, which is a useful starting point for the privacy cleanup path.
- `face_references` already enforces one reference per user at the database level.
- `users` already provides the stable identity anchor for enrollments.
- The schema does not yet include enrollment session or audit tables, so the feature needs schema and repository additions for workflow traceability.

## Implications

- Enrollment completion should update a derived reference and a session record together so tests can verify both business outcome and cleanup.
- Raw-image cleanup should be validated in the same path that saves the derived reference and in failure/cancellation paths.
- Session uniqueness and audit records should be enforced with the same local database boundary used elsewhere in the project.