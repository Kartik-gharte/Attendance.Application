# Decisions

Record significant repository and architecture decisions here. Add new entries rather than rewriting history; supersede old decisions explicitly.

## D-001 — Documentation-first foundation

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** The repository contains working experimental code but no project documentation, agent instructions, or contribution workflow. Runtime behavior has several confirmed blockers.
- **Decision:** Establish documentation, governance, and templates on `chore/project-foundation` before changing runtime code.
- **Consequences:** Reviewers can evaluate scope and behavior from authoritative documents. Runtime fixes remain outstanding and must be tracked separately.

## D-002 — Single `main` with short-lived branches

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** Feature work had accumulated on separate branches and was merged on GitHub. Obsolete remote branches remained.
- **Decision:** Keep `main` as the integration branch; use short-lived `feat/`, `fix/`, `test/`, `docs/`, and `chore/` branches; integrate through pull requests.
- **Consequences:** Remote feature branches were deleted with explicit authorization. Local backup refs were retained. Branch protection is not configured/verified and must be addressed separately.

## D-003 — No runtime changes in the foundation change

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** Mixing documentation and behavioral fixes would make review and rollback harder.
- **Decision:** The foundation branch changes only documentation, GitHub templates, and repository-hygiene ignore rules. It does not modify application code, dependencies, configuration, models, database logic, or tests.
- **Consequences:** Known runtime blockers remain open and are documented in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## D-004 — Treat biometric artifacts as non-versioned data

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** Face images, embeddings, and attendance databases are sensitive and may be subject to biometric-privacy law.
- **Decision:** Never commit real face images, embeddings, databases, or student records. Use synthetic or explicitly consented test data only.
- **Consequences:** Clean checkouts lack fixtures and models; provisioning must be documented and performed locally. Git ignore rules are a safety net, not access control.

## D-005 — Describe anti-spoofing honestly

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** The current checks are heuristic frame-quality and blink tests, not a trained presentation-attack detection model.
- **Decision:** Document them as heuristic screening only; never describe them as trained, certified, or production-grade anti-spoofing.
- **Consequences:** Security claims are limited. A trained PAD evaluation is required before stronger claims.

## D-006 — Documentation structure and source of truth

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** Project knowledge was scattered across code, scripts, and conversation, with a stale README.
- **Decision:** Use `AGENTS.md` as the coding-agent entry point and `docs/` as the authoritative documentation set, indexed by `docs/README.md`. Keep the root README concise.
- **Consequences:** Behavior changes must update the relevant document in the same pull request. Duplicated specifications should be avoided.

## D-007 — Conventional branch and commit conventions

- **Date:** 2026-10-27
- **Status:** Accepted
- **Context:** There was no documented contribution convention.
- **Decision:** Use issue-first work, prefixed branch names, and Conventional Commit messages as documented in [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).
- **Consequences:** History and pull requests are easier to review. No enforcement exists until CI/branch protection is configured.

## D-008 — Keep SQLite for now; defer schema evolution

- **Date:** 2026-10-27
- **Status:** Accepted (provisional)
- **Context:** The current implementation uses a single SQLite file with no migration system.
- **Decision:** Do not replace the database or add migrations in the foundation change. Document the schema and the initialization gap.
- **Consequences:** SQLite remains a development-store assumption. Revisit when concurrency, deployment, or multi-user requirements are defined.

## D-009 — Python 3.11 and pinned requirements

- **Date:** 2026-10-30
- **Status:** Accepted
- **Context:** A reproducible install requires a documented interpreter and dependency set compatible with MediaPipe, InsightFace, ONNX Runtime, and OpenCV on the development platform.
- **Decision:** Target Python 3.11 and pin direct runtime dependencies in `requirements.txt`; keep test-only dependencies in `requirements-dev.txt`. Record the verified platform and versions in [SETUP.md](SETUP.md).
- **Consequences:** The manifest is reproducible for the verified platform. Other Python versions and platforms must be tested before being claimed as supported. MediaPipe and InsightFace both declare OpenCV packages, so both `opencv-python` and `opencv-contrib-python` are pinned to the same version.

## D-010 — Validated settings and lifespan-managed shared services

- **Date:** 2026-10-30
- **Status:** Accepted
- **Context:** Model services were constructed at import time with a hardcoded Windows path, and no configuration system existed.
- **Decision:** Use a `pydantic-settings` `Settings` object backed by environment variables and a project-root `.env` file. Build the model services once in the FastAPI lifespan, store them on `app.state`, and inject the shared instances into routes and the attendance service. Missing MediaPipe assets fail startup with an actionable error.
- **Consequences:** Importing `app.main` is lightweight and testable. Startup now requires the MediaPipe model unless a test provides a fake service factory. Database schema initialization remains separate ([#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3)).

## Proposed decisions (not yet accepted)

These are candidates for later phases; they are not implemented:

- Initialize the database in the FastAPI lifespan ([#3](https://github.com/Kartik-gharte/Attendance.Application/issues/3)).
- Add pytest-compatible unit/API tests with a temporary database and mocked model services ([#7](https://github.com/Kartik-gharte/Attendance.Application/issues/7)).
- Add structured, redacted logging ([#8](https://github.com/Kartik-gharte/Attendance.Application/issues/8)).
