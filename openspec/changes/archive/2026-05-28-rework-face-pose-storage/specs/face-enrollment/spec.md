## MODIFIED Requirements

### Requirement: Admin UI for Biometric Enrollment
The system SHALL provide an `EnrollmentWidget` in the Admin Dashboard for enrolling user faces. This widget MUST allow the admin to select an existing user to enroll.

#### Scenario: Enrolling a user
- **WHEN** the admin opens the Enrollment widget
- **THEN** they can select a user from a dropdown field
- **AND** they can start the camera stream to capture the user's face

### Requirement: Visual Guidance for Enrollment
The system SHALL display visual guidance on the camera feed during enrollment to ensure high-quality captures.

#### Scenario: User is capturing face
- **WHEN** the enrollment camera is active
- **THEN** text overlays like "Chính diện", "Quay phải", "Quay trái", "Ngửa lên", and "Cúi xuống" are displayed in the required order

### Requirement: Pose-specific capture for enrollment
The system SHALL collect five pose-specific face embeddings per user and store them separately rather than averaging them into a single embedding.

#### Scenario: All required poses are captured
- **WHEN** the required five pose captures complete successfully
- **THEN** the system persists one embedding per pose label
- **AND** the user is marked as enrolled only after all five pose references are saved

### Requirement: Replace full pose set on re-enrollment
The system SHALL replace all existing face references for a user when re-enrollment succeeds.

#### Scenario: Re-enrollment completes
- **WHEN** the admin re-enrolls a user and all five pose captures succeed
- **THEN** the system deletes the previous pose references for that user
- **AND** stores the new five pose references in a single transaction
