"""Tests for the versioned database migrations.

The tests cover fresh database initialization, the upgrade path from a
database that was created before schema versioning existed, migration
failure handling, and data integrity after a migration.
"""

import sqlite3

import pytest

from app.database import migrations as migration_module
from app.database.migrations import (
    MIGRATIONS,
    SCHEMA_VERSION,
    MigrationError,
    apply_migrations,
    ensure_schema,
    get_applied_versions,
    get_current_schema_version,
    get_pending_migrations,
    get_schema_version,
)


EXPECTED_TABLES = {
    "attendance",
    "users",
    "auth_tokens",
    "schema_migrations",
}


def table_names(database_path) -> set[str]:
    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        connection.close()


# =========================================================
# FRESH DATABASE
# =========================================================


def test_fresh_database_initialization_creates_expected_tables(tmp_path):
    database_path = tmp_path / "fresh.db"

    applied = ensure_schema(database_path)

    assert applied == list(range(1, SCHEMA_VERSION + 1))
    assert EXPECTED_TABLES.issubset(table_names(database_path))


def test_fresh_database_records_the_schema_version(tmp_path):
    database_path = tmp_path / "fresh.db"

    ensure_schema(database_path)

    assert get_current_schema_version(database_path) == SCHEMA_VERSION


def test_migrations_are_applied_in_ascending_version_order():
    versions = [version for version, _, _ in MIGRATIONS]

    assert versions == sorted(versions)
    assert versions == list(range(1, len(versions) + 1))


def test_ensure_schema_is_idempotent(tmp_path):
    database_path = tmp_path / "fresh.db"

    first = ensure_schema(database_path)
    second = ensure_schema(database_path)

    assert first
    assert second == []


def test_get_pending_migrations_reports_nothing_after_upgrade(tmp_path):
    database_path = tmp_path / "fresh.db"

    ensure_schema(database_path)

    connection = sqlite3.connect(str(database_path))
    try:
        assert get_pending_migrations(connection) == []
    finally:
        connection.close()


def test_status_command_reports_current_version(tmp_path, capsys):
    database_path = tmp_path / "fresh.db"

    ensure_schema(database_path)

    exit_code = migration_module.main(
        ["status", "--database-path", str(database_path)]
    )

    assert exit_code == 0


def test_upgrade_command_is_idempotent(tmp_path):
    database_path = tmp_path / "fresh.db"

    ensure_schema(database_path)

    exit_code = migration_module.main(
        ["upgrade", "--database-path", str(database_path)]
    )

    assert exit_code == 0
    assert get_current_schema_version(database_path) == SCHEMA_VERSION


# =========================================================
# UPGRADE FROM AN EXISTING DATABASE
# =========================================================


