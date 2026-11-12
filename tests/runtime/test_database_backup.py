"""Tests for the database backup and restore workflows.

The tests cover backup creation, verification, restore, and the refusal
paths. No model assets or camera are required.
"""

import json
import sqlite3

import numpy as np
import pytest

from app.database import backup as backup_module
from app.database.backup import (
    MANIFEST_NAME,
    BackupError,
    create_backup,
    list_backups,
    restore_backup,
    verify_backup,
)


@pytest.fixture
def seeded_database(tmp_path):
    """Create a database with accounts and attendance records."""

    from app.auth.service import (
        create_user,
        initialize_auth_database,
    )
    from app.database.attendance_db import (
        initialize_database,
        mark_attendance,
    )

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)
    initialize_auth_database(database_path)

    create_user(
        "student-test",
        "test-password-123",
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    mark_attendance(
        student_id="STU001",
        subject="Maths",
        lecture_id="MATH-001",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.91,
        attendance_status="PRESENT",
        database_path=database_path,
    )

    return database_path


@pytest.fixture
def seeded_embeddings(tmp_path):
    embedding_dir = tmp_path / "face_embeddings"
    embedding_dir.mkdir()

    for name in ("STU001.npy", "STU002.npy"):
        np.save(
            str(embedding_dir / name),
            np.array([0.1, 0.2, 0.3], dtype=np.float32),
        )

    return embedding_dir


def read_attendance(database_path):
    connection = sqlite3.connect(str(database_path))
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT student_id, subject, similarity FROM attendance"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def read_user_count(database_path):
    connection = sqlite3.connect(str(database_path))
    try:
        return connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]
    finally:
        connection.close()


# =========================================================
# BACKUP CREATION
# =========================================================


def test_backup_creates_database_and_manifest(tmp_path, seeded_database):
    backup_dir = tmp_path / "backups"

    path = create_backup(
        backup_dir=backup_dir,
        database_path=seeded_database,
    )

    assert path.is_dir()
    assert (path / "attendance.db").is_file()
    assert (path / MANIFEST_NAME).is_file()


def test_backup_manifest_records_the_schema_version(
    tmp_path,
    seeded_database,
):
    from app.database.migrations import get_current_schema_version

    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    manifest = json.loads((path / MANIFEST_NAME).read_text())

    assert manifest["schema_version"] == get_current_schema_version(
        seeded_database
    )
    assert manifest["version"] == 1


def test_backup_manifest_records_the_database_checksum(
    tmp_path,
    seeded_database,
):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    manifest = json.loads((path / MANIFEST_NAME).read_text())

    assert len(manifest["database_sha256"]) == 64


def test_backup_includes_the_embeddings(tmp_path, seeded_database, seeded_embeddings):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
    )

    manifest = json.loads((path / MANIFEST_NAME).read_text())

    assert manifest["embedding_count"] == 2
    assert sorted(manifest["embedding_files"]) == [
        "STU001.npy",
        "STU002.npy",
    ]
    assert (path / "embeddings" / "STU001.npy").is_file()


def test_backup_can_exclude_the_embeddings(
    tmp_path,
    seeded_database,
    seeded_embeddings,
):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
        include_embeddings=False,
    )

    manifest = json.loads((path / MANIFEST_NAME).read_text())

    assert manifest["embedding_count"] == 0


def test_backup_of_a_missing_database_fails(tmp_path):
    with pytest.raises(BackupError):
        create_backup(
            backup_dir=tmp_path / "backups",
            database_path=tmp_path / "does-not-exist.db",
        )


def test_backup_does_not_store_plaintext_credentials(
    tmp_path,
    seeded_database,
):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    connection = sqlite3.connect(str(path / "attendance.db"))
    try:
        rows = connection.execute(
            "SELECT password_hash FROM users"
        ).fetchall()
    finally:
        connection.close()

    assert rows
    assert all(row[0].startswith("$argon2") for row in rows)
    assert all("test-password-123" not in row[0] for row in rows)


# =========================================================
# VERIFICATION
# =========================================================


def test_verify_accepts_a_valid_backup(tmp_path, seeded_database):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    manifest = verify_backup(path)

    assert manifest.embedding_count == 0


def test_verify_rejects_a_missing_backup(tmp_path):
    with pytest.raises(BackupError):
        verify_backup(tmp_path / "not-a-backup")


def test_verify_rejects_a_backup_without_a_manifest(tmp_path, seeded_database):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (path / MANIFEST_NAME).unlink()

    with pytest.raises(BackupError):
        verify_backup(path)


def test_verify_rejects_a_corrupt_database(tmp_path, seeded_database):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (path / "attendance.db").write_bytes(b"not a database")

    with pytest.raises(BackupError):
        verify_backup(path)


def test_verify_rejects_a_backup_missing_the_database(tmp_path, seeded_database):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (path / "attendance.db").unlink()

    with pytest.raises(BackupError):
        verify_backup(path)


def test_verify_rejects_a_backup_missing_an_embedding(
    tmp_path,
    seeded_database,
    seeded_embeddings,
):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
    )

    (path / "embeddings" / "STU002.npy").unlink()

    with pytest.raises(BackupError):
        verify_backup(path)


