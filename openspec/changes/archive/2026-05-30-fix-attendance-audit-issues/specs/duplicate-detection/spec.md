## MODIFIED Requirements

### Requirement: Optimized Duplicate Detection with Reduced Query Count
The system SHALL detect duplicate attendance (same user in same session twice) with minimal database queries. The total query count for handling a duplicate recognition SHALL NOT EXCEED 6 queries.

#### Scenario: Duplicate detection uses single validation pass
- **WHEN** a user is recognized for the second time in a session
- **THEN** the system validates the session and user once (2 queries), not twice

#### Scenario: Duplicate path avoids redundant event insertion
- **WHEN** a duplicate recognition is detected
- **THEN** the system does not re-insert the recognition event (one event INSERT, not two)

#### Scenario: Duplicate path executes within 6-query budget
- **WHEN** a duplicate recognition is processed (success → UNIQUE constraint → fallback)
- **THEN** the total SQL query count is: 2 validations + 1 event INSERT + 1 attendance INSERT + 1 fallback SELECT + 1 metadata = ≤6 queries

#### Scenario: Duplicate detection maintains transactional integrity
- **WHEN** processing a duplicate recognition
- **THEN** all database writes occur within a single transaction (no partial commits)

#### Scenario: Query optimization does not impact correctness
- **WHEN** detecting duplicates in a session with many records
- **THEN** the duplicate detection is still accurate and does not skip or misidentify records
