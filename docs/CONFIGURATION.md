# Configuration

## Current state

There is no configuration system. `app/core/config.py` is empty, and the application does not read environment variables. The `.env` pattern is ignored by Git but no code loads `.env` files.

All current settings are hardcoded in source files. The tables below record them so future configuration work starts from the actual state.

## Application and server

| Setting | Value | Location | Notes |
| --- | --- | --- | --- |
| FastAPI title | `AI Attendance System` | `app/main.py:9` | OpenAPI metadata. |
| FastAPI version | `1.0.0` | `app/main.py:10` | Not a release tag. |
| CORS origins | `http://127.0.0.1:5500`, `http://localhost:5500`, `http://127.0.0.1:5173`, `http://localhost:5173` | `app/main.py:21-26` | Local development origins only. |
| CORS credentials | `True` | `app/main.py:28` | All methods and headers allowed. |
| Liveness validity | `30` seconds | `app/api/liveness_routes.py:22` | Applied after successful liveness verification. |
| Server host/port | Not configured in code | — | Supplied to Uvicorn at launch. |

## Liveness and anti-spoofing

| Setting | Value | Location | Notes |
| --- | --- | --- | --- |
| MediaPipe model path | `C:\AI-Attendance-System\ai-service\models\mediapipe\face_landmarker.task` | `app/services/liveness.py:13-16` | Windows-only; non-portable. |
| MediaPipe face count | `1` | `app/services/liveness.py:31` | At most one face is processed. |
| Eye-closed EAR threshold | `0.10` | `app/services/liveness.py:18` | EAR below this counts as closed. |
| Required closed frames | `4` | `app/services/liveness.py:19` | Consecutive frames before a blink can be detected. |
| Minimum face size | `80` pixels per side | `app/services/anti_spoofing.py:20` | Bounding box check. |
| Minimum brightness | `35` | `app/services/anti_spoofing.py:21` | Mean grayscale value. |
| Maximum brightness | `235` | `app/services/anti_spoofing.py:22` | Mean grayscale value. |
| Minimum sharpness | Laplacian variance `< 10` rejected | `app/services/anti_spoofing.py:164` | Basic blur screening. |
| Low-detail penalty | Laplacian variance `< 25` | `app/services/anti_spoofing.py:179` | Reduces score by `0.10`. |
| Lighting penalty | Brightness `< 50` or `> 220` | `app/services/anti_spoofing.py:184-190` | Reduces score by `0.10`. |

These are heuristic thresholds, not calibrated values or a trained model.

## Face recognition

| Setting | Value | Location | Notes |
| --- | --- | --- | --- |
| InsightFace model | `buffalo_l` | `app/services/face_recognition.py:13-16` | Loaded with `CPUExecutionProvider`. |
| Detection size | `640x640` initially; `1024x1024` on later attempts | `app/services/face_recognition.py` | Multi-attempt detection. |
| Detection threshold override | `0.35` | `app/services/face_recognition.py:26` | Applied inside a `try/except`; may be ignored. |
| Upscale factor | `2x` | `app/services/face_recognition.py:218` | Applied for retry attempts. |
| Similarity threshold | `0.40` | `app/services/face_recognition.py:31` | Cosine similarity at or above this is `MATCH`. |

## Storage paths

| Setting | Value | Location | Notes |
| --- | --- | --- | --- |
| Database path | `<repo>/data/attendance.db` | `app/database/attendance_db.py:10-14` | Directory created on first connection. |
| Embedding path | `<repo>/data/face_embeddings/<student_id>.npy` | `app/services/face_recognition.py:464-475` | `student_id` is interpolated into the path without validation. |
| Model directory | `models/mediapipe/` (intended by other scripts) | `tests/services/test_landmarks.py`, `test_face.py` | The app itself uses the hardcoded Windows path. |

## Manual client configuration

| Setting | Value | Location |
| --- | --- | --- |
| API base URL | `http://127.0.0.1:8000` | `test_api_attendance.py` |
| Student ID | `STU001` | `test_api_attendance.py`, registration scripts |
| Subject | `Java Programming` | `test_api_attendance.py` |
| Lecture ID | `JAVA-LECTURE-API-001` | `test_api_attendance.py` |
| Registration output | `../../data/face_embeddings/STU001.npy` | `app/services/register_face.py:64-70` |

The registration path is relative to the current working directory and can write outside the repository. Fix this during Phase 1/2.

## Environment variables

No environment variables are currently read. `.env` and `.env.*` are ignored, but there is no loader. Do not assume `.env` changes application behavior.

## Proposed configuration (not implemented)

The following are recommendations, not current behavior:

| Proposed variable | Purpose | Safe example |
| --- | --- | --- |
| `ATTENDANCE_DB_PATH` | Override the SQLite path for development/tests | `/tmp/attendance-test.db` |
| `MEDIAPIPE_FACE_LANDMARKER_MODEL` | Portable model path | `./models/mediapipe/face_landmarker.task` |
| `FACE_MATCH_THRESHOLD` | Tune similarity threshold after evaluation | `0.40` |
| `LIVENESS_VALIDITY_SECONDS` | Session validity window | `30` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated development origins | `http://localhost:5173` |
| `LOG_LEVEL` | Structured logging verbosity | `INFO` |

Any configuration work must be a focused, reviewed change with tests and updated documentation. Do not add secrets to source control or documentation.
