## Why

The current test coverage for the attendance system is incomplete, with 3 out of 20 testable modules missing tests. Adding tests for `recognition_event_repository.py`, `ai_pipeline.py`, and `time_utils.py` ensures full coverage of business logic and system reliability.

## What Changes

- Add unit tests for `RecognitionEventRepository` covering all result types, validations, and listing by session.
- Add unit tests for `LivenessChecker` covering model checks, threshold logic, and image preprocessing with mocked ONNX Runtime.
- Add unit tests for `FaceRecognizer` covering cosine similarity edge cases, embeddings averaging, and identification logic with mocked OpenCV `FaceRecognizerSF`.
- Add unit tests for `time_utils.py` to verify UTC timestamp generation and formatting.

## Capabilities

### New Capabilities
- `unit-tests-coverage`: Comprehensive unit tests for database repositories, AI pipeline, and utility modules.

### Modified Capabilities

## Impact

- `tests/unit/test_recognition_event_repository.py` (New file)
- `tests/unit/test_ai_pipeline.py` (New file)
- `tests/unit/test_time_utils.py` (New file)
- Ensures test suites run completely without errors or failures, boosting overall project health.
