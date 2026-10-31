# Testing

## Current status

Focused runtime tests exist under `tests/runtime/`. They cover settings validation, path resolution, the missing-model error, lifespan service wiring with a fake service factory, database initialization, configured database paths, attendance retrieval, duplicate handling, identifier validation, upload limits, controlled error responses, local account provisioning, Argon2id password verification, bearer-token expiry/revocation, login/logout, role checks, cross-student denial, and liveness-session ownership using temporary databases and fake model services. They do not load real models or open a camera.

The older files named `test_*.py` are still manual scripts that execute top-level code when imported or run. Do not run plain `pytest` against the whole `tests/` directory: collection imports those modules, which can load models, open a camera, exit the process, or require missing fixtures.

Runtime verification of the real liveness and face-recognition camera flow was **not performed**. SQLite schema initialization, retrieval, duplicate handling, input validation, upload limits, controlled error responses, authentication, token lifecycle, and authorization were verified through focused runtime tests without loading real models.

## What was verified

On macOS 27.0.1 arm64 with Python 3.11.16:

| Check | Result | Scope |
| --- | --- | --- |
| `python -m compileall -q app tests` | Passed | Syntax/bytecode compilation only. |
| `python -m pytest tests/runtime -q` | Passed (45 tests) | Settings, lifespan wiring, `/`, `/docs`, missing-model failure, database initialization, retrieval, duplicate handling, validation, upload limits, controlled errors, authentication, token lifecycle, and authorization. |
| Attendance API with temporary database and fake model services | Passed | Fresh retrieval returns an empty list; repeated insert maps to duplicate response; unauthenticated requests return `401`; cross-student and wrong-role requests return `403`. |
| Authentication API with temporary database | Passed | Login, `/auth/me`, logout revocation, expired-token rejection, student self-access, admin read-only access, and session ownership checks. |
| `python -m uvicorn app.main:app` | Startup complete | Real MediaPipe and InsightFace models loaded once each. |
| `GET /` and `GET /docs` | `200` | Served after lifespan startup. |
| Missing `MEDIAPIPE_FACE_LANDMARKER_MODEL` | Startup failed with `RuntimeError` | Names the setting that must be fixed. |

The compile and test checks do not establish that the same Python version works on another platform, nor do they cover the camera-based flows.

## Manual scripts (opt‑in)

The following scripts are **not** collected by `pytest` (they are outside `tests/runtime/`). They can be run manually from the repository root (e.g. `python -m manual.script` or `PYTHONPATH=. python script.py`). They require model assets and a webcam; they are not part of the automated test suite.

| Script | What it does | Requirements | Current state |
| --- | --- | --- | --- |
| `manual/api_attendance.py` | Authenticates, starts a liveness session, opens a webcam, sends frames, waits for a blink, then submits the final frame to `/attendance/verify`. | Running API, provisioned student account, webcam, `requests`, OpenCV, registered embedding for `STU001`. | Manual, no assertions; prompts for a password; hardcoded student/subject/lecture; reads `ATTENDANCE_API_URL` and `ATTENDANCE_USERNAME`. |
| `manual/liveness_service.py` | Older liveness camera script. | Webcam, MediaPipe model. | Broken import: `from app.services.liveness import LivenessService`; not runnable as‑is without `PYTHONPATH=.`. |
| `manual/attendance_verification.py` | Full camera liveness + face‑recognition flow. | Webcam, MediaPipe + InsightFace models, embedding for `STU001`. | Manual; no assertions. |
| `manual/embedding.py` | Extracts an InsightFace embedding from a fixture image. | `manual/fixtures/test.jpg` (or provide `INSIGHTFACE_ROOT`), InsightFace model. | Fixture absent; manual. |
| `manual/face_detector.py` | Legacy MediaPipe face‑detector check. | `manual/fixtures/test.jpg`, `models/mediapipe/blaze_face_short_range.tflite`. | Fixture/model absent; uses a different model than the app. |
| `manual/landmarks.py` | MediaPipe landmark and EAR check on a closed‑eye image. | `manual/fixtures/closed_eye.jpeg`, `models/mediapipe/face_landmarker.task`. | Fixtures/model absent; manual. |
| `manual/recognition.py` | Compares a fixture image with `data/face_embeddings/STU001.npy`. | Fixture image, InsightFace model, registered embedding. | Assets absent; manual. |
| `manual/liveness_anti_spoofing.py` | Camera liveness test with anti‑spoofing status display. | Webcam, MediaPipe model. | Manual; no assertions. |
| `manual/combined_demo.py` | Standalone camera demo combining liveness and recognition. | Webcam, models, Windows‑specific paths. | Not part of the API; manual. |

