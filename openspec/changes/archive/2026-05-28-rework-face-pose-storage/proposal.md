## Why

The current enrollment flow collapses five pose-specific captures into one averaged embedding, which leaves recognition less accurate when the live face angle differs from the averaged reference. We need to store and match the five pose signatures separately so recognition can compare against the closest pose-specific reference.

## What Changes

- Store five pose-specific face embeddings per user instead of one averaged embedding.
- Keep the `face_references` table name, but add `pose_label` and enforce uniqueness per `(user_id, pose_label)`.
- Use fixed outside-facing pose labels: `center`, `right`, `left`, `up`, `down`.
- Require all five poses to be captured successfully before enrollment can be saved.
- Re-enrollment replaces the full set of five pose references in one transaction.
- Recognition keeps best-match behavior across all stored references and records the matched pose label in logs.
- Enrollment guidance follows the outside-world pose order rather than the mirrored camera-order labels.
- **BREAKING**: existing single-embedding enrollment data is not migrated; this change assumes a fresh database.

## Capabilities

### New Capabilities
- `face-pose-reference-storage`: Persist and manage one embedding per fixed pose label for each user, including bulk replace and pose-aware logging.

### Modified Capabilities
- `face-enrollment`: Enrollment now saves five pose-specific references instead of one averaged embedding and requires all five captures to succeed.
- `head-pose-guided-enrollment`: Pose guidance follows the outside-world pose labels and capture order used for storage.

## Impact

- Database schema for `face_references` changes to include `pose_label` and a composite uniqueness rule.
- Enrollment UI, enrollment worker, enrollment service, face reference repository, and recognition result payload all need updates.
- Recognition event logging gains pose information in raw-text form via `details`.
- Unit and integration tests for enrollment, storage, and face recognition need to be updated.
