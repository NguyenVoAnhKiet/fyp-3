## MODIFIED Requirements

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
