# Contributing

Thank you for helping improve Attendance.Application. This project is an academic/experimental attendance-verification backend. Please keep changes focused, documented, and safe for biometric data.

Prefer multiple small, coherent contributions over one large change. Separate behavior, tests, and documentation when that keeps each contribution independently reviewable; use multiple focused commits and, when practical, multiple pull requests.

## Before you start

1. Read [README.md](README.md), [AGENTS.md](AGENTS.md), and [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md).
2. Check [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) and [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).
3. Pick or create an issue before starting significant work.
4. Check `git status` and start from an up-to-date `main`.

## Local prerequisites

- Python and `pip`/`venv`. The exact supported Python version is not yet verified; see [docs/SETUP.md](docs/SETUP.md).
- A webcam for manual end-to-end tests.
- MediaPipe Face Landmarker and InsightFace `buffalo_l` model assets for runtime tests.
- SQLite (included with Python).

Setup is currently blocked by known runtime gaps. Do not claim that a fresh clone is runnable until [docs/SETUP.md](docs/SETUP.md) is updated with a verified workflow.

## Branch naming

Create a branch from the current `main`:

```bash
git switch main
git pull --ff-only
git switch -c <prefix>/<short-description>
```

Use these prefixes:

- `feat/` — new user-visible functionality
- `fix/` — bug fix
- `test/` — tests or test infrastructure
- `docs/` — documentation only
- `chore/` — maintenance, tooling, or configuration

Keep one logical change per branch. Avoid mixing refactoring with behavior changes. For larger work, split it into multiple focused commits and, when independently reviewable, multiple branches and pull requests.

## Commit messages

Use Conventional Commits:

```text
feat: add attendance history endpoint
fix: handle expired liveness sessions
test: cover duplicate attendance protection
docs: document model setup
chore: add issue templates
```

Use the imperative mood and a concise subject. Add a body when the reason or trade-off is not obvious. Do not include secrets, biometric data, or student records in commit messages.

## Code expectations

- Follow the existing style and structure unless the issue explicitly requires a change.
- Keep API contracts and database schemas stable unless the change is documented and reviewed.
- Use parameterized SQL; never interpolate user input into SQL.
- Validate and sanitize external input where the framework does not already do so.
- Do not add dependencies without explaining why and updating the dependency manifest (when that task is in scope).
- Do not weaken security checks to make tests pass.
- Avoid committing generated files, model binaries, local databases, or `.env` files.

## Testing

- Add automated tests for new logic where practical.
- For AI/camera behavior that cannot be automated reliably, document the manual verification performed and the hardware/model prerequisites.
- Run any available checks before opening a pull request:
  - syntax/compile checks;
  - automated tests, if present;
  - `git diff --check`;
  - a focused manual check of the changed flow.
- Report exactly what was run and what could not be run. Do not claim a test passed unless it was executed.

Focused runtime tests live under `tests/runtime/`; camera-dependent scripts remain manual. See [docs/TESTING.md](docs/TESTING.md).

## Documentation

Update documentation in the same change when you modify:

- behavior or requirements — `docs/PROJECT_SPEC.md`, `docs/PROJECT_STATUS.md`;
- architecture — `docs/ARCHITECTURE.md`;
- endpoints — `docs/API_REFERENCE.md`;
- schema — `docs/DATABASE.md`;
- configuration — `docs/CONFIGURATION.md`;
- setup — `docs/SETUP.md`;
- tests — `docs/TESTING.md`;
- security/privacy — `docs/SECURITY_AND_PRIVACY.md`;
- significant decisions — `docs/DECISIONS.md`;
- known gaps — `docs/KNOWN_ISSUES.md`.

Keep links valid and avoid duplicating the same content across files.

## Pull requests

1. Push your branch only when authorized.
2. Open a pull request using `.github/PULL_REQUEST_TEMPLATE.md`.
3. Link the related issue.
4. Describe the change, the verification performed, and any unverified behavior.
5. Call out security, privacy, API, and database implications.
6. Keep the pull request focused; split unrelated work into separate contributions.
7. Respond to review comments and re-run checks after changes.

Do not merge without review and explicit approval. Branch protection, required reviews, and CI are not currently verified in this repository.

## Secrets and sensitive data

- Never commit credentials, tokens, private keys, `.env` files, face images, embeddings, attendance databases, or real student information.
- Use environment variables or local untracked files for local configuration.
- If you discover a secret in the repository or history, do not copy it into an issue or pull request. Report it privately using [SECURITY.md](SECURITY.md).
- Use synthetic or explicitly consented test data only.
