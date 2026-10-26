# Project Status

**As of:** 2026-10-27

## Repository state

| Item | State |
| --- | --- |
| Foundation branch | `chore/project-foundation` (prepared from `main` at `79373d6`) |
| Remote branches | `main` only after cleanup; temporary PR branches are deleted after merge |
| Local backups | `refs/backup/feature-ai-attendance-security`, `refs/backup/feature-attendance-verification-stable`, `refs/backup/main-before-attendance-merge-2026-10-26`, `refs/backup/main-initial` |
| Foundation changes | Drafted; documentation checks passed; merge state is in Git history |
| CI | No workflow exists in the repository; branch protection has not been verified |
| Test suite | Manual scripts only; no pytest suite |

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
| Application shell | Implemented, unverified | FastAPI app with CORS and two routers in `app/main.py`. Import requires model assets. |
| Liveness start/frame API | Implemented, unverified | `POST /liveness/start`, `POST /liveness/frame`; in-memory sessions. |
| Blink liveness | Implemented, unverified | MediaPipe landmarks + EAR threshold; accuracy untested. |
| Anti-spoofing screening | Implemented, unverified | Heuristic size/brightness/sharpness checks; not a trained PAD model. |
| Face embedding/recognition | Implemented, unverified | InsightFace `buffalo_l`, cosine similarity, threshold `0.40`; accuracy untested. |
| Attendance verification API | Implemented, unverified | `POST /attendance/verify`; consumes liveness session and writes attendance. |
| Attendance retrieval API | Implemented, unverified | `GET /attendance/student/{student_id}`, `GET /attendance/all`; no auth. |
| SQLite schema | Implemented, unverified | Table and constraints exist; `initialize_database()` is not called, so a fresh database is not initialized. |
| Enrollment/registration | Partial | Manual scripts with hardcoded `STU001`, `test.jpg`, and output paths. No API. |
| Dependency manifest | Missing | `requirements.txt` is empty. |
| Configuration | Missing | `app/core/config.py` is empty; no environment variables are read. |
| Startup resilience | Blocked | Hardcoded model path and missing assets prevent portable startup. |
| Automated tests | Not implemented | `test_*.py` files are manual scripts; collection is unsafe. |
| Syntax check | Verified | `python -m compileall` passed for `app`, `tests`, and the two top-level test scripts. |
| Lint/type checks | Not configured | No verified tool configuration exists. |
| CI | Not implemented | No workflow files; checks are manual. |
| Authentication/authorization | Not implemented | Every endpoint is open. |
| Privacy controls | Partial | Git ignores biometric artifacts; no retention/deletion/consent implementation. |
| Deployment | Not implemented | No container, service, or deployment documentation. |
| Project documentation | In progress | Foundation documentation drafted on this branch; not yet reviewed/merged. |

## What was actually verified

1. Local branch and commit relationships.
2. Only `main` remains on the remote after authorized cleanup.
3. Source inspection of routes, services, database, scripts, and configuration.
4. Syntax compilation with `python -m compileall` (no imports executed).
5. Repository hygiene checks recorded in the foundation plan.

## What was not verified

- Application startup or import with real dependencies.
- Any liveness, anti-spoofing, face-matching, or attendance endpoint.
- Face-recognition accuracy, false-accept/false-reject rates, or anti-spoofing effectiveness.
- Database creation, inserts, duplicate handling, or retrieval at runtime.
- Webcam client behavior.
- Python/dependency compatibility.
- Deployment, load, or security testing.

## Current blockers

1. Empty dependency manifest and missing configuration.
2. Hardcoded Windows MediaPipe model path.
3. Missing model/embedding assets in the checkout.
4. Database initialization is not wired into startup.
5. No automation to prevent regressions.

## Definition of a working next milestone

Phase 1 is complete when all of the following are true and documented:

1. A fresh environment installs dependencies from a reviewed manifest.
2. The application starts using portable model paths.
3. A fresh database schema is created automatically.
4. `/` and `/docs` respond.
5. A consented test flow completes liveness, face verification, and attendance storage, with duplicate handling verified.
