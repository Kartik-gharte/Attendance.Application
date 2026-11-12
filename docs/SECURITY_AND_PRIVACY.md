# Security and Privacy

## Scope

This document covers the current implementation only. It does not certify the system for production use or assert legal compliance.

## Biometric data and personal data

The system processes:

| Data | Where it appears | Sensitivity |
| --- | --- | --- |
| Face images / webcam frames | HTTP uploads; the final attendance image is briefly written to a temporary file | High — biometric identifiers. |
| Face embeddings (`.npy`) | `FACE_EMBEDDING_DIR/<student_id>.npy` (default `data/face_embeddings/`) | High — derived biometric data. |
| Attendance records | `ATTENDANCE_DB_PATH` (default `data/attendance.db`) | Personal data (student ID, subject, lecture, timestamps, similarity). |
| Account data | `users` table in `ATTENDANCE_DB_PATH` | Username, Argon2id password hash, role, linked student ID. |
| Bearer tokens | `auth_tokens` table and client memory | Sensitive credentials; only SHA-256 hashes and expiry timestamps are stored. |
| Liveness session IDs | Process memory, query strings, client state | Sensitive short-lived capability. |
| Console logs | Standard output | May contain student IDs, subject/lecture IDs, filenames, similarity, and error text. Credentials and raw tokens are not logged by the current code. |

`.gitignore` excludes `data/`, `models/`, `*.npy`, `*.db`, `.env`, and image files. This is a repository-hygiene control, not encryption or access control.

## Current controls

- SQL queries use parameterized statements.
- Local accounts are required for biometric operations and attendance retrieval. There is no public signup.
- Passwords are hashed with Argon2id (`argon2-cffi`) with a minimum length of 12 characters. Plaintext passwords are not stored.
- Authentication uses opaque 256-bit bearer tokens. The server stores only SHA-256 token hashes, expiry timestamps, and revocation timestamps.
- Tokens expire after `AUTH_TOKEN_TTL_SECONDS` (default 3600 seconds). Logout, password reset, and account deactivation revoke tokens.
- Students can only mark and read their own attendance. Admins can read attendance but cannot mark it.
- Liveness sessions are bound to the authenticated user ID and cannot be submitted by another authenticated student.
- Uploaded attendance images are written to a temporary file and deleted in a `finally` block.
- Client identifiers are validated and embedding paths are contained before lookup.
- Upload size, content type, and decoded image limits are enforced before model inference.
- Liveness sessions expire after `LIVENESS_VALIDITY_SECONDS` (default 30); they are consumed after a face-verification rejection or a database insert attempt.
- CORS defaults to local development origins and is configurable through `CORS_ALLOWED_ORIGINS`. CORS is not an access-control mechanism.
- Face images, embeddings, databases, and model files are excluded from Git.
- Face matching requires a single detected face and a similarity of at least `FACE_MATCH_THRESHOLD` (default `0.40`).
- Attendance and retrieval error responses use stable client-facing messages; server-side exception details are not returned.
- Authentication failures return `401`; role and ownership violations return `403`.

## Current gaps and risks

### Authentication and authorization limits

Authentication is implemented, but it is a local-account baseline, not a production identity platform:

- Account provisioning and password resets are manual CLI operations.
- There is no rate limiting, account lockout, login audit log, or anomaly detection.
- Tokens are bearer credentials. Anyone who obtains one can use it until expiry or revocation; there is no sender binding, device binding, or token-theft detection.
- There is no MFA, SSO, or institutional identity integration.
- There is no per-lecture enrollment or subject-level authorization; a student can mark attendance for any subject/lecture ID with a matching face.
- Admin accounts have broad read access to all attendance records; there is no finer-grained faculty scoping.
- TLS is not configured by the application. Bearer tokens and passwords must not be sent over plaintext networks.

### Session and replay risks

- Liveness sessions are bound to an authenticated user ID, but they remain bearer-like identifiers with no device, IP, or cryptographic challenge binding.
- `session_id` is sent as a query parameter for `/liveness/frame`, so it may be captured in proxy or server logs.
- The final attendance image is not cryptographically tied to the liveness frames.
- Sessions are stored in one process's memory; multiple workers or restarts change behavior.
- Abandoned sessions are never cleaned up, causing unbounded memory growth over time.
- A captured session may be replayed within the configured validity window by the same authenticated user.

### Path construction from user input

`student_id` is validated against a safe identifier pattern and the resolved embedding path is checked against the configured embedding directory before lookup (`app/services/face_recognition.py`). Values containing path separators, `..`, or an absolute path are rejected.

### Input validation

- `student_id`, `subject`, and `lecture_id` are now validated, upload size and image limits are enforced, and images are decoded before model inference.
- There is no verification that the student is enrolled in the supplied subject or lecture.
- `subject` and `lecture_id` are validated with defined limits and patterns before use.

### Error handling and information disclosure

`POST /attendance/verify` returns stable internal error messages to clients instead of raw exception text. Retrieval endpoints catch database failures and return a controlled error response.

### Logging

The code uses `print()` rather than structured logging. Logs include student IDs, subject/lecture identifiers, filenames, similarity, and error details. There is no log level, redaction, rotation, or retention policy. Do not log raw images, embeddings, session IDs, or credentials.

### Storage protection

Embeddings and the attendance database are stored unencrypted on the local filesystem. Filesystem permissions are the only access control. There is no encryption at rest, key management, or backup policy.

### Data retention and deletion

There is no retention period, deletion endpoint, or subject-access workflow. Deleting a local `data/` directory removes records but is manual and not auditable. A production design needs documented retention, deletion, and backup handling.

