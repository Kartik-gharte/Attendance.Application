# Issue Audit

**As of:** 2026-11-13

## Repository State

- **Integration branch:** `main`
- **Test suite:** 258 runtime tests pass (`python -m pytest tests/runtime -q`)
- **Compile check:** `python -m compileall -q app manual tests` passes
- **CI:** compile, test, and secret-scan jobs pass on every pull request
- **Model assets:** provisioned on the development machine; MediaPipe Face Landmarker 3.6 MB, InsightFace `buffalo_l` five ONNX models
- **Measured baseline:** 2.3 s import, 165 MB resident without models, 1.0 s startup and 986 MB resident with them

## Total Issues Discovered

| Status | Count |
|---|---|
| Completed (acceptance criteria met, merged, verified) | 10 |
| Partially completed (machinery delivered, a remaining blocker) | 2 |
| Not started | 0 |
| Implemented but unmerged | 0 |
| Blocked (cannot proceed due to unavailable resources) | 0 |
| Needs verification (implementation exists but correctness unproven) | 0 |
| **Total** | **12** |

## Completed Issues (10)

| # | Title | Priority | PR | Status |
|---|---|---|---|---|
| #2 | [P0] Runtime bootstrap: dependencies, configuration, portable models, and startup | Critical | #17 | Completed |
| #3 | [P0] Initialize SQLite schema at startup and make the database path configurable | Critical | #18 | Completed |
| #4 | [P0] Add authentication and authorization for attendance and biometric endpoints | Critical | #20 | Completed |
| #5 | [P0] Harden input validation, embedding path containment, uploads, and error responses | Critical | #19 | Completed |
| #6 | [P1] Harden liveness sessions against replay, leakage, and stale state | High | #26 | Completed |
| #7 | [P1] Add an automated test suite and required CI checks | High | #24 | Completed |
| #8 | [P1] Replace print logging with structured, redacted logging | High | #29 | Completed |
| #9 | [P1] Define and implement biometric data retention, deletion, and storage protection | High | #25 | Completed |
| #10 | [P2] Replace hardcoded enrollment and manual-client scripts with parameterized workflows | Medium | #27, #30 | Completed |
| #12 | [P2] Add database migrations, backup/restore, health checks, and deployment baseline | Medium | #31, #32, #33, #34 | Completed |

### Verification notes

- **#6** — `created_at` TTL from session creation, `consumed_at` replay tracking, user binding, and audit logging. KI-006 and KI-012 resolved.
- **#8** — Logging configured once at startup. A redaction record factory masks bearer tokens, passwords, API keys, UUID session identifiers, and embedding vectors at record creation, so every handler is protected. Log capture tests assert the bearer token, session identifier, and password never reach the log stream. KI-017 resolved.
- **#10** — PR #27 parameterized `register_face.py`. PR #30 finished `recognize_face.py` and the manual client, removed the Windows paths, added atomic writes and overwrite protection, and added 22 tests.
- **#12** — Delivered across four pull requests: versioned migrations, backup and restore, health and readiness endpoints, and the deployment baseline with a runbook and a reproducible measurement harness.

## Partially Completed Issues (2)

| # | Title | Priority | PR | Status |
|---|---|---|---|---|
| #11 | [P2] Evaluate face-recognition accuracy and presentation-attack resistance | Medium | #35 | The measurement machinery is merged and tested: a versioned dataset description, dataset validation, per-attempt scoring, FAR/FRR/ROC/EER metrics, the liveness success rate, and Wilson intervals. **Blocked on a consented evaluation dataset.** The model assets are not the blocker; they are provisioned and load correctly. KI-020 partially resolved. |
| #13 | [Tracking] Stabilization backlog: runtime, security, tests, and operations | Medium | — | Metadata tracking issue. Its contents are now covered by the documentation set. |

## Blocked Issues (0)

None.

## Needs Verification (0)

None. Every merged change is covered by an automated test in the runtime suite.

## Closed Issues with Unfinished Work (0)

None.

## Open Issues That Appear Completed (0)

None.

## Follow-Up Work Delivered (not tracked by an issue)

These came out of the audit of the remaining gaps. Each is a separate, focused pull request.

| Work | PR | Summary |
|---|---|---|
| Backup retention policy | #37 | Old backups are pruned by age and count, so copies of biometric templates do not accumulate. |
| Enrollment audit trail | #38 | Every enrollment is recorded with the operator and the consent reference. The trail holds no biometric material. |
| Dead code removal and the cleanup command fix | #39 | `attendance_already_marked()` was deleted, the unused imports were removed, and the `app auth cleanup` command now actually deletes. |
| Metrics endpoint | #40 | Operational metrics in the Prometheus text format, with route labels that cannot contain personal data. |

## Corrections Recorded

Two issues were previously reported as complete when the work had not reached `main`. Both are corrected:

