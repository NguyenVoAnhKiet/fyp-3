# Research: Attendance UI Navigation Architecture

## Decisions

### Choose PyQt5 as the primary UI framework
- Decision: Standardize Module 5 implementation on PyQt5 rather than Tkinter.
- Rationale: PyQt5 provides stronger event-loop control, timer precision, and rendering capabilities for stable 24+ FPS preview in desktop CV workloads.
- Alternatives considered: Tkinter. Rejected because high-frequency video refresh and richer stateful UI feedback are harder to maintain consistently at target responsiveness.

### Use explicit UI state machine with guarded transitions
- Decision: Model UI mode as explicit states (`IDLE`, `LIVE_ATTENDANCE`) with validated transitions.
- Rationale: Guarded transitions reduce ambiguous behavior for start/end commands and align with attendance integrity requirements.
- Alternatives considered: Implicit state via scattered flags. Rejected due to higher risk of inconsistent control behavior.

### Keep video rendering non-blocking through producer-consumer handoff
- Decision: Consume camera frames from existing vision pipeline using queue-based handoff and render on UI timer ticks.
- Rationale: Decoupling capture/inference from rendering keeps UI responsive under load.
- Alternatives considered: Render directly from capture loop on UI thread. Rejected because it can stall hotkey handling and state updates.

### Preserve deterministic pipeline ownership outside UI
- Decision: UI only consumes finalized recognition outcomes and never computes liveness/recognition decisions.
- Rationale: Protects detect -> liveness -> recognize ordering and threshold governance from presentation-layer drift.
- Alternatives considered: UI-side post-processing of confidence rules. Rejected because it can create non-deterministic interpretations.

### Define strict color semantics for operator feedback
- Decision: Use fixed mapping: green=success, yellow=caution/pending, red=warning/failure.
- Rationale: Consistent semantics reduce interpretation errors during live operation.
- Alternatives considered: Context-dependent dynamic palettes. Rejected because changing meaning by screen context increases cognitive load.

### Validate offline-first operation as baseline behavior
- Decision: Treat network availability as irrelevant for UI operation and test all workflows without internet.
- Rationale: Classroom operation must remain functional in unstable connectivity conditions.
- Alternatives considered: Optional cloud sync dependency for UI status. Rejected because it introduces avoidable failure modes.

## Resolved Clarifications

- Framework ambiguity resolved: PyQt5 selected as the implementation baseline for this feature.
- Performance threshold clarified: UI must sustain >=24 FPS for at least 95% of sampled intervals in a 10-minute run.
- Input contract clarified: Hotkeys are constrained to `S`, `E`, `Q` with state-aware validation and non-blocking feedback.
- No unresolved NEEDS CLARIFICATION items remain for planning.
