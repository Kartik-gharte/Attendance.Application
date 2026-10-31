# Known Issues

These are confirmed gaps based on source inspection and repository state as of 2026-10-31. KI-001, KI-002, KI-003, KI-004, KI-005, KI-007, KI-009, KI-010, and KI-013 are resolved; KI-006 is partially resolved; the remaining issues are still open.

Severity is a triage aid, not a formal risk rating.

## Summary

| ID | Severity | Issue | Status |
| --- | --- | --- | --- |
| KI-001 | Critical | Empty dependency manifest | Resolved |
| KI-002 | Critical | Hardcoded Windows model path | Resolved |
| KI-003 | Critical | Database schema is never initialized | Resolved |
| KI-004 | Critical | No authentication or authorization | Resolved |
| KI-005 | High | `student_id` is used in a filesystem path without validation | Resolved |
| KI-006 | High | Liveness sessions are bearer-like and replayable | Partially resolved |
| KI-007 | High | No upload size/type limits or domain validation | Resolved |
| KI-008 | High | No automated test suite | Open |
| KI-009 | High | No configuration system | Resolved |
| KI-010 | High | Error responses expose internal messages | Resolved |
| KI-011 | High | No retention, deletion, encryption, or backup policy | Open |
| KI-012 | Medium | In-memory sessions are per-process and never cleaned up | Open |
| KI-013 | Medium | Models are loaded twice at import; startup is slow and fragile | Resolved |
| KI-014 | Medium | Broken import in `test_liveness_service.py` | Open |
| KI-015 | Medium | Missing fixtures and model assets | Open |
| KI-016 | Medium | Registration and client paths/IDs are hardcoded | Open |
| KI-017 | Medium | Logs contain personal data and use `print()` | Open |
| KI-018 | Medium | No CI or verified branch protection | Open |
| KI-019 | Low | Dead/duplicate code paths and scripts | Open |
| KI-020 | High | Anti-spoofing effectiveness is unmeasured | Open |

## Details

### KI-001 — Empty dependency manifest

- **Evidence:** `requirements.txt` was 0 bytes.
- **Impact:** A fresh clone could not install the application. Setup instructions could not be verified.
- **Proposed fix:** Define a reviewed, pinned manifest compatible with a documented Python version; test installation in a clean environment.
- **Resolution:** `requirements.txt` and `requirements-dev.txt` are pinned. A clean Python 3.11.16 virtual environment installed successfully from the manifest on 2026-10-30.
- **Status:** Resolved 2026-10-30.

### KI-002 — Hardcoded Windows model path

- **Evidence:** `app/services/liveness.py` previously set an absolute `C:\...` path.
- **Impact:** Import failed on macOS/Linux and on any machine without that exact Windows layout.
- **Proposed fix:** Read a portable path from configuration, validate existence, and document model provisioning.
- **Resolution:** The path is read from `MEDIAPIPE_FACE_LANDMARKER_MODEL` (default `models/mediapipe/face_landmarker.task`). Missing files fail startup with an actionable error. Startup was verified on macOS arm64.
- **Status:** Resolved 2026-10-30.

### KI-003 — Database schema is never initialized

- **Evidence:** `initialize_database()` was defined but had no call sites.
- **Impact:** A fresh database lacked the `attendance` table; insert/query calls could fail with `no such table: attendance`.
- **Proposed fix:** Initialize on application startup (lifespan) and in test setup; add a fresh-database test.
- **Resolution:** The FastAPI lifespan calls `initialize_database(settings.database_path)`, which creates the parent directory and table idempotently. Attendance routes use the configured path. Focused tests cover fresh creation, restart preservation, retrieval, and duplicate rejection.
- **Status:** Resolved 2026-10-30.

### KI-004 — No authentication or authorization

- **Evidence:** All routes were unauthenticated; there was no auth dependency, token handling, or user model.
- **Impact:** Anyone who could reach the API could mark attendance, read all records, or probe biometric services. CORS does not prevent non-browser access.
- **Proposed fix:** Add authentication, role-based authorization, and audited access controls. This is required before any real deployment.
- **Resolution:** Local SQLite accounts use Argon2id password hashes and opaque bearer tokens stored as SHA-256 hashes with expiry/revocation. Students can mark/read only their own attendance; admins can read records but cannot mark attendance. Liveness sessions are bound to the authenticated user. Tokens are issued by `POST /auth/token` and accounts are provisioned through `python -m app.auth.cli`. Tests cover login, logout, expiry, revocation, roles, cross-student denial, and session ownership.
- **Remaining risk:** TLS, rate limiting, account lockout, MFA/SSO, and audit logging are not implemented. See [SECURITY_AND_PRIVACY.md](SECURITY_AND_PRIVACY.md).
- **Status:** Resolved 2026-10-31 for the local-account baseline.

