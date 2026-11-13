"""Tests for the enrollment audit trail.

The tests cover the recorded content, the refusals, and the guarantee that
no biometric material reaches the audit trail.
"""

import sqlite3

import numpy as np
import pytest

from app.services.enrollment_audit import (
    OUTCOME_ENROLLED,
    OUTCOME_FAILED,
    OUTCOME_REJECTED,
    AuditError,
    delete_old_enrollment_audit,
    embedding_digest,
    list_enrollments,
    record_enrollment,
)


@pytest.fixture
def database_path(tmp_path):
    from app.database.attendance_db import initialize_database

    path = tmp_path / "attendance.db"

    initialize_database(path)

    return path


# =========================================================
# RECORDING
# =========================================================


def test_record_enrollment_stores_the_entry(database_path):
    entry_id = record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        outcome=OUTCOME_ENROLLED,
        source_name="enrolled.jpg",
        database_path=database_path,
    )

    assert entry_id > 0

    entries = list_enrollments(database_path=database_path)

    assert len(entries) == 1

    entry = entries[0]

    assert entry.student_id == "STU001"
    assert entry.operator == "admin-user"
    assert entry.consent_reference == "consent-2026-001"
    assert entry.outcome == OUTCOME_ENROLLED
    assert entry.source_name == "enrolled.jpg"
    assert entry.enrolled_at


def test_record_enrollment_requires_a_student_identifier(database_path):
    with pytest.raises(AuditError):
        record_enrollment(
            student_id="",
            operator="admin-user",
            consent_reference="consent-2026-001",
            database_path=database_path,
        )


def test_record_enrollment_requires_an_operator(database_path):
    with pytest.raises(AuditError):
        record_enrollment(
            student_id="STU001",
            operator="  ",
            consent_reference="consent-2026-001",
            database_path=database_path,
        )


def test_record_enrollment_requires_a_consent_reference(database_path):
    with pytest.raises(AuditError):
        record_enrollment(
            student_id="STU001",
            operator="admin-user",
            consent_reference=None,
            database_path=database_path,
        )


def test_record_enrollment_rejects_an_unknown_outcome(database_path):
    with pytest.raises(AuditError):
        record_enrollment(
            student_id="STU001",
            operator="admin-user",
            consent_reference="consent-2026-001",
            outcome="maybe",
            database_path=database_path,
        )


# =========================================================
# CONTENT SAFETY
# =========================================================


def test_source_name_is_reduced_to_the_file_name(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        source_name="/home/someone/Private Folder/enrolled.jpg",
        database_path=database_path,
    )

    entries = list_enrollments(database_path=database_path)

    assert entries[0].source_name == "enrolled.jpg"

    # The directory must not be recorded.
    assert "Private" not in entries[0].source_name
    assert "home" not in entries[0].source_name


def test_detail_is_truncated(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        outcome=OUTCOME_FAILED,
        detail="x" * 500,
        database_path=database_path,
    )

    entries = list_enrollments(database_path=database_path)

    assert len(entries[0].detail) <= 200


def test_audit_trail_holds_no_biometric_material(database_path):
    embedding = np.array([0.123456, -0.654321, 0.987654], dtype=np.float32)

    digest = embedding_digest(embedding)

    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        outcome=OUTCOME_ENROLLED,
        source_name="enrolled.jpg",
        embedding_digest_value=digest,
        database_path=database_path,
    )

    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT * FROM enrollment_audit"
        ).fetchall()
    finally:
        connection.close()

    serialized = " ".join(str(value) for row in rows for value in row)

    # No embedding values.
    assert "0.123456" not in serialized
    assert "-0.654321" not in serialized

    # The digest is a hash, not the vector.
    assert digest in serialized
    assert "0.987" not in serialized


def test_embedding_digest_is_stable_and_not_reversible():
    embedding = np.array([0.5, 0.25, 0.125], dtype=np.float32)

    first = embedding_digest(embedding)
    second = embedding_digest(embedding)

    assert first == second
    assert len(first) == 64

    # A different embedding produces a different digest.
    other = embedding_digest(np.array([0.5, 0.25, 0.126], dtype=np.float32))

    assert other != first


