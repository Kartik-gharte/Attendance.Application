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
| Liveness session IDs | Process memory, query strings, client state | Sensitive short-lived capability. |
| Console logs | Standard output | May contain student IDs, subject/lecture IDs, filenames, similarity, and error text. |

`.gitignore` excludes `data/`, `models/`, `*.npy`, `*.db`, `.env`, and image files. This is a repository-hygiene control, not encryption or access control.

## Current controls

- SQL queries use parameterized statements.
- Uploaded attendance images are written to a temporary file and deleted in a `finally` block.
- Client identifiers are validated and embedding paths are contained before lookup.
- Upload size, content type, and decoded image limits are enforced before model inference.
- Liveness sessions expire after `LIVENESS_VALIDITY_SECONDS` (default 30); they are consumed after a face-verification rejection or a database insert attempt.
- CORS defaults to local development origins and is configurable through `CORS_ALLOWED_ORIGINS`. CORS is not an access-control mechanism.
- Face images, embeddings, databases, and model files are excluded from Git.
- Face matching requires a single detected face and a similarity of at least `FACE_MATCH_THRESHOLD` (default `0.40`).
- Attendance and retrieval error responses use stable client-facing messages; server-side exception details are not returned.

## Current gaps and risks

### No authentication or authorization

Every endpoint is open. Anyone who can reach the API can start sessions, submit frames, mark attendance for a supplied `student_id`, and read all attendance records. CORS is not an access-control mechanism; non-browser clients can call the API directly.

### Session and replay risks

- Liveness sessions are bearer-like identifiers with no binding to a student, device, or IP address.
- `session_id` is sent as a query parameter for `/liveness/frame`, so it may be captured in proxy or server logs.
- The final attendance image is not cryptographically tied to the liveness frames.
- Sessions are stored in one process's memory; multiple workers or restarts change behavior.
- Abandoned sessions are never cleaned up, causing unbounded memory growth over time.

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

Identifier validation, embedding-path containment, upload limits, and stable error responses are already implemented. Remaining work:

1. Add authentication and role-based authorization; protect all attendance endpoints.
2. Bind liveness sessions to a student/request and use non-query transport for session IDs.
3. Introduce structured, redacted logging.
4. Add HTTPS, rate limiting, and secure deployment configuration.
5. Encrypt or otherwise protect biometric storage; restrict filesystem access.
6. Define consent, retention, deletion, and access-review policies.
7. Evaluate a trained presentation-attack detection component before claiming anti-spoofing security.
8. Add dependency and secret scanning to the development workflow.

## Reporting

See [SECURITY.md](../SECURITY.md). Do not include real biometric data or secrets in a report.