### KI-005 — Unvalidated `student_id` in filesystem path

- **Evidence:** `app/services/face_recognition.py` builds the embedding path from request/form data; `app/services/validation.py` now validates identifiers and resolved paths before lookup.
- **Impact:** Path separators, `..`, or an absolute path in `student_id` may escape the intended directory.
- **Proposed fix:** Validate against a strict identifier pattern and verify the resolved path remains under the embeddings directory; add adversarial tests.
- **Status:** Resolved; validation and containment checks are implemented and covered by focused tests.

### KI-006 — Liveness sessions are replayable and exposed in query strings

- **Evidence:** `session_id` is a UUID stored in a module-level dictionary; `/liveness/frame` accepts it as a query parameter; `/attendance/verify` trusts that a verified session exists. Sessions are now bound to the authenticated user ID, but not to a device, IP, or one-time challenge.
- **Impact:** A captured session may be replayed by the same authenticated student within the configured validity window (default 30 seconds). A different student receives `403`. Session IDs may appear in logs.
- **Proposed fix:** Use headers/body instead of query strings, add device/request binding, and add a one-time cryptographic challenge.
- **Status:** Partially resolved; authenticated-user binding is implemented and tested. Replay and query-string exposure remain open.

### KI-007 — Missing input and upload validation

- **Evidence:** `student_id`, `subject`, and `lecture_id` were previously plain `Form(...)` strings; images were read without size/content validation.
- **Impact:** Oversized uploads, malformed images, and arbitrary identifiers were possible.
- **Proposed fix:** Add length/pattern validation, size/type limits, and enrollment/subject checks; return structured errors.
- **Status:** Resolved for input and upload validation; enrollment/subject authorization remains tracked separately.

### KI-008 — No automated tests

- **Evidence:** Focused runtime tests now exist under `tests/runtime/` (45 passing tests) and cover settings, startup, database, validation, authentication, and attendance API behavior with fake model services. Root `test_*.py` files still execute top-level code, open cameras, use `exit()`, and require absent fixtures. No CI workflow exists.
- **Impact:** The focused suite catches regressions in covered paths, but model/camera scripts remain dangerous to collect and there is no CI enforcement.
- **Proposed fix:** Keep expanding deterministic tests and add CI; retire or isolate manual scripts.
- **Status:** Open; focused coverage exists, broader suite and CI remain Phase 2 priority ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).

### KI-009 — No configuration system

- **Evidence:** `app/core/config.py` was empty; no environment or dotenv usage existed.
- **Impact:** Paths, thresholds, origins, and storage locations could not be changed without editing source.
- **Proposed fix:** Add validated configuration with safe defaults and documented environment variables; do not add secrets to the repository.
- **Resolution:** `app/core/config.py` defines a validated `Settings` object backed by environment variables and a project-root `.env` file. Defaults and overrides are documented in [CONFIGURATION.md](CONFIGURATION.md).
- **Status:** Resolved 2026-10-30.

### KI-010 — Internal error messages returned to clients

- **Evidence:** The attendance verification route previously returned `str(error)` in the response, and retrieval endpoints did not catch database errors.
- **Impact:** Paths, model errors, and database details could be disclosed; unhandled errors could produce HTTP 500.
- **Proposed fix:** Log details server-side with redaction; return stable, non-sensitive error codes/messages.
- **Status:** Resolved; stable attendance and retrieval error responses are implemented.

### KI-011 — No retention, deletion, encryption, or backup policy

- **Evidence:** Embeddings and SQLite records are stored unencrypted; no deletion/retention code or documentation exists.
- **Impact:** Biometric and attendance data may persist indefinitely and be exposed through filesystem access or backups.
- **Proposed fix:** Define retention and deletion workflows, protect storage, restrict access, and document backup handling. Obtain privacy review.
- **Status:** Open.

