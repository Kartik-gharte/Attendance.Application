# Project Specification

## Purpose

Attendance.Application is an AI-assisted attendance verification backend. It verifies a student's identity from a camera image, checks that the interaction includes a blink, applies basic image-quality screening, and records verified attendance in SQLite.

The project is an academic/experimental system. It is not a production attendance platform. It provides a local-account authentication and role-based authorization baseline, but not institutional identity, a user interface, or a certified presentation-attack detection system.

## Scope

### In scope for the current baseline

- Liveness sessions and webcam-frame processing.
- Face landmark detection and blink detection.
- Basic image-quality screening.
- Face embedding extraction and similarity comparison.
- Attendance verification decisions.
- SQLite attendance records and duplicate prevention.
- Attendance retrieval by student and for all records.
- Local student/admin accounts, opaque bearer tokens, and role-based access.
- Administrator-only enrollment through the API and the CLI, with an audit trail.
- Versioned schema migrations.
- Encrypted backup and restore, retention, and generated backup schedules.
- Structured, redacted logging; health, readiness, and metrics endpoints.
- Manual scripts for registration, recognition, liveness, and API testing.

### Explicitly out of scope for the current baseline

- Institutional SSO, MFA, self-service registration, and password recovery.
- Rate limiting and account lockout.
- Comprehensive attendance audit logging.
- A web or mobile client.
- Attendance reports, dashboards, or analytics.
- Production deployment, tracing, alerting, and ERP integration.
- A trained or certified face presentation-attack detection model.
- Guaranteed recognition accuracy or performance.

## Users

| User | Current reality | Intended future role |
| --- | --- | --- |
| Student | Local account linked to one `student_id`; can start liveness sessions and mark/read only their own attendance. No UI. | Verify their own attendance through a client. |
| Faculty/administrator | Local admin account; can read any student's attendance and all records, and can enroll students and read the enrollment audit trail, but cannot mark attendance. No UI. | Manage lectures and review attendance; finer-grained faculty scoping is future work. |
| Developer/researcher | Provisions accounts with the CLI, runs the API, and maintains manual scripts locally. | Maintain and extend the system. |

Accounts are stored locally in SQLite. There is no public signup or institutional identity provider. The authenticated student's account determines which `student_id` can be marked and read.

## Functional requirements

Status labels:

- **Implemented** — a code path exists. Runtime behavior may still be unverified.
- **Partially implemented** — some pieces exist but the requirement is incomplete or constrained.
- **Unverified** — code exists but could not be exercised in the current environment.
- **Planned** — not implemented.

| ID | Requirement | Status | Evidence / notes |
| --- | --- | --- | --- |
| FR-01 | Create a liveness session | Implemented | `POST /liveness/start`; in-memory UUID session bound to the authenticated user in `app/api/liveness_routes.py`. |
| FR-02 | Process webcam frames for a session | Implemented | `POST /liveness/frame`; multipart image plus `session_id` query parameter. Covered by runtime tests and the real-model rejection path. |
| FR-03 | Detect a face and facial landmarks | Implemented | MediaPipe Face Landmarker in `app/services/liveness.py`; the provisioned model is exercised by the real-model pipeline test. |
| FR-04 | Detect a blink | Implemented | Eye Aspect Ratio with `CLOSED_THRESHOLD = 0.10` and `REQUIRED_CLOSED_FRAMES = 4`; covered by runtime tests. |
| FR-05 | Apply image-quality screening | Partially implemented | Face-size, brightness, and Laplacian-variance checks in `anti_spoofing.py`. No trained PAD model. |
| FR-06 | Prevent simple static-image attacks | Partially implemented | Blink interaction plus heuristic screening. Not a certified or robust defense. |
| FR-07 | Extract a face embedding | Implemented | InsightFace `buffalo_l` in `face_recognition.py`; the provisioned model is exercised by the real-model pipeline test. |
| FR-08 | Compare embeddings | Implemented | Cosine similarity with a configurable threshold (default `0.40`); covered by runtime tests. |
| FR-09 | Verify attendance from liveness + face match | Implemented | `POST /attendance/verify`; rejects unless the liveness session and face match are valid. The rejection path is verified with real models; the acceptance path needs a consented face. |
| FR-10 | Persist attendance in SQLite | Implemented | Versioned migrations create the schema; inserts, retrieval, duplicate rejection, and restart persistence are covered by tests. |
| FR-11 | Prevent duplicate attendance | Implemented | `UNIQUE (student_id, lecture_id, attendance_date)` plus `sqlite3.IntegrityError` handling; covered by tests. |
| FR-12 | Retrieve attendance | Implemented | `GET /attendance/student/{student_id}` and `GET /attendance/all`, with role and ownership checks. |
| FR-13 | Expire and consume liveness sessions | Implemented | Configurable validity (default 30 seconds); session removed after rejection, success, or expiry. |
| FR-14 | Register a student's face | Implemented | Shared enrollment service with `python -m app.services.register_face` and administrator-only `POST /admin/enrollments`; validated identifiers, overwrite protection, atomic writes, and an audit trail. |
| FR-15 | Authenticate users | Implemented (verified with temporary storage and fake services) | Local accounts with Argon2id password hashes and opaque bearer tokens in `app/auth/`; CLI provisioning. Real deployment, TLS, and identity-provider integration remain unverified. |
| FR-16 | Authorize attendance access | Implemented (verified with temporary storage and fake services) | Students can mark/read only their own attendance; admins can read all records and manage enrollment but cannot mark attendance. Liveness sessions are bound to the authenticated user. |
| FR-17 | Provide a web client | Planned | The only client is the manual `manual/api_attendance.py`; it reads its student, subject, and lecture from arguments or environment variables. There is no web UI. |
| FR-18 | Automated test suite | Implemented | 324 runtime tests run in CI on every pull request, covering settings, startup, database, API, authentication, authorization, migrations, backup and restore, scheduling, enrollment, metrics, and the evaluation and benchmark harnesses. |
| FR-19 | Reports and dashboards | Planned | No reporting endpoints or UI. |
| FR-20 | Database migrations | Implemented | Versioned, transactional migrations with rollback on failure and a readiness check on the schema version. Downgrade is not implemented. |