def test_audit_table_has_no_image_or_embedding_column(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
    )

    connection = sqlite3.connect(str(database_path))
    try:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(enrollment_audit)"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "image" not in columns
    assert "embedding" not in columns
    assert "face" not in columns
    assert "embedding_digest" in columns


# =========================================================
# QUERYING
# =========================================================


def test_list_enrollments_filters_by_student(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-1",
        database_path=database_path,
    )
    record_enrollment(
        student_id="STU002",
        operator="admin-user",
        consent_reference="consent-2",
        database_path=database_path,
    )

    entries = list_enrollments(
        student_id="STU001",
        database_path=database_path,
    )

    assert len(entries) == 1
    assert entries[0].student_id == "STU001"


def test_list_enrollments_respects_the_limit(database_path):
    for index in range(5):
        record_enrollment(
            student_id="STU001",
            operator="admin-user",
            consent_reference=f"consent-{index}",
            database_path=database_path,
        )

    entries = list_enrollments(database_path=database_path, limit=2)

    assert len(entries) == 2


def test_list_enrollments_returns_the_newest_first(database_path):
    record_enrollment(
        student_id="STU001",
        operator="first",
        consent_reference="consent-1",
        database_path=database_path,
    )
    record_enrollment(
        student_id="STU001",
        operator="second",
        consent_reference="consent-2",
        database_path=database_path,
    )

    entries = list_enrollments(database_path=database_path)

    assert entries[0].operator == "second"


# =========================================================
# RETENTION
# =========================================================


def test_delete_old_enrollment_audit_removes_old_entries(database_path):
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

    deleted = delete_old_enrollment_audit(
        database_path=database_path,
        retention_days=30,
    )

    assert deleted == 1
    assert list_enrollments(database_path=database_path) == []


def test_delete_old_enrollment_audit_keeps_recent_entries(database_path):
    record_enrollment(
        student_id="STU001",
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
    )

    deleted = delete_old_enrollment_audit(
        database_path=database_path,
        retention_days=365,
    )

    assert deleted == 0
    assert len(list_enrollments(database_path=database_path)) == 1


# =========================================================
# ENROLLMENT WORKFLOW INTEGRATION
# =========================================================


def test_enrollment_records_an_audit_entry(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    class StubFace:
        def __init__(self, embedding):
            self.embedding = np.asarray(embedding, dtype=np.float32)

    class StubAnalyzer:
        def get(self, image):
            return [StubFace([0.5, 0.25, 0.125])]

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: StubAnalyzer(),
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    database_path = tmp_path / "attendance.db"

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
    )

    assert result is not None

    entries = list_enrollments(database_path=database_path)

    assert len(entries) == 1
    assert entries[0].outcome == OUTCOME_ENROLLED
    assert entries[0].operator == "admin-user"
    assert entries[0].consent_reference == "consent-2026-001"
    assert entries[0].embedding_digest is not None


def test_enrollment_records_a_rejection(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    existing = embedding_dir / "STU001.npy"
    np.save(str(existing), np.zeros(4, dtype=np.float32))

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    database_path = tmp_path / "attendance.db"

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
    )

    assert result is None

    entries = list_enrollments(database_path=database_path)

    assert len(entries) == 1
    assert entries[0].outcome == OUTCOME_REJECTED


def test_enrollment_without_audit_records_nothing(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    class StubFace:
        def __init__(self, embedding):
            self.embedding = np.asarray(embedding, dtype=np.float32)

    class StubAnalyzer:
        def get(self, image):
            return [StubFace([0.5, 0.25, 0.125])]

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: StubAnalyzer(),
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    database_path = tmp_path / "attendance.db"

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
        database_path=database_path,
        audit=False,
    )

    assert result is not None
    assert list_enrollments(database_path=database_path) == []


def test_dry_run_is_not_audited(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    class StubFace:
        def __init__(self, embedding):
            self.embedding = np.asarray(embedding, dtype=np.float32)

    class StubAnalyzer:
        def get(self, image):
            return [StubFace([0.5, 0.25, 0.125])]

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: StubAnalyzer(),
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    database_path = tmp_path / "attendance.db"

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
        operator="admin-user",
        consent_reference="consent-2026-001",
        database_path=database_path,
        dry_run=True,
    )

    assert result is None
    assert list_enrollments(database_path=database_path) == []
