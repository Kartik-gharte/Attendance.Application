# Known Issues

These are confirmed gaps based on source inspection and repository state as of 2026-10-27. None were fixed during the documentation foundation task.

Severity is a triage aid, not a formal risk rating.

## Summary

| ID | Severity | Issue |
| --- | --- | --- |
| KI-001 | Critical | Empty dependency manifest |
| KI-002 | Critical | Hardcoded Windows model path |
| KI-003 | Critical | Database schema is never initialized |
| KI-004 | Critical | No authentication or authorization |
| KI-005 | High | `student_id` is used in a filesystem path without validation |
| KI-006 | High | Liveness sessions are bearer-like and replayable |
| KI-007 | High | No upload size/type limits or domain validation |
| KI-008 | High | No automated test suite |
| KI-009 | High | No configuration system |
| KI-010 | High | Error responses expose internal messages |
| KI-011 | High | No retention, deletion, encryption, or backup policy |
| KI-012 | Medium | In-memory sessions are per-process and never cleaned up |
| KI-013 | Medium | Models are loaded twice at import; startup is slow and fragile |
| KI-014 | Medium | Broken import in `test_liveness_service.py` |
| KI-015 | Medium | Missing fixtures and model assets |
| KI-016 | Medium | Registration and client paths/IDs are hardcoded |
| KI-017 | Medium | Logs contain personal data and use `print()` |
| KI-018 | Medium | No CI or verified branch protection |
| KI-019 | Low | Dead/duplicate code paths and scripts |
| KI-020 | High | Anti-spoofing effectiveness is unmeasured |

## Details

### KI-001 — Empty dependency manifest

- **Evidence:** `requirements.txt` is 0 bytes.
- **Impact:** A fresh clone cannot install the application. Setup instructions cannot be verified.
- **Proposed fix:** Define a reviewed, pinned manifest compatible with a documented Python version; test installation in a clean environment.
- **Status:** Open; Phase 1 blocker.

### KI-002 — Hardcoded Windows model path

- **Evidence:** `app/services/liveness.py:13-16` sets an absolute `C:\...` path.
- **Impact:** Import fails on macOS/Linux and on any machine without that exact Windows layout.
- **Proposed fix:** Read a portable path from configuration, validate existence, and document model provisioning.
- **Status:** Open; Phase 1 blocker.

### KI-003 — Database schema is never initialized

- **Evidence:** `initialize_database()` is defined at `app/database/attendance_db.py:40` and has no call sites outside its definition.
- **Impact:** A fresh database lacks the `attendance` table; insert/query calls can fail with `no such table: attendance`.
- **Proposed fix:** Initialize on application startup (lifespan) and in test setup; add a fresh-database test.
- **Status:** Open; Phase 1 blocker.

### KI-004 — No authentication or authorization

- **Evidence:** All routes are unauthenticated; there is no auth dependency, token handling, or user model.
- **Impact:** Anyone who can reach the API can mark attendance, read all records, or probe biometric services. CORS does not prevent non-browser access.
- **Proposed fix:** Add authentication, role-based authorization, and audited access controls. This is required before any real deployment.
- **Status:** Open; security blocker.

### KI-005 — Unvalidated `student_id` in filesystem path

- **Evidence:** `app/services/face_recognition.py:459-475` builds `data/face_embeddings/<student_id>.npy` directly from request/form data.
- **Impact:** Path separators, `..`, or an absolute path in `student_id` may escape the intended directory.
- **Proposed fix:** Validate against a strict identifier pattern and verify the resolved path remains under the embeddings directory; add adversarial tests.
- **Status:** Open; security fix required.

### KI-006 — Liveness sessions are replayable and exposed in query strings

- **Evidence:** `session_id` is a UUID stored in a module-level dictionary; `/liveness/frame` accepts it as a query parameter; `/attendance/verify` trusts that a verified session exists. Sessions are not bound to a student or client.
- **Impact:** A captured session or final image can be replayed within the 30-second window. Session IDs may appear in logs.
- **Proposed fix:** Bind sessions to an authenticated user/student and device context, use headers/body instead of query strings, and add one-time, cryptographic challenge binding.
- **Status:** Open.

