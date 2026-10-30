# Configuration

## Current state

Configuration is implemented in `app/core/config.py` as a validated
`pydantic-settings` object. Settings are read from environment variables and
from an optional `.env` file at the repository root. The `.env` file is ignored
by Git; [`.env.example`](../.env.example) contains placeholders only.

Settings are loaded when `app.main` is imported. Model services are created
later, once per process, in the FastAPI lifespan.

Relative paths are resolved against the repository root, not the current
working directory. `~` is expanded and paths are normalized with
`Path.resolve()`.

## Environment variables

| Variable | Default | Purpose | Validation |
| --- | --- | --- | --- |
| `MEDIAPIPE_FACE_LANDMARKER_MODEL` | `models/mediapipe/face_landmarker.task` | MediaPipe Face Landmarker `.task` file. | Must exist when the service starts. |
| `FACE_EMBEDDING_DIR` | `data/face_embeddings` | Directory containing `<student_id>.npy` embeddings. | Path. |
| `ATTENDANCE_DB_PATH` | `data/attendance.db` | SQLite database file. | Path; schema is initialized at startup. |
| `CORS_ALLOWED_ORIGINS` | Local ports `5500` and `5173` on `127.0.0.1` and `localhost` | Comma-separated CORS origins. | Empty entries are ignored. |
| `FACE_MATCH_THRESHOLD` | `0.40` | Cosine-similarity threshold for a face `MATCH`. | `0.0`–`1.0`. |
| `LIVENESS_VALIDITY_SECONDS` | `30` | Window in which a verified liveness session can be used. | Positive integer. |
| `INSIGHTFACE_MODEL_NAME` | `buffalo_l` | InsightFace model pack name. | Non-empty string. |
| `INSIGHTFACE_ROOT` | `~/.insightface` | InsightFace model cache/download directory. | Path. |

Copy [`.env.example`](../.env.example) to `.env` to override defaults locally.
Do not commit `.env` or real credentials.

## Startup behavior

`create_app()` in `app/main.py` builds the FastAPI application and registers a
lifespan handler. The lifespan:

1. Stores the settings object on `app.state.settings`.
2. Calls `initialize_database(settings.database_path)`, which creates the parent
   directory and the idempotent `attendance` schema, then sets
   `app.state.database_initialized = True`.
3. Calls `build_services(settings)` once.
4. Creates one `LivenessService`, one `FaceRecognitionService`, and one
   `AttendanceVerificationService` that shares those instances.
5. Stores the services on `app.state`.
6. Closes the MediaPipe detector on shutdown.

If the MediaPipe model file does not exist, startup fails with:

```text
RuntimeError: MediaPipe Face Landmarker model not found. Set
MEDIAPIPE_FACE_LANDMARKER_MODEL to the path of a valid
face_landmarker.task file.
```

InsightFace initialization failures are wrapped with a message naming
`INSIGHTFACE_MODEL_NAME` and `INSIGHTFACE_ROOT`.

`GET /` and `/docs` are served only after the lifespan completes, so they are
not available when model initialization fails.

## Settings still hardcoded

The following values are not configurable yet:

| Setting | Value | Location |
| --- | --- | --- |
| MediaPipe face count | `1` | `app/services/liveness.py` |
| Eye-closed EAR threshold | `0.10` | `app/services/liveness.py` |
| Required closed frames | `4` | `app/services/liveness.py` |
| InsightFace execution provider | `CPUExecutionProvider` | `app/services/face_recognition.py` |
| Detection size | `640x640`, then `1024x1024` on retries | `app/services/face_recognition.py` |
| InsightFace detection threshold override | `0.35` | `app/services/face_recognition.py` |
| Upscale factor | `2x` | `app/services/face_recognition.py` |
| Minimum face size | `80` pixels per side | `app/services/anti_spoofing.py` |
| Brightness bounds | `35`–`235` | `app/services/anti_spoofing.py` |
| Sharpness heuristics | Laplacian variance `< 10` rejected, `< 25` penalized | `app/services/anti_spoofing.py` |

These are heuristic values, not calibrated or certified security thresholds.

## Manual client configuration

| Setting | Value | Location |
| --- | --- | --- |
| API base URL | `http://127.0.0.1:8000` | `test_api_attendance.py` |
| Student ID | `STU001` | `test_api_attendance.py`, registration scripts |
| Subject | `Java Programming` | `test_api_attendance.py` |
| Lecture ID | `JAVA-LECTURE-API-001` | `test_api_attendance.py` |
| Registration output | `../../data/face_embeddings/STU001.npy` | `app/services/register_face.py` |

The manual client and registration scripts still use hardcoded values and
relative output paths. Parameterizing them is tracked in
[#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10).

## Not implemented

- Input validation and upload limits ([#5](https://github.com/Kartik-gharte/Attendance.Application/issues/5)).
- Authentication and authorization ([#4](https://github.com/Kartik-gharte/Attendance.Application/issues/4)).
- Structured, redacted logging ([#8](https://github.com/Kartik-gharte/Attendance.Application/issues/8)).
- A configurable log level.

Do not add secrets to source control or documentation.
