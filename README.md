<p align="center">
  <img src="assets/readme/hero.svg" width="100%" alt="Attendance.Application: one camera pass for liveness, face matching, and a duplicate-safe attendance record.">
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> ·
  <a href="#how-verification-works">How it works</a> ·
  <a href="#api-surface">API</a> ·
  <a href="#status">Status</a> ·
  <a href="#setup-status">Setup</a> ·
  <a href="#documentation">Docs</a>
</p>

> [!WARNING]
> **Active development — not production-ready.** Runtime bootstrap (pinned dependencies, configuration, portable model paths, lifespan-managed services, and SQLite schema initialization) is implemented and was verified on macOS arm64 with Python 3.11. Input validation, upload limits, stable error responses, local-account authentication, bearer tokens, and role-based attendance authorization are implemented. TLS, rate limiting, MFA/SSO, audit logging, and the automated test/CI baseline are still open. Track stabilization in [#13](https://github.com/Kartik-gharte/Attendance.Application/issues/13).

## What it does

Attendance.Application is a camera-based attendance verification backend built with FastAPI. It combines blink-based liveness, heuristic frame screening, InsightFace matching, and SQLite persistence.

The intended flow is narrow: establish presence, match identity, and write one attendance record. There is no web UI; the current client is a manual Python/OpenCV script.

- **Presence** — a face must produce a blink while basic image-quality screening passes. Both checks are heuristic, not certified presentation-attack detection.
- **Identity** — an InsightFace `buffalo_l` embedding is compared with the registered student embedding using cosine similarity at a configurable threshold (default `0.40`).
- **Record** — a match is inserted into SQLite with a `UNIQUE (student_id, lecture_id, attendance_date)` constraint. Attendance can be queried by student or across all records.

## How verification works

<p align="center">
  <img src="assets/readme/verification-flow.svg" width="100%" alt="Verification pipeline: start an in-memory liveness session, detect a blink and screen frame quality, match an InsightFace embedding at 0.40, then write a duplicate-protected SQLite record.">
</p>

1. **Authenticate** — `POST /auth/token` exchanges a locally provisioned username/password for an opaque bearer token. Tokens expire and can be revoked.
2. **Start a session** — `POST /liveness/start` creates an in-memory UUID session bound to the authenticated student.
3. **Prove liveness** — `POST /liveness/frame` checks for a face, a blink, and basic frame quality. A blink plus the screening must pass for liveness to be verified.
4. **Match identity** — `POST /attendance/verify` requires a liveness-verified session owned by the same student, no older than `LIVENESS_VALIDITY_SECONDS` (default 30 seconds), and a `student_id` matching the authenticated account. It extracts an InsightFace embedding and compares it with the registered student embedding.
5. **Write one record** — a match inserts into SQLite; a duplicate is rejected by the unique constraint. Success and face rejection both consume the session.

Liveness sessions are process-local: they disappear on restart and are not shared between workers. Students can mark and read only their own attendance; admins can read attendance but cannot mark it. The full response and failure behavior is documented in [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## API surface

| Method | Endpoint | Purpose | Auth |
| --- | --- | --- | --- |
| `GET` | `/` | Static service message; not a model/database readiness check | Public |
| `POST` | `/auth/token` | Exchange username/password for a bearer token | Public |
| `GET` | `/auth/me` | Return the current account | Bearer |
| `POST` | `/auth/logout` | Revoke the current token | Bearer |
| `POST` | `/liveness/start` | Create a user-bound liveness session | Bearer, student |
| `POST` | `/liveness/frame` | Submit a webcam frame for liveness processing | Bearer, student and session owner |
| `POST` | `/attendance/verify` | Verify liveness + face and attempt to mark attendance | Bearer, student; matching `student_id` |
| `GET` | `/attendance/student/{student_id}` | List a student's attendance records | Bearer, student self or admin |
| `GET` | `/attendance/all` | List all attendance records | Bearer, admin |

Accounts are provisioned locally with `python -m app.auth.cli`; there is no public signup. Unauthenticated protected requests return HTTP `401`; wrong-role or cross-student requests return `403`. Application-level validation errors usually return HTTP `200` with `status: "error"`; missing form fields return HTTP `422`. Interactive OpenAPI docs are available at `/docs` and `/redoc` only after startup succeeds.

## Stack

| Layer | Tools |
| --- | --- |
| API | FastAPI, Uvicorn, `python-multipart` |
| Configuration | `pydantic-settings`, `.env` |
| Auth | Local SQLite accounts, `argon2-cffi`, opaque bearer tokens |
| Vision | OpenCV, MediaPipe, InsightFace, ONNX Runtime |
| Numerics | NumPy |
| Persistence | SQLite (Python standard library) |
| Manual client | OpenCV webcam capture, `requests` |

Direct dependencies are pinned in [`requirements.txt`](requirements.txt); the verified platform is Python 3.11.16 on macOS arm64. See [Setup](docs/SETUP.md) for model provisioning and startup commands.

## Status

Runtime bootstrap, service wiring, SQLite schema initialization, and the local authentication/authorization baseline were verified locally; the camera-based flow and production security controls are not.

| Verified locally | Still missing or unverified |
| --- | --- |
| Pinned dependencies, validated settings, `.env` support | End-to-end liveness → face match → attendance flow |
| Startup, `GET /`, `GET /docs`, database initialization, missing-model failure | TLS, rate limiting, account lockout, MFA/SSO, audit logging |
| One MediaPipe and one InsightFace load per process | Retention/deletion ([#9](https://github.com/Kartik-gharte/Attendance.Application/issues/9)), broader service tests (#7) |
| Local login/logout, token expiry/revocation, student self-access, admin read-only access | Manual client camera run with authentication; hardcoded student/subject/lecture values ([#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10)) |
| CI compile, runtime-test, and gitleaks checks on PR #22 | Enforced branch protection; broader automated coverage (#7) |

No benchmarked face-recognition accuracy, liveness performance, or presentation-attack resistance results exist. Stabilization work is sequenced in the [tracking backlog](https://github.com/Kartik-gharte/Attendance.Application/issues/13).

## Setup status

Install and startup are verified on **Python 3.11.16 / macOS arm64** with the pinned manifest. Model assets are not committed and must be provisioned locally:

- MediaPipe `face_landmarker.task` must be downloaded or supplied via `MEDIAPIPE_FACE_LANDMARKER_MODEL`.
- InsightFace `buffalo_l` is downloaded on first startup or provisioned in `INSIGHTFACE_ROOT`.
- Registered embeddings are required for face matching and must never be committed.
- The FastAPI lifespan initializes the attendance, user, and token schemas for the configured database path and uses that path for attendance writes, retrieval, and authentication.
- Local accounts are provisioned with `python -m app.auth.cli`; there is no public signup.

Follow [docs/SETUP.md](docs/SETUP.md) for commands and [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for environment variables. CI is running; the next stabilization work is broader deterministic service coverage and manual-script isolation ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)). Local authentication and authorization are implemented, while TLS, rate limiting, and broader operational controls remain open. Manual script requirements are in [docs/TESTING.md](docs/TESTING.md).

## Repository map

```text
Attendance.Application/
├── app/
│   ├── api/              # liveness and attendance routes
│   ├── auth/             # accounts, tokens, dependencies, routes, CLI
│   ├── database/         # SQLite schema and queries
│   ├── services/         # liveness, screening, matching, manual scripts
│   └── main.py           # FastAPI entry point
├── assets/readme/        # README visuals (static SVG)
├── docs/                 # setup, architecture, API, security, status
├── tests/runtime/        # focused settings, startup, database, and API tests
├── tests/services/       # manual camera/model scripts
├── test_api_attendance.py
├── test_liveness_service.py
├── requirements.txt      # pinned runtime dependencies
└── README.md
```

## Security & privacy

> [!CAUTION]
> This is biometric software under active development. Do not use real student faces, embeddings, or attendance records in development or public repositories.

- The API uses local accounts and opaque bearer tokens. Students can mark/read only their own attendance; admins can read attendance. TLS, rate limiting, account lockout, MFA/SSO, and audit logging are not implemented, so do not treat this as a production authentication system.
- Liveness session IDs behave like short-lived bearer tokens within an authenticated student account and should not be logged.
- Anti-spoofing is heuristic blink and image-quality screening, not a trained or certified presentation-attack detection system.
- Liveness sessions live in process memory, are single-worker only, and expire after `LIVENESS_VALIDITY_SECONDS` (default 30 seconds).
- There is no biometric retention, deletion, or storage-protection policy yet; this is tracked in [#9](https://github.com/Kartik-gharte/Attendance.Application/issues/9).
- Face images, embeddings, model files, and local databases are excluded from Git. Never force-add them.

Read [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) before handling biometric data.

## Documentation

**Start here:** [Setup](docs/SETUP.md) · [Architecture](docs/ARCHITECTURE.md) · [API reference](docs/API_REFERENCE.md) · [Security & privacy](docs/SECURITY_AND_PRIVACY.md)

**Project state:** [Status](docs/PROJECT_STATUS.md) · [Known issues](docs/KNOWN_ISSUES.md) · [Roadmap](docs/ROADMAP.md) · [Full index](docs/README.md)

**Reference:** [Database](docs/DATABASE.md) · [Configuration](docs/CONFIGURATION.md) · [Testing](docs/TESTING.md) · [Decisions](docs/DECISIONS.md)

## Contributing

Start from a GitHub issue and a focused branch. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md). Prefer multiple small, coherent contributions (focused commits and, when practical, separate PRs) over one large change. Do not commit secrets, biometric data, model files, or local databases.

## Maintainer

Kartik Gharte — [Kartik-gharte](https://github.com/Kartik-gharte)

## License

No license file is present. The project is currently presented as an academic and experimental project. Do not assume permission to reuse it beyond applicable law or the repository owner's instructions.
