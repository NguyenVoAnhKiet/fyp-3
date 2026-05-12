# Data Model: Attendance UI Navigation Architecture

## UI Session State

Represents the current operational mode of the attendance interface.

Fields:
- `state`: `IDLE` or `LIVE_ATTENDANCE`
- `active_session_id`: nullable identifier for the currently active attendance session
- `entered_at`: ISO 8601 timestamp for when state was entered
- `state_message`: operator-visible summary text for current mode

Validation rules:
- `active_session_id` must be null in `IDLE` and non-null in `LIVE_ATTENDANCE`.
- Transitions allowed only: `IDLE -> LIVE_ATTENDANCE`, `LIVE_ATTENDANCE -> IDLE`.

## Video Render Health

Represents runtime health of the displayed camera feed.

Fields:
- `stream_status`: `READY`, `DEGRADED`, or `UNAVAILABLE`
- `display_fps`: rolling measured frame rate for UI display
- `last_frame_at`: ISO 8601 timestamp of most recent rendered frame
- `warning_message`: nullable human-readable warning text

Validation rules:
- `display_fps` must be numeric and non-negative.
- `UNAVAILABLE` requires a visible warning state.

## Operator Command Event

Represents a keyboard-triggered operator action handled by the UI.

Fields:
- `command`: `START` (`S`), `END` (`E`), or `QUIT` (`Q`)
- `triggered_at`: ISO 8601 timestamp
- `origin_state`: UI state at the moment command was received
- `result`: `ACCEPTED` or `REJECTED`
- `rejection_reason`: nullable text when `result=REJECTED`

Validation rules:
- `START` is valid only in `IDLE`.
- `END` is valid only in `LIVE_ATTENDANCE`.
- `QUIT` is valid in both states.

## Visual Outcome Signal

Represents the normalized color-coded feedback shown to operators.

Fields:
- `outcome_type`: `SUCCESS`, `CAUTION`, or `WARNING`
- `color_code`: `GREEN`, `YELLOW`, or `RED`
- `label`: short text rendered with color
- `updated_at`: ISO 8601 timestamp

Validation rules:
- Mapping is fixed and one-to-one:
  - `SUCCESS -> GREEN`
  - `CAUTION -> YELLOW`
  - `WARNING -> RED`
- UI must not display conflicting color semantics for the same outcome type.

## Consistency Notes

- UI state transitions drive command validity and visible controls.
- Video health state must not block command handling.
- Visual outcome updates are presentation artifacts and do not overwrite underlying attendance persistence records.
