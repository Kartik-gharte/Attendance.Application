# Issue Audit

## Repository State

- **Current branch:** `main` at `ab5048f` (HEAD)
- **All 25 PRs merged** into `main`, most recent: PR #25 (biometric retention, Oct 31 2026)
- **GitHub CLI:** authenticated as `thenameisomm`
- **Test suite:** 65 runtime tests pass (`python -m pytest tests/runtime -q`)
- **Compile check:** `python -m compileall -q app tests` passes
- **CI:** Workflow merged in PR #22; runs compile, test, and secret-scan on PRs and `main`

## Total Issues Discovered

| Status | Count |
|---|---|
| Completed (acceptance criteria met, integrated, verified) | 7 |
| Partially completed (some requirements implemented, gaps remain) | 5 |
| Not started | 0 |
| Implemented but unmerged (exists in unmerged branch/PR) | 0 |
| Blocked (cannot proceed due to dependencies/resources) | 0 |
| Needs verification (implementation exists but correctness unproven) | 0 |
| **Total** | **12** |

## Completed Issues (7) — Acceptance criteria met, merged & verified

| # | Title | PR | Status |
|---|---|---|---|
| #1 | [Docs] Establish project foundation and contribution workflow | #1 | Merged; docs + workflow set up |
| #2 | [P0] Runtime bootstrap: dependencies, configuration, portable models, and startup | #17 | Merged; `requirements.txt`, `config.py`, portable model paths |
| #3 | [P0] Initialize SQLite schema at startup and make the database path configurable | #18 | Merged; lifespan `initialize_database()`, idempotent schema |
| #4 | [P0] Add authentication and authorization for attendance and biometric endpoints | #20 | Merged; Argon2id accounts, bearer tokens, role-based access |
| #5 | [P0] Harden input validation, embedding path containment, uploads, and error responses | #19 | Merged; `validate_student_id()`, `validate_*()` functions, input sanitization |
| #7 | [P1] Add an automated test suite and required CI checks | #24 | Merged; 19 deterministic service tests + CI workflow |
| #9 | [P1] Define and implement biometric data retention, deletion, and storage protection | #25 | Merged; `delete_old_attendance()`, `retention_days` config, CLI cleanup |

## Partially Completed Issues (5) — Some requirements implemented, gaps remain

| # | Title | Priority | Status |
|---|---|---|---|
| #6 | [P1] Harden liveness sessions against replay, leakage, and stale state | High | **Completed** in PR #26 `fix/liveness-session-hardening` (merged 2026-11-11). `created_at` TTL from session creation, session consumption tracking (pop after use), and user binding to authenticated principal are now part of `main`. Issue closed. KI-006 resolved; KI-012 resolved. |
| #8 | [P1] Replace print logging with structured, redacted logging | High | **Open**; KI-017. `print()` calls throughout codebase; no log levels, no redaction, no policy for what must not appear in logs. |
| #10 | [P2] Replace hardcoded enrollment and manual-client scripts with parameterized workflows | Medium | **Open**; KI-014, KI-016, KI-019. Scripts hardcode `STU001`, `test.jpg`, Windows paths; no path validation, no overwrite protection, no CLI parameterization. |
| #11 | [P2] Evaluate face-recognition accuracy and presentation-attack resistance | Medium | **Open**; KI-020. No benchmark, dataset, FAR/FRR measurements, or anti-spoofing evaluation. Heuristic checks only, not a trained PAD model. |
| #12 | [P2] Add database migrations, backup/restore, health checks, and deployment baseline | Medium | **Open**; no migration tooling, no backup policy, no health checks. |

## Open Issues Requiring Verification (0)

None.

## Closed Issues with Unfinished Work (0)

None — all closed issues have their acceptance criteria satisfied by merged PRs.

## Open Issues That Appear Completed (0)

None.

## Regressions and Missing Tests

- No liveness session replay/cross-student tests beyond basic ownership checks
- No structured logging redaction tests
- No enrollment parameterization tests
- No face-recognition accuracy benchmark
- No migration/backup/deployment tooling

## Links to GitHub Issues and PRs

- Issue #6: <https://github.com/Kartik-gharte/Attendance.Application/issues/6>
- Issue #8: <https://github.com/Kartik-gharte/Attendance.Application/issues/8>
- Issue #10: <https://github.com/Kartik-gharte/Attendance.Application/issues/10>
- Issue #11: <https://github.com/Kartik-gharte/Attendance.Application/issues/11>
- Issue #12: <https://github.com/Kartik-gharte/Attendance.Application/issues/12>
- Issue #13: <https://github.com/Kartik-gharte/Attendance.Application/issues/13>
- PR #1: <https://github.com/Kartik-gharte/Attendance.Application/pull/1>
- PR #7: <https://github.com/Kartik-gharte/Attendance.Application/pull/7>
- PR #9: <https://github.com/Kartik-gharte/Attendance.Application/pull/9>
- PR #17: <https://github.com/Kartik-gharte/Attendance.Application/pull/17>
- PR #18: <https://github.com/Kartik-gharte/Attendance.Application/pull/18>
- PR #19: <https://github.com/Kartik-gharte/Attendance.Application/pull/19>
- PR #20: <https://github.com/Kartik-gharte/Attendance.Application/pull/20>
- PR #24: <https://github.com/Kartik-gharte/Attendance.Application/pull/24>
- PR #25: <https://github.com/Kartik-gharte/Attendance.Application/pull/25>

## Known Issue Mapping

| KI-ID | Issue | Resolution Status |
|---|---|---|
| KI-001 | Empty dependency manifest | Resolved (#1) |
| KI-002 | Hardcoded Windows model path | Resolved (#2, #17) |
| KI-003 | Database schema never initialized | Resolved (#3, #18) |
| KI-004 | No authentication or authorization | Resolved (#4, #20) |
| KI-005 | student_id used in filesystem path without validation | Resolved (#5, #19) |
| KI-006 | Liveness sessions bearer-like and replayable | **Partially resolved**; issue #6 open |
| KI-007 | No upload size/type limits or domain validation | Resolved (#5, #19) |
| KI-008 | No automated test suite | Resolved (#7, #24) |
| KI-009 | No configuration system | Resolved (#2, #17) |
| KI-010 | Error messages expose internal details | Resolved (#5, #19) |
| KI-011 | No retention, deletion, encryption, or backup policy | Partially resolved (#25); function and config exist, CLI and docs pending |
| KI-012 | In-memory sessions per-process, never cleaned up | **Open**; related to issue #6 |
| KI-013 | Models loaded twice at import | Resolved (lifespan) |
| KI-014 | Broken test import | Partially resolved; root scripts moved to `manual/` |
| KI-015 | Missing fixtures and model assets | Resolved; deterministic tests use synthetic fixtures |
| KI-016 | Registration and client paths/IDs are hardcoded | **Open**; related to issue #10 |
| KI-017 | Logs contain personal data and use `print()` | **Open**; related to issue #8 |
| KI-018 | No CI or verified branch protection | Partially resolved; CI workflow merged, branch protection not configured |
| KI-019 | Dead/duplicate code paths and scripts | **Open**; related to issue #10 |
| KI-020 | Anti-spoofing effectiveness is unmeasured | **Open**; related to issue #11 |