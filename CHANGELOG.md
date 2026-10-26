# Changelog

All notable changes to this project are recorded here. The project does not yet have tagged releases, so entries are grouped under `Unreleased`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to follow [Semantic Versioning](https://semver.org/) once versioned releases begin.

## Unreleased

### Added

- Project foundation documentation: project specification, architecture, API reference, database, setup, configuration, testing, security/privacy, workflow, roadmap, status, known issues, decisions, and foundation plan.
- Root agent instructions (`AGENTS.md`) and contribution guidance (`CONTRIBUTING.md`).
- Security policy (`SECURITY.md`).
- GitHub pull-request and issue templates.

### Changed

- Replaced the initial README with a documentation-oriented project overview that distinguishes implemented, unverified, and planned behavior.
- Extended `.gitignore` hygiene for Python caches, build artifacts, editor files, and model binaries.

### Repository

- `main` now contains the integrated attendance-verification and AI-security feature work. The original feature branches were fully merged before remote cleanup on 2026-10-27.
- No application source code, dependency manifest, configuration, database logic, or runtime behavior was changed as part of this documentation foundation.

### Known gaps

- Dependency manifest and configuration module are empty.
- MediaPipe model path is hardcoded to a Windows path.
- Database initialization is not called during application startup.
- No automated test suite or CI workflow exists.
- No authentication or authorization is implemented.
- Anti-spoofing is heuristic screening, not a trained PAD model.
