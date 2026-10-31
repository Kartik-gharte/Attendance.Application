# Project Status

**As of:** 2026-10-31

## Repository state

| Item | State |
| --- | --- |
| Foundation PR | #1 merged into `main` at `885cf7b` |
| Runtime bootstrap | Merged via PR #17 at `323db2f` |
| Remote branches | `main` plus active topic branches until their PRs merge |
| Local backups | `refs/backup/feature-ai-attendance-security`, `refs/backup/feature-attendance-verification-stable`, `refs/backup/main-before-attendance-merge-2026-10-26`, `refs/backup/main-initial` |
| Open stabilization backlog | [#13](https://github.com/Kartik-gharte/Attendance.Application/issues/13) |
| CI | No workflow exists in the repository; branch protection has not been verified |
| Test suite | 32 focused runtime tests exist under `tests/runtime/`; the broader pytest suite is still tracked in [#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7) |

## Status legend

- **Implemented** — code exists and was inspected.
- **Verified** — executed successfully in a recorded run.
- **Unverified** — code exists, but runtime behavior was not executed in this task.
- **Partial** — some required behavior is missing.
- **Not implemented** — no code exists.
- **Blocked** — cannot run until another issue is fixed.

## Component status

| Area | Status | Evidence / notes |
| --- | --- | --- |
| Application shell | Implemented, verified | `create_app()` with lifespan in `app/main.py`; startup completed on macOS arm64. |
| Dependency manifest | Implemented, verified | `requirements.txt` pinned; clean venv install succeeded with Python 3.11.16. |
| Configuration | Implemented, verified | `app/core/config.py` with `pydantic-settings`; environment and `.env` overrides tested. |
| Model startup | Implemented, verified | One MediaPipe and one InsightFace instance created in the lifespan; missing MediaPipe model fails startup with an actionable error. |
| Liveness start/frame API | Implemented, unverified | `POST /liveness/start`, `POST /liveness/frame`; in-memory sessions. |
| Blink liveness | Implemented, unverified | MediaPipe landmarks + EAR threshold; accuracy untested. |
| Anti-spoofing screening | Implemented, unverified | Heuristic size/brightness/sharpness checks; not a trained PAD model. |
| Face embedding/recognition | Implemented, unverified | InsightFace `buffalo_l`, cosine similarity, configurable threshold; accuracy untested. |
| Attendance verification API | Implemented, partially verified | `POST /attendance/verify`; success, duplicate, validation, upload-limit, and retrieval-error paths tested with a temporary database and fake model services. Real model flow unverified. |
| Attendance retrieval API | Implemented, verified without models | `GET /attendance/student/{student_id}` and `GET /attendance/all` return empty lists on a fresh initialized database; no auth. |
| SQLite schema | Implemented, verified | `initialize_database()` runs in the lifespan for `ATTENDANCE_DB_PATH`, creates the table idempotently, and preserves rows across restart. Tests cover fresh creation, retrieval, and duplicate rejection. |
| Enrollment/registration | Partial | Manual scripts with hardcoded `STU001`, `test.jpg`, and output paths. No API. |
| Startup resilience | Implemented, verified | Importing `app.main` does not touch models or the database; schema initialization and missing MediaPipe assets fail lifespan startup explicitly. |
| Automated tests | Partial | Focused settings, startup, database, API, and validation runtime tests pass (32 tests); manual camera scripts remain unsafe for pytest collection; broader pytest suite is still open. |
| Syntax check | Verified | `python -m compileall -q app tests` passed. |
| Lint/type checks | Not configured | No verified tool configuration exists. |
| CI | Not implemented | No workflow files; checks are manual. |
| Authentication/authorization | Not implemented | Every endpoint is open. |
| Privacy controls | Partial | Git ignores biometric artifacts; no retention/deletion/consent implementation. |
| Deployment | Not implemented | No container, service, or deployment documentation. |
| Project documentation | In progress | Runtime, database, configuration, API, security, and validation docs updated on `fix/input-validation`. |

## What was actually verified

On macOS 27.0.1 arm64 with Python 3.11.16:

1. Clean virtual environment installed all runtime dependencies from `requirements.txt`.
2. `python -m pytest tests/runtime -q` passed (32 tests), including focused validation, upload-limit, and retrieval-error coverage.
3. `python -m uvicorn app.main:app` reached "Application startup complete".
4. `GET /` and `GET /docs` returned `200`.
5. A temporary configured database was created with the `attendance` table during startup; restart preserved an inserted row.
6. The attendance API returned an empty list on a fresh database, inserted a record, and mapped a repeated insert to the duplicate response using fake model services.
7. Startup logs showed schema initialization before MediaPipe and InsightFace loading once each.
8. Starting with `MEDIAPIPE_FACE_LANDMARKER_MODEL` pointed at a missing file failed startup with a `RuntimeError` naming that setting.
9. `python -m compileall -q app tests` passed.

## What was not verified

- Startup on Windows, Linux, or any Python version other than 3.11.16.
- Any liveness, anti-spoofing, or face-matching flow with real model assets and data.
- Face-recognition accuracy, false-accept/false-reject rates, or anti-spoofing effectiveness.
- Webcam client behavior.
- Deployment, load, or security testing.

## Current blockers

1. Authentication/authorization is missing ([#4](https://github.com/Kartik-gharte/Attendance.Application/issues/4)).
2. Automated tests and CI are incomplete ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).
3. No liveness, face-recognition, or anti-spoofing accuracy has been measured.

## Definition of a working next milestone

Phase 1 is complete when all of the following are true and documented:

1. A fresh environment installs dependencies from a reviewed manifest. **Done.**
2. The application starts using portable model paths. **Done on the verified platform.**
3. A fresh database schema is created automatically. **Done.**
4. `/` and `/docs` respond. **Done.**
5. A consented test flow completes liveness, face verification, and attendance storage with real model assets; duplicate handling is verified at the database and API layers with fake model services. **Outstanding.**
