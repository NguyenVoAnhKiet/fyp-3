## 1. Time Utils Tests

- [x] 1.1 Create `tests/unit/test_time_utils.py`
- [x] 1.2 Implement tests for `utc_now_iso` covering string type, ISO 8601 format, and proximity to current time

## 2. Recognition Event Repository Tests

- [x] 2.1 Create `tests/unit/test_recognition_event_repository.py`
- [x] 2.2 Implement tests for `create()` covering all result types (success, spoof_warning, unrecognized, duplicate)
- [x] 2.3 Implement tests for `create()` validation logic (session_id, user_id, event_time, result)
- [x] 2.4 Implement tests for `create()` handling optional fields and None user_id
- [x] 2.5 Implement tests for `list_by_session()` including ordering, empty lists, and invalid session IDs

## 3. AI Pipeline Tests

- [x] 3.1 Create `tests/unit/test_ai_pipeline.py`
- [x] 3.2 Implement `LivenessChecker.check()` tests with mocked `model_path=None` and mocked threshold edge cases
- [x] 3.3 Implement `LivenessChecker._preprocess()` tests verifying output shapes and handling of various input dimensions (square, portrait, landscape, large, small)
- [x] 3.4 Implement `FaceRecognizer._cosine_similarity()` logic tests (identical, orthogonal, opposite, zero vectors)
- [x] 3.5 Implement `FaceRecognizer.average_embeddings()` edge cases and mean logic
- [x] 3.6 Implement `FaceRecognizer.identify()` tests covering empty DB, below threshold, match, best match, and orphan references using mocked OpenCV FaceRecognizerSF
