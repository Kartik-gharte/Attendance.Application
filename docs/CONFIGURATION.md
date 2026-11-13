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
| `AUTH_TOKEN_TTL_SECONDS` | `3600` | Lifetime of opaque bearer tokens issued by `/auth/token`. | `60`–`604800`. |
| `MAX_UPLOAD_SIZE_BYTES` | `5242880` | Maximum accepted image upload size. | Positive integer. |
| `MAX_IMAGE_WIDTH` | `4096` | Maximum decoded image width. | `1`–`8192`. |
| `MAX_IMAGE_HEIGHT` | `4096` | Maximum decoded image height. | `1`–`8192`. |
| `MAX_IMAGE_PIXELS` | `16777216` | Maximum decoded image pixel count. | `1`–`67108864`. |
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
3. Calls `initialize_auth_database(settings.database_path)`, which creates the
   `users` and `auth_tokens` tables idempotently and sets
   `app.state.auth_initialized = True`.
4. Calls `build_services(settings)` once.
5. Creates one `LivenessService`, one `FaceRecognitionService`, and one
   `AttendanceVerificationService` that shares those instances.
6. Stores the services on `app.state`.
7. Closes the MediaPipe detector on shutdown.

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
| API base URL | `ATTENDANCE_API_URL`, default `http://127.0.0.1:8000` | `test_api_attendance.py` |
| Login username | `ATTENDANCE_USERNAME`, default `student1` | `test_api_attendance.py` |
| Login password | Prompted with `getpass` at runtime | `test_api_attendance.py` |
| Student ID | `STU001` | `test_api_attendance.py`, registration scripts |
| Subject | `Java Programming` | `test_api_attendance.py` |
| Lecture ID | `JAVA-LECTURE-API-001` | `test_api_attendance.py` |
| Registration output | `../../data/face_embeddings/STU001.npy` | `app/services/register_face.py` |

The manual API client prompts for a password and obtains a bearer token from
`POST /auth/token`. It reads `ATTENDANCE_API_URL` and `ATTENDANCE_USERNAME` from
the environment. It still uses hardcoded values for the student ID, subject,
and lecture, and the registration scripts still use hardcoded paths.
Parameterizing the remaining values is tracked in
[#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10).

## Account provisioning

Local accounts are created with the CLI, not a public endpoint:

```bash
python -m app.auth.cli create-user student1 \
  --role student --student-id STU001
python -m app.auth.cli create-user admin1 --role admin
python -m app.auth.cli set-password student1
python -m app.auth.cli deactivate-user student1
```

The CLI prompts for the password without placing it in shell history. Use
`--database-path` to target a database other than `ATTENDANCE_DB_PATH`. Password
reset and deactivation revoke all active tokens for that account.

## Not implemented

- Rate limiting, account lockout, and login audit logging.
- SSO, institutional identity providers, and multi-factor authentication.
- Structured, redacted logging ([#8](https://github.com/Kartik-gharte/Attendance.Application/issues/8)).
- A configurable log level.

Do not add secrets to source control or documentation.

## Logging

| Variable | Default | Description |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Application log level. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FORMAT` | `%(asctime)s %(levelname)s %(name)s %(message)s` | `logging.Formatter` format string applied to application log records. |

Logging is configured once during application startup in `app/main.py` using
`app/core/logging_config.py`. Records are written to `stderr` so that they
can be collected by a process supervisor or container runtime without
interfering with standard output.

### Redaction policy

The following values are masked before any handler receives a record:

- bearer tokens, passwords, API keys, and other `key=value` credentials;
- UUID-shaped liveness session identifiers;
- float vectors that resemble face embeddings.

Redaction is applied through a log record factory, so records are sanitized
at creation time and every handler — including one attached later by an
operator — receives sanitized values.

`student_id` is logged at `INFO` level for attendance outcomes, because an
administrator must be able to reconcile a record. It is never logged
alongside raw biometric material. At `WARNING` level and above, server-side
diagnostics are limited to the exception type, so internal filesystem paths
do not appear at the default level.

### Retention and access

Logs are ordinary process output and are not stored by the application. When
the service runs under a supervisor or container runtime, log retention and
access are controlled by that runtime. Treat logs as a personal-data store:
they may contain `student_id` values and must be access-controlled and
retained only as long as the operational need requires.

## Enrollment and client values

The enrollment and manual client workflows read their values from arguments
first and environment variables second. The embedding directory used by the
supported workflow is the configured `FACE_EMBEDDING_DIR`; a caller may
narrow it with `--output-dir` but cannot point it outside that directory.

| Variable | Default | Used by |
| --- | --- | --- |
| `FACE_EMBEDDING_DIR` | `data/face_embeddings` | Enrollment and recognition |
| `MEDIAPIPE_FACE_LANDMARKER_MODEL` | `models/mediapipe/face_landmarker.task` | Liveness and the manual demo scripts |
| `ATTENDANCE_API_URL` | `http://127.0.0.1:8000` | Manual API client |
| `ATTENDANCE_USERNAME` | — | Manual API client |
| `ATTENDANCE_STUDENT_ID` | — | Manual API client, manual demo scripts |
| `ATTENDANCE_SUBJECT` | `Java Programming` | Manual API client |
| `ATTENDANCE_LECTURE_ID` | — | Manual API client |
| `ATTENDANCE_CAMERA_INDEX` | `0` | Manual API client |
| `ATTENDANCE_PASSWORD` | — | Manual API client; prompts when unset |
| `RECOGNITION_IMAGE_PATH` | `tests/fixtures/test.jpg` | `manual/recognition.py` |
| `EMBEDDING_IMAGE_PATH` | `tests/fixtures/test.jpg` | `manual/embedding.py` |
| `FACE_DETECTOR_IMAGE_PATH` | `tests/fixtures/test.jpg` | `manual/face_detector.py` |
| `REGISTERED_EMBEDDING_PATH` | `data/face_embeddings/<student>.npy` | `manual/combined_demo.py` |
| `EAR_THRESHOLD` | `0.10` | `manual/combined_demo.py` |
| `RECOGNITION_THRESHOLD` | `0.40` | `manual/combined_demo.py` |

The manual scripts under `manual/` are opt-in developer tools. They are not
part of the supported runtime workflow and are not covered by the API
contract.
## Backup retention

Backups contain biometric templates and personal data, so old copies are
removed automatically.

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKUP_RETENTION_DAYS` | `30` | A backup older than this many days is removed. |
| `BACKUP_RETENTION_COUNT` | `14` | At most this many backups are kept, regardless of age. |
| `BACKUP_PRUNE_ON_CREATE` | `true` | Prune expired backups automatically after a backup is created. |

The two limits apply independently. A backup is removed when it is older
than the age limit or when it falls outside the newest backups. The newest
backup is always kept, so a misconfigured policy cannot empty the backup
directory.

Only directories that follow the backup naming convention and contain a
manifest are considered. An unrelated directory in the backup root is
never deleted.

Pruning can also be run on its own:

```bash
python -m app.database.backup prune --dry-run
python -m app.database.backup prune
```
