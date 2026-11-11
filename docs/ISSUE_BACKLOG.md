# Issue Backlog — Prioritized Execution Queue

## Execution Order

Issues are ordered by priority (P0 > P1 > P2) and within priority by dependency order and estimated effort. Work begins at the top of the queue.

---

### P1 — High Priority (2 issues)

#### #6 — Harden liveness sessions against replay, leakage, and stale state

- **Priority:** P1 (High)
- **Related KI:** KI-006, KI-012
- **Status:** Open — sessions are module-level dict, bearer-like, replayable
- **Dependencies:** Requires authentication (issue #4 / PR #20 already merged — Argon2id accounts, bearer tokens, role-based access exist). Session binding to authenticated principal is the next step.
- **Acceptance criteria:**
  - [ ] Every session has a documented TTL from creation, even if liveness is never verified.
  - [ ] Expired sessions are rejected and removed; abandoned sessions do not grow memory without bound.
  - [ ] A session can be used only by the authenticated student/principal it was created for.
  - [ ] A session is consumed exactly once.
  - [ ] Replaying a used or expired session is rejected.
  - [ ] `session_id` does not appear in URL query strings or access logs.
  - [ ] Multi-worker behavior is either supported through a shared store or explicitly documented as unsupported.
  - [ ] Tests cover expiry, replay, cross-student use, cleanup, and malformed session IDs.
  - [ ] API reference, architecture, security/privacy, and changelog document the new behavior and any breaking change.
- **Required implementation:**
  - Add `created_at`, `verified_at`, `consumed_at` fields to session record
  - Add TTL expiry check from session creation (not just from verification)
  - Bind session to `current_user.id` (already partially done) + student ID validation
  - Move `session_id` from query string to header/body
  - Add replay/consume tracking (single-use)
  - Add cleanup of expired/abandoned sessions
  - Add tests for expiry, replay, cross-student use, cleanup, malformed IDs
  - Document API contract change (breaking: session_id transport)
- **Proposed branch:** `fix/liveness-session-hardening`
- **Next action:** Create feature branch from `main` and implement session lifecycle

#### #8 — Replace print logging with structured, redacted logging

- **Priority:** P1 (High)
- **Related KI:** KI-017
- **Status:** Open — `print()` calls throughout codebase; no log levels, no redaction
- **Dependencies:** No blocking dependencies; can start independently.
- **Acceptance criteria:**
  - [ ] Application code uses the logging module or an approved structured logger, not `print()` for operational events.
  - [ ] Log levels are configurable and documented.
  - [ ] No raw images, embeddings, session IDs, tokens, passwords, or secrets appear in logs.
  - [ ] Client-facing errors remain sanitized while internal details are logged with redaction.
  - [ ] A test inspects captured logs for forbidden values.
  - [ ] Log retention/rotation/access expectations are documented.
  - [ ] `docs/CONFIGURATION.md`, `docs/SECURITY_AND_PRIVACY.md`, and `docs/ARCHITECTURE.md` are updated.
  - [ ] KI-017 is closed only after verification.
- **Required implementation:**
  - Configure logging once at application startup in `app/main.py`
  - Replace `print()` calls with `logging` module at appropriate levels
  - Define redaction policy: no raw images, embeddings, session IDs, tokens, passwords, secrets, full exception strings
  - Add request correlation if practical
  - Update all `print()` calls in `app/api/routes.py`, `app/api/liveness_routes.py`, `app/services/*.py`
  - Add tests that assert sensitive values do not appear in captured logs
  - Document log retention/rotation/access in `docs/SECURITY_AND_PRIVACY.md`
- **Proposed branch:** `fix/structured-logging`
- **Next action:** Create feature branch and replace print statements with structured logging

---

### P2 — Medium Priority (3 issues)

#### #10 — Replace hardcoded enrollment and manual-client scripts with parameterized workflows

- **Priority:** P2 (Medium)
- **Related KI:** KI-014, KI-016, KI-019
- **Status:** Open — Scripts hardcode `STU001`, `test.jpg`, Windows paths; no path validation, no overwrite protection
- **Dependencies:** Enrollment writes biometric data; should depend on authentication/authorization if becoming an API, but CLI-only path is acceptable for now.
- **Acceptance criteria:**
  - [ ] No hardcoded student ID, image name, output path, or API URL remains in the enrollment/client workflow.
  - [ ] The output path is validated and cannot escape the configured embeddings directory.
  - [ ] Existing embeddings are not overwritten without an explicit flag.
  - [ ] Failed enrollment does not leave a partial embedding file.
  - [ ] The source image is validated and must contain exactly one face before writing.
  - [ ] The command exits nonzero with a clear message on validation or model failure.
  - [ ] Manual client values are configurable and documented.
  - [ ] Tests cover valid enrollment, invalid ID/path, multiple/no faces (mocked), and overwrite refusal.
  - [ ] `docs/SETUP.md`, `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, `docs/KNOWN_ISSUES.md`, and `CHANGELOG.md` are updated.
- **Required implementation:**
  - Parameterize `app/services/register_face.py` with CLI args: `--student-id`, `--image`, `--output-dir`, `--dry-run`, `--force`
  - Validate student identifier against `STUDENT_ID_PATTERN` and path containment under embeddings dir
  - Write atomically (temp file + rename); refuse to overwrite existing by default
  - Validate source image has exactly one detectable face
  - Refactor `app/services/recognize_face.py` to accept parameters instead of hardcoding
  - Parameterize `test_api_attendance.py` values via env vars or CLI
  - Add deterministic tests for path validation, overwrite refusal, multi-face refusal
  - Update documentation
- **Proposed branch:** `feat/enrollment-workflow`
- **Next action:** Create feature branch and parameterize enrollment scripts

#### #11 — Evaluate face-recognition accuracy and presentation-attack resistance

- **Priority:** P2 (Medium)
- **Related KI:** KI-020
- **Status:** Open — No benchmark, dataset, FAR/FRR measurements, or anti-spoofing evaluation. Heuristic checks only.
- **Dependencies:** Model assets (MediaPipe + InsightFace) must be available; this work is blocked until model provisioning is verified. See KNOWN_ISSUES.md.
- **Acceptance criteria:**
  - [ ] Documented evaluation protocol with attack dataset.
  - [ ] Measured FAR/FRR or published limitations of current heuristic checks.
  - [ ] If a trained PAD model is added, it must be optional/configurable and not commit biometric data.
  - [ ] `docs/SECURITY_AND_PRIVACY.md` updated with evaluation results and limitations.
- **Required implementation:**
  - Document current heuristic anti-spoofing checks (size, brightness, Laplacian variance) with known limitations.
  - If model assets available, run benchmarks against synthetic and real attack data.
  - Publish measured FAR/FRR or explicitly state that effectiveness is unmeasured.
  - Update `docs/SECURITY_AND_PRIVACY.md` and `docs/KNOWN_ISSUES.md` (KI-020).
- **Proposed branch:** `test/face-recognition-evaluation`
- **Next action:** Verify model assets exist, then document current heuristic limitations; if assets unavailable, document as known gap.

#### #12 — Add database migrations, backup/restore, health checks, and deployment baseline

- **Priority:** P2 (Medium)
- **Status:** Open — No migration tooling, no backup policy, no health checks.
- **Dependencies:** Can start independently; depends on SQLite schema being stable (already verified via lifespan).
- **Acceptance criteria:**
  - [ ] Database migration tooling (e.g., Alembic or custom schema versioning) is available.
  - [ ] Backup mechanism for the attendance database.
  - [ ] Health check endpoint or script.
  - [ ] Deployment baseline documented.
- **Required implementation:**
  - Add Alembic or lightweight migration script for attendance schema evolution.
  - Add `backup_attendance_db()` function or script.
  - Add health check route or script that verifies database accessibility and schema version.
  - Document deployment baseline in `docs/DEPLOYMENT.md` or update `docs/SETUP.md`.
- **Proposed branch:** `test/database-migrations`
- **Next action:** Create lightweight migration and backup utilities.

---

## Quick Reference: Issue Priority Order

| Rank | Issue | Priority | Branch |
|---|---|---|---|
| 1 | #6 — Liveness session hardening | P1 | `fix/liveness-session-hardening` |
| 2 | #8 — Structured logging | P1 | `fix/structured-logging` |
| 3 | #10 — Parameterized enrollment | P2 | `feat/enrollment-workflow` |
| 4 | #11 — Face-recognition evaluation | P2 | `test/face-recognition-evaluation` |
| 5 | #12 — Database migrations/backup | P2 | `test/database-migrations` |
| 6 | #13 — Stabilization backlog (tracking) | P2 | — (metadata only) |

---

## Dependencies Between Issues

- **#6 (liveness hardening)** depends on **authentication** (already merged in #4/PR #20) but is independent otherwise. Session binding to authenticated principal is the key integration.
- **#8 (structured logging)** is independent; no blocking dependencies.
- **#10 (parameterized enrollment)** depends on configuration for embedding directory (already resolved in #2/#17) and input validation (already resolved in #5/#19). Can proceed independently.
- **#11 (face-recognition evaluation)** blocked by model asset availability. Document current limitations while awaiting assets.
- **#12 (database migrations)** independent; can proceed once schema stability is confirmed (already verified).