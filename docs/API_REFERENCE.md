# API Reference

This document describes the endpoints implemented in the current code. FastAPI's automatic OpenAPI documentation is available at `/docs` and `/redoc` when the application starts successfully.

## General behavior

- Base URL in local examples: `http://127.0.0.1:8000`.
- `GET /`, `POST /auth/token`, `/docs`, and `/redoc` are public. Every other endpoint requires an `Authorization: Bearer <token>` header.
- Obtain a token from `POST /auth/token`, then send it as `Authorization: Bearer <access_token>`.
- Tokens are opaque, stored as SHA-256 hashes, and expire after `AUTH_TOKEN_TTL_SECONDS` (default 3600 seconds). `POST /auth/logout`, a password reset, or account deactivation revokes tokens.
- Roles are `student` and `admin`. Students may use liveness and mark/read only their own attendance. Admins may read attendance records but cannot start liveness sessions or mark attendance.
- Authentication failures return HTTP `401` with `{"detail": "Not authenticated"}` (or `{"detail": "Incorrect username or password"}` for login). Role and ownership violations return HTTP `403` with `{"detail": "Forbidden"}`. These responses include `WWW-Authenticate: Bearer` for `401`.
- Request bodies use multipart form data where files or `Form` fields are declared; `POST /auth/token` uses form-urlencoded data.
- Application-level errors return a JSON object with `status: "error"` and typically HTTP `200`. Missing required form fields are rejected by FastAPI with HTTP `422`.
- Client-controlled identifiers and uploads are validated before model inference. Upload size and decoded image limits are enforced from settings.
- Client-facing error messages are stable and do not include internal exception details.
- CORS allows credentials from the origins in `CORS_ALLOWED_ORIGINS`. The default is `http://127.0.0.1:5500`, `http://localhost:5500`, `http://127.0.0.1:5173`, and `http://localhost:5173`.
- Liveness sessions are stored in process memory, are bound to the authenticated user ID, and are not shared between workers or restarts.
- The `attendance`, `users`, and `auth_tokens` tables are initialized idempotently during application startup. Retrieval against a fresh initialized database returns an empty list.

## Endpoint summary

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| GET | `/` | Service liveness probe/message | Public |
| POST | `/auth/token` | Exchange username/password for a bearer token | Public |
| GET | `/auth/me` | Return the current account | Bearer, any role |
| POST | `/auth/logout` | Revoke the current token | Bearer, any role |
| POST | `/liveness/start` | Create a user-bound liveness session | Bearer, student |
| POST | `/liveness/frame` | Submit a webcam frame for liveness processing | Bearer, student and session owner |
| POST | `/attendance/verify` | Verify liveness + face and mark attendance | Bearer, student; `student_id` must match |
| GET | `/attendance/student/{student_id}` | List a student's attendance | Bearer, student self or admin |
| GET | `/attendance/all` | List all attendance records | Bearer, admin |

---

## Authorization and authentication

### Roles

| Role | Capabilities |
| --- | --- |
| `student` | Start and submit their own liveness sessions; verify and mark only their own attendance; read only their own attendance. |
| `admin` | Read any student's attendance and all attendance records. Cannot start liveness sessions, submit frames, or mark attendance. |

There is no public signup. Accounts are provisioned locally with `python -m app.auth.cli`; see [CONFIGURATION.md](CONFIGURATION.md).

### Authorization matrix

| Endpoint | Unauthenticated | Student | Admin |
| --- | --- | --- | --- |
| `GET /` | Allowed | Allowed | Allowed |
| `POST /auth/token` | Allowed | Allowed | Allowed |
| `GET /auth/me` | `401` | Own account | Own account |
| `POST /auth/logout` | `401` | Revokes own token | Revokes own token |
| `POST /liveness/start` | `401` | Allowed | `403` |
| `POST /liveness/frame` | `401` | Own session only | `403` |
| `POST /attendance/verify` | `401` | Own `student_id` and own session only | `403` |
| `GET /attendance/student/{student_id}` | `401` | Own records only | Any student |
| `GET /attendance/all` | `401` | `403` | Allowed |