To run any of these scripts from the repository root:

```bash
PYTHONPATH=. python -m manual.script_name
```

or

```bash
python manual/script_name.py   # (runs from the repo root directory)
```

The `pytest.ini` file configures `pytest` to only collect tests under `tests/runtime/`, so these manual scripts are never executed by `pytest`.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pull requests and pushes to `main`:

- **Compile and test**: installs pinned dependencies, runs `python -m compileall -q app tests`, and runs `python -m pytest tests/runtime -q`.
- **Secret scan**: runs `gitleaks/gitleaks-action` with full Git history.

CI does not download model assets, open a camera, or run the manual scripts. A passing run proves only the checks listed above.

Branch protection is **not configured** because the current collaborator account does not have repository admin permission. The repository owner must apply these settings:

1. Open **Settings → Branches → Add branch protection rule**.
2. Set the branch name pattern to `main`.
3. Enable **Require a pull request before merging**.
4. Enable **Require status checks to pass before merging** and select `Compile and test` and `Secret scan`.
5. Enable **Require branches to be up to date before merging**.
6. Disable force pushes and branch deletion.
7. Save the rule.

Until that rule exists, CI results are advisory rather than enforced by GitHub.
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
python -m compileall -q app tests
python -m pytest tests/runtime -q
git diff --check
```

They verify syntax, focused runtime behavior, and diff hygiene. They do not prove the camera-based flows.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pull requests and pushes to `main`:

- **Compile and test**: installs pinned dependencies, runs `python -m compileall -q app tests`, and runs `python -m pytest tests/runtime -q`.
- **Secret scan**: runs `gitleaks/gitleaks-action` with full Git history.

CI does not download model assets, open a camera, or run the manual scripts. A passing run proves only the checks listed above. Both jobs passed on PR #22: `Compile and test` in 56 seconds and `Secret scan` in 7 seconds.

Branch protection is **not configured** because the current collaborator account does not have repository admin permission. The repository owner must apply these settings:

1. Open **Settings → Branches → Add branch protection rule**.
2. Set the branch name pattern to `main`.
3. Enable **Require a pull request before merging**.
4. Enable **Require status checks to pass before merging** and select `Compile and test` and `Secret scan`.
5. Enable **Require branches to be up to date before merging**.
6. Disable force pushes and branch deletion.
7. Save the rule.

Until that rule exists, CI results are advisory rather than enforced by GitHub.

## Future automated test plan

Proposed for Phase 2 of the [roadmap](ROADMAP.md):

1. Unit tests for `compare_faces`, EAR calculation, and anti-spoofing heuristics using synthetic arrays.
2. Broaden database tests to additional insert, duplicate, and query cases.
3. Expand API tests with mocked model services to cover liveness rejection and the full session state machine.
4. Liveness state-machine tests using synthetic frames or mocked detectors.
5. Face-matching tests with synthetic or explicitly consented fixtures; never real student data.
6. CI workflow that runs tests without a camera or model downloads.

Temporary-database and fake-model-service API/database/auth coverage now exists, including validation and upload rejection cases, but broad coverage and CI are still outstanding ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).

## Hardware and test-data requirements

- Webcam for the manual end-to-end flow.
- MediaPipe Face Landmarker model.
- InsightFace `buffalo_l` assets.
- Registered embeddings for the test student.
- Synthetic or explicitly consented test images.
- Do not commit real biometric data, even as test fixtures.
