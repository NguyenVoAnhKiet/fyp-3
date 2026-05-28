## Context

The current enrollment pipeline captures five head poses but reduces them to one averaged embedding before persistence. Recognition then compares the live embedding against a single reference per user. The system now needs pose-specific storage so each user keeps one embedding per fixed outside-world pose label and recognition can match against the closest pose-specific reference.

This change touches enrollment UI, enrollment worker, enrollment service, face reference repository, recognition result payloads, database schema, and tests.

## Goals / Non-Goals

**Goals:**
- Persist five pose-specific embeddings per user.
- Keep `face_references` as the storage table, but make it pose-aware.
- Use fixed labels: `center`, `right`, `left`, `up`, `down`.
- Replace all five pose rows atomically on re-enrollment.
- Keep recognition best-match based across all stored references.
- Capture matched pose label in recognition logs.
- Preserve optional embedding encryption.

**Non-Goals:**
- No migration of legacy averaged embeddings.
- No pose-aware recognition filtering during runtime.
- No new external ML models or new runtime dependencies.
- No new user-facing UI for technical pose labels.

## Decisions

### Store one row per pose label
Keep `face_references` and add `pose_label`, with `UNIQUE(user_id, pose_label)`. This is simpler than creating a separate table and keeps repository and query code close to the current shape.

Alternative considered: pack all five embeddings into one BLOB. Rejected because it makes reads, writes, debugging, and future pose-level inspection much harder.

### Use outside-world pose labels
Persist `center/right/left/up/down` in the database rather than camera-mirror labels. The camera preview remains mirrored for UX, but storage and logs should reflect the physical movement the user actually performed.

Alternative considered: store labels in mirrored camera order. Rejected because it is less intuitive for debugging and for interpreting reference data.

### Treat re-enrollment as full replacement
Re-enrollment deletes all existing pose rows for the user and inserts the five new rows in one transaction. This prevents mixed old/new pose sets.

Alternative considered: upsert pose-by-pose individually. Rejected because it can leave partially updated data if enrollment fails midway.

### Keep recognition pose-agnostic
Recognition continues to compare the live embedding against all stored references and returns the best match. The matched pose label is recorded for observability, but it does not restrict which references may match.

Alternative considered: filter by live head pose before matching. Rejected for now because it adds runtime complexity without being necessary to realize the main accuracy improvement.

### Keep raw-text logging for matched pose
Use the existing `details` text field to store `matched_pose=<label>`. This avoids an immediate schema expansion for logs while still making the match visible for debugging.

## Risks / Trade-offs

- [More stored rows per user] → Recognition will compare against up to 5x more references, so runtime cost increases moderately.
- [Threshold drift] → Best-of-five matching may raise similarity scores, so the similarity threshold may need recalibration after rollout.
- [Atomicity sensitivity] → Re-enrollment must be transaction-safe; partial writes would create invalid pose sets. Use a bulk replace operation inside one DB transaction.
- [Legacy data discarded] → Fresh-DB rollout means existing embeddings are not preserved. This is acceptable by request but must be made explicit to operators.
