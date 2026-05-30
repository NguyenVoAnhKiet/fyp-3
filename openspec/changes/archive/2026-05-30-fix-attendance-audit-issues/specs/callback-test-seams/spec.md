## ADDED Requirements

### Requirement: Callback Unit Test Infrastructure
The system SHALL provide isolated unit test seams for the `_on_recognition_result()` callback flow, allowing tests to:
1. Mock `AttendanceService` to avoid database writes
2. Call `_on_recognition_result()` directly with controlled inputs
3. Assert that service methods are called with correct arguments

#### Scenario: Callback invokes record_success on successful recognition
- **WHEN** `_on_recognition_result("success", user_id=1, ...)` is called
- **THEN** `AttendanceService.record_success()` is invoked with the user_id and session_id

#### Scenario: Callback invokes record_duplicate on duplicate
- **WHEN** `_on_recognition_result("duplicate", user_id=2, ...)` is called
- **THEN** `AttendanceService.record_duplicate()` is invoked with the user_id and session_id

#### Scenario: Callback invokes record_spoof_warning on spoof
- **WHEN** `_on_recognition_result("spoof", user_id=None, ...)` is called
- **THEN** `AttendanceService.record_spoof_warning()` is invoked (no user_id)

#### Scenario: Callback catches service exceptions gracefully
- **WHEN** `AttendanceService.record_success()` raises an exception
- **THEN** the callback does not propagate the exception and logs it instead

#### Scenario: Test runs without Qt UI or camera
- **WHEN** the callback test is executed
- **THEN** no Qt window is created and no camera device is opened