| Issue | What was wrong | Correction |
|---|---|---|
| #8 | Closed on GitHub with no code committed. `main` still had 30 `print()` calls in `app/api/routes.py`. | Reopened, implemented on `fix/structured-logging-clean`, merged as PR #29. |
| #10 | Closed on GitHub after PR #27 landed only half the work. `recognize_face.py` and the manual client still hardcoded values. | PR #30 completed the work and merged it. |

## Known Issue Mapping

| KI-ID | Issue | Status |
|---|---|---|
| KI-001 | Empty dependency manifest | Resolved |
| KI-002 | Hardcoded Windows model path | Resolved |
| KI-003 | Database schema never initialized | Resolved |
| KI-004 | No authentication or authorization | Resolved |
| KI-005 | `student_id` used in filesystem path without validation | Resolved |
| KI-006 | Liveness sessions bearer-like and replayable | Resolved |
| KI-007 | No upload size/type limits or domain validation | Resolved |
| KI-008 | No automated test suite | Resolved |
| KI-009 | No configuration system | Resolved |
| KI-010 | Error messages expose internal details | Resolved |
| KI-011 | No retention, deletion, encryption, or backup policy | **Partially resolved.** Retention, deletion, the backup and restore workflow, the backup retention policy, and the enrollment audit retention are implemented. Backups are still not encrypted at rest and there is no automatic backup schedule. |
| KI-012 | In-memory sessions per-process and never cleaned up | Resolved |
| KI-013 | Models loaded twice at import | Resolved |
| KI-014 | Broken import in `test_liveness_service.py` | Resolved |
| KI-015 | Missing fixtures and model assets | Resolved |
| KI-016 | Registration and client paths/IDs are hardcoded | Resolved |
| KI-017 | Logs contain personal data and use `print()` | Resolved |
| KI-018 | No CI or verified branch protection | Partially resolved — CI merged and passing; branch protection still requires owner action |
| KI-019 | Dead/duplicate code paths and scripts | **Resolved.** The hardcoded scripts were replaced, the duplicate broken test module was removed, the unused `attendance_already_marked()` was deleted, and the unused imports were removed. The scan also uncovered the `app auth cleanup` command silently doing nothing, which is now fixed. |
| KI-020 | Anti-spoofing effectiveness is unmeasured | Partially resolved — the evaluation harness is merged and tested; blocked on a consented dataset |

## Links

### Issues
[#2](https://github.com/Kartik-gharte/Attendance.Application/issues/2) · [#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3) · [#4](https://github.com/Kartik-gharte/Attendance.Application/issues/4) · [#5](https://github.com/Kartik-gharte/Attendance.Application/issues/5) · [#6](https://github.com/Kartik-gharte/Attendance.Application/issues/6) · [#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7) · [#8](https://github.com/Kartik-gharte/Attendance.Application/issues/8) · [#9](https://github.com/Kartik-gharte/Attendance.Application/issues/9) · [#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10) · [#11](https://github.com/Kartik-gharte/Attendance.Application/issues/11) · [#12](https://github.com/Kartik-gharte/Attendance.Application/issues/12) · [#13](https://github.com/Kartik-gharte/Attendance.Application/issues/13)

### Pull requests
[#17](https://github.com/Kartik-gharte/Attendance.Application/pull/17) · [#18](https://github.com/Kartik-gharte/Attendance.Application/pull/18) · [#19](https://github.com/Kartik-gharte/Attendance.Application/pull/19) · [#20](https://github.com/Kartik-gharte/Attendance.Application/pull/20) · [#24](https://github.com/Kartik-gharte/Attendance.Application/pull/24) · [#25](https://github.com/Kartik-gharte/Attendance.Application/pull/25) · [#26](https://github.com/Kartik-gharte/Attendance.Application/pull/26) · [#27](https://github.com/Kartik-gharte/Attendance.Application/pull/27) · [#29](https://github.com/Kartik-gharte/Attendance.Application/pull/29) · [#30](https://github.com/Kartik-gharte/Attendance.Application/pull/30) · [#31](https://github.com/Kartik-gharte/Attendance.Application/pull/31) · [#32](https://github.com/Kartik-gharte/Attendance.Application/pull/32) · [#33](https://github.com/Kartik-gharte/Attendance.Application/pull/33) · [#34](https://github.com/Kartik-gharte/Attendance.Application/pull/34) · [#35](https://github.com/Kartik-gharte/Attendance.Application/pull/35) · [#37](https://github.com/Kartik-gharte/Attendance.Application/pull/37) · [#38](https://github.com/Kartik-gharte/Attendance.Application/pull/38) · [#39](https://github.com/Kartik-gharte/Attendance.Application/pull/39) · [#40](https://github.com/Kartik-gharte/Attendance.Application/pull/40)

### Superseded pull request
[#28](https://github.com/Kartik-gharte/Attendance.Application/pull/28) — closed without merging. The secret scan flagged credential-shaped literals in the redaction tests. Replacing it would have required rewriting published history, so the work was redone on a clean branch as PR #29.
