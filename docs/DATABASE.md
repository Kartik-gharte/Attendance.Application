# Database

## Technology and location

- Engine: SQLite via Python's standard-library `sqlite3`.
- Path: `ATTENDANCE_DB_PATH`, defaulting to `<repository-root>/data/attendance.db`.
- Relative paths are resolved against the repository root by `app/core/config.py`.
- The parent directory is created by `get_connection()` if it does not exist.
- `data/` and all `*.db` files are ignored by Git. Do not commit local or production attendance databases.

## Schema

The code defines three tables: `attendance`, `users`, and `auth_tokens`.

### Attendance

```sql
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    lecture_id TEXT NOT NULL,
    attendance_date TEXT NOT NULL,
    attendance_time TEXT NOT NULL,
    liveness_status TEXT NOT NULL,
    face_status TEXT NOT NULL,
    similarity REAL,
    attendance_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (student_id, lecture_id, attendance_date)
);
```

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | INTEGER | No | Primary key, auto-increment. |
| `student_id` | TEXT | No | Must match the authenticated student's account for API writes. |
| `subject` | TEXT | No | Client-supplied subject name. |
| `lecture_id` | TEXT | No | Client-supplied lecture identifier. |
| `attendance_date` | TEXT | No | Local date, `YYYY-MM-DD`. |
| `attendance_time` | TEXT | No | Local time, `HH:MM:SS`. |
| `liveness_status` | TEXT | No | `VERIFIED` in the normal success path. |
| `face_status` | TEXT | No | `MATCH`, `UNKNOWN`, `NO_FACE`, or `ERROR`. |
| `similarity` | REAL | Yes | Cosine similarity, if available. |
| `attendance_status` | TEXT | No | `PRESENT` for inserted records. |
| `created_at` | TEXT | No | Local ISO 8601 timestamp with seconds, no timezone suffix. |

The unique constraint prevents more than one record for the same student, lecture, and date. No additional indexes are defined; SQLite creates an automatic index for the unique constraint.

### Users

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    student_id TEXT UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    CHECK (
        (role = 'student' AND student_id IS NOT NULL)
        OR (role = 'admin' AND student_id IS NULL)
    )
);
```

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | INTEGER | No | Primary key. |
| `username` | TEXT | No | Case-insensitive unique login name, stored lowercase. |
| `password_hash` | TEXT | No | Argon2id hash; never a plaintext password. |
| `role` | TEXT | No | `student` or `admin`. |
| `student_id` | TEXT | Yes | Required for students; prohibited for admins. Unique when present. |
| `is_active` | INTEGER | No | `1` for active, `0` after deactivation. |
| `created_at` | TEXT | No | UTC ISO 8601 timestamp. |

### Auth tokens

```sql
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_auth_tokens_user_id ON auth_tokens (user_id);
CREATE INDEX idx_auth_tokens_expires_at ON auth_tokens (expires_at);
```

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `id` | INTEGER | No | Primary key. |
| `user_id` | INTEGER | No | References `users.id`. |
| `token_hash` | TEXT | No | SHA-256 hash of the opaque bearer token; unique. |
| `created_at` | TEXT | No | UTC ISO 8601 timestamp. |
| `expires_at` | TEXT | No | UTC ISO 8601 expiry timestamp. |
| `revoked_at` | TEXT | Yes | Set when the token is revoked. |

Plaintext bearer tokens are returned once to the client and are not stored. Expired tokens are deleted opportunistically when a new token is issued; revoked tokens are retained until manual cleanup.

## Initialization status

The FastAPI lifespan calls `initialize_database()` and `initialize_auth_database()` before model services are constructed. They:

1. Create the configured parent directory through `get_connection()`.
2. Run `CREATE TABLE IF NOT EXISTS` for `attendance`, `users`, and `auth_tokens`, including the unique constraints and indexes.
3. Commit and close the connection in `finally`.
4. Set `app.state.database_initialized = True` and `app.state.auth_initialized = True`.

The operation is idempotent, so restarting against an existing database preserves rows. A failure during initialization aborts startup and closes the connection. `get_connection()` itself only creates the parent directory and opens the database; it does not create tables.

Fresh initialization, restart preservation, API retrieval, duplicate rejection, account provisioning, token lifecycle, and authorization are covered by focused tests without loading real models:
`tests/runtime/test_database_path.py`, `tests/runtime/test_app_startup.py`, `tests/runtime/test_attendance_api.py`, and `tests/runtime/test_auth.py`.

## Write path

`mark_attendance()`:

1. Uses `datetime.now()` for local date, time, and ISO timestamp.
2. Opens a connection with `row_factory = sqlite3.Row`.
3. Executes a parameterized `INSERT`.
4. Commits and returns a success dictionary with the inserted row ID and timestamp.
5. Catches `sqlite3.IntegrityError` and returns `{"success": False, "duplicate": True, ...}`.
6. Closes the connection in `finally`, including on unexpected errors.

The route maps a duplicate result to `status: "duplicate"` and `attendance_status: "ALREADY_MARKED"`.

## Read path

`get_student_attendance(student_id)` and `get_all_attendance()`:

- Use parameterized queries.
- Return a list of dictionaries.
- Order by `attendance_date DESC, attendance_time DESC`.
- Have no pagination or filtering.
- Are protected at the API layer: students can read only their own records; admins can read any student's records and the full list. The database helpers themselves do not enforce access control.

## Duplicate helper

`attendance_already_marked(student_id, lecture_id, attendance_date)` performs a pre-check query, but no route calls it. Duplicate protection currently relies on the database constraint and `IntegrityError` handling.

## Migrations

There is no migration framework, schema version table, or upgrade path. The schema is created by the idempotent `initialize_database()` startup path. Any future schema change needs a documented migration strategy and a decision record.

## Time handling

Attendance timestamps are local server time (`datetime.now()`) without timezone information. Duplicate attendance is scoped to the server's local calendar date. This is ambiguous across timezones and daylight-saving changes. A future fix should standardize on UTC or an explicit application timezone.

Authentication timestamps (`users.created_at`, `auth_tokens.created_at`, `expires_at`, and `revoked_at`) are UTC ISO 8601 values with an offset. Token expiry and revocation comparisons use UTC.

## Testing the database safely

Set `ATTENDANCE_DB_PATH` to a temporary path before importing or starting the application, or construct `Settings(database_path=...)` and pass it to `create_app()`. The lifespan initializes the schema for that path, and attendance routes use the path stored on `app.state.settings`.

Database helpers also accept an explicit `database_path` argument for isolated tests. Do not write test records into a real local attendance database.
