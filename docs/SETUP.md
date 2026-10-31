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
| Database startup | A temporary database was created with the `attendance`, `users`, and `auth_tokens` tables; restart preserved rows; duplicate insert was rejected |
| Authentication | Local accounts, login/logout, token expiry/revocation, student self-access, and admin read-only access verified with temporary storage and fake model services |
| Missing model | Startup failed with a `RuntimeError` naming `MEDIAPIPE_FACE_LANDMARKER_MODEL` |
| Model services | MediaPipe and InsightFace each initialized once during startup |

This does **not** mean the whole application is verified. Tests/CI, TLS, rate
limiting, and the end-to-end camera flow remain open. See the
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

`argon2-cffi` provides Argon2id password hashing for local accounts. It is a
runtime dependency and is installed from `requirements.txt`.

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
| Attendance database | Created on first connection; attendance, user, and token schemas are initialized at startup. | `data/attendance.db` |

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

Startup initializes the attendance and authentication schemas, then loads the
models once. If schema initialization fails, startup aborts. If the MediaPipe
model is missing, the process exits with an error naming
`MEDIAPIPE_FACE_LANDMARKER_MODEL`; `/` and `/docs` will not be available.

## Create local accounts

There is no public signup. Provision accounts before using protected endpoints:

```bash
# Student linked to the embedding student ID.
python -m app.auth.cli create-user student1 \
  --role student --student-id STU001

# Read-only attendance reviewer.
python -m app.auth.cli create-user admin1 --role admin

# Rotate a password and revoke existing tokens.
python -m app.auth.cli set-password student1

# Disable an account and revoke existing tokens.
python -m app.auth.cli deactivate-user student1
```

The CLI prompts for passwords. Use `--database-path` to target a database other
than the configured `ATTENDANCE_DB_PATH`. Do not pass passwords as command-line
arguments.

Obtain a token:

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=student1" \
  --data-urlencode "password=<password>"
```

Send `Authorization: Bearer <access_token>` on protected requests. Tokens expire
after `AUTH_TOKEN_TTL_SECONDS` (default 3600) and are revoked by
`POST /auth/logout`.

## Configuration

All supported environment variables, defaults, path resolution, and startup
behavior are documented in [CONFIGURATION.md](CONFIGURATION.md).

## Database initialization

The FastAPI lifespan calls `initialize_database()` and
`initialize_auth_database()` for the configured `ATTENDANCE_DB_PATH` before
constructing model services. They create the parent directory and the
`attendance`, `users`, and `auth_tokens` tables if they do not exist, commit the
schema, and set `app.state.database_initialized` and
`app.state.auth_initialized`. Initialization is idempotent, so restarting
against an existing database preserves rows.

To verify against a throwaway database:

```bash
ATTENDANCE_DB_PATH=/tmp/attendance-test.db \
  python -m uvicorn app.main:app

# In another terminal:
sqlite3 /tmp/attendance-test.db '.schema'
```

Delete the temporary database when finished. Do not point tests at a real
attendance database.

## Manual client

`test_api_attendance.py` is a manual client, not an automated test. It requires:

- the API running at `http://127.0.0.1:8000`;
- a webcam;
- `requests` and OpenCV;
- a registered embedding for `STU001`;
- a provisioned student account;
- a liveness flow completed by a person.

The client prompts for the account password, obtains a bearer token from
`POST /auth/token`, and sends it on protected requests. It reads
`ATTENDANCE_API_URL` and `ATTENDANCE_USERNAME` from the environment (defaults:
`http://127.0.0.1:8000` and `student1`). It still uses hardcoded values for
`STUDENT_ID`, `SUBJECT`, and `LECTURE_ID`; review before running.
Parameterizing the remaining values is tracked in
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
- A complete liveness + face-match + attendance flow with a camera and a bearer token.
- Recognition accuracy, liveness accuracy, and presentation-attack resistance.
- TLS, rate limiting, account lockout, MFA/SSO, and audit logging.
- Full API/database coverage and CI beyond the focused runtime tests.
