"""Tests for the authentication command line interface.

The cleanup command deletes records that are past the retention period.
It was previously parsed but never handled, so it exited successfully
without deleting anything. These tests cover the behaviour that was
missing.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.cli import main
from app.services.enrollment_audit import record_enrollment


@pytest.fixture
def database_path(tmp_path):
    from app.database.attendance_db import initialize_database

    path = tmp_path / "attendance.db"

    initialize_database(path)

    return path


def insert_attendance(database_path, attendance_date: str) -> None:
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
                attendance_date,
                "09:00:00",
                "VERIFIED",
                "MATCH",
                0.9,
                "PRESENT",
                f"{attendance_date}T09:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def count_attendance(database_path) -> int:
    connection = sqlite3.connect(str(database_path))
    try:
        return connection.execute(
            "SELECT COUNT(*) FROM attendance"
        ).fetchone()[0]
    finally:
        connection.close()


def old_date(days: int) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%d")


# =========================================================
# CLEANUP COMMAND
# =========================================================


def test_cleanup_deletes_the_old_attendance_records(database_path):
    insert_attendance(database_path, old_date(400))
    insert_attendance(database_path, old_date(10))

    exit_code = main(
        [
            "cleanup",
            "--database-path",
            str(database_path),
            "--retention-days",
            "30",
        ]
    )

    assert exit_code == 0
    assert count_attendance(database_path) == 1


def test_cleanup_deletes_the_old_enrollment_audit_entries(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
    )

    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            "UPDATE enrollment_audit SET enrolled_at = ?",
            ("2020-01-01T00:00:00+00:00",),
        )
        connection.commit()
    finally:
        connection.close()

    exit_code = main(
        [
            "cleanup",
            "--database-path",
            str(database_path),
            "--retention-days",
            "30",
        ]
    )

    assert exit_code == 0

    connection = sqlite3.connect(str(database_path))
    try:
        remaining = connection.execute(
            "SELECT COUNT(*) FROM enrollment_audit"
        ).fetchone()[0]
    finally:
        connection.close()

    assert remaining == 0


def test_cleanup_keeps_the_recent_records(database_path):
    insert_attendance(database_path, old_date(10))

    exit_code = main(
        [
            "cleanup",
            "--database-path",
            str(database_path),
            "--retention-days",
            "365",
        ]
    )

    assert exit_code == 0
    assert count_attendance(database_path) == 1


def test_cleanup_on_an_empty_database_succeeds(database_path):
    exit_code = main(
        [
            "cleanup",
            "--database-path",
            str(database_path),
            "--retention-days",
            "30",
        ]
    )

    assert exit_code == 0


def test_cleanup_actually_deletes_something(database_path):
    """The command must not exit successfully without deleting anything."""

    for index in range(3):
        insert_attendance(database_path, old_date(400 + index))

    assert count_attendance(database_path) == 3

    exit_code = main(
        [
            "cleanup",
            "--database-path",
            str(database_path),
            "--retention-days",
            "30",
        ]
    )

    assert exit_code == 0
    assert count_attendance(database_path) == 0
