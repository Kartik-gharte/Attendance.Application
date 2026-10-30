import sqlite3
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings


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


def initialize_database():
    """
    Create the attendance table if it does not exist.
    """

    connection = get_connection()

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

    connection.commit()

    connection.close()


# =========================================================
# CHECK DUPLICATE ATTENDANCE
# =========================================================

def attendance_already_marked(
    student_id,
    lecture_id,
    attendance_date
):
    """
    Check whether a student has already marked
    attendance for the specified lecture and date.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE student_id = ?
        AND lecture_id = ?
        AND attendance_date = ?
        """,
        (
            student_id,
            lecture_id,
            attendance_date
        )
    )

    row = cursor.fetchone()

    connection.close()

    return row is not None


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
    attendance_status
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

    connection = get_connection()

    cursor = connection.cursor()

    try:

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

        connection.close()

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

        connection.close()

        return {
            "success": False,
            "duplicate": True,
            "message": (
                "Attendance already marked "
                "for this lecture"
            )
        }


# =========================================================
# GET STUDENT ATTENDANCE
# =========================================================

def get_student_attendance(student_id):
    """
    Return all attendance records for a student.
    """

    connection = get_connection()

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

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# GET ALL ATTENDANCE
# =========================================================

def get_all_attendance():
    """
    Return all attendance records.
    """

    connection = get_connection()

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

    connection.close()

    return [
        dict(row)
        for row in rows
    ]