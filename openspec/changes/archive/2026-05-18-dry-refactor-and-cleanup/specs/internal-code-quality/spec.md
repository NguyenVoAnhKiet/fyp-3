## ADDED Requirements

### Requirement: No duplicated validation logic in attendance recording
The attendance service SHALL consolidate session and user validation into a single private helper method. Both `record_success` and `record_duplicate` SHALL use this helper. The helper SHALL validate positive integers for session_id and user_id, verify session existence, and verify user existence.

#### Scenario: record_success validates session and user
- **WHEN** `record_success` is called with valid session_id and user_id
- **THEN** the shared validation helper confirms both exist before inserting records

#### Scenario: record_duplicate validates session and user
- **WHEN** `record_duplicate` is called with valid session_id and user_id
- **THEN** the shared validation helper confirms both exist before inserting records

#### Scenario: validation raises LookupError for missing session
- **WHEN** either method is called with a non-existent session_id
- **THEN** a LookupError is raised with message "Session {id} not found"

#### Scenario: validation raises LookupError for missing user
- **WHEN** either method is called with a non-existent user_id
- **THEN** a LookupError is raised with message "User {id} not found"

### Requirement: No duplicated export logic in attendance service
The attendance service SHALL use a single private method for exporting session data to both CSV and Excel formats. The method SHALL accept a format parameter and produce identical column selection and ordering for both formats.

#### Scenario: export to CSV produces correct columns
- **WHEN** `_export_session` is called with format "csv"
- **THEN** the output file contains columns: Student ID, Full Name, Status, Time

#### Scenario: export to Excel produces correct columns
- **WHEN** `_export_session` is called with format "excel"
- **THEN** the output file contains columns: Student ID, Full Name, Status, Time

#### Scenario: invalid format raises error
- **WHEN** `_export_session` is called with an unsupported format
- **THEN** a ValueError is raised

### Requirement: No duplicated cryptography import logic
The face reference repository SHALL use a single private helper method to obtain the Fernet instance. The import of `cryptography.fernet` SHALL occur in exactly one location.

#### Scenario: encryption uses shared Fernet helper
- **WHEN** `_encrypt_embedding` is called with a Fernet key set
- **THEN** it obtains the Fernet instance via the shared helper

#### Scenario: decryption uses shared Fernet helper
- **WHEN** `_decrypt_embedding` is called with a Fernet key set
- **THEN** it obtains the Fernet instance via the shared helper

#### Scenario: missing cryptography package raises clear error
- **WHEN** encryption or decryption is called with Fernet key set but cryptography not installed
- **THEN** a RuntimeError is raised with message mentioning "cryptography package is required"

### Requirement: No dead parameters in public methods
The `save_face_reference` method SHALL NOT accept a `raw_image_path` parameter. All parameters SHALL be used by the method body.

#### Scenario: save_face_reference has no unused parameters
- **WHEN** `save_face_reference` is inspected
- **THEN** it accepts only user_id, embedding, model_name, and vector_length

### Requirement: Spoof detection emits None for similarity score
When a spoof is detected, the camera thread SHALL emit `None` for the similarity score to indicate no recognition was attempted.

#### Scenario: spoof detection emits None similarity
- **WHEN** liveness check fails (spoof detected)
- **THEN** `recognition_result` is emitted with similarity_score = None

### Requirement: No stale bug-fix comments in production code
Source files SHALL NOT contain comments referencing past bug numbers or fixes that have been resolved.

#### Scenario: no "Bug" fix comments remain
- **WHEN** the codebase is searched for bug fix comments
- **THEN** no comments matching pattern "Bug \d+ fix" or similar exist