### KI-012 — Per-process, unbounded in-memory sessions

- **Evidence:** `sessions = {}` at `app/api/liveness_routes.py`; sessions are now bound to an authenticated user ID, but abandoned sessions are never removed and there is no shared store or lock.
- **Impact:** Memory growth; behavior differs with multiple workers/restarts; no cross-process verification.
- **Proposed fix:** Add expiry cleanup and, if scaling, a shared store with lifecycle management.
- **Status:** Open.

### KI-013 — Duplicate model loading at import

- **Evidence:** Routers previously constructed services at import; two `LivenessService` instances and one `FaceRecognitionService` loaded before serving.
- **Impact:** Slow startup, higher memory use, and import-time failure.
- **Proposed fix:** Create shared services once in a lifespan/application state and inject dependencies.
- **Resolution:** `build_services()` runs once in the FastAPI lifespan. Routes read the shared instances from `app.state`; startup logs confirmed one MediaPipe and one InsightFace load.
- **Status:** Resolved 2026-10-30.

### KI-014 — Broken test import

- **Evidence:** `test_liveness_service.py:3` imports `from liveness import LivenessService`; the module lives at `app.services.liveness`.
- **Impact:** The root script fails immediately.
- **Proposed fix:** Correct the import or retire the duplicate script as part of the test refactor.
- **Status:** Open.

### KI-015 — Missing fixtures and model assets

- **Evidence:** Scripts reference `tests/fixtures/test.jpg`, `closed_eye.jpeg`, `test.jpg`, `blaze_face_short_range.tflite`, and `face_landmarker.task`; none are present in the repository. Images/models are ignored by Git. The MediaPipe application model and InsightFace cache now have documented provisioning in [SETUP.md](SETUP.md), but script fixtures are still absent.
- **Impact:** Manual scripts cannot run from a clean checkout without additional fixtures.
- **Proposed fix:** Document asset provisioning; use synthetic or consented fixtures; provide an opt-in local setup path without committing biometric data or large models.
- **Status:** Open.

### KI-016 — Hardcoded registration and client values

- **Evidence:** `app/services/register_face.py`, `recognize_face.py`, `combined_test.py`, and `test_api_attendance.py` hardcode `STU001`, image names, API URLs, subject/lecture values, and output paths.
- **Impact:** Accidental data overwrite, wrong-student testing, and non-portable paths.
- **Proposed fix:** Parameterize via CLI arguments/environment and validate output paths.
- **Status:** Open.

### KI-017 — PII in console logs

- **Evidence:** `app/api/routes.py` prints student ID, subject, lecture ID, filename, byte size, face result, and database result; services print detection details.
- **Impact:** Personal data may persist in terminal/CI logs with no redaction or retention control.
- **Proposed fix:** Adopt structured logging with levels and redaction; prohibit raw images, embeddings, and session IDs in logs.
- **Status:** Open.

### KI-018 — No CI or verified branch protection

- **Evidence:** A CI workflow now runs compile checks, focused tests, and gitleaks. Branch protection still requires repository-owner action and has not been configured.
- **Impact:** Checks exist, but GitHub does not yet block merges when they fail.
- **Proposed fix:** Apply the documented `main` branch-protection rule requiring the `Compile and test` and `Secret scan` checks.
- **Status:** Partially resolved; CI is defined, branch protection is documented but not configured.

### KI-019 — Dead/duplicate code paths

- **Evidence:** `attendance_already_marked()` is unused; `AttendanceVerificationService.verify_attendance()` and `verify_face_from_frame()` are not used by the API; multiple overlapping camera scripts exist; `test_liveness_service.py` duplicates `tests/services/test_liveness_service.py`.
- **Impact:** Confusing ownership and maintenance risk.
- **Proposed fix:** Remove or consolidate during a scoped cleanup after tests protect behavior.
- **Status:** Open; low priority.

### KI-020 — Anti-spoofing effectiveness is unmeasured

- **Evidence:** `app/services/anti_spoofing.py` explicitly states it is not a trained model; thresholds are heuristics. No evaluation data or metrics exist.
- **Impact:** The system may be vulnerable to presentation attacks; current checks must not be represented as certified PAD.
- **Proposed fix:** Evaluate with a documented attack dataset, add a trained PAD component if required, and publish measured limitations.
- **Status:** Open; do not make security claims until addressed.
