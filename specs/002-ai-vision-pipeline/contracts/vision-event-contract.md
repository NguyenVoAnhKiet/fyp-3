# Vision Event Contract

This contract defines the normalized event payload emitted by the AI engine and consumed by the attendance module.

## Event Types

- `recognized_identity`: a real face matched a known user with sufficient similarity
- `unknown_identity`: a real face passed liveness but did not meet the recognition threshold
- `spoof_warning`: liveness failed and the frame must not be treated as a valid attendance attempt
- `no_face_detected`: no usable face was found in the frame; diagnostic only

## Required Fields

- `session_id`: integer session identifier
- `event_time`: ISO 8601 timestamp
- `event_type`: one of the event types above
- `liveness_score`: numeric score or null when not applicable
- `similarity_score`: numeric score or null when not applicable
- `user_id`: integer or null
- `details`: optional diagnostic text

## Mapping to persisted results

- `recognized_identity` maps to a successful attendance flow.
- `unknown_identity` maps to an unrecognized result.
- `spoof_warning` maps to a spoof warning result.
- `no_face_detected` is not written as attendance and may remain transient unless later diagnostic persistence is added.

## Validation Rules

- The event must include the current session context.
- A spoof warning must not include a successful attendance claim.
- A recognized identity event must only be emitted after liveness passes.
- The event contract must remain compatible with the existing recognition event persistence model.