---

## POST `/auth/token`

Exchanges a username and password for an opaque bearer token.

**Request (`application/x-www-form-urlencoded`):**

| Name | Type | Required |
| --- | --- | --- |
| `username` | string | Yes |
| `password` | string | Yes |

Example:

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=student1" \
  --data-urlencode "password=<password>"
```

**Success response `200`:**

```json
{
  "access_token": "<opaque-token>",
  "token_type": "bearer",
  "expires_at": "2026-10-31T18:00:00+00:00"
}
```

**Failure response `401`:**

```json
{
  "detail": "Incorrect username or password"
}
```

The route does not distinguish an unknown username from a wrong password. Tokens are not returned by any other endpoint and should not be logged.

---

## GET `/auth/me`

Returns the authenticated account. Requires a bearer token for any role.

**Response `200`:**

```json
{
  "username": "student1",
  "role": "student",
  "student_id": "STU001"
}
```

Admin accounts return `"student_id": null`.

**Failure responses:** `401` for a missing, invalid, expired, or revoked token.

---

## POST `/auth/logout`

Revokes the token used for the request.

**Response `200`:**

```json
{
  "status": "success",
  "message": "Logged out"
}
```

**Failure responses:** `401` for a missing or invalid token. Calling logout again with the same token returns `401` because the token is revoked.

---

## GET `/`

Returns a static service message. Public.

**Response `200`:**

```json
{
  "message": "AI Attendance Service is running"
}
```

This endpoint does not verify that models or the database are ready.

---

## POST `/liveness/start`

Creates an in-memory liveness session bound to the authenticated student.

**Authorization:** bearer token with role `student`.

**Request:** no body or parameters.

Example:

```bash
curl -X POST http://127.0.0.1:8000/liveness/start \
  -H "Authorization: Bearer <token>"
```

**Response `200`:**

```json
{
  "status": "success",
  "session_id": "<uuid>",
  "message": "Liveness session started"
}
```

**Side effects:** inserts a new entry into the process-local `sessions` dictionary with the authenticated user ID.

**Failure behavior:** `401` without a valid token; `403` for admin accounts. A process restart loses all sessions.

---

## POST `/liveness/frame`

Processes one uploaded image for a liveness session. The session must belong to the authenticated student.

**Authorization:** bearer token with role `student`.

**Request:**

| Name | Location | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `session_id` | Query | string | Yes | Session returned by `/liveness/start`. |
| `image` | Multipart file | file | Yes | Content type starting with `image/`, decodable by OpenCV, within configured size and dimensions. |

Example:

```bash
curl -X POST "http://127.0.0.1:8000/liveness/frame?session_id=<uuid>" \
  -H "Authorization: Bearer <token>" \
  -F "image=@frame.jpg"
