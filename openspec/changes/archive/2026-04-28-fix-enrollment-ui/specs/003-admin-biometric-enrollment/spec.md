## MODIFIED Requirements

### Requirement: FR-004
System MUST provide a guided capture workflow that includes a live camera preview, reports current progress, provides an explicit capture action (e.g. button or hotkey), and displays required remaining samples.

#### Scenario: Live camera preview
- **WHEN** the administrator opens the enrollment dialog
- **THEN** a live camera feed is displayed to help position the user's face

#### Scenario: Manual sample capture
- **WHEN** the administrator activates the "Capture" action (via button or hotkey)
- **THEN** the system captures the current frame from the camera feed and processes it as an enrollment sample
