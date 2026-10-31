# Security Policy

Attendance.Application processes biometric information (face images and embeddings) and attendance records. Treat security and privacy issues as high priority.

## Supported versions

There are no tagged releases. Security fixes currently target the `main` branch only. This policy does not promise support for older commits or forks.

## Reporting a vulnerability

Do not open a public issue containing:

- credentials, tokens, or private keys;
- real face images or embeddings;
- student records or attendance database contents;
- exploit details that could enable abuse before a fix is available.

Use GitHub's private vulnerability reporting from the repository **Security** tab if it is enabled. If private reporting is unavailable, open a minimal public issue that describes the affected area without sensitive details and ask the maintainer for a private channel.

There is no security contact email declared in this repository. Do not invent one.

## What to include

- A short description of the issue and its impact.
- Affected endpoint, component, or file.
- Reproduction steps using synthetic or redacted data only.
- Whether authentication, biometric data, or attendance records are involved.
- Any suggested mitigation, if known.

## Scope and current limitations

The current application:

- uses local accounts and opaque bearer tokens, with student self-access and
  read-only admin attendance access;
- binds liveness sessions to the authenticated user but stores them in process
  memory;
- does not implement TLS, rate limiting, account lockout, MFA/SSO, or audit
  logging;
- uses heuristic image screening plus a blink check, not a trained
  presentation-attack detection system;
- normalizes validation and common retrieval errors but may still expose
  unexpected internal errors;
- has no documented data-retention or deletion policy.

These are known limitations, not guarantees of safety. See [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) and [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## Safe research expectations

- Do not access, modify, or exfiltrate real student data.
- Use a local or test environment and synthetic data.
- Do not perform denial-of-service testing against shared or public deployments.
- Give the maintainer reasonable time to respond before public disclosure.
- Do not include secrets in reports; rotate any exposed credential immediately.

## Secret handling

If a credential was committed, removing it from the current tree is not enough: rotate it and assess whether Git history must be rewritten with the repository owner's authorization. Do not rewrite shared history without explicit approval.
