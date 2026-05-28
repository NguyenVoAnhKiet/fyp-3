## 1. Database and repository foundation

- [ ] 1.1 Update `face_references` schema to add `pose_label` and composite uniqueness on `(user_id, pose_label)`. (@fixer)
- [ ] 1.2 Add or update repository helpers for bulk replacement of a user's five pose references in one transaction. (@fixer)
- [ ] 1.3 Preserve optional embedding encryption/decryption for each stored pose row. (@fixer)

## 2. Enrollment data flow

- [ ] 2.1 Change enrollment output to collect and return a `pose_label -> embedding` mapping for the five required poses. (@fixer)
- [ ] 2.2 Update `EnrollmentService` to delete old pose rows and write the full five-pose set atomically. (@fixer)
- [ ] 2.3 Set `users.face_registered = 1` only after all five pose references are saved successfully. (@fixer)

## 3. Recognition and logging

- [ ] 3.1 Extend recognition result data to include `matched_pose_label`. (@fixer)
- [ ] 3.2 Update recognition matching to keep best-match behavior across all stored pose references. (@oracle)
- [ ] 3.3 Write `matched_pose=<label>` into recognition event `details` as raw text. (@fixer)

## 4. UI and pose guidance

- [ ] 4.1 Update enrollment guidance text to follow the outside-world pose order: `center`, `right`, `left`, `up`, `down`. (@designer)
- [ ] 4.2 Keep the enrollment UI Vietnamese-friendly while using fixed internal pose labels. (@designer)
- [ ] 4.3 Ensure re-enrollment continues to require all five poses and fails as a unit if any pose is missing. (@fixer)

## 5. Tests and verification

- [ ] 5.1 Update storage tests for the new `pose_label` schema and bulk replacement behavior. (@fixer)
- [ ] 5.2 Update enrollment tests to cover five-pose persistence and full replacement on re-enrollment. (@fixer)
- [ ] 5.3 Update recognition tests to cover best-match behavior across pose-specific references and matched pose logging. (@fixer)