def test_verify_rejects_an_unreadable_manifest(tmp_path, seeded_database):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (path / MANIFEST_NAME).write_text("{not json", encoding="utf-8")

    with pytest.raises(BackupError):
        verify_backup(path)


# =========================================================
# RESTORE
# =========================================================


def test_restore_replaces_the_database(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    # Change the live database after the backup was taken.
    connection = sqlite3.connect(str(seeded_database))
    try:
        connection.execute("DELETE FROM attendance")
        connection.commit()
    finally:
        connection.close()

    result = restore_backup(
        backup,
        database_path=seeded_database,
        overwrite=True,
    )

    assert result["database"] == str(seeded_database)
    assert len(read_attendance(seeded_database)) == 1


def test_restore_preserves_the_attendance_records(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    restore_backup(
        backup,
        database_path=seeded_database,
        overwrite=True,
    )

    records = read_attendance(seeded_database)

    assert len(records) == 1
    assert records[0]["student_id"] == "STU001"
    assert records[0]["similarity"] == 0.91


def test_restore_preserves_the_accounts(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    restore_backup(
        backup,
        database_path=seeded_database,
        overwrite=True,
    )

    assert read_user_count(seeded_database) == 1


def test_restore_refuses_to_overwrite_without_the_flag(
    tmp_path,
    seeded_database,
):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    with pytest.raises(BackupError):
        restore_backup(
            backup,
            database_path=seeded_database,
            overwrite=False,
        )


def test_restore_writes_a_safety_copy(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    result = restore_backup(
        backup,
        database_path=seeded_database,
        overwrite=True,
    )

    assert result["safety_copy"] is not None
    assert seeded_database.with_suffix(".db.pre_restore").is_file()


def test_restore_into_an_empty_location_creates_the_database(
    tmp_path,
    seeded_database,
):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    target = tmp_path / "restored" / "attendance.db"

    result = restore_backup(
        backup,
        database_path=target,
        overwrite=False,
    )

    assert result["safety_copy"] is None
    assert target.is_file()
    assert len(read_attendance(target)) == 1


def test_restore_rejects_an_invalid_backup(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (backup / "attendance.db").write_bytes(b"corrupt")

    with pytest.raises(BackupError):
        restore_backup(
            backup,
            database_path=tmp_path / "restored.db",
        )


def test_restore_rejects_a_backup_without_a_manifest(tmp_path, seeded_database):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (backup / MANIFEST_NAME).unlink()

    with pytest.raises(BackupError):
        restore_backup(
            backup,
            database_path=tmp_path / "restored.db",
        )


def test_restore_rejects_a_corrupt_backup_before_touching_the_database(
    tmp_path,
    seeded_database,
):
    """A backup that fails verification must not modify the live database."""

    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
    )

    (backup / "attendance.db").write_bytes(b"corrupt")

    before = read_attendance(seeded_database)

    with pytest.raises(BackupError):
        restore_backup(
            backup,
            database_path=seeded_database,
            overwrite=True,
        )

    assert read_attendance(seeded_database) == before


# =========================================================
# EMBEDDING RESTORE
# =========================================================


def test_restore_reinstates_the_embeddings(
    tmp_path,
    seeded_database,
    seeded_embeddings,
):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
    )

    # Remove the embeddings from the live directory.
    for entry in seeded_embeddings.glob("*.npy"):
        entry.unlink()

    result = restore_backup(
        backup,
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
        overwrite=True,
    )

    assert result["embeddings_restored"] == 2
    assert (seeded_embeddings / "STU001.npy").is_file()
    assert (seeded_embeddings / "STU002.npy").is_file()


def test_restored_embedding_content_matches(tmp_path, seeded_database, seeded_embeddings):
    backup = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
    )

    restore_backup(
        backup,
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
        overwrite=True,
    )

    restored = np.load(str(seeded_embeddings / "STU001.npy"))

    assert restored.shape == (3,)
    assert np.allclose(restored, [0.1, 0.2, 0.3])


# =========================================================
# COMMAND LINE INTERFACE
# =========================================================


def test_cli_create_list_verify_and_restore(tmp_path, seeded_database):
    backup_root = tmp_path / "backups"

    assert (
        backup_module.main(
            [
                "create",
                "--backup-dir",
                str(backup_root),
                "--database-path",
                str(seeded_database),
            ]
        )
        == 0
    )

    assert (
        backup_module.main(
            ["list", "--backup-dir", str(backup_root)]
        )
        == 0
    )

    backups = list_backups(backup_root)

    assert len(backups) == 1

    assert (
        backup_module.main(
            [
                "verify",
                "--backup-path",
                str(backups[0]),
            ]
        )
        == 0
    )

    target = tmp_path / "restored.db"

    assert (
        backup_module.main(
            [
                "restore",
                "--backup-path",
                str(backups[0]),
                "--database-path",
                str(target),
            ]
        )
        == 0
    )

    assert target.is_file()


def test_cli_verify_requires_a_backup_path():
    assert backup_module.main(["verify"]) == 2


def test_cli_restore_requires_a_backup_path():
    assert backup_module.main(["restore"]) == 2


def test_cli_reports_a_failure_for_a_missing_database(tmp_path):
    assert (
        backup_module.main(
            [
                "create",
                "--backup-dir",
                str(tmp_path / "backups"),
                "--database-path",
                str(tmp_path / "missing.db"),
            ]
        )
        == 1
    )