### KI-007 — Missing input and upload validation

- **Evidence:** `student_id`, `subject`, and `lecture_id` are plain `Form(...)` strings; images are read without size/content validation; no enrollment/subject authorization checks exist.
- **Impact:** Oversized uploads, malformed images, arbitrary identifiers, and attendance for unrelated subjects/lectures are possible.
- **Proposed fix:** Add length/pattern validation, size/type limits, and enrollment/subject checks; return structured errors.
- **Status:** Open.

### KI-008 — No automated tests

- **Evidence:** `test_*.py` files execute top-level code, open cameras, use `exit()`, and require absent fixtures. No pytest configuration or CI workflow exists.
- **Impact:** Regressions cannot be detected automatically. Pytest collection may execute dangerous/manual code.
- **Proposed fix:** Add unit/API/database tests with mocked models and temporary storage; keep model/camera checks separate and opt-in.
- **Status:** Open; Phase 2 priority.

### KI-009 — No configuration system

- **Evidence:** `app/core/config.py` is empty; no `os.environ`, `getenv`, or dotenv usage exists.
- **Impact:** Paths, thresholds, origins, and storage locations cannot be changed without editing source. `.env` files are ignored but not loaded.
- **Proposed fix:** Add validated configuration with safe defaults and documented environment variables; do not add secrets to the repository.
- **Status:** Open; Phase 1.

### KI-010 — Internal error messages returned to clients

- **Evidence:** `app/api/routes.py:254-268` returns `str(error)` in the response. Retrieval endpoints do not catch `sqlite3` errors.
- **Impact:** Paths, model errors, and database details may be disclosed; unhandled errors can produce HTTP 500.
- **Proposed fix:** Log details server-side with redaction; return stable, non-sensitive error codes/messages.
- **Status:** Open.

### KI-011 — No retention, deletion, encryption, or backup policy

- **Evidence:** Embeddings and SQLite records are stored unencrypted; no deletion/retention code or documentation exists.
- **Impact:** Biometric and attendance data may persist indefinitely and be exposed through filesystem access or backups.
- **Proposed fix:** Define retention and deletion workflows, protect storage, restrict access, and document backup handling. Obtain privacy review.
- **Status:** Open.

### KI-012 — Per-process, unbounded in-memory sessions

- **Evidence:** `sessions = {}` at `app/api/liveness_routes.py:19`; abandoned sessions are never removed; no shared store or lock.
- **Impact:** Memory growth; behavior differs with multiple workers/restarts; no cross-process verification.
- **Proposed fix:** Add expiry cleanup and, if scaling, a shared store with lifecycle management.
- **Status:** Open.

### KI-013 — Duplicate model loading at import

- **Evidence:** `app/api/liveness_routes.py:12` creates one `LivenessService`; `app/services/attendance_verification.py:11` creates another inside `AttendanceVerificationService`; `app/api/routes.py:22` instantiates that service at import.
- **Impact:** Two MediaPipe detectors and one InsightFace model load before serving; slow startup, higher memory use, and import-time failure.
- **Proposed fix:** Create shared services once in a lifespan/application state and inject dependencies.
- **Status:** Open.

### KI-014 — Broken test import

- **Evidence:** `test_liveness_service.py:3` imports `from liveness import LivenessService`; the module lives at `app.services.liveness`.
- **Impact:** The root script fails immediately.
- **Proposed fix:** Correct the import or retire the duplicate script as part of the test refactor.
- **Status:** Open.

### KI-015 — Missing fixtures and model assets

- **Evidence:** Scripts reference `tests/fixtures/test.jpg`, `closed_eye.jpeg`, `test.jpg`, `blaze_face_short_range.tflite`, and `face_landmarker.task`; none are present. Images/models are ignored by Git.
- **Impact:** Manual tests cannot run from a clean checkout.
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

- **Evidence:** No workflow files exist in the repository. Branch protection/required reviews were not verified.
- **Impact:** Checks and review requirements depend on individual discipline.
- **Proposed fix:** Add CI for syntax/tests/secret scanning and configure branch protection with explicit maintainer approval.
- **Status:** Open.

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