```

**Success response `200`:**

```json
{
  "status": "success",
  "session_id": "<uuid>",
  "face_detected": true,
  "ear": 0.27,
  "eyes_closed": false,
  "closed_frames": 0,
  "blink_detected": false,
  "liveness_verified": false
}
```

If the session is already verified and still valid, the route returns a success object with `face_detected: true`, `ear: null`, `eyes_closed: false`, `closed_frames: 0`, `blink_detected: false`, and `liveness_verified: true`.

**Authentication/authorization errors:**

| Condition | Response |
| --- | --- |
| Missing, invalid, expired, or revoked token | HTTP `401` |
| Admin account | HTTP `403` |
| Session belongs to another student | HTTP `403` with `{"detail": "Forbidden"}` |

**Application-level errors (HTTP `200`):**

| Condition | Response |
| --- | --- |
| Invalid session identifier | `{"status": "error", "message": "Invalid liveness session"}` |
| Unknown session | `{"status": "error", "message": "Invalid or expired liveness session"}` |
| Verified session older than `LIVENESS_VALIDITY_SECONDS` (default 30) | Session is deleted; `{"status": "error", "message": "Liveness session expired"}` |
| Invalid or unsupported image | `{"status": "error", "message": "Invalid or unsupported image"}` |
| Image exceeds maximum allowed size | `{"status": "error", "message": "Image exceeds maximum allowed size"}` |
| Image dimensions exceed maximum allowed size | `{"status": "error", "message": "Image dimensions exceed maximum allowed size"}` |

**Not exposed in the response:** `LivenessService.process_frame` returns an `anti_spoofing` object, but the route does not include it. The screening result affects the internal `liveness_verified` decision.

**Side effects:** updates `closed_frames`, `eyes_closed`, and potentially `liveness_verified`/`verified_at` in the in-memory session.

---

## POST `/attendance/verify`

Verifies a liveness session and a face image, then attempts to persist attendance. The authenticated student must match the submitted `student_id` and own the liveness session.

**Authorization:** bearer token with role `student`.

**Request (multipart form):**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `student_id` | string | Yes | Must equal the authenticated student's `student_id`. Safe identifier (max 64 characters, alphanumeric start, no path separators). Located under `<FACE_EMBEDDING_DIR>`. |
| `session_id` | string | Yes | Valid UUID. Must belong to the authenticated student, be liveness-verified, and be less than `LIVENESS_VALIDITY_SECONDS` old. |
| `subject` | string | Yes | Max 120 characters, non-empty, and free of control characters. |
| `lecture_id` | string | Yes | Safe identifier (max 64 characters, alphanumeric start, no path separators). |
| `image` | file | Yes | Content type starting with `image/`, decodable by OpenCV, within configured size and dimensions. |

Example:

```bash
curl -X POST http://127.0.0.1:8000/attendance/verify \
  -H "Authorization: Bearer <token>" \
  -F "student_id=STU001" \
  -F "session_id=<uuid>" \
  -F "subject=Java Programming" \
  -F "lecture_id=JAVA-LECTURE-001" \
  -F "image=@face.jpg"
