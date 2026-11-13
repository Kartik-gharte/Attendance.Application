"""Versioned schema migrations for the attendance database.

The project uses SQLite and a single local process, so a full migration
framework would be more machinery than the problem needs. This module
implements a small, dependency-free versioned migration runner instead.

Design
------

- Every schema change is a numbered migration in :data:`MIGRATIONS`.
- Applied versions are recorded in the ``schema_migrations`` table.
- Migrations are applied in ascending version order and each one runs inside
  a transaction, so a failing migration leaves the schema unchanged.
- Migration 1 is idempotent, because it creates its tables with
  ``CREATE TABLE IF NOT EXISTS``. A database created by an earlier version
  of this project therefore adopts the same baseline without a manual
  upgrade step and without losing its rows.

Usage
-----

::

    from app.database.migrations import (
        ensure_schema,
        get_schema_version,
    )

    ensure_schema(database_path)
    version = get_schema_version(database_path)

The command line interface reports the applied version and applies pending
migrations::

    python -m app.database.migrations status
    python -m app.database.migrations upgrade
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging_config import get_logger


logger = get_logger("database.migrations")


# =========================================================
# SCHEMA VERSION
# =========================================================

# The version the application expects. Bump this and add a migration when
# the schema changes.
SCHEMA_VERSION = 2

SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


class MigrationError(RuntimeError):
    """Raised when a migration cannot be applied."""


# =========================================================
# MIGRATION DEFINITIONS
# =========================================================

def _create_initial_schema(connection: sqlite3.Connection) -> None:
    """Create the attendance, users, and auth token tables.

    This migration is idempotent so that it can be applied to a database
    that was created before schema versioning existed.
    """

    cursor = connection.cursor()

    cursor.execute(
        """
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

            UNIQUE (
                student_id,
                lecture_id,
                attendance_date
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
            student_id TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL,
            CHECK (
                (role = 'student' AND student_id IS NOT NULL)
                OR (role = 'admin' AND student_id IS NULL)
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id
        ON auth_tokens (user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at
        ON auth_tokens (expires_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attendance_student_date
        ON attendance (student_id, attendance_date)
        """
    )


def _create_enrollment_audit_table(connection: sqlite3.Connection) -> None:
    """Create the enrollment audit table.

    The table records that an enrollment happened and who authorized it.
    It deliberately holds no biometric material: no image, no embedding,
    and no face crop. The embedding is identified by a digest so that a
    specific template can be traced without storing the template itself.
    """

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS enrollment_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id TEXT NOT NULL,

            enrolled_at TEXT NOT NULL,

            operator TEXT NOT NULL,

            consent_reference TEXT NOT NULL,

            source_name TEXT,

            embedding_digest TEXT,

            outcome TEXT NOT NULL,

            detail TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_enrollment_audit_student
        ON enrollment_audit (student_id, enrolled_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_enrollment_audit_enrolled_at
        ON enrollment_audit (enrolled_at)
        """
    )


# Ordered list of migrations. Each entry is (version, name, function).
MIGRATIONS = [
    (1, "initial_schema", _create_initial_schema),
    (2, "enrollment_audit", _create_enrollment_audit_table),
]


# =========================================================
# CONNECTION
# =========================================================

def _connect(database_path) -> sqlite3.Connection:
    path = Path(database_path)

    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row

    # Autocommit mode. Migrations open an explicit transaction so that a
    # failing migration rolls back every statement it executed, including
    # DDL. The default driver mode only opens a transaction for data
    # modification, which would leave a partially applied schema behind.
    connection.isolation_level = None

    return connection


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


# =========================================================
# VERSION READING
# =========================================================

def get_applied_versions(connection: sqlite3.Connection) -> list[int]:
    """Return the sorted list of applied migration versions."""

    _ensure_migrations_table(connection)

    rows = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()

    # The connection may or may not use a sqlite3.Row factory, so both
    # access styles are supported.
    versions = []

    for row in rows:
        try:
            versions.append(row["version"])

        except TypeError:
            versions.append(row[0])

    return versions


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return the highest applied migration version."""

    versions = get_applied_versions(connection)

    return versions[-1] if versions else 0


def get_pending_migrations(
    connection: sqlite3.Connection,
) -> list[tuple[int, str]]:
    """Return the migrations that have not been applied yet."""

    applied = set(get_applied_versions(connection))

    return [
        (version, name)
        for version, name, _ in MIGRATIONS
        if version not in applied
    ]


# =========================================================
# APPLYING MIGRATIONS
# =========================================================

def apply_migrations(connection: sqlite3.Connection) -> list[int]:
    """Apply every pending migration and return the applied versions.

    Each migration runs inside its own transaction. When a migration
    raises, the transaction is rolled back, the exception is wrapped in
    :class:`MigrationError`, and the previously applied migrations stay
    recorded.
    """

    applied_now = []

    for version, name, migrate in sorted(
        MIGRATIONS,
        key=lambda item: item[0],
    ):

        if version in get_applied_versions(connection):
            continue

        try:

            connection.execute("BEGIN")

            migrate(connection)

            connection.execute(
                """
                INSERT INTO schema_migrations (
                    version,
                    name,
                    applied_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    version,
                    name,
                    datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            connection.execute("COMMIT")

        except sqlite3.Error as error:

            _rollback(connection)

            raise MigrationError(
                f"Migration {version} ({name}) failed and was rolled back: "
                f"{type(error).__name__}"
            ) from error

        except Exception as error:

            _rollback(connection)

            raise MigrationError(
                f"Migration {version} ({name}) failed and was rolled back: "
                f"{type(error).__name__}: {error}"
            ) from error

        applied_now.append(version)

    return applied_now


def _rollback(connection: sqlite3.Connection) -> None:
    """Roll back an open transaction, ignoring an already closed one."""

    try:
        connection.execute("ROLLBACK")

    except sqlite3.Error:
        pass


def ensure_schema(database_path=None) -> list[int]:
    """Bring the database up to the current schema version.

    Returns the list of migration versions applied by this call. The call is
    idempotent: a database that is already current applies nothing.
    """

    connection = _connect(database_path)

    try:

        _ensure_migrations_table(connection)

        return apply_migrations(connection)

    finally:

        connection.close()


def get_current_schema_version(database_path=None) -> int:
    """Return the applied schema version of a database."""

    connection = _connect(database_path)

    try:

        return get_schema_version(connection)

    finally:

        connection.close()


# =========================================================
# COMMAND LINE INTERFACE
# =========================================================

def build_parser():
    import argparse

    from app.core.config import get_settings

    parser = argparse.ArgumentParser(
        description="Inspect and apply attendance database migrations",
    )

    parser.add_argument(
        "command",
        choices=["status", "upgrade"],
        help=(
            "status reports the applied and pending migrations, "
            "upgrade applies the pending migrations"
        ),
    )
    parser.add_argument(
        "--database-path",
        default=None,
        help="Database path (defaults to the configured database path)",
    )

    return parser


def main(argv=None) -> int:
    import argparse

    from app.core.config import get_settings
    from app.core.logging_config import configure_logging

    parser = build_parser()

    args = parser.parse_args(argv)

    settings = get_settings()

    # The application configures logging during startup. The command line
    # interface runs outside that lifecycle, so it configures logging here.
    configure_logging(settings)

    database_path = args.database_path or settings.database_path

    connection = _connect(database_path)

    try:

        _ensure_migrations_table(connection)

        applied = get_applied_versions(connection)
        pending = get_pending_migrations(connection)

        if args.command == "status":

            logger.info("Database: %s", database_path)
            logger.info(
                "Expected schema version: %s",
                SCHEMA_VERSION,
            )
            logger.info(
                "Applied versions: %s",
                applied or "none",
            )

            if pending:
                logger.info("Pending migrations:")

                for version, name in pending:
                    logger.info("  %s: %s", version, name)

            else:
                logger.info("No pending migrations.")

            return 0

        if pending:

            logger.info("Database: %s", database_path)
            logger.info("Applying migrations:")

            for version, name in pending:
                logger.info("  %s: %s", version, name)

        applied_now = apply_migrations(connection)

        if applied_now:
            logger.info("Applied migrations: %s", applied_now)

        else:
            logger.info("Database is already up to date.")

        return 0

    except MigrationError as error:

        logger.error("Migration failed: %s", error)
        return 1

    finally:

        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
