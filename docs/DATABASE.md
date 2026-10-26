# Database

## Technology and location

- Engine: SQLite via Python's standard-library `sqlite3`.
- Path: `<repository-root>/data/attendance.db`, derived from `app/database/attendance_db.py`.
- The `data/` directory is created by `get_connection()` if it does not exist.
- `data/` and all `*.db` files are ignored by Git. Do not commit local or production attendance databases.

## Schema

The only table defined in the code is `attendance`:

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
| `student_id` | TEXT | No | Client-supplied identifier. |
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

## Initialization status

`initialize_database()` exists at `app/database/attendance_db.py:40` and would create the table if called. **It is not called anywhere in the application.** `get_connection()` only creates the `data/` directory and opens the database; it does not create tables.

Consequences:

- A fresh database has no `attendance` table.
- `mark_attendance()` raises `sqlite3.OperationalError` (`no such table: attendance`), which is not caught by its `IntegrityError` handler.
- `GET /attendance/student/{id}` and `GET /attendance/all` raise an unhandled error, which FastAPI returns as HTTP `500`.
- `POST /attendance/verify` catches the error in its generic `except Exception` block and returns `status: "error"` with the SQLite message.

This is a confirmed runtime blocker, documented in [KNOWN_ISSUES.md](KNOWN_ISSUES.md). Do not claim fresh-database initialization works.

## Write path

`mark_attendance()`:

1. Uses `datetime.now()` for local date, time, and ISO timestamp.
2. Opens a connection with `row_factory = sqlite3.Row`.
3. Executes a parameterized `INSERT`.
4. Commits and returns a success dictionary with the inserted row ID and timestamp.
5. Catches `sqlite3.IntegrityError` and returns `{"success": False, "duplicate": True, ...}`.
6. Does not close the connection if an exception other than `IntegrityError` occurs. The generic route handler does not close it either.

The route maps a duplicate result to `status: "duplicate"` and `attendance_status: "ALREADY_MARKED"`.

## Read path

`get_student_attendance(student_id)` and `get_all_attendance()`:

- Use parameterized queries.
- Return a list of dictionaries.
- Order by `attendance_date DESC, attendance_time DESC`.
- Have no pagination, filtering, or access control.

## Duplicate helper

`attendance_already_marked(student_id, lecture_id, attendance_date)` performs a pre-check query, but no route calls it. Duplicate protection currently relies on the database constraint and `IntegrityError` handling.

## Migrations

There is no migration framework, schema version table, or upgrade path. The schema is created only by the unused `initialize_database()` helper. Any future schema change needs a documented migration strategy and a decision record.

## Time handling

All timestamps are local server time (`datetime.now()`) without timezone information. Duplicate attendance is scoped to the server's local calendar date. This is ambiguous across timezones and daylight-saving changes. A future fix should standardize on UTC or an explicit application timezone.

## Testing the database safely

For future tests, point the database at a temporary path or use dependency injection; do not write test records into a real local attendance database. The current code hardcodes the database path, so isolation requires a code change (Phase 1/2 work, not part of the documentation foundation).
