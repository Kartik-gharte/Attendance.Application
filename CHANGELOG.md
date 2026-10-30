# Changelog

All notable changes to this project are recorded here. The project does not yet have tagged releases, so entries are grouped under `Unreleased`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project intends to follow [Semantic Versioning](https://semver.org/) once versioned releases begin.

## Unreleased

### Added

- Project foundation documentation: project specification, architecture, API reference, database, setup, configuration, testing, security/privacy, workflow, roadmap, status, known issues, decisions, and foundation plan.
- Root agent instructions (`AGENTS.md`) and contribution guidance (`CONTRIBUTING.md`).
- Security policy (`SECURITY.md`).
- GitHub pull-request and issue templates.
- Validated configuration in `app/core/config.py` backed by environment variables and a project-root `.env` file.
- `.env.example` with placeholders for model, embedding, database, CORS, recognition, and liveness settings.
- Pinned runtime dependencies in `requirements.txt` and development dependencies in `requirements-dev.txt`.
- Focused runtime tests under `tests/runtime/` for settings, lifespan wiring, `/`, `/docs`, missing-model failure, database initialization, retrieval, and duplicate handling with fake model services.
- FastAPI lifespan-managed service construction with a shared `LivenessService` and `FaceRecognitionService`.

### Changed

- Replaced the initial README with a documentation-oriented project overview that distinguishes implemented, unverified, and planned behavior.
- Extended `.gitignore` hygiene for Python caches, build artifacts, editor files, and model binaries.
- Replaced the hardcoded Windows MediaPipe path with `MEDIAPIPE_FACE_LANDMARKER_MODEL`.
- Replaced import-time service construction and duplicate model loading with a single lifespan startup path.
- Made the embedding directory, SQLite path, CORS origins, face threshold, liveness validity, and InsightFace cache configurable.
- `get_connection()` now honors `ATTENDANCE_DB_PATH`, and attendance routes use the configured database path from the app state. The FastAPI lifespan now calls `initialize_database()` before constructing model services and marks the database initialized.
- Updated setup, configuration, architecture, database, testing, roadmap, status, known-issue, and decision documentation with verified runtime behavior.

### Repository

- `main` now contains the integrated attendance-verification and AI-security feature work. The original feature branches were fully merged before remote cleanup on 2026-10-27.
- Runtime bootstrap was developed on `fix/runtime-bootstrap` and verified locally on macOS 27.0.1 arm64 with Python 3.11.16.

### Known gaps

- No full automated test suite or CI workflow exists (issue #7).
- No authentication or authorization is implemented (issue #4).
- Input validation, upload limits, and error sanitization are still missing (issue #5).
- Anti-spoofing is heuristic screening, not a trained PAD model.
- Startup is verified only on macOS arm64 with Python 3.11.16.
