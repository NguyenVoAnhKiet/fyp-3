# face-pose-reference-storage Specification

## Purpose
Pose-specific face reference storage for enrollment and recognition.

## Requirements
### Requirement: Pose-specific face reference storage
The system SHALL store one face embedding per fixed pose label for each enrolled user in the `face_references` table.

#### Scenario: User has five stored pose references
- **WHEN** a user completes enrollment successfully
- **THEN** the system stores five face reference rows for that user
- **AND** each row is associated with exactly one pose label

### Requirement: Fixed outside-world pose labels
The system SHALL use the fixed pose labels `center`, `right`, `left`, `up`, and `down` for stored face references.

#### Scenario: Pose label is persisted
- **WHEN** the system stores a pose-specific embedding
- **THEN** the stored row includes the pose label used for that capture

### Requirement: Unique pose reference per user
The system SHALL enforce uniqueness on the combination of user and pose label so that a user can store at most one reference for each pose label.

#### Scenario: Duplicate pose for the same user
- **WHEN** the system attempts to store a second embedding for the same user and pose label
- **THEN** the existing pose reference is replaced or updated as part of the enrollment replacement flow

### Requirement: Optional embedding encryption per row
The system SHALL preserve the existing optional embedding encryption behavior for each stored pose reference.

#### Scenario: Encryption key is configured
- **WHEN** the embedding encryption key is available
- **THEN** each stored pose embedding is encrypted before being written to the database
