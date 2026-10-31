# Development Workflow

## Principles

- Work from an issue, not an unstated idea.
- Prefer multiple small, focused contributions over one large change.
- Keep every contribution independently reviewable and buildable.
- Preserve existing behavior unless the issue explicitly changes it.
- Update documentation with behavior changes.
- Never commit secrets, biometric data, local databases, or model files.
- Do not claim verification that was not performed.

## Lifecycle

1. **Select or create an issue.** Define the problem, scope, and acceptance criteria using `.github/ISSUE_TEMPLATE/`.
2. **Update local information.** Fetch and confirm `main` is current.
3. **Create a focused branch** from `main` using the naming conventions below.
4. **Implement the task in slices.** Split behavior, tests, and documentation into multiple focused commits; use sequential or stacked pull requests when the slices are independently reviewable. Avoid unrelated refactoring or opportunistic changes.
5. **Add or update tests.** If automated tests are not available, describe the manual verification and remaining gaps.
6. **Update documentation** affected by the change.
7. **Run checks.** At minimum, compile/syntax checks and `git diff --check`; run the available test suite when one exists.
8. **Review the diff and status.** Inspect `git diff`, `git diff --cached`, and `git status` before requesting review.
9. **Push the branch only when authorized.** Do not push directly to `main`.
10. **Open a pull request** using `.github/PULL_REQUEST_TEMPLATE.md` and link the issue.
11. **Review and merge** after approval and required checks. Delete the branch after merge if the repository policy allows it.

## Branch naming

| Prefix | Use |
| --- | --- |
| `feat/` | New user-visible functionality |
| `fix/` | Bug or security fix |
| `test/` | Tests and test infrastructure |
| `docs/` | Documentation only |
| `chore/` | Maintenance, tooling, configuration |

Use a short, lowercase, hyphenated description, for example `fix/runtime-bootstrap` or `docs/api-reference`.

## Commit messages

Use Conventional Commits:

```text
<type>(optional scope): <short summary>

Optional body explaining why the change is needed and any trade-offs.
```

Common types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `build`, `ci`. Keep the subject imperative and under roughly 72 characters. Do not include secrets or personal data.

## Testing expectations

- Add tests for changed logic whenever practical.
- Do not weaken assertions or security checks to make a test pass.
- For camera/model-dependent behavior, document the exact manual steps, assets, and hardware used.
- Report what was run and what could not be run.
- Do not claim a test passed unless it was executed.

Focused runtime tests live under `tests/runtime/`; camera-dependent scripts remain manual. See [TESTING.md](TESTING.md).

## Documentation expectations

Update the relevant documents in the same pull request:

| Change | Documents |
| --- | --- |
| Requirements or status | `docs/PROJECT_SPEC.md`, `docs/PROJECT_STATUS.md` |
| Architecture or data flow | `docs/ARCHITECTURE.md` |
| Endpoint behavior | `docs/API_REFERENCE.md` |
| Database schema | `docs/DATABASE.md` |
| Configuration | `docs/CONFIGURATION.md` |
| Setup | `docs/SETUP.md` |
| Tests | `docs/TESTING.md` |
| Security/privacy | `docs/SECURITY_AND_PRIVACY.md`, `SECURITY.md` |
| Significant decision | `docs/DECISIONS.md` |
| Known gap | `docs/KNOWN_ISSUES.md` |

Do not duplicate the same specification across files; link to the authoritative document.

## Pull requests

Use `.github/PULL_REQUEST_TEMPLATE.md`. A good pull request includes:

- the problem and linked issue;
- the focused change;
- tests run and their results;
- manual verification and unverified areas;
- security/privacy impact;
- documentation updates;
- breaking changes, if any.

Keep pull requests small. Split unrelated cleanup into a separate issue and branch. For larger features, use multiple focused PRs and avoid one large mixed change.

## Review expectations

Reviewers should check:

- correctness against the issue and source behavior;
- scope and unnecessary changes;
- API/schema compatibility;
- error handling and input validation;
- biometric-data handling and secret exposure;
- tests and documentation;
- commit history clarity.

Do not approve a change that claims unverified behavior works.

## Merge policy

The CI workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs compile checks, focused tests, and a secret scan on pull requests and pushes to `main`.

Branch protection is not configured yet. The repository owner should create a `main` protection rule that requires a pull request, the `Compile and test` and `Secret scan` checks, an up-to-date branch, and no force pushes or deletions. The exact steps are in [TESTING.md](TESTING.md#ci).

Until the rule exists:

- obtain explicit human approval;
- run the checks documented in the pull request;
- confirm both CI jobs pass before merging;
- use the merge method agreed by the maintainer;
- do not force-push shared branches;
- do not rewrite `main` history.

## Security and sensitive data

- Never commit `.env` files, credentials, tokens, private keys, face images, embeddings, attendance databases, or model binaries.
- Use synthetic or explicitly consented test data.
- Report vulnerabilities privately per [SECURITY.md](../SECURITY.md).
- If a secret is committed, rotate it and involve the repository owner before any history rewrite.

## Useful commands

```bash
git switch main
git pull --ff-only
git switch -c fix/example
git status
git diff
git diff --check
python -m compileall -q app tests test_api_attendance.py test_liveness_service.py
git diff --cached
```

Push and pull-request commands require explicit authorization:

```bash
git push -u origin fix/example
```

For coding agents, [AGENTS.md](../AGENTS.md) adds stricter rules: never commit, push, or create remote resources without explicit authorization.
