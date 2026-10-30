# Setup

## Current status

Runtime bootstrap is implemented and was verified on one documented platform:

| Item | Verified value |
| --- | --- |
| Platform | macOS 27.0.1, arm64 |
| Python | 3.11.16 |
| Dependency install | Clean virtual environment + `python -m pip install -r requirements.txt` |
| Startup | `python -m uvicorn app.main:app` reached "Application startup complete" |
| Endpoints | `GET /` returned `200`; `GET /docs` returned `200` |
| Database startup | A temporary database was created with the `attendance` table; restart preserved rows; duplicate insert was rejected |
| Missing model | Startup failed with a `RuntimeError` naming `MEDIAPIPE_FACE_LANDMARKER_MODEL` |
| Model services | MediaPipe and InsightFace each initialized once during startup |

This does **not** mean the whole application is verified. Authentication, input
validation, tests/CI, and the end-to-end camera flow remain open. See the
[tracking backlog](https://github.com/Kartik-gharte/Attendance.Application/issues/13).

## Supported Python version

**Python 3.11** is the documented and tested version. The current dependency
set was installed and started successfully with Python 3.11.16 on macOS arm64.
Other Python versions and platforms have not been verified.

Native AI dependencies are sensitive to Python and platform versions. Do not
claim support for another combination without running the commands below.

## Dependencies

Runtime dependencies are pinned in [`requirements.txt`](../requirements.txt).
Development dependencies are in [`requirements-dev.txt`](../requirements-dev.txt).

`mediapipe` and `insightface` both declare OpenCV packages. Both
`opencv-python` and `opencv-contrib-python` are pinned to the same version so
the shared `cv2` namespace stays consistent.

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# For pytest-based runtime checks:
python -m pip install -r requirements-dev.txt
```

Create local configuration only if you need to override defaults:

```bash
cp .env.example .env
```

`.env` is ignored by Git. Never put real credentials or student data in it.

## Model and data assets

These assets are required at runtime but are deliberately excluded from Git.

| Asset | How to provision it | Default location |
| --- | --- | --- |
| MediaPipe Face Landmarker | Download `face_landmarker.task` from the MediaPipe model storage URL below. | `models/mediapipe/face_landmarker.task` |
| InsightFace `buffalo_l` | InsightFace downloads it on first startup, or pre-provision it in the InsightFace cache. | `~/.insightface/models/buffalo_l` |
| Registered embedding | Generate with the registration workflow using synthetic or consented data. Never commit it. | `data/face_embeddings/<student_id>.npy` |
| Attendance database | Created on first connection; the schema startup hook is still tracked in [#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3). | `data/attendance.db` |

MediaPipe model download:

```bash
mkdir -p models/mediapipe
curl -fL -o models/mediapipe/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

InsightFace downloads `buffalo_l` into the configured `INSIGHTFACE_ROOT`
(default `~/.insightface`) when it is first used. The download requires network
access and is roughly 275 MB. Review model licensing and redistribution terms
before shipping any model asset; do not commit model files.

Set `MEDIAPIPE_FACE_LANDMARKER_MODEL`, `INSIGHTFACE_ROOT`, and
`FACE_EMBEDDING_DIR` in `.env` if you keep assets elsewhere.

## Start the API

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/` — service message
- `http://127.0.0.1:8000/docs` — OpenAPI UI

Startup initializes the database schema, then loads the models once. If schema
initialization fails, startup aborts. If the MediaPipe model is missing, the
process exits with an error naming `MEDIAPIPE_FACE_LANDMARKER_MODEL`; `/` and
`/docs` will not be available.

## Configuration

All supported environment variables, defaults, path resolution, and startup
behavior are documented in [CONFIGURATION.md](CONFIGURATION.md).

## Database initialization

The FastAPI lifespan calls `initialize_database()` for the configured
`ATTENDANCE_DB_PATH` before constructing model services. It creates the parent
directory and the `attendance` table if they do not exist, commits the schema,
and sets `app.state.database_initialized = True`. Initialization is idempotent,
so restarting against an existing database preserves rows.

To verify against a throwaway database:

```bash
ATTENDANCE_DB_PATH=/tmp/attendance-test.db \
  python -m uvicorn app.main:app

# In another terminal:
sqlite3 /tmp/attendance-test.db '.schema attendance'
```

Delete the temporary database when finished. Do not point tests at a real
attendance database.

## Manual client

`test_api_attendance.py` is a manual client, not an automated test. It requires:

- the API running at `http://127.0.0.1:8000`;
- a webcam;
- `requests` and OpenCV;
- a registered embedding for `STU001`;
- a liveness flow completed by a person.

It uses hardcoded values for `STUDENT_ID`, `SUBJECT`, and `LECTURE_ID`; review
before running. Parameterizing these scripts is tracked in
[#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10).

## Verification commands

```bash
# Syntax check
python -m compileall -q app tests

# Focused runtime tests (no models or camera required)
python -m pytest tests/runtime -q

# Full startup check (requires model assets)
python -m uvicorn app.main:app
```

See [TESTING.md](TESTING.md) for what is and is not covered.

## Troubleshooting

| Symptom | Likely cause | Next step |
| --- | --- | --- |
| `ModuleNotFoundError` during startup | Dependencies not installed in the active environment | Activate `.venv` and install `requirements.txt`. |
| Startup fails with `MediaPipe Face Landmarker model not found` | Model path is missing or wrong | Download the model and set `MEDIAPIPE_FACE_LANDMARKER_MODEL`. |
| Startup fails while initializing InsightFace | `buffalo_l` is unavailable, the cache is not writable, or the download failed | Check `INSIGHTFACE_ROOT`, network access, and model licensing. |
| `Registered face not found for student: ...` | Missing `FACE_EMBEDDING_DIR/<student_id>.npy` | Generate a consented test embedding; do not use real student data. |
| `no such table: attendance` | Startup initialization did not run or used a different database path | Check `ATTENDANCE_DB_PATH` and startup logs for schema initialization. |
| Camera cannot be opened | No camera, permission denied, or device in use | Check OS camera permissions and device access. |
| Port already in use | Another server on port 8000 | Stop it or run Uvicorn on another port. |

## What is still unverified

- Startup on Windows or Linux, or with any Python version other than 3.11.16.
- A complete liveness + face-match + attendance flow with a camera.
- Recognition accuracy, liveness accuracy, and presentation-attack resistance.
- Full API/database coverage beyond the focused runtime tests and CI.
