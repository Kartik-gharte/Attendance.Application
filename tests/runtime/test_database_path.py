import sqlite3

from app.database.attendance_db import (
    get_all_attendance,
    get_connection,
    initialize_database,
    mark_attendance,
)


def test_connection_creates_configured_parent_directory(tmp_path):

    database_path = tmp_path / "nested" / "attendance-test.db"

    connection = get_connection(database_path)

    try:
        assert database_path.exists()
    finally:
        connection.close()


def test_initialize_database_creates_schema_idempotently(tmp_path):

    database_path = tmp_path / "nested" / "attendance.db"

    initialize_database(database_path)
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:

        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'attendance'
            """
        ).fetchone()

    assert table == ("attendance",)


def test_initialize_database_preserves_existing_rows(tmp_path):

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)

    inserted = mark_attendance(
        student_id="STU-TEST",
        subject="Test Subject",
        lecture_id="TEST-LECTURE",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.9,
        attendance_status="PRESENT",
        database_path=database_path,
    )

    initialize_database(database_path)

    records = get_all_attendance(database_path)

    assert inserted["success"] is True
    assert len(records) == 1
    assert records[0]["student_id"] == "STU-TEST"


def test_duplicate_attendance_is_rejected(tmp_path):

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)

    first = mark_attendance(
        student_id="STU-TEST",
        subject="Test Subject",
        lecture_id="TEST-LECTURE",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.9,
        attendance_status="PRESENT",
        database_path=database_path,
    )

    duplicate = mark_attendance(
        student_id="STU-TEST",
        subject="Test Subject",
        lecture_id="TEST-LECTURE",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.9,
        attendance_status="PRESENT",
        database_path=database_path,
    )

    assert first["success"] is True
    assert duplicate["success"] is False
    assert duplicate["duplicate"] is True
    assert len(get_all_attendance(database_path)) == 1


def test_fresh_database_retrieval_returns_empty(tmp_path):

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)

    assert get_all_attendance(database_path) == []
