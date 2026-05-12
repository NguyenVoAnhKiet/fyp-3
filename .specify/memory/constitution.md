<!--
Sync Impact Report
- Version change: 0.0.0-template -> 1.0.0
- Modified principles:
	- N/A -> I. Attendance Integrity First
	- N/A -> II. Privacy by Design and Data Minimization
	- N/A -> III. Offline-First Reliability
	- N/A -> IV. Deterministic AI Pipeline and Threshold Governance
	- N/A -> V. Measurable Quality Gates
- Added sections:
	- Technical and Operational Constraints
	- Delivery Workflow and Quality Gates
- Removed sections:
	- None
- Templates requiring updates:
	- ✅ updated: .specify/templates/plan-template.md
	- ✅ updated: .specify/templates/spec-template.md
	- ✅ updated: .specify/templates/tasks-template.md
	- ⚠ pending: .specify/templates/commands/*.md (directory not present in repository)
- Follow-up TODOs:
	- TODO(RATIFICATION_DATE): Confirm original ratification date from project supervisor or team records.
-->

# Face Attendance and Anti-Spoofing System Constitution

## Core Principles

### I. Attendance Integrity First
All features MUST protect the integrity of attendance outcomes before optimizing convenience.
The system MUST prevent duplicate attendance within a session, MUST block spoof attempts where
liveness is below configured threshold, and MUST persist auditable attendance status values.
Rationale: The project exists to reduce fraud and administrative error in classroom attendance.

### II. Privacy by Design and Data Minimization
The system MUST store face embeddings only and MUST NOT retain raw face images after registration
is completed. Administrative credentials MUST be stored as one-way hashes. Data access paths MUST
be limited to role-appropriate capabilities (admin-only management and configuration operations).
Rationale: Biometric data handling is high risk and requires strict minimization and access control.

### III. Offline-First Reliability
Core attendance operations MUST function without internet connectivity. Local persistence,
attendance session lifecycle, recognition pipeline execution, and report export MUST remain
available in offline mode. Any optional online integrations MUST fail safely without disrupting
attendance capture.
Rationale: Classroom operation cannot depend on stable internet and must remain resilient.

### IV. Deterministic AI Pipeline and Threshold Governance
Recognition flow MUST execute in the ordered pipeline detect -> liveness -> recognize. Threshold
values for liveness and similarity MUST be explicitly configurable, versioned in system settings,
and referenced in test scenarios. Changes to threshold defaults MUST include rationale and
regression evidence for false acceptance and false rejection impacts.
Rationale: Predictable pipeline behavior is necessary for reproducibility and trustworthy outcomes.

### V. Measurable Quality Gates
Every release candidate MUST satisfy measurable non-functional targets: pipeline processing within
2 seconds per person under stated test conditions, responsive UI operation, and documented quality
evidence for FAR and FRR targets. Security, privacy, and attendance integrity tests MUST be present
for any feature that changes data flow or AI decision logic.
Rationale: Objective acceptance criteria prevent quality drift and hidden regressions.

## Technical and Operational Constraints

- Primary runtime stack MUST remain Python desktop architecture with local SQLite persistence unless
	an amendment explicitly authorizes a platform change.
- Attendance record timestamps and session timestamps MUST use ISO 8601 format.
- Exported reports MUST include at minimum identity, class/subject context, timestamp, and
	attendance status fields.
- Camera processing MUST be designed to keep UI responsiveness stable through asynchronous or
	multi-threaded execution.

## Delivery Workflow and Quality Gates

- Plans MUST include a Constitution Check section that explicitly maps design choices to all five
	principles.
- Specifications MUST define privacy constraints, offline behavior, spoof-handling outcomes, and
	measurable success criteria.
- Tasks MUST include validation work for privacy controls, offline operation, and anti-spoofing
	behavior when related functionality is modified.
- Pull requests MUST include evidence of testing for affected quality gates and MUST document
	threshold/configuration changes.

## Governance

This Constitution overrides conflicting local conventions for architecture, requirements, and
delivery quality decisions. Amendments require: (1) written proposal, (2) impact analysis for
templates and active specifications, (3) approval by project maintainers, and (4) migration notes
for in-flight work. Semantic versioning policy applies to this document: MAJOR for incompatible
principle removals or redefinitions, MINOR for new principles/sections or materially expanded
obligations, PATCH for wording clarifications and non-semantic edits. Compliance review is required
at planning, specification, task generation, and pull request review checkpoints.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): Original adoption date not found in repository records. | **Last Amended**: 2026-04-24
