# Testing

## Current status

There is **no automated pytest suite**. The files named `test_*.py` are manual scripts that execute top-level code when imported or run. They are not safe to collect with pytest: collection imports the modules, which can load models, open a camera, exit the process, or require missing fixtures.

Runtime verification of the liveness, face-recognition, API, and database flows was **not performed** during the documentation foundation task.

## What was verified in this task

| Check | Result | Scope |
| --- | --- | --- |
| `python -m compileall -q app tests test_api_attendance.py test_liveness_service.py` | Passed | Syntax/bytecode compilation only. It does not import models or verify runtime behavior. |
| `git diff --check` | Passed | Whitespace/conflict-marker check, including untracked files marked intent-to-add. |

The compile check ran with the Python interpreter available in the development environment. It does not establish that the same Python version works with FastAPI, MediaPipe, InsightFace, or the native model assets.

## Manual scripts

| Script | What it does | Requirements | Current state |
| --- | --- | --- | --- |
| `test_api_attendance.py` | Starts a liveness session, opens a webcam, sends frames, waits for a blink, then submits the final frame to `/attendance/verify`. | Running API, webcam, `requests`, OpenCV, registered embedding for `STU001`. | Manual, no assertions; hardcoded student/subject/lecture. |
| `test_liveness_service.py` | Older liveness camera script. | Webcam, MediaPipe model. | Broken import: `from liveness import LivenessService`; not runnable as-is. |
| `tests/services/test_liveness_service.py` | Camera liveness test with anti-spoofing status display. | Webcam, MediaPipe model. | Manual; no assertions. |
| `tests/services/test_attendance_verification.py` | Full camera liveness + face-recognition flow. | Webcam, MediaPipe + InsightFace models, embedding for `STU001`. | Manual; no assertions. |
| `tests/services/test_embedding.py` | Extracts an InsightFace embedding from a fixture image. | `tests/fixtures/test.jpg`, InsightFace model. | Fixture absent; manual. |
| `tests/services/test_face.py` | Legacy MediaPipe face-detector check. | `tests/fixtures/test.jpg`, `models/mediapipe/blaze_face_short_range.tflite`. | Fixture/model absent; uses a different model than the app. |
| `tests/services/test_landmarks.py` | MediaPipe landmark and EAR check on a closed-eye image. | `tests/fixtures/closed_eye.jpeg`, `models/mediapipe/face_landmarker.task`. | Fixtures/model absent; manual. |
| `tests/services/test_recognition.py` | Compares a fixture image with `data/face_embeddings/STU001.npy`. | Fixture image, InsightFace model, registered embedding. | Assets absent; manual. |
| `app/services/combined_test.py` | Standalone camera demo combining liveness and recognition. | Webcam, models, Windows-specific paths. | Not part of the API; manual. |
| `app/services/register_face.py` | Creates an embedding from `test.jpg` and saves it under `../../data/face_embeddings/`. | InsightFace model, `test.jpg`, writable path. | Hardcoded student ID and paths. |
| `app/services/recognize_face.py` | Compares `test.jpg` with a registered embedding. | InsightFace model, `test.jpg`, embedding. | Hardcoded paths. |

## Why the scripts are not automated tests

- They contain top-level executable code instead of test functions.
- They call `exit()` and open cameras during import.
- They require large model assets and hardware that are not part of the repository.
- They assert nothing; they print results for a human to inspect.
- Several reference ignored/absent fixtures.

Do not modify a test merely to make it pass. Convert or replace these scripts only as part of a planned testing task.

## Verification commands that are safe today

These do not require model assets or a camera:

```bash
python -m compileall -q app tests test_api_attendance.py test_liveness_service.py
git diff --check
```

They verify only syntax and diff hygiene. They do not prove application behavior.

## Future automated test plan

Proposed for Phase 2 of the [roadmap](ROADMAP.md):

1. Unit tests for `compare_faces`, EAR calculation, and anti-spoofing heuristics using synthetic arrays.
2. Database tests against a temporary SQLite path, covering insert, duplicate protection, and queries.
3. API tests with mocked model services, covering session validation, rejection, duplicate, and retrieval.
4. Liveness state-machine tests using synthetic frames or mocked detectors.
5. Face-matching tests with synthetic or explicitly consented fixtures; never real student data.
6. CI workflow that runs tests without a camera or model downloads.

Test isolation requires a configurable database path and dependency injection; neither exists yet.

## Hardware and test-data requirements

- Webcam for the manual end-to-end flow.
- MediaPipe Face Landmarker model.
- InsightFace `buffalo_l` assets.
- Registered embeddings for the test student.
- Synthetic or explicitly consented test images.
- Do not commit real biometric data, even as test fixtures.
