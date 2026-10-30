# Project Specification

## Purpose

Attendance.Application is an AI-assisted attendance verification backend. It verifies a student's identity from a camera image, checks that the interaction includes a blink, applies basic image-quality screening, and records verified attendance in SQLite.

The project is an academic/experimental system. It is not a production attendance platform and does not currently provide authentication, authorization, a user interface, or a certified presentation-attack detection system.

## Scope

### In scope for the current baseline

- Liveness sessions and webcam-frame processing.
- Face landmark detection and blink detection.
- Basic image-quality screening.
- Face embedding extraction and similarity comparison.
- Attendance verification decisions.
- SQLite attendance records and duplicate prevention.
- Attendance retrieval by student and for all records.
- Manual scripts for registration, recognition, liveness, and API testing.

### Explicitly out of scope for the current baseline

- Student, faculty, or administrator accounts.
- Authentication, authorization, and role-based access.
- A web or mobile client.
- Attendance reports, dashboards, or analytics.
- Production deployment, monitoring, and ERP integration.
- A trained or certified face presentation-attack detection model.
- Guaranteed recognition accuracy or performance.

## Users

| User | Current reality | Intended future role |
| --- | --- | --- |
| Student | No account or UI. A manual client can submit a face image and student ID. | Verify their own attendance through a client. |
| Faculty/administrator | No account or UI. | Manage lectures and review attendance. |
| Developer/researcher | Runs the API and manual scripts locally. | Maintain and extend the system. |

There is no user model or identity provider in the current code. The `student_id` is supplied by the client and is not authenticated.

## Functional requirements

Status labels:

- **Implemented** — a code path exists. Runtime behavior may still be unverified.
- **Partially implemented** — some pieces exist but the requirement is incomplete or constrained.
- **Unverified** — code exists but could not be exercised in the current environment.
- **Planned** — not implemented.

| ID | Requirement | Status | Evidence / notes |
| --- | --- | --- | --- |
| FR-01 | Create a liveness session | Implemented (runtime unverified) | `POST /liveness/start`; in-memory UUID session in `app/api/liveness_routes.py`. |
| FR-02 | Process webcam frames for a session | Implemented (runtime unverified) | `POST /liveness/frame`; multipart image plus `session_id` query parameter. |
| FR-03 | Detect a face and facial landmarks | Implemented (runtime unverified) | MediaPipe Face Landmarker in `app/services/liveness.py`; requires a model file. |
| FR-04 | Detect a blink | Implemented (runtime unverified) | Eye Aspect Ratio with `CLOSED_THRESHOLD = 0.10` and `REQUIRED_CLOSED_FRAMES = 4`. |
| FR-05 | Apply image-quality screening | Partially implemented | Face-size, brightness, and Laplacian-variance checks in `anti_spoofing.py`. No trained PAD model. |
| FR-06 | Prevent simple static-image attacks | Partially implemented | Blink interaction plus heuristic screening. Not a certified or robust defense. |
| FR-07 | Extract a face embedding | Implemented (runtime unverified) | InsightFace `buffalo_l` in `face_recognition.py`. |
| FR-08 | Compare embeddings | Implemented (runtime unverified) | Cosine similarity with a configurable threshold (default `0.40`). |
| FR-09 | Verify attendance from liveness + face match | Implemented (runtime unverified) | `POST /attendance/verify`; rejects unless liveness session and face match are valid. |
| FR-10 | Persist attendance in SQLite | Implemented (startup and persistence verified without models) | Startup creates the schema idempotently; inserts, retrieval, and duplicate rejection are covered by focused tests. End-to-end API verification with real models is still outstanding. |
| FR-11 | Prevent duplicate attendance | Implemented (runtime unverified) | `UNIQUE (student_id, lecture_id, attendance_date)` plus `sqlite3.IntegrityError` handling. |
| FR-12 | Retrieve attendance | Implemented (runtime unverified) | `GET /attendance/student/{student_id}` and `GET /attendance/all`. |
| FR-13 | Expire and consume liveness sessions | Implemented (runtime unverified) | Configurable validity (default 30 seconds); session removed after rejection, success, or expiry. |
| FR-14 | Register a student's face | Partially implemented | `app/services/register_face.py` is a manual script with hardcoded `STU001`, `test.jpg`, and a relative output path. Not exposed through the API. |
| FR-15 | Authenticate users | Planned | No authentication code or dependency exists. |
| FR-16 | Authorize attendance access | Planned | Retrieval endpoints are open to any caller. |
| FR-17 | Provide a web client | Planned | The only client is `test_api_attendance.py`. |
| FR-18 | Automated test suite | Planned | Files named `test_*.py` are manual scripts, not pytest tests. |
| FR-19 | Reports and dashboards | Planned | No reporting endpoints or UI. |
| FR-20 | Database migrations | Planned | No migration tooling or versioned schema. |

## Non-functional requirements

| Area | Current state |
| --- | --- |
| Security | No authentication or authorization. Heuristic anti-spoofing only. Error messages may disclose internals. |
| Privacy | Face embeddings and attendance databases are local and gitignored. No retention/deletion policy or consent workflow. |
| Portability | Startup verified on macOS arm64. The MediaPipe path, embedding directory, database path, CORS origins, and InsightFace cache are configurable. Windows/Linux are unverified. |
| Reproducibility | Runtime and development dependencies are pinned; a clean Python 3.11.16 virtual environment installed successfully. |
| Persistence | A fresh configured database is initialized at startup; restart preserves rows; duplicate insertion is rejected. |
| Performance | Unverified. Models load once during lifespan startup; SQLite calls are synchronous inside async routes. |
| Accuracy | Unverified. No benchmark, dataset, false-accept/false-reject measurements, or calibration. |
| Observability | `print()` statements only; no structured logging, metrics, or tracing. |
| Reliability | In-memory sessions are single-process only; no retry, timeout, or concurrency handling. |
| Maintainability | Shared lifespan-managed services and focused runtime tests exist; manual camera scripts and the missing CI/test baseline remain. |

## Constraints and assumptions

- A camera is required for the intended liveness flow.
- MediaPipe and InsightFace model assets are required at runtime and are not committed.
- Each student must have a registered embedding under `data/face_embeddings/<student_id>.npy`.
- The current deployment model is a single local FastAPI process with SQLite.
- Liveness frames and the final attendance image are separate HTTP requests; the final image is not tied cryptographically to the liveness frames.

## Acceptance criteria for a future stable baseline

A future runtime-stabilization milestone should demonstrate:

1. A fresh clone can install dependencies from the repository manifest.
2. The documented startup command works without Windows-specific paths.
3. A fresh database is initialized automatically and duplicate protection is verified.
4. The liveness and attendance flows can be exercised with documented, consented test assets.
5. The README and setup documents match the verified behavior.

These are proposed criteria, not current claims.