### Anti-spoofing limitations

The blink check plus face-size, brightness, and sharpness screening is **not** a trained or certified presentation-attack detection system. It can likely be bypassed by determined attackers using replayed video, prepared displays, or other presentation attacks. Do not describe it as robust anti-spoofing or use it as the sole security control for high-stakes attendance.

### Consent and legal obligations

Face data is sensitive personal data in many jurisdictions, including regimes such as GDPR, BIPA, and India's DPDP Act. The repository does not include consent notices, privacy notices, retention schedules, or a lawful-basis assessment. Obtain institutional/legal review before collecting real student biometric data. This document is not legal advice.

## Recommended remediation order

Identifier validation, embedding-path containment, upload limits, stable error responses, local authentication, and role-based attendance authorization are already implemented. Remaining work:

1. Add rate limiting, account lockout, and login/authorization audit events.
2. Move liveness session IDs out of query strings and bind them to a stronger one-time challenge.
3. Introduce structured, redacted logging.
4. Add HTTPS, secure deployment configuration, and token handling guidance for clients.
5. Encrypt or otherwise protect biometric storage; restrict filesystem access.
6. Define consent, retention, deletion, and access-review policies.
7. Evaluate a trained presentation-attack detection component before claiming anti-spoofing security.
8. Add dependency and secret scanning to the development workflow.
9. Consider SSO/institutional identity and MFA before broader deployment.

## Reporting

See [SECURITY.md](../SECURITY.md). Do not include real biometric data or secrets in a report.

## Logging and redaction

Application logs are a personal-data store. They may contain `student_id`
values so that an administrator can reconcile attendance records, and they
must be access-controlled and retained only as long as the operational need
requires.

The following must never appear in logs at any level, and are masked by the
redaction filter in `app/core/logging_config.py`:

| Value | Reason |
| --- | --- |
| Raw images, video frames, face crops | Biometric data |
| Face embeddings and `.npy` embedding contents | Biometric data |
| Bearer tokens, passwords, API keys, secrets | Credential material |
| Liveness session identifiers | A session is a bearer-like capability |
| Full multipart request bodies | May contain biometric or credential material |

Redaction is applied when a log record is created, so it protects every
handler including handlers an operator attaches later. A test captures the
log stream during a successful attendance attempt and asserts that the
bearer token, the liveness session identifier, and the account password do
not appear.

`student_id` is logged at `INFO` level for attendance outcomes only. It is
never logged together with raw biometric material. Operators who require
logs without personal identifiers should run at `WARNING` level or above,
where per-request identifiers are not emitted.

Internal filesystem paths may appear in exception diagnostics at `ERROR`
level. Operators who require path-free logs should run at `WARNING` level
or above, where server-side diagnostics are limited to the exception type.

### Retention and access

The application does not write log files and does not implement log
retention or rotation. Retention, rotation, and access control are the
responsibility of the process supervisor or container runtime that captures
stderr. When the service is deployed, configure the runtime with an
appropriate retention period and restrict access to the log stream.

Logs are not an audit system. They are diagnostic output and do not provide
tamper-evident records of attendance operations.

## Enrollment consent and authorization

Enrollment writes a biometric template. It is a controlled local operation
that is not exposed through the API, and it is not reachable by a student
account.

Before an enrollment is performed:

- the person in the source image must have consented to being enrolled;
- the source image must contain exactly one face, so that the template is
  unambiguous;
- the image must not be committed to the repository. Face images and
  embeddings are gitignored.

Controls that protect the enrollment workflow:

- the student identifier is validated against a strict pattern before it is
  used to build a path;
- the destination is always resolved inside the configured embedding
  directory, and a caller cannot point it elsewhere;
- an existing embedding is never replaced without an explicit `--overwrite`
  flag, because replacing it makes the student unverifiable against the
  previous template;
- the embedding is written to a temporary file and moved into place only
  after it is complete, so a failure never leaves a corrupt template;
- the workflow logs operational metadata only. Embedding vectors and image
  contents are never written to the log.

There is no self-service enrollment path and no enrollment audit trail.
Both remain future work.

## Backups

A backup contains the attendance database and the face embeddings. It is
therefore a personal-data store and a copy of biometric templates.

Controls that apply to a backup:

- the database copy is created with the SQLite online backup API, so it is
  consistent and does not capture a half-written transaction;
- the backup does not contain plaintext credentials. Passwords are stored
  as Argon2id hashes and bearer tokens as SHA-256 hashes;
- the backup records a SHA-256 checksum of the database and the schema
  version, so a truncated or tampered backup is detected by the verify
  command before it is restored;
- restoring refuses to replace a live database without an explicit
  overwrite flag, and always writes a safety copy of the current database
  first;
- a restore that fails puts the safety copy back.

A backup is still sensitive. It must be stored with the same access
controls as the live data, kept only as long as the operational need
requires, and deleted when it is no longer needed. Backups must not be
committed to the repository. The `data/` directory is gitignored, and the
default backup location lives inside it.

## Health endpoints

The health and readiness endpoints are unauthenticated so that a process
supervisor or a load balancer can reach them. They expose only operational
status.

They do not expose:

- student identifiers, subjects, or lecture identifiers;
- credentials, tokens, or password hashes;
- filesystem paths such as the database path or the embedding directory;
- model contents, embeddings, or images.

A test asserts each of these is absent from the responses. The readiness
endpoint reports the schema version, which is a number the application
publishes anyway, and whether the models are loaded, which is a boolean.
