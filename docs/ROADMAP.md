# Roadmap

## Direction

Build a trustworthy attendance-verification backend in small, reviewable increments. Correctness, privacy, and honest reporting come before feature breadth.

This roadmap is a proposal. It does not promise dates and does not mean any listed item is implemented.

## Phase 0 — Project foundation (merge complete; CI expectations pending)

**Goal:** make the repository understandable and governable before changing runtime behavior.

- [x] Audit repository, branches, and current behavior.
- [x] Consolidate on `main`; remove obsolete remote feature branches with authorization.
- [x] Add root project and agent documentation.
- [x] Add documentation set and index.
- [x] Add issue and pull-request templates.
- [x] Review and merge the foundation branch through pull request #1.
- [ ] Confirm CI/branch-protection expectations.

**Exit criteria:** documentation matches the code, links and claims are reviewed, and the changes are merged without altering runtime behavior.

## Phase 1 — Runtime bootstrap (in progress)

**Goal:** make a fresh clone start predictably.

- [x] Define and pin a dependency manifest compatible with the chosen Python version.
- [x] Add a real configuration module or documented environment-variable loader.
- [x] Replace the hardcoded Windows MediaPipe path with a portable setting.
- [x] Provision models through a documented, non-committed mechanism.
- [x] Verify startup, `/`, and `/docs`; document the tested platform and versions.
- [ ] Call database initialization during application startup ([#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3)).
- [ ] Validate `student_id` and constrain the embedding path ([#5](https://github.com/Kartik-gharte/Attendance.Application/issues/5)).
- [ ] Fix or remove the broken `test_liveness_service.py` import ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).
- [ ] Make registration output paths project-relative and parameterized ([#10](https://github.com/Kartik-gharte/Attendance.Application/issues/10)).
- [ ] Verify one consented end-to-end flow.

**Exit criteria:** a fresh environment following [SETUP.md](SETUP.md) starts successfully and the verified commands/values are documented.

**Branch:** `fix/runtime-bootstrap`

## Phase 2 — Automated tests and observability

**Goal:** make regressions visible without a camera or real biometric data.

- Add pytest-compatible tests for EAR, similarity comparison, anti-spoofing heuristics, and database behavior.
- Add API tests with mocked model services and a temporary database.
- Replace `print()` with structured, redacted logging.
- Add CI for syntax checks, tests, and secret scanning.
- Document a test-data policy using synthetic or explicitly consented fixtures.

**Exit criteria:** CI runs deterministic tests on every pull request, with no camera/model downloads required.

## Phase 3 — Security and access control

**Goal:** protect biometric operations and attendance records.

- Add authentication and role-based authorization for staff/student operations.
- Bind liveness sessions to a request/student and remove session IDs from query strings.
- Add upload size/type limits and strict input validation.
- Protect or encrypt biometric storage; define retention and deletion.
- Sanitize error responses and rate-limit endpoints.
- Evaluate a trained presentation-attack detection component before claiming anti-spoofing security.

**Exit criteria:** all sensitive endpoints require authorization, documented threat-model controls are tested, and privacy handling is reviewed.

## Phase 4 — Operational readiness

**Goal:** support controlled deployment.

- Add schema migrations and backup/restore procedures.
- Add health/readiness checks and deployment configuration.
- Define monitoring, audit logging, incident response, and data-retention operations.
- Complete an institutional privacy/legal review for the target jurisdiction.
- Load-test and document capacity limits.

**Exit criteria:** a reviewed deployment runbook exists and the system is deployable without undocumented manual steps.

## Phase 5 — Product maturity

**Goal:** improve usability only after the security and testing foundations are solid.

- Add a proper enrollment/registration workflow.
- Add reporting and export with access controls.
- Build a frontend or documented API client.
- Consider multi-class, multi-tenant, or integration requirements through separate design work.

## Explicit non-goals for now

- Claiming production readiness.
- Claiming certified or trained anti-spoofing.
- Adding unrelated frameworks or infrastructure.
- Storing real student biometric data in the repository.
- Building a frontend before the API is secure and tested.

## Prioritization rules

1. Security and data-loss issues first.
2. Runtime blockers next.
3. Testability and observability before feature work.
4. Features only with a documented requirement and privacy impact.
