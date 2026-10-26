# Setup

## Current status: blocked and unverified

The repository cannot yet be set up reproducibly from a fresh clone. Do not present the commands below as a verified installation until the blockers are resolved and this document is updated.

Confirmed blockers:

- `requirements.txt` is empty.
- `app/core/config.py` is empty.
- The MediaPipe model path is hardcoded to a Windows path in `app/services/liveness.py`.
- `initialize_database()` is not called during startup.
- No model files, registered embeddings, fixtures, or test database are tracked.

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for evidence and proposed fixes.

## Python compatibility

The supported Python version is **not verified**. The code does not use especially new syntax, but the native AI dependencies are sensitive to Python and platform versions. Choose a Python version supported by all selected dependencies and record the tested version here once verified.

Do not claim Python compatibility based on syntax checks alone.

## Dependencies

`requirements.txt` is intentionally not populated as part of the documentation foundation. The imports in the current code imply these runtime packages:

- `fastapi`
- `uvicorn`
- `python-multipart`
- `opencv-python` (imported as `cv2`)
- `numpy`
- `mediapipe`
- `insightface`
- `onnxruntime`
- `requests` for the manual API client

This list is inferred from imports, not from a verified manifest. Versions, exact package variants, and platform-specific constraints are not declared.

## Model and data assets

| Asset | Expected by code | Current status |
| --- | --- | --- |
| MediaPipe Face Landmarker model | `face_landmarker.task`; currently hardcoded at `C:\AI-Attendance-System\ai-service\models\mediapipe\face_landmarker.task` | Not present; non-Windows startup is blocked. |
| InsightFace `buffalo_l` | `FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])` | Provisioning/caching is external to this repository and unverified. |
| Registered embedding | `data/face_embeddings/<student_id>.npy` | Not present; must be generated with a registration workflow. |
| Attendance database | `data/attendance.db` | Directory/database created on first connection; table is not created because initialization is not called. |
| Test fixtures | `tests/fixtures/test.jpg`, `closed_eye.jpeg` | Referenced by scripts but ignored by Git and absent. |

Do not commit real face images, embeddings, or databases.

## Intended setup workflow (not verified)

The following is the intended workflow after the Phase 1 runtime fixes. It is **not** currently guaranteed to work.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # currently installs nothing
# Place the MediaPipe model where the configured path expects it.
# Provide or register a face embedding for the test student.
uvicorn app.main:app --reload
```

The README and this document must be updated with the exact tested Python version, package versions, model paths, and commands once the workflow succeeds.

## Startup behavior

Importing `app.main` imports both routers. Both routers construct services at import time:

- `app/api/routes.py` creates `AttendanceVerificationService`, which creates `LivenessService` and `FaceRecognitionService`.
- `app/api/liveness_routes.py` creates another `LivenessService`.

Therefore, the application requires the MediaPipe and InsightFace models **before** it can import. A missing model raises during import, not on the first request.

Recommended verification once assets exist:

```bash
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/` — service message
- `http://127.0.0.1:8000/docs` — OpenAPI UI

Do not report startup as successful until these requests have been executed and recorded.

## Database initialization

A fresh checkout has no `data/attendance.db` and no `attendance` table. The helper `initialize_database()` is not invoked by the app, the routes, or any test. Until Phase 1 fixes this, attendance inserts and queries can fail with `no such table: attendance`.

## Manual client

`test_api_attendance.py` is a manual client, not an automated test. It requires:

- the API running at `http://127.0.0.1:8000`;
- a webcam;
- `requests` and OpenCV;
- a registered embedding for `STU001`;
- a liveness flow completed by a person.

It uses hardcoded values for `STUDENT_ID`, `SUBJECT`, and `LECTURE_ID`; review before running.

## Troubleshooting

| Symptom | Likely cause | Next step |
| --- | --- | --- |
| `pip install -r requirements.txt` installs no application packages | Manifest is empty | Wait for Phase 1 dependency work; do not guess versions as verified. |
| Import error mentioning `face_landmarker.task` or a `C:\...` path | Hardcoded Windows model path | Documented blocker; requires a code/config fix. |
| InsightFace model load/download error | `buffalo_l` assets unavailable or cache incomplete | Provision the model through InsightFace's supported mechanism; verify before documenting. |
| `Registered face not found for student: ...` | Missing `data/face_embeddings/<student_id>.npy` | Generate a consented test embedding; do not use real student data. |
| `no such table: attendance` | Database schema not initialized | Confirmed blocker; requires startup initialization. |
| Camera cannot be opened | No camera, permission denied, or device in use | Check OS camera permissions and device access. |
| Port already in use | Another server on port 8000 | Stop it or run Uvicorn on another port. |

## What to verify before marking setup complete

1. Fresh clone + documented commands install dependencies successfully.
2. The application starts without Windows-specific paths.
3. A fresh database gets its schema automatically.
4. `/` and `/docs` respond.
5. A consented test face can complete liveness and attendance verification.
6. Duplicate attendance is rejected as documented.
7. README, SETUP, and CONFIGURATION reflect the verified values.