def create_legacy_database(database_path) -> None:
    """Create a database the way the project did before schema versioning.

    The schema matches the pre-migration definition and there is no
    ``schema_migrations`` table.
    """

    connection = sqlite3.connect(str(database_path))

    try:
        connection.execute(
            """
            CREATE TABLE attendance (
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
        connection.commit()
    finally:
        connection.close()


def test_existing_database_is_upgraded_and_version_recorded(tmp_path):
    database_path = tmp_path / "legacy.db"

    create_legacy_database(database_path)

    assert "schema_migrations" not in table_names(database_path)

    applied = ensure_schema(database_path)

    assert applied == [1]
    assert get_current_schema_version(database_path) == SCHEMA_VERSION
    assert EXPECTED_TABLES.issubset(table_names(database_path))


def test_existing_database_rows_survive_the_upgrade(tmp_path):
    database_path = tmp_path / "legacy.db"

    create_legacy_database(database_path)

    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            INSERT INTO attendance (
                student_id,
                subject,
                lecture_id,
                attendance_date,
                attendance_time,
                liveness_status,
                face_status,
                similarity,
                attendance_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "STU001",
                "Maths",
                "MATH-001",
                "2026-01-01",
                "09:00:00",
                "VERIFIED",
                "MATCH",
                0.91,
                "PRESENT",
                "2026-01-01T09:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    ensure_schema(database_path)

    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT student_id, subject, similarity FROM attendance"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [("STU001", "Maths", 0.91)]


def test_upgrade_preserves_the_attendance_unique_constraint(tmp_path):
    """The upgrade must not drop the duplicate protection."""

    database_path = tmp_path / "legacy.db"

    create_legacy_database(database_path)
    ensure_schema(database_path)

    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            INSERT INTO attendance (
                student_id,
                subject,
                lecture_id,
                attendance_date,
                attendance_time,
                liveness_status,
                face_status,
                similarity,
                attendance_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "STU001",
                "Maths",
                "MATH-001",
                "2026-01-01",
                "09:00:00",
                "VERIFIED",
                "MATCH",
                0.91,
                "PRESENT",
                "2026-01-01T09:00:00",
            ),
        )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO attendance (
                    student_id,
                    subject,
                    lecture_id,
                    attendance_date,
                    attendance_time,
                    liveness_status,
                    face_status,
                    similarity,
                    attendance_status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "STU001",
                    "Maths",
                    "MATH-001",
                    "2026-01-01",
                    "10:00:00",
                    "VERIFIED",
                    "MATCH",
                    0.88,
                    "PRESENT",
                    "2026-01-01T10:00:00",
                ),
            )
    finally:
        connection.close()


def test_unversioned_database_reports_the_baseline_version(tmp_path):
    database_path = tmp_path / "legacy.db"

    create_legacy_database(database_path)

    connection = sqlite3.connect(str(database_path))
    try:
        connection.row_factory = sqlite3.Row

        assert get_schema_version(connection) == 0
    finally:
        connection.close()


# =========================================================
# MIGRATION FAILURE HANDLING
# =========================================================


def test_failed_migration_rolls_back_and_raises(tmp_path, monkeypatch):
    database_path = tmp_path / "fresh.db"

    def _failing_migration(connection):
        connection.execute(
            "CREATE TABLE should_not_survive (id INTEGER PRIMARY KEY)"
        )
        raise sqlite3.OperationalError("simulated migration failure")

    monkeypatch.setattr(
        migration_module,
        "MIGRATIONS",
        [
            *MIGRATIONS,
            (2, "failing", _failing_migration),
        ],
    )

    with pytest.raises(MigrationError):
        ensure_schema(database_path)

    tables = table_names(database_path)

    assert "should_not_survive" not in tables

    # The migration that failed must not be recorded as applied.
    connection = sqlite3.connect(str(database_path))
    try:
        connection.row_factory = sqlite3.Row
        applied = get_applied_versions(connection)
    finally:
        connection.close()

    assert 2 not in applied
    assert 1 in applied


def test_failed_migration_leaves_the_previous_version_applied(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "fresh.db"

    ensure_schema(database_path)

    def _failing_migration(connection):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        migration_module,
        "MIGRATIONS",
        [
            *MIGRATIONS,
            (2, "failing", _failing_migration),
        ],
    )

    with pytest.raises(MigrationError):
        ensure_schema(database_path)

    assert get_current_schema_version(database_path) == SCHEMA_VERSION


def test_migration_error_message_names_the_failing_version(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "fresh.db"

    def _failing_migration(connection):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        migration_module,
        "MIGRATIONS",
        [
            *MIGRATIONS,
            (2, "failing", _failing_migration),
        ],
    )

    with pytest.raises(MigrationError) as error:
        ensure_schema(database_path)

    assert "2" in str(error.value)
    assert "failing" in str(error.value)


def test_apply_migrations_returns_only_newly_applied_versions(tmp_path):
    database_path = tmp_path / "fresh.db"

    connection = sqlite3.connect(str(database_path))
    try:
        connection.row_factory = sqlite3.Row

        first = apply_migrations(connection)
        second = apply_migrations(connection)

        assert first == [1]
        assert second == []
    finally:
        connection.close()


# =========================================================
# DATA INTEGRITY
# =========================================================


def test_attendance_round_trip_after_migration(tmp_path):
    from app.database.attendance_db import (
        get_all_attendance,
        initialize_database,
        mark_attendance,
    )

    database_path = tmp_path / "roundtrip.db"

    initialize_database(database_path)

    result = mark_attendance(
        student_id="STU001",
        subject="Physics",
        lecture_id="PHY-001",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.87,
        attendance_status="PRESENT",
        database_path=database_path,
    )

    assert result["success"] is True

    records = get_all_attendance(database_path)

    assert len(records) == 1
    assert records[0]["student_id"] == "STU001"
    assert records[0]["similarity"] == 0.87


def test_duplicate_attendance_is_still_rejected_after_migration(tmp_path):
    from app.database.attendance_db import (
        initialize_database,
        mark_attendance,
    )

    database_path = tmp_path / "duplicate.db"

    initialize_database(database_path)

    arguments = {
        "student_id": "STU001",
        "subject": "Physics",
        "lecture_id": "PHY-001",
        "liveness_status": "VERIFIED",
        "face_status": "MATCH",
        "similarity": 0.87,
        "attendance_status": "PRESENT",
        "database_path": database_path,
    }

    first = mark_attendance(**arguments)
    second = mark_attendance(**arguments)

    assert first["success"] is True
    assert second["success"] is False
    assert second["duplicate"] is True


def test_auth_tables_are_available_after_migration(tmp_path):
    from app.auth.service import (
        create_user,
        initialize_auth_database,
    )

    database_path = tmp_path / "auth.db"

    initialize_auth_database(database_path)

    user = create_user(
        "student-test",
        "test-password-123",
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    assert user.username == "student-test"
    assert get_current_schema_version(database_path) == SCHEMA_VERSION
