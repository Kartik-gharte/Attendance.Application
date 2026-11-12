# Issue Backlog — Prioritized Execution Queue

**As of:** 2026-11-12

All twelve tracked issues have been worked. Ten are complete and merged.
This document records what remains and what would be done next.

---

## Remaining Work

### P2 — Medium Priority (2 items)

#### #11 — Evaluate face-recognition accuracy and presentation-attack resistance

- **Priority:** P2 (Medium)
- **Related KI:** KI-020 (partially resolved)
- **Status:** Partially completed. The measurement machinery is merged in PR #35.
- **Delivered:**
  - `app/evaluation/harness.py` — a versioned dataset description, dataset validation, per-attempt scores and decisions, false accept and false reject rates, a ROC curve, the equal error rate, the liveness success rate, and Wilson score intervals.
  - `app/evaluation/evaluate.py` — runs the evaluation against the real models and writes a report with no biometric material.
  - `docs/EVALUATION_DATASET_POLICY.md` — the dataset requirements, the consent rules, the description format, and what may not be claimed until the evaluation has been run.
  - `tests/runtime/test_evaluation_harness.py` — 26 tests.
- **Acceptance criteria still open:**
  - [ ] A consented or licensed dataset exists and passes the dataset validation.
  - [ ] The evaluation has been run and the report reviewed.
  - [ ] FAR/FRR, ROC/EER, and the liveness success rate are published with their intervals.
  - [ ] The heuristic screening has been evaluated against the presentation attacks.
  - [ ] A threshold recommendation is made, only if the evidence supports one.
  - [ ] The limitations and the dataset gaps are documented.
- **Dependencies:** A consenting participant set. The biometric model assets are **not** a dependency; they are provisioned and load correctly.
- **Testing requirements:** The evaluation harness is already covered by the runtime suite. Any new measurement must come from the harness, so that it is reproducible and carries its uncertainty.
- **Proposed branch:** `feat/evaluation-run`
- **Next action:** Assemble a consented dataset that meets `docs/EVALUATION_DATASET_POLICY.md`, then run `python -m app.evaluation.evaluate --dataset <path> --output <path>`.

#### #13 — [Tracking] Stabilization backlog: runtime, security, tests, and operations

- **Priority:** P2 (Medium)
- **Status:** Metadata tracking issue. Its contents are now covered by the documentation set.
- **Acceptance criteria:** None of its own. It closes when the items it tracks are closed.
- **Dependencies:** Depends on #11 being resolved, because the accuracy evaluation is the last unaddressed item in its scope.
- **Testing requirements:** None.
- **Proposed branch:** None. It is a metadata issue.
- **Next action:** Close it once #11 is resolved, or convert it into a tracking issue for the remaining operational work.

---

## Completed This Cycle

These are recorded for traceability. They need no further action.

| Issue | PRs | Summary |
|---|---|---|
| #6 | #26 | Session TTL from creation, consumption tracking, user binding, audit logging |
| #8 | #29 | Structured logging with a redaction record factory, 17 tests |
| #10 | #27, #30 | Parameterized enrollment, recognition, and manual client; atomic writes; overwrite protection; 22 tests |
| #12 | #31, #32, #33, #34 | Versioned migrations, backup and restore, health and readiness endpoints, deployment baseline and runbook |

---

## Follow-up Work Not Tracked by an Issue

These were identified while working the cycle. None is urgent, and none has an acceptance criterion yet.

| Item | Where it is recorded | Priority |
|---|---|---|
| Enable branch protection on `main` requiring the `Compile and test` and `Secret scan` checks | KI-018 | P1 — needs owner action in the repository settings |
| Remove the unused service methods (`attendance_already_marked`, `verify_attendance`, `verify_face_from_frame`) | KI-019 | P3 |
| Encrypt backups at rest | `docs/DATABASE.md`, `docs/SECURITY_AND_PRIVACY.md` | P2 |
| Add a backup retention policy so old backups do not accumulate | `docs/DATABASE.md` | P2 |
| Schedule backups automatically | `docs/DEPLOYMENT.md` | P2 |
| Load test the attendance verification path with real faces | `docs/ROADMAP.md` | P2 — depends on a dataset |
| Add metrics and tracing | `docs/ROADMAP.md`, `docs/DEPLOYMENT.md` | P2 |
| Add an authenticated admin enrollment API | `docs/ARCHITECTURE.md`, `docs/SECURITY_AND_PRIVACY.md` | P2 |
| Add an enrollment audit trail and a consent record | `docs/SECURITY_AND_PRIVACY.md` | P2 |
| Support multiple workers with a shared liveness session store | `docs/DEPLOYMENT.md` | P2 |
| Add a schema downgrade path | `docs/DATABASE.md` | P3 |
| Checksum the migrations so a modified applied migration is detected | `docs/DATABASE.md` | P3 |

---

## Suggested Execution Order

1. **#11** — assemble the consented dataset, run the evaluation, publish the measurements. Everything else in the backlog depends on this being the last accuracy blocker.
2. **Branch protection** — one repository settings change. It is the only P1 item left and it is the owner's action, not a code change.
3. **Backup encryption, retention, and scheduling** — closes the remaining data-protection gaps.
4. **Metrics and tracing** — needed before any real deployment.
5. **The P3 cleanups** — when there is time.

---

## Execution Queue

| Rank | Item | Priority | Branch | Next action |
|---|---|---|---|---|
| 1 | #11 — accuracy evaluation | P2 | `feat/evaluation-run` | Assemble a consented dataset |
| 2 | Branch protection | P1 | — | Owner action in the repository settings |
| 3 | Backup encryption and retention | P2 | `feat/backup-hardening` | Implement |
| 4 | Automatic backup schedule | P2 | `feat/backup-schedule` | Implement |
| 5 | Metrics and tracing | P2 | `feat/observability` | Implement |
| 6 | Dead code removal | P3 | `chore/remove-dead-code` | Implement |
| 7 | #13 — close the tracking issue | P2 | — | Close after #11 |
