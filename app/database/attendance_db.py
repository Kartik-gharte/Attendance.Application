import sqlite3
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings
from app.database.migrations import ensure_schema


# =========================================================
# DATABASE PATH
# =========================================================

def get_database_path():
    """
    Return the configured SQLite database path.
    """

    return get_settings().database_path


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def get_connection(database_path=None):
    """
    Create and return a SQLite database connection.
    """

    path = Path(
        database_path
        or get_database_path()
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        str(path)
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database(database_path=None):
    """
    Bring the database up to the current schema version.

    The schema is created by the versioned migrations in
    :mod:`app.database.migrations`. The call is idempotent: a database that
    is already current applies nothing, and a database created before
    schema versioning existed is adopted at the baseline version without
    losing its rows.
    """

    ensure_schema(database_path)


# =========================================================
# MARK ATTENDANCE
# =========================================================

def mark_attendance(
    student_id,
    subject,
    lecture_id,
    liveness_status,
    face_status,
    similarity,
    attendance_status,
    database_path=None
):
    """
    Store a verified attendance record.
    """

    now = datetime.now()

    attendance_date = now.strftime(
        "%Y-%m-%d"
    )

    attendance_time = now.strftime(
        "%H:%M:%S"
    )

    created_at = now.isoformat(
        timespec="seconds"
    )

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
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
        )

        connection.commit()

        attendance_id = cursor.lastrowid

        return {
            "success": True,
            "attendance_id": attendance_id,
            "student_id": student_id,
            "subject": subject,
            "lecture_id": lecture_id,
            "date": attendance_date,
            "time": attendance_time,
            "status": attendance_status
        }

    except sqlite3.IntegrityError:

        return {
            "success": False,
            "duplicate": True,
            "message": (
                "Attendance already marked "
                "for this lecture"
            )
        }

    finally:

        connection.close()


# =========================================================
# GET STUDENT ATTENDANCE
# =========================================================

def get_student_attendance(
    student_id,
    database_path=None
):
    """
    Return all attendance records for a student.
    """

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM attendance
            WHERE student_id = ?
            ORDER BY attendance_date DESC,
                     attendance_time DESC
            """,
            (student_id,)
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# =========================================================
# GET ALL ATTENDANCE
# =========================================================

def get_all_attendance(database_path=None):
    """
    Return all attendance records.
    """

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM attendance
            ORDER BY attendance_date DESC,
                     attendance_time DESC
            """
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# =========================================================
# DELETE OLD ATTENDANCE (RETENTION)
# =========================================================

def delete_old_attendance(database_path=None, retention_days=365):
    """
    Delete attendance records older than retention_days.

    Args:
        database_path: Path to the SQLite database
        retention_days: Keep records from this many days back

    Returns:
        Number of records deleted
    """

    import sqlite3

    from pathlib import Path

    from datetime import datetime, timedelta

    path = Path(database_path or get_database_path())

    if not path.exists():

        return 0

    cutoff_date = (
        datetime.now() - timedelta(days=retention_days)
    ).strftime("%Y-%m-%d")

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM attendance
            WHERE attendance_date < ?
            """,
            (cutoff_date,)
        )

        deleted_count = cursor.rowcount

        connection.commit()

        return deleted_count

    finally:

        connection.close()
