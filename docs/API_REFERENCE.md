# API Reference

This document describes the endpoints implemented in the current code. FastAPI's automatic OpenAPI documentation is available at `/docs` and `/redoc` when the application starts successfully.

## General behavior

- Base URL in local examples: `http://127.0.0.1:8000`.
- There is no authentication or authorization.
- Request bodies use multipart form data where files or `Form` fields are declared.
- Application-level errors return a JSON object with `status: "error"` and typically HTTP `200`. Missing required form fields are rejected by FastAPI with HTTP `422`.
- Client-controlled identifiers and uploads are validated before model inference. Upload size and decoded image limits are enforced from settings.
- Client-facing error messages are stable and do not include internal exception details.
- CORS allows credentials from the origins in `CORS_ALLOWED_ORIGINS`. The default is `http://127.0.0.1:5500`, `http://localhost:5500`, `http://127.0.0.1:5173`, and `http://localhost:5173`.
- Liveness sessions are stored in process memory and are not shared between workers or restarts.
- The `attendance` table is initialized idempotently during application startup. Retrieval against a fresh initialized database returns an empty list.

## Endpoint summary

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| GET | `/` | Service liveness probe/message | None |
| POST | `/liveness/start` | Create a liveness session | None |
| POST | `/liveness/frame` | Submit a webcam frame for liveness processing | None |
| POST | `/attendance/verify` | Verify liveness + face and mark attendance | None |
| GET | `/attendance/student/{student_id}` | List a student's attendance | None |
| GET | `/attendance/all` | List all attendance records | None |

---

## GET `/`

Returns a static service message.

**Request:** no parameters.

**Response `200`:**

```json
{
  "message": "AI Attendance Service is running"
}
```

This endpoint does not verify that models or the database are ready.

---

## POST `/liveness/start`

Creates an in-memory liveness session.

**Request:** no body or parameters.

**Response `200`:**

```json
{
  "status": "success",
  "session_id": "<uuid>",
  "message": "Liveness session started"
}
```

**Side effects:** inserts a new entry into the process-local `sessions` dictionary.

**Failure behavior:** none specified by the route. A process restart loses all sessions.

---

## POST `/liveness/frame`

Processes one uploaded image for a liveness session.

**Request:**

| Name | Location | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `session_id` | Query | string | Yes | Session returned by `/liveness/start`. |
| `image` | Multipart file | file | Yes | Content type starting with `image/`, decodable by OpenCV, within configured size and dimensions. |

Example:

```bash
curl -X POST "http://127.0.0.1:8000/liveness/frame?session_id=<uuid>" \
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

Verifies a liveness session and a face image, then attempts to persist attendance.

**Request (multipart form):**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `student_id` | string | Yes | Safe identifier (max 64 characters, alphanumeric start, no path separators). Located under `<FACE_EMBEDDING_DIR>`. Not authenticated. |
| `session_id` | string | Yes | Valid UUID. Must be liveness-verified and less than `LIVENESS_VALIDITY_SECONDS` old. |
| `subject` | string | Yes | Max 120 characters, non-empty, and free of control characters. |
| `lecture_id` | string | Yes | Safe identifier (max 64 characters, alphanumeric start, no path separators). |
| `image` | file | Yes | Content type starting with `image/`, decodable by OpenCV, within configured size and dimensions. |

Example:

```bash
curl -X POST http://127.0.0.1:8000/attendance/verify \
  -F "student_id=STU001" \
  -F "session_id=<uuid>" \
  -F "subject=Java Programming" \
  -F "lecture_id=JAVA-LECTURE-001" \
  -F "image=@face.jpg"
```

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

**Side effects:** writes a temporary file (deleted in `finally`), loads models, may insert an attendance row, and removes the liveness session after rejection or a database attempt. Pre-verification failures do not consume the session, except expiry.

**Dependencies:** the student's embedding must exist; the database schema is initialized at startup for the configured path.

---

## GET `/attendance/student/{student_id}`

Returns all attendance records for one student, newest first by date and time.

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

**Failure behavior:** catches retrieval database exceptions and returns an error object with `status: "error"` and `"message": "Attendance database error"`. A fresh initialized database returns an empty list.

---

## GET `/attendance/all`

Returns all attendance records, newest first by date and time.

**Response `200`:**

```json
{
  "status": "success",
  "count": 0,
  "attendance": []
}
```

**Failure behavior:** same as the student endpoint. There is no pagination, filtering, or access control.

## Security notes

- Every endpoint is unauthenticated and unauthenticated callers can read all attendance records.
- `session_id` behaves like a bearer token for a short-lived liveness result. Do not log or expose it.
- `student_id`, `subject`, and `lecture_id` are validated before use, and uploaded images are size- and dimension-checked before model inference.
- The final attendance image is not cryptographically bound to the liveness frames.
- Error messages are stable client-facing responses and do not include raw exception details; server-side logs may contain operational details.
