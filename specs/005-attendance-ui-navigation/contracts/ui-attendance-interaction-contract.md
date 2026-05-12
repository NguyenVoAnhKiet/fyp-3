# Contract: UI Attendance Interaction

## Purpose

Define the interaction contract between the UI layer (Module 5) and core attendance/session services for state transitions, live status rendering, and operator commands.

## 1. UI State Contract

### States
- `IDLE`
- `LIVE_ATTENDANCE`

### Allowed transitions
- `IDLE -> LIVE_ATTENDANCE` on accepted `START` command
- `LIVE_ATTENDANCE -> IDLE` on accepted `END` command

### Invalid transitions
- `IDLE -> IDLE` via `END` command must be rejected
- `LIVE_ATTENDANCE -> LIVE_ATTENDANCE` via duplicate `START` command must be rejected

## 2. Operator Command Contract

### Input commands
- `S` => `START`
- `E` => `END`
- `Q` => `QUIT`

### Command response schema

```json
{
  "command": "START|END|QUIT",
  "origin_state": "IDLE|LIVE_ATTENDANCE",
  "result": "ACCEPTED|REJECTED",
  "reason": "string|null",
  "handled_at": "ISO_8601"
}
```

### Rules
- `START` is accepted only when `origin_state=IDLE`.
- `END` is accepted only when `origin_state=LIVE_ATTENDANCE`.
- `QUIT` is accepted in all states.
- Rejected commands MUST return a non-null `reason`.

## 3. Live Video Status Contract

### Video status schema

```json
{
  "stream_status": "READY|DEGRADED|UNAVAILABLE",
  "display_fps": 0,
  "updated_at": "ISO_8601",
  "message": "string|null"
}
```

### Rules
- `display_fps` is measured at render output level.
- `stream_status=UNAVAILABLE` MUST provide a user-visible warning message.
- Command handling remains available regardless of video status.

## 4. Outcome-to-Color Contract

### Mapping
- `SUCCESS -> GREEN`
- `CAUTION -> YELLOW`
- `WARNING -> RED`

### Response schema

```json
{
  "outcome_type": "SUCCESS|CAUTION|WARNING",
  "color": "GREEN|YELLOW|RED",
  "label": "string",
  "updated_at": "ISO_8601"
}
```

### Rules
- Mapping is fixed and MUST NOT vary by screen context.
- UI layer MUST render only mapped colors for defined outcomes.

## 5. Non-Functional Contract

- UI command response target: <=200ms for 99% of valid commands.
- Live preview target: >=24 FPS for >=95% sampled intervals during a 10-minute run.
- All workflows above MUST function without internet connectivity.
