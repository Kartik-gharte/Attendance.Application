# Changelog

All notable changes to this project are recorded here. The project does not yet have tagged releases, so entries are grouped under `Unreleased`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to follow [Semantic Versioning](https://semver.org/) once versioned releases begin.

## Unreleased

### Added

- Project foundation documentation: project specification, architecture, API reference, database, setup, configuration, testing, security/privacy, workflow, roadmap, status, known issues, decisions, and foundation plan.
- Root agent instructions (`AGENTS.md`) and contribution guidance (`CONTRIBUTING.md`).
- Security policy (`SECURITY.md`).
- GitHub pull-request and issue templates.
- Validated configuration in `app/core/config.py` backed by environment variables and a project-root `.env` file.
- `.env.example` with placeholders for model, embedding, database, CORS, recognition, and liveness settings.
- Pinned runtime dependencies in `requirements.txt` and development dependencies in `requirements-dev.txt`.
- Focused runtime tests under `tests/runtime/` for settings, lifespan wiring, `/`, `/docs`, missing-model failure, database initialization, retrieval, duplicate handling, validation, upload limits, and controlled errors with fake model services.
- `app/services/validation.py` for identifier/session validation, embedding-path containment, and upload content/size/dimension checks.
- Configurable `MAX_UPLOAD_SIZE_BYTES`, `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT`, and `MAX_IMAGE_PIXELS` settings.
- FastAPI lifespan-managed service construction with a shared `LivenessService` and `FaceRecognitionService`.
- Local account authentication in `app/auth/`: Argon2id password hashing, opaque bearer tokens stored as SHA-256 hashes, token expiry, revocation, and SQLite-backed users/tokens.
- `POST /auth/token`, `GET /auth/me`, and `POST /auth/logout`.
- Student/admin role dependencies and attendance authorization: student self-access only, admin read-only review, and user-bound liveness sessions.
- `python -m app.auth.cli` for `create-user`, `set-password`, and `deactivate-user`; no public signup.
- Configurable `AUTH_TOKEN_TTL_SECONDS` (default 3600).
- Bearer-token authentication in the manual `test_api_attendance.py` client, with password prompt and `ATTENDANCE_API_URL`/`ATTENDANCE_USERNAME` overrides.
- Runtime tests for login/logout, token expiry/revocation, 401/403 behavior, cross-student denial, session ownership, and account validation (45 focused tests total).
- GitHub Actions CI for compile checks, focused runtime tests, and gitleaks secret scanning, with documented branch-protection steps.

### Changed

- Replaced the initial README with a documentation-oriented project overview that distinguishes implemented, unverified, and planned behavior.
- Extended `.gitignore` hygiene for Python caches, build artifacts, editor files, and model binaries.
- Replaced the hardcoded Windows MediaPipe path with `MEDIAPIPE_FACE_LANDMARKER_MODEL`.
- Replaced import-time service construction and duplicate model loading with a single lifespan startup path.
- Made the embedding directory, SQLite path, CORS origins, face threshold, liveness validity, upload limits, image dimensions, and InsightFace cache configurable.
- Attendance and liveness routes now validate identifiers, sessions, and uploaded images; attendance retrieval returns a controlled database-error response.
- `get_connection()` now honors `ATTENDANCE_DB_PATH`, and attendance routes use the configured database path from the app state. The FastAPI lifespan now calls `initialize_database()` and `initialize_auth_database()` before constructing model services and marks both schemas initialized.
- Attendance verification now requires a student bearer token, a matching `student_id`, and ownership of the liveness session. Attendance retrieval requires a bearer token and enforces student self-access/admin read-only access.
- Updated setup, configuration, architecture, database, testing, roadmap, status, known-issue, decision, API, security, and README documentation with authentication behavior and verified runtime results.

### Repository

- `main` now contains the integrated attendance-verification and AI-security feature work. The original feature branches were fully merged before remote cleanup on 2026-10-27.
- Runtime bootstrap was developed on `fix/runtime-bootstrap` and verified locally on macOS 27.0.1 arm64 with Python 3.11.16.
- Contribution guidance now requires multiple focused commits and, when practical, separate pull requests rather than one large mixed change.

### Known gaps

- No CI workflow exists, and the broader automated test suite is still open (issue #7).
- TLS, rate limiting, account lockout, MFA/SSO, and audit logging are not implemented.
- Enrollment/subject authorization is still missing.
- Liveness session IDs remain in query strings and may be replayed by the same authenticated student within the validity window.
- Anti-spoofing is heuristic screening, not a trained PAD model.
- Startup is verified only on macOS arm64 with Python 3.11.16.

### Added
- `app/services/register_face.py` rewritten as a parameterized enrollment workflow with a `register_face()` function and a CLI entry point. Student identifiers are validated, the destination is resolved inside the configured embedding directory, existing embeddings are refused without `--overwrite`, and the embedding is written atomically.
- `app/services/recognize_face.py` rewritten as a parameterized recognition workflow with a `recognize_face()` function and a CLI entry point.
- `manual/api_attendance.py` rewritten so that the API URL, username, student, subject, lecture, and camera index are configurable through arguments or environment variables. The password is never accepted as a command line argument.
- `tests/runtime/test_enrollment_workflow.py` covering identifier validation, path containment, overwrite refusal, atomic writes, dry runs, the CLI surfaces, and the manual client configuration.

### Fixed
- `app/services/recognize_face.py` no longer loads a model or reads a hardcoded image at import time, and no longer calls `logger` before the logger is defined.
- The manual demo scripts no longer contain Windows-specific paths or hardcoded student identifiers.

### Added
- `app/database/migrations.py` with a dependency-free versioned migration runner. Applied versions are recorded in a `schema_migrations` table, migrations run in ascending version order, and each migration runs inside its own transaction so that a failure rolls back completely.
- `python -m app.database.migrations status` and `python -m app.database.migrations upgrade` to inspect and apply migrations.
- `tests/runtime/test_database_migrations.py` covering fresh database initialization, the upgrade path from a database created before schema versioning existed, migration failure and rollback, and data integrity after a migration.

### Changed
- `initialize_database()` and `initialize_auth_database()` now delegate to the migration runner. The schema has a single source of truth in `app/database/migrations.py`, and both calls are idempotent.

### Fixed
- A failing migration no longer leaves a partially applied schema behind. The migration connection uses autocommit mode with an explicit transaction, so DDL is rolled back as well.

### Added
- `app/database/backup.py` with backup creation, verification, and restore for the attendance database and the face embeddings. The database copy uses the SQLite online backup API so it is consistent while the service runs. Each backup carries a manifest with the schema version, the SHA-256 checksum of the database, and the list of embedding files.
- `python -m app.database.backup create`, `list`, `verify`, and `restore`.
- `tests/runtime/test_database_backup.py` covering backup creation, manifest contents, verification refusals, restore, the overwrite refusal, the safety copy, embedding restore, and data integrity after a restore.

### Added
- `GET /health/live` reports whether the process is alive. It inspects nothing outside the process, so a dependency outage cannot cause a restart loop.
- `GET /health/ready` reports whether the service can serve requests. It verifies that the database exists, passes the SQLite integrity check, contains the attendance table, and is at the expected schema version, and that the biometric models are loaded. It returns `503` when the service is not ready.
- `tests/runtime/test_health_endpoints.py` covering the liveness and readiness behaviour, the dependency failure paths, and the absence of personal data, credentials, and filesystem paths in the responses.

### Added
- `docs/DEPLOYMENT.md` describing the requirements, the single-worker constraint for the in-memory liveness sessions, the TLS expectation, the health probe configuration, the measured baseline, and a runbook covering deploying, backing up, upgrading, rolling back, and diagnosing failures.
- `manual/benchmark.py` measuring the import time, the resident memory, the startup cost, the request latency, and the throughput under concurrency. The measurement is reproducible with `python -m manual.benchmark`, and `python -m manual.benchmark --with-models` additionally reports the startup cost and memory with the real biometric models loaded.

### Added
- `app/evaluation/harness.py` with the reproducible evaluation machinery: a versioned dataset description, dataset validation that refuses an untrustworthy dataset, per-attempt scores and decisions, false accept and false reject rates, a ROC curve, the equal error rate, the liveness success rate, and Wilson score intervals.
- `app/evaluation/evaluate.py` running the evaluation against the real models and writing a report that contains no images, embeddings, or biometric templates.
- `tests/runtime/test_evaluation_harness.py` covering the dataset parsing and validation, the metric computations, the uncertainty intervals, and the report format.
- `docs/EVALUATION_DATASET_POLICY.md` specifying the dataset that the accuracy evaluation needs, the consent rules, the dataset description format, how to run the evaluation, and what may not be claimed until it has been run.

### Changed
- `docs/DEPLOYMENT.md` records the measured baseline with the real model assets: 1.0 s startup and 986 MB resident memory, against 165 MB without the models.
- `manual/benchmark.py` accepts `--with-models` to report the startup cost and memory with the real biometric models loaded.

### Fixed
- The deployment baseline no longer omits the cost of the biometric models.

### Changed
- `docs/ISSUE_AUDIT.md`, `docs/ISSUE_BACKLOG.md`, and `docs/PROJECT_STATUS.md` updated to the verified state after PRs #26, #29, #30, #31, #32, #33, #34, and #35. The audit records that issues #8 and #10 were previously reported as complete while the code had not reached `main`, and how each was corrected.

### Added
- An enrollment audit trail. Every enrollment is recorded in the new `enrollment_audit` table with the operator, the time, the consent reference, the source image file name, a digest of the stored embedding, and the outcome. The trail holds no biometric material: no image, no embedding, and no face crop.
- `app/services/enrollment_audit.py` with `record_enrollment()`, `list_enrollments()`, `embedding_digest()`, and `delete_old_enrollment_audit()`.
- Migration 2 creates the `enrollment_audit` table. The schema version is now 2.
- The enrollment command accepts `--operator`, `--consent-reference`, `--database-path`, and `--no-audit`.
- `tests/runtime/test_enrollment_audit.py` covering the recorded content, the refusals, the retention, the guarantee that no biometric material is recorded, and the enrollment workflow integration.
- Backup retention. A backup is removed when it is older than `BACKUP_RETENTION_DAYS` or when it falls outside the newest `BACKUP_RETENTION_COUNT` backups. The newest backup is always kept, so a misconfigured policy cannot empty the backup directory. Only directories that follow the backup naming convention and contain a manifest are considered, so an unrelated directory in the backup root is never deleted.
- `python -m app.database.backup prune`, with `--dry-run` to report what would be removed without deleting it.
- `BACKUP_RETENTION_DAYS`, `BACKUP_RETENTION_COUNT`, and `BACKUP_PRUNE_ON_CREATE` settings. Pruning runs automatically after a backup is created.
- `tests/runtime/test_backup_retention.py` covering both limits, the safety rule, the directory guard, the dry run, and the command line interface.
