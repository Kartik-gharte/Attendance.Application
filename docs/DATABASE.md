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

## Schema versioning and migrations

The schema is versioned. Applied versions are recorded in the
`schema_migrations` table, which holds the version number, the migration
name, and the time it was applied.

| Version | Name | Change |
| --- | --- | --- |
| 1 | `initial_schema` | Creates the `attendance`, `users`, and `auth_tokens` tables and their indexes. |

### Applying migrations

Migrations are applied automatically during application startup. The
lifespan calls `ensure_schema()` before the service accepts requests, so a
fresh database is created and an existing database is brought up to date
without operator action.

They can also be applied and inspected from the command line:

```bash
python -m app.database.migrations status
python -m app.database.migrations upgrade
```

Both commands accept `--database-path` and default to the configured
`ATTENDANCE_DB_PATH`.

### Behaviour

- **Idempotent.** Applying migrations to a current database does nothing.
- **Adopting an existing database.** Migration 1 creates its tables with
  `CREATE TABLE IF NOT EXISTS`, so a database that was created before schema
  versioning existed is adopted at the baseline version. Existing rows and
  the `UNIQUE (student_id, lecture_id, attendance_date)` duplicate
  protection are preserved.
- **Atomic.** Each migration runs inside its own transaction. When a
  migration raises, the transaction is rolled back, the failure is reported
  as a `MigrationError` that names the version and the migration, and the
  versions that were applied earlier stay recorded. A partially applied
  schema is never left behind.
- **Ordered.** Migrations run in ascending version order and each version
  is applied at most once.

### Adding a migration

1. Append a new entry to `MIGRATIONS` in `app/database/migrations.py` with
   the next version number.
2. Bump `SCHEMA_VERSION` to the new version.
3. Write the migration so that it can run against a database that already
   has the previous version, and so that it is safe to re-run.
4. Add a test that covers the fresh path, the upgrade path from the
   previous version, and the failure path.

## Backup and restore

The database and the face embeddings are local state that cannot be
regenerated from the repository. `app/database/backup.py` copies them to a
safe place and puts them back.

### What a backup contains

| Item | Description |
| --- | --- |
| `attendance.db` | The SQLite database, copied with the SQLite online backup API so the copy is consistent even while the service is running. |
| `embeddings/` | The `.npy` face embedding files. |
| `manifest.json` | The backup version, creation time, schema version, the SHA-256 checksum of the database, and the list of embedding files. |

A backup does not contain plaintext credentials. Passwords are stored as
Argon2id hashes and bearer tokens as SHA-256 hashes, so a backup does not
reveal either. It does contain biometric templates and personal data, so it
must be stored with the same care as the live data.

### Creating a backup

```bash
python -m app.database.backup create
```

The backup is written to a `backups` directory next to the database, in a
timestamped subdirectory. A backup is never overwritten.

Options:

| Option | Meaning |
| --- | --- |
| `--backup-dir` | Directory that holds the backups. |
| `--database-path` | Database to back up. |
| `--embedding-dir` | Embedding directory to back up. |
| `--no-embeddings` | Do not include the face embeddings. |

### Listing and verifying

```bash
python -m app.database.backup list
python -m app.database.backup verify --backup-path backups/backup_20260101T120000Z
```

Verification checks that the manifest is readable, that the database file
is present, that its SHA-256 checksum matches the manifest, that the
database passes the SQLite integrity check, that it contains the
attendance table, and that every embedding listed in the manifest is
present.

### Restoring

```bash
python -m app.database.backup restore \
  --backup-path backups/backup_20260101T120000Z \
  --overwrite
```

The restore:

1. verifies the backup before the live database is touched;
2. refuses to replace an existing database unless `--overwrite` is given;
3. copies the current database to a `<database>.pre_restore` safety file
   before replacing it;
4. restores the embeddings when the backup contains them;
5. verifies the restored database afterwards.

If the restore fails, the safety copy is put back.

To restore into a new location, omit `--overwrite` and point
`--database-path` at a path that does not exist yet.

### Recommended schedule

The project does not schedule backups automatically. A minimal schedule:

- before every schema migration;
- daily, while the service is in use;
- before any restore or destructive maintenance.

Keep at least one backup outside the machine that runs the service, and
test a restore periodically. A backup that has never been restored is not
a backup.
