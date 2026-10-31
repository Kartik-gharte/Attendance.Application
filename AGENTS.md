# Agent Instructions

This file is the entry point for coding agents working on Attendance.Application. Read it before changing code or documentation.

## Project context

Attendance.Application is an AI-assisted student attendance verification backend. It uses FastAPI, OpenCV, MediaPipe, InsightFace, ONNX Runtime, NumPy, and SQLite. The current client is a manual Python/OpenCV script; there is no web frontend.

The project is under active development. Do not describe it as production-ready or claim that a feature works unless it has been verified.

## Read before working

Use the source code as the authority for behavior. Start with:

1. [README.md](README.md) — public overview and current limitations.
2. [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) — requirements and implementation status.
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components and data flow.
4. [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) — current verified state.
5. [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) — confirmed gaps.
6. [docs/SETUP.md](docs/SETUP.md) and [docs/TESTING.md](docs/TESTING.md) — setup and verification constraints.
7. [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) — biometric and security restrictions.

Relevant source files:

- `app/main.py`
- `app/api/routes.py`
- `app/api/liveness_routes.py`
- `app/auth/routes.py`
- `app/auth/dependencies.py`
- `app/auth/service.py`
- `app/auth/cli.py`
- `app/services/liveness.py`
- `app/services/anti_spoofing.py`
- `app/services/face_recognition.py`
- `app/services/attendance_verification.py`
- `app/database/attendance_db.py`

## Mandatory rules

1. Never commit or push without explicit authorization.
2. Never force-push, reset shared history, or delete branches without explicit authorization.
3. Never discard uncommitted user changes.
4. Never expose or commit secrets, credentials, API keys, real student data, face images, biometric embeddings, or local databases.
5. Never fabricate test results or claim unverified behavior works.
6. Never implement unrelated changes or opportunistic refactors.
7. Never introduce dependencies without justification and documentation.
8. Never silently change API contracts, response fields, database schemas, or validation behavior.
9. Never describe the heuristic anti-spoofing checks as a trained or certified presentation-attack detection system.
10. Never represent planned features as implemented.
11. Update documentation whenever behavior, configuration, architecture, or project status changes.
12. Prefer focused, independently reviewable changes.
13. Run relevant verification commands when practical and clearly report what was not tested.

## Working method

1. Inspect `git status`, the active branch, and the relevant docs and code.
2. State the intended change and the files involved before editing.
3. Create or switch to a focused branch when authorized.
4. Keep the change scoped to one issue.
5. Add or update tests when behavior changes. If automated tests are not available, explain the manual verification performed and what remains unverified.
6. Update the relevant docs in the same change.
7. Run available checks: syntax/compile checks, tests, and `git diff --check`.
8. Review `git diff` and `git status` before reporting.
9. Report blockers instead of guessing when behavior or intent is unclear.

## Branching and pull requests

- Branch from the current `main` unless the issue specifies another base.
- Use prefixes such as `feat/`, `fix/`, `test/`, `docs/`, and `chore/`.
- Follow [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md).
- Use the pull request template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Do not create remote branches, issues, or pull requests without explicit authorization.
- Do not assume branch protection or CI exists; verify it first.

## Documentation expectations

Update the smallest relevant set of documents:

- Requirements/status: `docs/PROJECT_SPEC.md`, `docs/PROJECT_STATUS.md`
- Architecture/behavior: `docs/ARCHITECTURE.md`
- API: `docs/API_REFERENCE.md`
- Database: `docs/DATABASE.md`
- Configuration: `docs/CONFIGURATION.md`
- Setup/testing: `docs/SETUP.md`, `docs/TESTING.md`
- Security/privacy: `docs/SECURITY_AND_PRIVACY.md`
- Significant decisions: `docs/DECISIONS.md`
- Known gaps: `docs/KNOWN_ISSUES.md`

Do not duplicate the full specification in this file. Link to the authoritative document instead.

## Security and privacy

- Treat all biometric data as sensitive.
- Never add real face images, embeddings, attendance databases, or student records to Git.
- Use synthetic or explicitly consented test data only.
- Do not log raw biometric data or credentials.
- Keep `.env` files, local databases, model files, and generated artifacts out of version control.
- Document security limitations honestly; do not imply that the current anti-spoofing or authentication model is sufficient for production.

## Reporting blockers

Stop and explain the blocker when:

- The working tree has user changes that cannot be preserved safely.
- The branch or history is unexpected.
- Required model assets, credentials, or services are unavailable.
- A change would alter an API contract or database schema without a documented decision.
- The intended behavior cannot be determined from code, tests, or documentation.

Include what was inspected, what failed, and the safest options.
