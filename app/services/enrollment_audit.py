"""Audit trail for face enrollment.

Enrollment writes a biometric template. This module records that it
happened, who authorized it, and under which consent reference.

What the audit trail holds
--------------------------

- the student identifier;
- the time of the enrollment;
- the operator, meaning the person who ran the enrollment;
- the consent reference, meaning the record that the person's consent
  was obtained;
- the source image file name, without the path;
- a digest of the stored embedding, so that a specific template can be
  traced without storing the template itself;
- the outcome and a short detail.

What it deliberately does not hold
----------------------------------

- the image, or any crop of it;
- the embedding, or any part of it;
- the full path of the source image;
- the embedding file contents.

The audit trail is personal data, because it holds a student identifier.
It is subject to the same retention rules as the attendance records.

Usage
-----

::

    from app.services.enrollment_audit import (
        record_enrollment,
        list_enrollments,
    )

    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        source_name="enrolled.jpg",
        embedding_digest=digest,
        outcome="enrolled",
        database_path=database_path,
    )
"""

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging_config import get_logger


logger = get_logger("services.enrollment_audit")

OUTCOME_ENROLLED = "enrolled"
OUTCOME_REJECTED = "rejected"
OUTCOME_FAILED = "failed"

OUTCOMES = {OUTCOME_ENROLLED, OUTCOME_REJECTED, OUTCOME_FAILED}

# The audit trail must never contain biometric material. The detail is
# operator supplied, so it is truncated to a bounded length.
MAX_DETAIL_LENGTH = 200


class AuditError(RuntimeError):
    """Raised when an audit entry cannot be recorded."""


@dataclass
class EnrollmentAuditEntry:
    """One audit record."""

    id: int
    student_id: str
    enrolled_at: str
    operator: str
    consent_reference: str
    source_name: str | None
    embedding_digest: str | None
    outcome: str
    detail: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "enrolled_at": self.enrolled_at,
            "operator": self.operator,
            "consent_reference": self.consent_reference,
            "source_name": self.source_name,
            "embedding_digest": self.embedding_digest,
            "outcome": self.outcome,
            "detail": self.detail,
        }


def embedding_digest(embedding) -> str:
    """Return a digest that identifies an embedding without storing it.

    The digest is not reversible. It exists so that an operator can tell
    which template is stored without the template being readable from the
    audit trail.
    """

    import numpy as np

    array = np.asarray(embedding, dtype=np.float32)

    return hashlib.sha256(array.tobytes()).hexdigest()


def _normalize_detail(detail: str | None) -> str | None:
    if detail is None:
        return None

    text = str(detail).strip()

    if not text:
        return None

    return text[:MAX_DETAIL_LENGTH]


def _normalize_source_name(source: str | None) -> str | None:
    """Return the file name only, never the path.

    The path can contain a person identifier, so only the base name is
    recorded.
    """

    if source is None:
        return None

    text = str(source).strip()

    if not text:
        return None

    return Path(text).name


def record_enrollment(
    student_id: str,
    operator: str,
    consent_reference: str,
    outcome: str = OUTCOME_ENROLLED,
    source_name: str | None = None,
    embedding_digest_value: str | None = None,
    detail: str | None = None,
    database_path=None,
) -> int:
    """Record an enrollment attempt and return the audit row identifier.

    Raises:
        AuditError: When the entry is incomplete or the outcome is not
            one of the known values.
    """

    if not student_id or not str(student_id).strip():
        raise AuditError("A student identifier is required")

    if not operator or not str(operator).strip():
        raise AuditError("An operator is required")

    if not consent_reference or not str(consent_reference).strip():
        raise AuditError("A consent reference is required")

    if outcome not in OUTCOMES:
        raise AuditError(
            f"Unknown outcome '{outcome}'. Use one of {sorted(OUTCOMES)}."
        )

    from app.database.attendance_db import get_connection
    from app.database.migrations import ensure_schema

    # The enrollment workflow can run without the API server, so the
    # schema is ensured rather than assumed.
    ensure_schema(database_path)

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO enrollment_audit (
                student_id,
                enrolled_at,
                operator,
                consent_reference,
                source_name,
                embedding_digest,
                outcome,
                detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(student_id).strip(),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                str(operator).strip(),
                str(consent_reference).strip(),
                _normalize_source_name(source_name),
                embedding_digest_value,
                outcome,
                _normalize_detail(detail),
            ),
        )

        connection.commit()

        return cursor.lastrowid

    except sqlite3.Error as error:

        logger.error(
            "The enrollment audit entry could not be recorded: %s",
            type(error).__name__,
        )

        raise AuditError(
            "The enrollment audit entry could not be recorded"
        ) from error

    finally:

        connection.close()


def list_enrollments(
    student_id: str | None = None,
    database_path=None,
    limit: int = 100,
) -> list[EnrollmentAuditEntry]:
    """Return the audit entries, most recent first.

    Args:
        student_id: Return only the entries for this student.
        database_path: Database to read from.
        limit: Maximum number of entries to return.
    """

    from app.database.attendance_db import get_connection
    from app.database.migrations import ensure_schema

    ensure_schema(database_path)

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        if student_id:
            cursor.execute(
                """
                SELECT id, student_id, enrolled_at, operator,
                       consent_reference, source_name, embedding_digest,
                       outcome, detail
                FROM enrollment_audit
                WHERE student_id = ?
                ORDER BY enrolled_at DESC, id DESC
                LIMIT ?
                """,
                (student_id, int(limit)),
            )

        else:
            cursor.execute(
                """
                SELECT id, student_id, enrolled_at, operator,
                       consent_reference, source_name, embedding_digest,
                       outcome, detail
                FROM enrollment_audit
                ORDER BY enrolled_at DESC, id DESC
                LIMIT ?
                """,
                (int(limit),),
            )

        rows = cursor.fetchall()

        return [
            EnrollmentAuditEntry(
                id=row["id"],
                student_id=row["student_id"],
                enrolled_at=row["enrolled_at"],
                operator=row["operator"],
                consent_reference=row["consent_reference"],
                source_name=row["source_name"],
                embedding_digest=row["embedding_digest"],
                outcome=row["outcome"],
                detail=row["detail"],
            )
            for row in rows
        ]

    except sqlite3.Error as error:

        raise AuditError(
            "The enrollment audit entries could not be read"
        ) from error

    finally:

        connection.close()


def delete_old_enrollment_audit(
    database_path=None,
    retention_days: int = 365,
) -> int:
    """Delete audit entries older than the retention period.

    The audit trail holds a student identifier, so it is subject to the
    same retention rule as the attendance records.

    Returns:
        The number of entries deleted.
    """

    from datetime import timedelta

    from app.core.config import get_settings
    from app.database.attendance_db import get_connection
    from app.database.migrations import ensure_schema

    ensure_schema(database_path)

    if retention_days is None:
        retention_days = get_settings().retention_days

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=retention_days)
    ).isoformat(timespec="seconds")

    connection = get_connection(database_path)

    try:

        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM enrollment_audit WHERE enrolled_at < ?",
            (cutoff,),
        )

        deleted = cursor.rowcount

        connection.commit()

        return deleted

    except sqlite3.Error as error:

        raise AuditError(
            "The old enrollment audit entries could not be deleted"
        ) from error

    finally:

        connection.close()
