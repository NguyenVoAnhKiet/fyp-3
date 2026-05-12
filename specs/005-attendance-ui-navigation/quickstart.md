# Quickstart: Attendance UI Navigation Architecture

## Purpose

Use this checklist to validate Module 5 UI navigation behavior and runtime quality targets.

## Setup

1. Activate the repository Python 3.11+ environment.
2. Ensure local SQLite database and existing attendance/vision services are initialized.
3. Connect a camera device and verify it is detected by the local workstation.
4. Disable internet connectivity for offline-first validation scenarios.

## Validation Steps

1. Run baseline unit/integration checks for attendance workflow dependencies:

```bash
python -m pytest tests/unit/test_attendance_service.py tests/integration/test_vision_pipeline_flow.py tests/integration/test_offline_behavior.py
```

1. Run Module 5 UI validation suite:

```bash
python -m pytest tests/unit/test_ui_bootstrap.py tests/unit/test_ui_foundation.py tests/unit/test_ui_state_machine.py tests/unit/test_ui_navigation_regression.py tests/unit/test_ui_frame_bridge.py tests/unit/test_ui_hotkeys.py tests/contract/test_ui_command_contract.py tests/integration/test_ui_state_navigation.py tests/integration/test_ui_live_preview.py tests/integration/test_ui_camera_degraded.py tests/integration/test_ui_fps_threshold.py tests/integration/test_ui_hotkey_latency.py tests/integration/test_ui_status_color_mapping.py tests/integration/test_ui_offline_navigation.py
```

2. Start the application in `IDLE` state and verify visible state indicator.
3. Press `S` and verify transition to `LIVE_ATTENDANCE` plus active-mode visual status.
4. Keep live preview running for 10 minutes and sample displayed FPS; confirm >=24 FPS in at least 95% of samples.
5. During live preview, press `E` and verify deterministic transition back to `IDLE`.
6. Press `E` while in `IDLE`; verify action is rejected safely with clear user feedback.
7. Press `Q` from both `IDLE` and `LIVE_ATTENDANCE`; verify graceful and responsive quit behavior.
8. Simulate temporary camera unavailability and verify non-blocking warning plus continued command responsiveness.
9. Feed representative recognition outcomes and verify color mapping remains fixed:
   - Success -> Green
   - Caution/Pending -> Yellow
   - Warning/Failure -> Red
10. Repeat key flows with internet disabled and verify all core controls remain operational.

## Expected Outcomes

- State transitions are deterministic and reflect valid command contexts.
- Hotkey commands respond quickly without freezing the UI.
- Live preview remains smooth and meets FPS target under normal conditions.
- Camera issues are surfaced as recoverable warnings without blocking controls.
- Color semantics are consistent and immediately interpretable by operators.
- Offline mode does not reduce core UI operation capabilities.

## Troubleshooting

- If FPS drops persistently below threshold, inspect frame handoff and UI render timer cadence.
- If hotkeys feel delayed, review UI-thread blocking operations and event dispatch sequence.
- If color feedback is inconsistent, verify centralized outcome-to-color mapping and remove local overrides.
- If camera warning does not clear, verify `update_stream_status` transitions to `READY` or `DEGRADED` after frames resume.
