## Requirements

### Requirement: Pose-guided enrollment sequence
When head pose guidance is enabled, the enrollment flow SHALL require the user to complete five poses in order before enrollment can finish: frontal, right turn, left turn, tilt up, and tilt down.

#### Scenario: Sequence starts at frontal pose
- **WHEN** an admin starts a new enrollment session with head pose guidance enabled
- **THEN** the system requires the first capture to satisfy the frontal pose target before advancing

#### Scenario: Sequence advances only to next required pose
- **WHEN** a capture succeeds for the current required pose
- **THEN** the system advances to exactly the next pose in the predefined sequence

### Requirement: Pose validation with tolerance
The system MUST evaluate estimated yaw and pitch against the current target pose using a bounded tolerance to determine whether the pose is valid for capture.

#### Scenario: Pose considered valid inside threshold
- **WHEN** the current frame angles are within the configured tolerance of the active pose target
- **THEN** the system marks the pose as matched for that frame

#### Scenario: Pose considered invalid outside threshold
- **WHEN** the current frame angles exceed the configured tolerance for the active pose target
- **THEN** the system marks the pose as unmatched for that frame

### Requirement: Hold-to-capture gating
The system SHALL only attempt capture for a required pose after the pose has remained matched for the configured number of consecutive frames.

#### Scenario: Hold counter increments on consecutive match
- **WHEN** consecutive frames continue matching the active pose target
- **THEN** the system increments hold progress toward the hold-frame requirement

#### Scenario: Hold counter resets on mismatch
- **WHEN** a frame does not match the active pose target before capture occurs
- **THEN** the system resets hold progress for that pose

### Requirement: Capture quality gate integration
Even when pose hold criteria are met, the system MUST only accept a capture if existing liveness and embedding extraction checks succeed.

#### Scenario: Pose matched but liveness fails
- **WHEN** the pose hold requirement is satisfied but liveness validation fails
- **THEN** the system rejects the capture and keeps the session on the same required pose

#### Scenario: Pose matched but embedding extraction fails
- **WHEN** the pose hold requirement is satisfied but embedding extraction fails
- **THEN** the system rejects the capture and keeps the session on the same required pose

### Requirement: Real-time enrollment guidance
The enrollment UI SHALL display the active required pose, current pose progress, and directional guidance derived from angle error while head pose guidance is enabled.

#### Scenario: Guidance shown for incorrect pose
- **WHEN** current yaw/pitch indicates the user is not in the required pose
- **THEN** the system shows corrective guidance indicating the adjustment direction

#### Scenario: Holding feedback shown for correct pose
- **WHEN** current yaw/pitch matches the required pose
- **THEN** the system shows hold progress feedback until capture is attempted

### Requirement: Real-time enrollment guidance
The enrollment UI SHALL display the active required pose, current pose progress, and directional guidance derived from angle error while head pose guidance is enabled.

#### Scenario: Guidance shown for incorrect pose
- **WHEN** current yaw/pitch indicates the user is not in the required pose
- **THEN** the system shows corrective guidance indicating the adjustment direction

#### Scenario: Holding feedback shown for correct pose
- **WHEN** current yaw/pitch matches the required pose
- **THEN** the system shows hold progress feedback until capture is attempted

### Requirement: Backward-compatible fallback mode
If head pose guidance is disabled by configuration or the model is unavailable, enrollment MUST continue using the legacy capture flow without pose enforcement.

#### Scenario: Guidance disabled by configuration
- **WHEN** head pose guidance is explicitly disabled at runtime
- **THEN** enrollment uses the existing non-pose-gated behavior

#### Scenario: Model unavailable at runtime
- **WHEN** head pose guidance cannot initialize due to missing or invalid model path
- **THEN** enrollment continues with legacy behavior and surfaces a warning
