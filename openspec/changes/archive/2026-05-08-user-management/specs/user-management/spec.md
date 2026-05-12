## ADDED Requirements

### Requirement: User Listing
The system SHALL display a list of all users in a tabular format within the Admin Dashboard.

#### Scenario: View User List
- **WHEN** an admin navigates to the User Management section
- **THEN** the system displays a table containing all users, including columns for Student ID and Full Name.

### Requirement: User Creation
The system SHALL allow administrators to add new users (students or staff) to the database.

#### Scenario: Successful User Creation
- **WHEN** an admin clicks the "Add User" button, fills in a valid Student ID and Full Name, and submits
- **THEN** the system adds the user to the database and updates the user table to reflect the new entry.

### Requirement: User Editing
The system SHALL allow administrators to edit the details of existing users.

#### Scenario: Successful User Edit
- **WHEN** an admin selects a user, clicks "Edit", modifies the Full Name, and submits
- **THEN** the system updates the user's record in the database and reflects the changes in the table.

### Requirement: User Deletion (Soft Delete)
The system SHALL allow administrators to remove users from active operation while preserving their historical attendance records.

#### Scenario: Successful User Soft Deletion
- **WHEN** an admin selects a user and clicks "Delete"
- **THEN** the system prompts the admin with a warning that the user's face embeddings will be deleted but historical attendance will be preserved.
- **WHEN** the admin confirms the deletion
- **THEN** the system marks the user as inactive (`is_active = 0`), removes their face embeddings, preserves their attendance logs, and updates the user table to hide them.
