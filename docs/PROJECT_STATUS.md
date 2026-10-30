# Project Status

**As of:** 2026-10-30

## Repository state

| Item | State |
| --- | --- |
| Foundation PR | #1 merged into `main` at `885cf7b` |
| Runtime bootstrap | Implemented on `fix/runtime-bootstrap`; verified locally, not merged |
| Remote branches | `main` only after cleanup; temporary PR branches are deleted after merge |
| Local backups | `refs/backup/feature-ai-attendance-security`, `refs/backup/feature-attendance-verification-stable`, `refs/backup/main-before-attendance-merge-2026-10-26`, `refs/backup/main-initial` |
| Open stabilization backlog | [#13](https://github.com/Kartik-gharte/Attendance.Application/issues/13) |
| CI | No workflow exists in the repository; branch protection has not been verified |
| Test suite | Focused runtime tests exist under `tests/runtime/`; the broader pytest suite is still tracked in [#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7) |

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
| Attendance verification API | Implemented, unverified | `POST /attendance/verify`; consumes liveness session and writes attendance. |
| Attendance retrieval API | Implemented, unverified | `GET /attendance/student/{student_id}`, `GET /attendance/all`; no auth. |
| SQLite schema | Implemented, unverified | Path is configurable; `initialize_database()` is still not called, so a fresh database is not initialized. Tracked in [#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3). |
| Enrollment/registration | Partial | Manual scripts with hardcoded `STU001`, `test.jpg`, and output paths. No API. |
| Startup resilience | Implemented, verified | Importing `app.main` does not load models; missing MediaPipe assets fail lifespan startup. |
| Automated tests | Partial | Focused settings/startup tests pass; manual camera scripts remain unsafe for pytest collection. |
| Syntax check | Verified | `python -m compileall -q app tests` passed. |
| Lint/type checks | Not configured | No verified tool configuration exists. |
| CI | Not implemented | No workflow files; checks are manual. |
| Authentication/authorization | Not implemented | Every endpoint is open. |
| Privacy controls | Partial | Git ignores biometric artifacts; no retention/deletion/consent implementation. |
| Deployment | Not implemented | No container, service, or deployment documentation. |
| Project documentation | In progress | Runtime docs updated on `fix/runtime-bootstrap`. |

## What was actually verified

On macOS 27.0.1 arm64 with Python 3.11.16:

1. Clean virtual environment installed all runtime dependencies from `requirements.txt`.
2. `python -m pytest tests/runtime -q` passed (8 tests).
3. `python -m uvicorn app.main:app` reached "Application startup complete".
4. `GET /` returned `200` with the service message.
5. `GET /docs` returned `200`.
6. Startup logs showed MediaPipe and InsightFace loading once each.
7. Starting with `MEDIAPIPE_FACE_LANDMARKER_MODEL` pointed at a missing file failed startup with a `RuntimeError` naming that setting.
8. `python -m compileall -q app tests` passed.

## What was not verified

- Startup on Windows, Linux, or any Python version other than 3.11.16.
- Automatic creation of the `attendance` table.
- Any liveness, anti-spoofing, face-matching, or attendance endpoint with real data.
- Face-recognition accuracy, false-accept/false-reject rates, or anti-spoofing effectiveness.
- Duplicate handling or retrieval at runtime.
- Webcam client behavior.
- Deployment, load, or security testing.

## Current blockers

1. Database schema initialization is not wired into startup ([#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3)).
2. Input validation, upload limits, and error sanitization are missing ([#5](https://github.com/Kartik-gharte/Attendance.Application/issues/5)).
3. Authentication/authorization is missing ([#4](https://github.com/Kartik-gharte/Attendance.Application/issues/4)).
4. Automated tests and CI are incomplete ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).
5. No liveness, face-recognition, or anti-spoofing accuracy has been measured.

## Definition of a working next milestone

Phase 1 is complete when all of the following are true and documented:

1. A fresh environment installs dependencies from a reviewed manifest. **Done.**
2. The application starts using portable model paths. **Done on the verified platform.**
3. A fresh database schema is created automatically. **Outstanding ([#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3)).**
4. `/` and `/docs` respond. **Done.**
5. A consented test flow completes liveness, face verification, and attendance storage, with duplicate handling verified. **Outstanding.**
