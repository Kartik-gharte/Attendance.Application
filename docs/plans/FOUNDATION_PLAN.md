# Project Foundation Plan

## Status

Documentation prepared and checks pass on `chore/project-foundation`, based on `main` at `79373d6`. Runtime behavior remains unverified.

Repository operations (commit, push, pull request, merge) are performed only with explicit authorization. Obsolete remote feature branches were deleted with explicit authorization; see Git history for the final merge state.

## Objective

Create a documentation-first foundation that lets contributors and coding agents understand the current system, its verified state, its gaps, and the rules for changing it — without altering runtime behavior.

## Constraints

- No application code, dependency, configuration, database, model, or test behavior changes.
- Documentation, GitHub templates, and repository-hygiene ignore rules only.
- No commit, push, remote branch, issue, or pull-request creation without explicit authorization.
- No secrets, credentials, real face images, embeddings, databases, or student data.
- Every status claim must be traceable to inspected code or a recorded check.
- Preserve existing branches, history, and user changes.

## Audit snapshot

| Item | Finding |
| --- | --- |
| Base branch | `main` at `79373d6` |
| Remote state | `main` only; feature branches previously merged and deleted |
| Local backups | `refs/backup/feature-ai-attendance-security` (`0270dd3`), `refs/backup/feature-attendance-verification-stable` (`b688687`), `refs/backup/main-before-attendance-merge-2026-10-26` (`b80e458`), `refs/backup/main-initial` (`4b475fe`) |
| Existing documentation | Only a stale root README; no `AGENTS.md`, `docs/`, or `.github` content |
| Runtime assets | No `data/`, `models/`, or `tests/fixtures/` directory |
| Dependency state | `requirements.txt` empty; `app/core/config.py` empty |
| Test state | Manual camera/model scripts; no pytest suite; root liveness test has a broken import |
| Key startup gap | Hardcoded Windows MediaPipe path; models instantiated at import; database initialization uncalled |
| Security posture | No authentication; open endpoints; heuristic-only anti-spoofing; path construction from `student_id` |

## Deliverables

### Root documentation

- [x] `README.md` — concise project overview, honest limitations, quick links.
- [x] `AGENTS.md` — agent entry point, required reading, mandatory rules.
- [x] `CONTRIBUTING.md` — contribution workflow and checks.
- [x] `SECURITY.md` — private reporting and biometric-data restrictions.
- [x] `CHANGELOG.md` — unreleased foundation changes.

### Documentation set

- [x] `docs/README.md` — index and authority map.
- [x] `docs/PROJECT_SPEC.md` — requirements and implementation status.
- [x] `docs/ARCHITECTURE.md` — components, startup side effects, data flows.
- [x] `docs/API_REFERENCE.md` — endpoint contracts and current errors.
- [x] `docs/DATABASE.md` — schema, constraints, initialization gap.
- [x] `docs/SETUP.md` — intended setup and confirmed blockers.
- [x] `docs/CONFIGURATION.md` — hardcoded settings and proposed configuration.
- [x] `docs/TESTING.md` — actual test state, manual scripts, future plan.
- [x] `docs/SECURITY_AND_PRIVACY.md` — data handling, risks, remediation.
- [x] `docs/DEVELOPMENT_WORKFLOW.md` — issue/branch/commit/PR lifecycle.
- [x] `docs/ROADMAP.md` — phased plan from bootstrap to maturity.
- [x] `docs/PROJECT_STATUS.md` — verified state and blockers.
- [x] `docs/KNOWN_ISSUES.md` — confirmed gaps with severity and fixes.
- [x] `docs/DECISIONS.md` — accepted decisions and proposals.
- [x] `docs/plans/FOUNDATION_PLAN.md` — this plan.

### Repository workflow

- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`
- [x] `.github/ISSUE_TEMPLATE/feature_request.md`
- [x] `.github/ISSUE_TEMPLATE/task.md`
- [x] `.gitignore` hygiene for caches, build artifacts, and model binaries.

## Verification log

| Check | Result | Scope |
| --- | --- | --- |
| `python -m compileall -q app tests test_api_attendance.py test_liveness_service.py` | Passed | Syntax-only; no imports or runtime behavior. |
| Markdown relative-link check | Passed | 24 Markdown files; no broken relative links or anchor links. |
| Sensitive-data scan of the branch diff | Passed | No credential patterns or tracked biometric/model/database artifacts found. |
| `git diff --check` | Passed | Includes tracked changes and untracked files marked intent-to-add. |
| Full `git diff` / `git status` review | Passed | Scope is limited to documentation, templates, and `.gitignore`. |

Update this table before requesting review. Do not replace a pending check with an assumption.

## Out of scope

- Fixing empty dependencies/configuration.
- Making model paths portable.
- Calling `initialize_database()`.
- Repairing or converting tests.
- Authentication, authorization, session hardening, or path-traversal fixes.
- Changing API responses or database schema.
- Committing, pushing, or opening a pull request.

## Risks

- Documentation can drift from code; tie claims to files/lines and re-check before merge.
- The worktree is uncommitted; a careless clean/reset would lose the draft. Do not run destructive Git commands.
- GitHub network checks were intermittent during the audit; local Git state is authoritative for this branch.
- Broad image/model ignore rules protect against accidental biometric commits but can also hide intentional documentation assets; review additions explicitly.

## Handoff / next step

After review and explicit authorization:

1. Commit the documentation/templates with a `docs:` or `chore:` conventional message.
2. Push `chore/project-foundation` and open a pull request using the new template.
3. Merge without runtime changes; verify `main` still matches the known code state.
4. Open the next issue: **Runtime bootstrap and verification**.
5. Use branch `fix/runtime-bootstrap` for dependency manifest, portable configuration/model path, database initialization, and the broken test import.

Do not start runtime fixes on this branch.
