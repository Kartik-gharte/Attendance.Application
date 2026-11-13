# Project Status

**As of:** 2026-11-13

## Repository state

| Item | State |
| --- | --- |
| Foundation PR | #1 merged into `main` at `885cf7b` |
| Runtime bootstrap | Merged via PR #17 at `323db2f` |
| Validation and security hardening | Merged via PR #18 at `ae8d8d3` |
| AI attendance verification | Merged via PR #19 at `30da359` |
| Authentication and authorization | Merged via PR #20 at `4421334` |
| Test suite and CI | Merged via PR #24 |
| Biometric retention | Merged via PR #25 |
| Liveness session hardening | Merged via PR #26 |
| Parameterized enrollment | Merged via PRs #27 and #30 |
| Structured logging | Merged via PR #29 |
| Schema migrations | Merged via PR #31 |
| Backup and restore | Merged via PR #32 |
| Health and readiness endpoints | Merged via PR #33 |
| Deployment baseline and runbook | Merged via PR #34 |
| Evaluation harness | Merged via PR #35 |
| Backup retention policy | Merged via PR #37 |
| Enrollment audit trail | Merged via PR #38 |
| Dead code removal and the cleanup command fix | Merged via PR #39 |
| Metrics endpoint | Merged via PR #40 |
| Remote branches | `main` plus merged topic branches; no branch is deleted |
| Local backups | `refs/backup/feature-ai-attendance-security`, `refs/backup/feature-attendance-verification-stable`, `refs/backup/main-before-attendance-merge-2026-10-26`, `refs/backup/main-initial` |
| Open stabilization backlog | [#11](https://github.com/Kartik-gharte/Attendance.Application/issues/11) and [#13](https://github.com/Kartik-gharte/Attendance.Application/issues/13) |
| CI | Compile, test, and secret-scan jobs pass on every pull request; branch protection is not configured |
| Test suite | 258 runtime tests exist under `tests/runtime/` |
| Model assets | Provisioned on the development machine; MediaPipe Face Landmarker and InsightFace `buffalo_l` both load correctly |
| Measured baseline | 2.3 s import, 165 MB resident without models, 1.0 s startup and 986 MB resident with them |

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
| Liveness start/frame API | Implemented, verified | `POST /liveness/start`, `POST /liveness/frame`; in-memory sessions with a TTL from creation, one-time consumption, and user binding. |
| Blink liveness | Implemented, unverified | MediaPipe landmarks + EAR threshold; accuracy untested. The model asset is provisioned and loads. |
| Anti-spoofing screening | Implemented, unverified | Heuristic size/brightness/sharpness checks; not a trained PAD model. Effectiveness unmeasured. |
| Face embedding/recognition | Implemented, unverified | InsightFace `buffalo_l`, cosine similarity, configurable threshold; accuracy untested. The model asset is provisioned and loads. |
| Attendance verification API | Implemented, partially verified | `POST /attendance/verify`; success, duplicate, validation, upload-limit, authentication, ownership, and retrieval-error paths tested with a temporary database and fake model services. Real model flow unverified. |
| Attendance retrieval API | Implemented, verified without models | `GET /attendance/student/{student_id}` and `GET /attendance/all` return empty lists on a fresh initialized database. Students can read only their own records; admins can read all records. |
| Authentication/authorization | Implemented, verified with temporary storage | Local Argon2id accounts, opaque bearer tokens with expiry/revocation, student/admin roles, and user-bound liveness sessions. Tested without real models. |
| SQLite schema | Implemented, verified | The lifespan initializes `attendance`, `users`, and `auth_tokens` idempotently for `ATTENDANCE_DB_PATH` and preserves rows across restart. Tests cover fresh creation, retrieval, duplicate rejection, account provisioning, and token lifecycle. |
| Enrollment/registration | Implemented, verified | `register_face()` with a CLI entry point; validated identifiers, path containment, overwrite protection, and atomic writes. CLI-only, no API. |
| Startup resilience | Implemented, verified | Importing `app.main` does not touch models or the database; schema initialization and missing MediaPipe assets fail lifespan startup explicitly. |
| Automated tests | Implemented, verified | 196 runtime tests cover settings, startup, the database, the API, validation, authentication, logging and redaction, migrations, backup and restore, health and readiness, the enrollment workflow, the evaluation harness, and the benchmark harness. |
| Structured logging | Implemented, verified | Configured once at startup. A redaction record factory masks credentials, session identifiers, and embedding vectors at record creation. Tests assert sensitive values never reach the log stream. |
| Schema migrations | Implemented, verified | Versioned, ordered, transactional. A failed migration rolls back completely. A database created before versioning existed is adopted at the baseline version. |
| Backup and restore | Implemented, verified | Consistent copy via the SQLite online backup API, checksummed manifest, verification before restore, safety copy of the live database. |
| Health and readiness | Implemented, verified | Liveness inspects nothing outside the process. Readiness verifies the database and the models and returns 503 when not ready. |
| Deployment baseline | Implemented, verified | Requirements, single-worker constraint, TLS expectation, probe configuration, measured baseline, and a runbook in `docs/DEPLOYMENT.md`. |
| Evaluation harness | Implemented, verified | Dataset validation, FAR/FRR/ROC/EER, liveness success rate, and Wilson intervals. No accuracy figure has been produced. |
| Syntax check | Verified | `python -m compileall -q app tests` passed. |
| Lint/type checks | Not configured | No verified tool configuration exists. |
| Observability | Partial | Structured, leveled, redacted logging with a configurable level and format. Metrics are exposed in the Prometheus text format with route labels that cannot contain personal data. No tracing and no alerting. |
| CI | Implemented, verified | Compile, runtime tests, and gitleaks run on pull requests and `main`; both jobs passed on PR #22. Branch protection still requires owner action. |
| Privacy controls | Partial | Git ignores biometric, account, token, and attendance data. Retention, deletion, backup and restore, backup retention, and an enrollment audit trail are implemented. The consent reference points at a record kept outside the application. |
| Deployment | Partial | Requirements, constraints, probes, a measured baseline, and a runbook are documented. No container image, service unit, or reverse-proxy configuration. |
| Project documentation | In progress | Runtime, database, configuration, API, security, authentication, and validation docs updated for the current implementation. |

## What was actually verified

On macOS 27.0.1 arm64 with Python 3.11.16:

1. Clean virtual environment installed all runtime dependencies from `requirements.txt`, including `argon2-cffi`.
2. `python -m pytest tests/runtime -q` passed (258 tests), including validation, upload-limit, retrieval-error, login/logout, token expiry/revocation, role, cross-student access, log redaction, schema migration and rollback, backup and restore, backup retention, health and readiness, the enrollment workflow, the enrollment audit trail, the metrics, the evaluation harness, and the authentication command line.
3. `python -m uvicorn app.main:app` reached "Application startup complete" against a temporary database.
4. `GET /` and `GET /docs` returned `200`; the real server issued a login token, `GET /auth/me` returned the student account, and an unauthenticated `GET /attendance/all` returned `401`.
5. A temporary configured database was created with the `attendance`, `users`, and `auth_tokens` tables during startup; restart preserved an inserted attendance row.
6. The attendance API returned an empty list on a fresh database, inserted a record, and mapped a repeated insert to the duplicate response using fake model services.
7. Authentication tests created local accounts, issued and revoked tokens, rejected expired tokens, and enforced student self-access/admin read-only behavior with a temporary database and fake model services.
8. Startup logs showed schema initialization before MediaPipe and InsightFace loading once each.
9. Starting with `MEDIAPIPE_FACE_LANDMARKER_MODEL` pointed at a missing file failed startup with a `RuntimeError` naming that setting.
10. `python -m compileall -q app tests` passed.
11. CI ran on PR #22: `Compile and test` passed in 56 seconds and `Secret scan` passed in 7 seconds.
12. The liveness session hardening was merged in PR #26 and verified by the runtime suite.
13. The structured logging work was merged in PR #29. The redaction factory was verified to protect handlers attached after configuration, and a log capture test confirmed that the bearer token, liveness session identifier, and account password never reach the log stream.
14. The parameterized enrollment work was merged in PR #30. Twenty-two tests cover identifier validation, path containment, overwrite refusal, atomic writes, dry runs, and the CLI surfaces.
15. The schema migration work was merged in PR #31. A failing migration was verified to roll back its DDL and to leave the previously applied version recorded.
16. The backup and restore work was merged in PR #32. The backup was verified to be checksummed and integrity checked, the restore was verified to refuse to overwrite without the flag and to write a safety copy, and a backup that fails verification was verified not to modify the live database.
17. The health and readiness endpoints were merged in PR #33. Liveness was verified to stay `ok` when the database is missing and when the models are not loaded. Readiness was verified to return `503` when the database is missing, when the attendance table is dropped, when either model is not loaded, and when the schema version is behind.
18. The deployment baseline was merged in PR #34. The harness was executed and produced the recorded numbers.
19. The evaluation harness was merged in PR #35. The runner was verified to refuse a missing dataset and an invalid dataset with a nonzero exit code.
20. The real biometric model assets were verified to load: MediaPipe Face Landmarker and InsightFace `buffalo_l` both initialize, with a measured startup of 1.0 s and 986 MB resident memory.
21. CI passed on PRs #29, #30, #31, #32, #33, #34, #35, #37, #38, #39, and #40. The `Compile and test` and `Secret scan` jobs passed on every one.
22. The backup retention policy was merged in PR #37. The age limit, the count limit, the rule that the newest backup is always kept, and the guard against deleting an unrelated directory were verified.
23. The enrollment audit trail was merged in PR #38. It was verified that no embedding value reaches the trail, that the source path is reduced to its file name, and that the enrollment outcomes are recorded.
24. The cleanup command fix was merged in PR #39. The old behaviour was confirmed first: the command exited successfully and deleted nothing.
25. The metrics endpoint was merged in PR #40. A request to `/attendance/student/SECRETSTUDENT42` was verified to produce the label `/attendance/student/{student_id}`, with the identifier absent from the output.

## What was not verified

- Startup on Windows, Linux, or any Python version other than 3.11.16.
- Any liveness, anti-spoofing, or face-matching accuracy. The evaluation machinery is implemented and tested, but no consented dataset exists, so no measurement has been made.
- Face-recognition accuracy, false-accept/false-reject rates, or anti-spoofing effectiveness.
- The attendance verification path under load with real faces.
- Webcam client behavior with a real camera.
- The single-worker constraint under a real multi-worker deployment. The constraint is documented, not exercised.
- TLS, rate limiting, MFA, SSO, account lockout, or audit logging.
- Deployment, load, or adversarial security testing.

## Current blockers

1. No consented evaluation dataset exists, so no liveness, face-recognition, or anti-spoofing accuracy has been measured ([#11](https://github.com/Kartik-gharte/Attendance.Application/issues/11)). The requirements are in `docs/EVALUATION_DATASET_POLICY.md`.
2. Branch protection is not configured on `main`. This requires a repository settings change by the owner.
3. The attendance verification path has not been load tested with real faces.
4. There is no consent workflow and no enrollment audit trail.

## Definition of a working next milestone

Phase 1 is complete when all of the following are true and documented:

1. A fresh environment installs dependencies from a reviewed manifest. **Done.**
2. The application starts using portable model paths. **Done on the verified platform.**
3. A fresh database schema is created automatically. **Done.**
4. `/` and `/docs` respond. **Done.**
5. A consented test flow completes liveness, face verification, and attendance storage with real model assets; duplicate handling is verified at the database and API layers with fake model services. **Outstanding.** The model assets are provisioned and load, but no consented face imagery exists to run the flow with.
6. All sensitive endpoints require authentication and enforce student/admin authorization; local login, token expiry, revocation, and cross-student denial are verified with temporary storage and fake model services. **Done.**

## Phase 2 — Operational baseline

The operational baseline is complete when all of the following are true:

1. The schema is versioned and a migration can be applied, rolled back on failure, and adopted from a database created before versioning existed. **Done (PR #31).**
2. The database and the embeddings can be backed up, verified, and restored without losing rows or overwriting live data without an explicit flag. **Done (PR #32).**
3. Liveness and readiness are distinguishable, and a dependency failure does not make the service report itself dead. **Done (PR #33).**
4. The requirements, the worker count constraint, the probe configuration, the measured baseline, and a runbook are documented. **Done (PR #34).**
5. The accuracy evaluation can be run reproducibly against a consented dataset. **Harness done (PR #35).** The dataset is outstanding.
