## Purpose

Control who can act within the system, using role-based permissions appropriate to a single-tenant internal finance tool.

## ADDED Requirements

### Requirement: Simple internal username/password authentication
The system SHALL authenticate internal staff users with a username/password credential, storing passwords only as salted hashes (bcrypt or argon2). Single sign-on (SSO) and multi-factor authentication (MFA) are explicitly out of scope for v1.

**Decision:** Simple internal username/password auth (hashed with bcrypt/argon2) was chosen over SSO/MFA (Section 14, Q6) as sufficient for v1 given the single-tenant, internal-staff-only user base and modest scale; SSO/MFA can be layered on in a later version if the organization's security requirements grow.

#### Scenario: Successful login
- **WHEN** a user submits a correct username and password
- **THEN** the system authenticates the user and issues a session/token
- **AND** the stored credential is never the plaintext password, only a bcrypt/argon2 hash

#### Scenario: Failed login
- **WHEN** a user submits an incorrect password
- **THEN** the system rejects the login attempt without revealing whether the username exists

#### Scenario: No SSO or MFA prompt in v1
- **WHEN** a user attempts to log in
- **THEN** the system presents only the username/password form; no SSO redirect or MFA challenge is offered

### Requirement: Role-based access control
The system SHALL support three roles — Admin, Finance Staff, and Viewer — and SHALL restrict state-changing actions (customer/invoice/payment create-edit-cancel, reminder override, kill-switch) to Admin and Finance Staff, while Viewer is read-only.

#### Scenario: Viewer cannot record a payment
- **WHEN** a user with the Viewer role attempts to record a payment
- **THEN** the system rejects the action with an authorization error

#### Scenario: Admin can use the reminder kill-switch
- **WHEN** a user with the Admin role toggles the emergency reminder kill-switch
- **THEN** the system applies the change and records it in the audit log

#### Scenario: Finance Staff can manage invoices and payments
- **WHEN** a user with the Finance Staff role creates, issues, or edits an invoice, or records a payment
- **THEN** the system permits the action, subject to all other business rules
