## Context

The current attendance system lacks full test coverage for core business logic components. Specifically, `recognition_event_repository.py`, `ai_pipeline.py`, and `time_utils.py` are untested. Adding these tests is critical for ensuring system reliability, especially for the face recognition and anti-spoofing logic.

## Goals / Non-Goals

**Goals:**
- Implement comprehensive unit tests for `RecognitionEventRepository`.
- Implement unit tests for `ai_pipeline.py` (`LivenessChecker` and `FaceRecognizer`) using mocking to avoid loading real models.
- Implement unit tests for `time_utils.py`.
- Achieve full test coverage for the specified modules.

**Non-Goals:**
- Do not write integration or end-to-end tests for the GUI components (PyQt5 `ui/` directory).
- Do not refactor `main.py` to make it unit-testable.
- Do not test real ONNX models or OpenCV actual implementations (use mocks instead).

## Decisions

- **Mocking external dependencies:** We will use `pytest.mark.parametrize` and `unittest.mock.patch` to mock ONNX Runtime sessions and OpenCV `FaceRecognizerSF` to ensure fast, isolated unit tests.
- **Test environment:** Use the existing `pytest` infrastructure and fixtures available in `tests/conftest.py`.

## Risks / Trade-offs

- **Risk**: Mocking `ai_pipeline.py` might mask real integration issues with the actual models.
  - *Mitigation*: The focus here is unit testing logic (thresholds, preprocessing arrays, distance metrics). Real integration testing is out of scope for these pure unit tests but can be done manually or in a separate integration suite.