```

**Authentication/authorization errors:**

| Condition | Response |
| --- | --- |
| Missing, invalid, expired, or revoked token | HTTP `401` |
| Admin account | HTTP `403` |
| `student_id` does not match the authenticated student | HTTP `403` with `{"detail": "Forbidden"}` |
| Liveness session belongs to another student | HTTP `403` with `{"detail": "Forbidden"}` |

### Pre-verification errors

These return HTTP `200` with an error object:

| Condition | Response |
| --- | --- |
| Invalid session identifier | `{"status": "error", "message": "Invalid liveness session"}` |
| Unknown session | `{"status": "error", "message": "Invalid or expired liveness session"}` |
| Invalid student identifier | `{"status": "error", "message": "Invalid student identifier"}` |
| Invalid subject | `{"status": "error", "message": "Invalid subject"}` |
| Invalid lecture identifier | `{"status": "error", "message": "Invalid lecture identifier"}` |
| Invalid or unsupported image | `{"status": "error", "message": "Invalid or unsupported image"}` |
| Image exceeds maximum allowed size | `{"status": "error", "message": "Image exceeds maximum allowed size"}` |
| Image dimensions exceed maximum allowed size | `{"status": "error", "message": "Image dimensions exceed maximum allowed size"}` |
| Session exists but is not liveness-verified | `{"status": "error", "message": "Liveness verification required"}` |
| Missing verification timestamp | `{"status": "error", "message": "Invalid liveness verification"}` |
| Verification older than `LIVENESS_VALIDITY_SECONDS` (default 30) | Session removed; `{"status": "error", "message": "Liveness session expired"}` |

### Rejected face

When the face does not match (or cannot be processed), the session is consumed and the route returns:

```json
{
  "status": "rejected",
  "message": "Face verification failed",
  "attendance_status": "ABSENT",
  "student_id": "STU001",
  "subject": "Java Programming",
  "lecture_id": "JAVA-LECTURE-001",
  "liveness": "VERIFIED",
  "face": "UNKNOWN",
  "similarity": 0.21
}
```

Possible `face` values include `MATCH`, `UNKNOWN`, `NO_FACE`, and `ERROR`, depending on the recognition result. `similarity` may be `null`.

### Success

```json
{
  "status": "success",
  "message": "Attendance marked successfully",
  "attendance_status": "PRESENT",
  "student_id": "STU001",
  "subject": "Java Programming",
  "lecture_id": "JAVA-LECTURE-001",
  "liveness_status": "VERIFIED",
  "face_status": "MATCH",
  "liveness": "VERIFIED",
  "face": "MATCH",
  "similarity": 0.653,
  "duplicate": false,
  "attendance_record": {
    "success": true,
    "attendance_id": 1,
    "student_id": "STU001",
    "subject": "Java Programming",
    "lecture_id": "JAVA-LECTURE-001",
    "date": "2026-10-27",
    "time": "10:15:00",
    "status": "PRESENT"
  }
}
```

### Duplicate

If the database uniqueness constraint rejects the insert:

```json
{
  "status": "duplicate",
  "message": "Attendance already marked for this lecture",
  "attendance_status": "ALREADY_MARKED",
  "student_id": "STU001",
  "subject": "Java Programming",
  "lecture_id": "JAVA-LECTURE-001",
  "liveness_status": "VERIFIED",
  "face_status": "MATCH",
  "liveness": "VERIFIED",
  "face": "MATCH",
  "similarity": 0.653,
  "duplicate": true,
  "attendance_record": {
    "success": false,
    "duplicate": true,
    "message": "Attendance already marked for this lecture"
  }
}
```

### Unexpected errors

The route catches `Exception` and returns:

```json
{
  "status": "error",
  "message": "Internal attendance verification error"
}
```

The underlying exception details are printed server-side and are not returned to the client.

**Side effects:** writes a temporary file (deleted in `finally`), loads models, may insert an attendance row, and removes the liveness session after rejection or a database attempt. Pre-verification failures do not consume the session, except expiry. Authorization failures do not consume the session.

**Dependencies:** the student's embedding must exist; the database schema is initialized at startup for the configured path.

---

## GET `/attendance/student/{student_id}`

Returns all attendance records for one student, newest first by date and time.

**Authorization:** a student may request only their own `student_id`; an admin may request any student.

**Path parameter:** `student_id` (string).

**Response `200`:**

```json
{
  "status": "success",
  "student_id": "STU001",
  "count": 1,
  "attendance": [
    {
      "id": 1,
      "student_id": "STU001",
      "subject": "Java Programming",
      "lecture_id": "JAVA-LECTURE-001",
      "attendance_date": "2026-10-27",
      "attendance_time": "10:15:00",
      "liveness_status": "VERIFIED",
      "face_status": "MATCH",
      "similarity": 0.653,
      "attendance_status": "PRESENT",
      "created_at": "2026-10-27T10:15:00"
    }
  ]
}
```

**Failure behavior:** `401` without a valid token; `403` when a student requests another student's records. Retrieval database exceptions return an error object with `status: "error"` and `"message": "Attendance database error"`. A fresh initialized database returns an empty list.

---

## GET `/attendance/all`

Returns all attendance records, newest first by date and time.

**Authorization:** bearer token with role `admin`.

**Response `200`:**

```json
{
  "status": "success",
  "count": 0,
  "attendance": []
}
```

**Failure behavior:** `401` without a valid token; `403` for student accounts. Same database-error behavior as the student endpoint. There is no pagination or filtering.

## Security notes

- Authentication is required for every endpoint except `GET /`, `POST /auth/token`, and the OpenAPI documentation.
- Passwords are stored as Argon2id hashes. Bearer tokens are stored as SHA-256 hashes with an expiry; plaintext tokens are never stored by the server.
- Liveness sessions are bound to the authenticated user ID but remain in process memory. `session_id` is still sent as a query parameter and behaves like a short-lived capability; do not log it.
- HTTPS, rate limiting, account lockout, token-theft detection, and comprehensive audit logging are not implemented. Do not use bearer tokens over plaintext networks.
- The final attendance image is not cryptographically bound to the liveness frames.
- `student_id`, `subject`, and `lecture_id` are validated before use, and uploaded images are size- and dimension-checked before model inference.
- Error messages are stable client-facing responses and do not include raw exception details; server-side logs may contain operational details.
