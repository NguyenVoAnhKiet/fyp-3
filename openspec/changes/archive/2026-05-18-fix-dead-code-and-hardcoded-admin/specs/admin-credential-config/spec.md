## ADDED Requirements

### Requirement: Admin credentials loaded from environment variables

The system SHALL read `ADMIN_USERNAME` and `ADMIN_PASSWORD` from environment variables when seeding the initial admin account. If either variable is unset or empty, the system SHALL fall back to the default values `"admin"` for username and `"admin"` for password.

#### Scenario: Both env vars are set
- **WHEN** `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set in the environment
- **THEN** the seeded admin account uses those values

#### Scenario: Env vars are unset
- **WHEN** neither `ADMIN_USERNAME` nor `ADMIN_PASSWORD` is set
- **THEN** the seeded admin account uses defaults `"admin"` / `"admin"`

#### Scenario: Only one env var is set
- **WHEN** `ADMIN_USERNAME` is set but `ADMIN_PASSWORD` is not
- **THEN** the seeded admin uses the custom username and default password `"admin"`

### Requirement: Admin seeding occurs only once

The system SHALL seed the admin account only when the `admin_credentials` table is empty. Subsequent application starts SHALL NOT overwrite or modify existing admin credentials.

#### Scenario: First run with empty table
- **WHEN** `initialize()` is called and `admin_credentials` has zero rows
- **THEN** a new admin record is inserted

#### Scenario: Subsequent run with existing admin
- **WHEN** `initialize()` is called and `admin_credentials` has one or more rows
- **THEN** no admin record is inserted and no error occurs

## REMOVED Requirements

### Requirement: Hardcoded admin credentials

**Reason**: Hardcoded credentials (`admin`/`admin`) in `storage_manager.py` bypass the `.env.example` configuration and represent a security risk even for a desktop application.

**Migration**: Credentials are now read from `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables with the same defaults as fallback. Existing installations with the default admin are unaffected.