## Non-functional requirements

| Area | Current state |
| --- | --- |
| Security | Local-account authentication, opaque bearer tokens, role-based authorization, administrator-only enrollment, and redacted logging are implemented. Heuristic anti-spoofing only. TLS, rate limiting, MFA, account lockout, and comprehensive attendance audit logging are not implemented. |
| Privacy | Face embeddings, account data, and attendance databases are local and gitignored. Attendance and enrollment-audit retention, encrypted backups, and a consent reference are implemented; live biometric storage is unencrypted and there is no consent workflow. |
| Portability | Startup verified on macOS arm64. The MediaPipe path, embedding directory, database path, CORS origins, and InsightFace cache are configurable. Windows/Linux are unverified. |
| Reproducibility | Runtime and development dependencies are pinned; a clean Python 3.11.16 virtual environment installed successfully. |
| Persistence | A fresh configured database is initialized through versioned migrations at startup; restart preserves rows; duplicate insertion is rejected. |
| Performance | A measured baseline exists for the current environment; load testing with real faces has not been performed. Models load once during lifespan startup; SQLite calls are synchronous inside async routes. |
| Accuracy | Unverified. No consented dataset, false-accept/false-reject measurements, or calibration; the evaluation harness is implemented. |
| Observability | Structured, leveled, redacted logging plus health, readiness, and Prometheus metrics endpoints. No tracing or alerting. |
| Reliability | In-memory sessions are single-process only; expired and consumed sessions are removed, but abandoned sessions are not swept in the background. No retry, timeout, or concurrency handling. |
| Maintainability | Shared lifespan-managed services, 324 runtime tests, and CI on every pull request; manual camera scripts remain. |

## Constraints and assumptions

- A camera is required for the intended liveness flow.
- MediaPipe and InsightFace model assets are required at runtime and are not committed.
- Each student must have a registered embedding under `data/face_embeddings/<student_id>.npy`.
- Each student and admin must have a locally provisioned account. There is no public signup.
- The current deployment model is a single local FastAPI process with SQLite.
- Bearer tokens and passwords must be transported over TLS; the application does not terminate or enforce TLS itself.
- Liveness frames and the final attendance image are separate HTTP requests; the final image is not tied cryptographically to the liveness frames.

## Acceptance criteria for a future stable baseline

A future runtime-stabilization milestone should demonstrate:

1. A fresh clone can install dependencies from the repository manifest.
2. The documented startup command works without Windows-specific paths.
3. A fresh database is initialized automatically and duplicate protection is verified.
4. The liveness and attendance flows can be exercised with documented, consented test assets.
5. The README and setup documents match the verified behavior.

These are proposed criteria, not current claims.
