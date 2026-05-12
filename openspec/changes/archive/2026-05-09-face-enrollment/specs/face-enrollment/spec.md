## ADDED Requirements

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
- **THEN** text overlays like "Nhìn thẳng" or "Xoay nhẹ trái/phải" are displayed

### Requirement: Auto-capture High Quality Faces
The system SHALL automatically capture frames only when the face passes the liveness check and meets a detection confidence threshold. It MUST buffer 3-5 such frames.

#### Scenario: Face is steady and passes liveness
- **WHEN** the user's face is steady and passes the MiniFASNet liveness detection
- **THEN** the system automatically captures a frame until 3-5 frames are buffered

### Requirement: Generate and Save Average Embedding
The system SHALL compute an average embedding from the buffered frames and save it to the database, marking the user as enrolled.

#### Scenario: Buffering complete
- **WHEN** the required number of high-quality frames (3-5) are captured
- **THEN** the system calculates the average embedding
- **AND** the embedding is saved via `EnrollmentService`
- **AND** the `face_registered` column is set to `1` in the `users` table
