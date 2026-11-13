"""Tests for the encrypted backup path.

A backup holds the face embeddings and the attendance records. These tests
cover the encryption, the verification, and the restore of an encrypted
backup, and they assert that the plaintext never reaches the stored
files.
"""

import os
import sqlite3

import numpy as np
import pytest

from app.core.crypto import (
    EncryptionError,
    decrypt_bytes,
    derive_key,
    encrypt_bytes,
    encrypted_name,
    generate_salt,
    resolve_passphrase,
)
from app.database.backup import (
    MANIFEST_NAME,
    BackupError,
    create_backup,
    list_backups,
    restore_backup,
    verify_backup,
)


PASSPHRASE = "correct horse battery staple"
WRONG_PASSPHRASE = "wrong passphrase"


@pytest.fixture
def seeded_database(tmp_path):
    from app.database.attendance_db import (
        initialize_database,
        mark_attendance,
    )

    path = tmp_path / "attendance.db"

    initialize_database(path)

    mark_attendance(
        student_id="STU001",
        subject="Maths",
        lecture_id="MATH-001",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.91,
        attendance_status="PRESENT",
        database_path=path,
    )

    return path


@pytest.fixture
def seeded_embeddings(tmp_path):
    directory = tmp_path / "face_embeddings"
    directory.mkdir()

    np.save(
        str(directory / "STU001.npy"),
        np.array([0.1, 0.2, 0.3], dtype=np.float32),
    )

    return directory


def make_backup(tmp_path, seeded_database, seeded_embeddings, **kwargs):
    return create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
        passphrase=PASSPHRASE,
        **kwargs,
    )


# =========================================================
# THE KEY DERIVATION
# =========================================================


def test_the_key_is_derived_from_the_passphrase_and_the_salt():
    salt = generate_salt()

    first = derive_key(PASSPHRASE, salt)
    second = derive_key(PASSPHRASE, salt)

    assert first == second
    assert len(first) == 32


def test_a_different_salt_gives_a_different_key():
    first = derive_key(PASSPHRASE, generate_salt())
    second = derive_key(PASSPHRASE, generate_salt())

    assert first != second


def test_a_different_passphrase_gives_a_different_key():
    salt = generate_salt()

    assert derive_key(PASSPHRASE, salt) != derive_key(WRONG_PASSPHRASE, salt)


def test_an_empty_passphrase_is_refused():
    with pytest.raises(EncryptionError):
        derive_key("", generate_salt())


def test_the_salt_is_random():
    assert generate_salt() != generate_salt()


# =========================================================
# THE CIPHER
# =========================================================


def test_the_ciphertext_does_not_contain_the_plaintext():
    key = derive_key(PASSPHRASE, generate_salt())

    plaintext = b"STU001 sensitive attendance data"

    encrypted = encrypt_bytes(key, plaintext, b"attendance.db.enc")

    assert plaintext not in encrypted
    assert decrypt_bytes(key, encrypted, b"attendance.db.enc") == plaintext


def test_the_nonce_is_fresh_for_every_value():
    key = derive_key(PASSPHRASE, generate_salt())

    first = encrypt_bytes(key, b"same", b"a")
    second = encrypt_bytes(key, b"same", b"a")

    assert first != second


def test_a_modified_ciphertext_fails_to_decrypt():
    key = derive_key(PASSPHRASE, generate_salt())

    encrypted = bytearray(encrypt_bytes(key, b"plaintext", b"a"))
    encrypted[-1] ^= 0xFF

    with pytest.raises(EncryptionError):
        decrypt_bytes(key, bytes(encrypted), b"a")


def test_the_associated_data_binds_the_value_to_its_name():
    key = derive_key(PASSPHRASE, generate_salt())

    encrypted = encrypt_bytes(key, b"plaintext", b"attendance.db.enc")

    # The same ciphertext under a different name must not decrypt.
    with pytest.raises(EncryptionError):
        decrypt_bytes(key, encrypted, b"STU001.npy.enc")


def test_a_truncated_value_is_refused():
    key = derive_key(PASSPHRASE, generate_salt())

    with pytest.raises(EncryptionError):
        decrypt_bytes(key, b"short", b"a")


def test_the_encrypted_name_has_the_suffix():
    assert encrypted_name("attendance.db") == "attendance.db.enc"


# =========================================================
# THE PASSPHRASE SOURCE
# =========================================================


def test_the_passphrase_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("BACKUP_PASSPHRASE", PASSPHRASE)

    assert resolve_passphrase() == PASSPHRASE


def test_the_explicit_passphrase_wins(monkeypatch):
    monkeypatch.setenv("BACKUP_PASSPHRASE", "from-environment")

    assert resolve_passphrase("explicit") == "explicit"


# =========================================================
# CREATING AN ENCRYPTED BACKUP
# =========================================================


def test_the_files_are_stored_encrypted(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    assert (path / "attendance.db.enc").is_file()
    assert (path / "embeddings" / "STU001.npy.enc").is_file()

    # The plaintext files must not be left behind.
    assert not (path / "attendance.db").exists()
    assert not (path / "embeddings" / "STU001.npy").exists()


def test_the_stored_database_is_not_readable_sqlite(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    raw = (path / "attendance.db.enc").read_bytes()

    assert raw[:15] != b"SQLite format 3"
    assert b"STU001" not in raw


def test_the_stored_embedding_is_not_the_plaintext(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    raw = (path / "embeddings" / "STU001.npy.enc").read_bytes()

    assert b"\x00\x00\xa0?" not in raw
    assert len(raw) > 12


def test_the_manifest_records_the_encryption(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    manifest = verify_backup(path, passphrase=PASSPHRASE)

    assert manifest.encrypted is True
    assert manifest.encryption["kdf"] == "scrypt"
    assert manifest.encryption["salt"]
    assert manifest.database_file == "attendance.db.enc"


def test_the_manifest_does_not_contain_the_passphrase(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    manifest_text = (path / MANIFEST_NAME).read_text()

    assert PASSPHRASE not in manifest_text


def test_the_database_checksum_is_of_the_plaintext(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    manifest = verify_backup(path, passphrase=PASSPHRASE)

    import hashlib

    plaintext = decrypt_bytes(
        derive_key(PASSPHRASE, manifest.encryption_salt),
        (path / "attendance.db.enc").read_bytes(),
        b"attendance.db.enc",
    )

    assert hashlib.sha256(plaintext).hexdigest() == manifest.database_sha256


def test_encryption_can_be_turned_off(tmp_path, seeded_database, seeded_embeddings):
    path = create_backup(
        backup_dir=tmp_path / "backups",
        database_path=seeded_database,
        embedding_dir=seeded_embeddings,
        encrypt=False,
    )

    assert (path / "attendance.db").is_file()
    assert not (path / "attendance.db.enc").exists()

    manifest = verify_backup(path)

    assert manifest.encrypted is False


def test_encryption_without_a_passphrase_is_refused(tmp_path, seeded_database, seeded_embeddings, monkeypatch):
    monkeypatch.delenv("BACKUP_PASSPHRASE", raising=False)

    with pytest.raises(BackupError):
        create_backup(
            backup_dir=tmp_path / "backups",
            database_path=seeded_database,
            embedding_dir=seeded_embeddings,
            encrypt=True,
            passphrase=None,
        )


# =========================================================
# VERIFYING
# =========================================================


def test_verify_accepts_an_encrypted_backup(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    manifest = verify_backup(path, passphrase=PASSPHRASE)

    assert manifest.encrypted is True


def test_verify_rejects_the_wrong_passphrase(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    with pytest.raises(BackupError):
        verify_backup(path, passphrase=WRONG_PASSPHRASE)


def test_verify_without_a_passphrase_checks_only_the_presence(tmp_path, seeded_database, seeded_embeddings, monkeypatch):
    monkeypatch.delenv("BACKUP_PASSPHRASE", raising=False)

    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    # The presence is checked, but the contents cannot be verified.
    manifest = verify_backup(path)

    assert manifest.encrypted is True


# =========================================================
# RESTORING
# =========================================================


def test_restore_returns_the_plaintext_database(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    target = tmp_path / "restored.db"

    restore_backup(
        path,
        database_path=target,
        embedding_dir=tmp_path / "restored_embeddings",
        passphrase=PASSPHRASE,
    )

    connection = sqlite3.connect(str(target))
    try:
        rows = connection.execute(
            "SELECT student_id, similarity FROM attendance"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [("STU001", 0.91)]

    # The restored file must be a readable SQLite database.
    assert target.read_bytes()[:15] == b"SQLite format 3"


def test_restore_returns_the_plaintext_embedding(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    target_dir = tmp_path / "restored_embeddings"

    result = restore_backup(
        path,
        database_path=tmp_path / "restored.db",
        embedding_dir=target_dir,
        passphrase=PASSPHRASE,
    )

    assert result["embeddings_restored"] == 1

    restored = target_dir / "STU001.npy"

    assert restored.is_file()

    # The restored name has no encryption suffix.
    assert not (target_dir / "STU001.npy.enc").exists()

    assert np.allclose(np.load(str(restored)), [0.1, 0.2, 0.3])


def test_restore_with_the_wrong_passphrase_does_not_touch_the_database(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    target = tmp_path / "restored.db"

    with pytest.raises(BackupError):
        restore_backup(
            path,
            database_path=target,
            passphrase=WRONG_PASSPHRASE,
        )

    assert not target.exists()


def test_restore_without_a_passphrase_is_refused(tmp_path, seeded_database, seeded_embeddings, monkeypatch):
    monkeypatch.delenv("BACKUP_PASSPHRASE", raising=False)

    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    with pytest.raises(BackupError):
        restore_backup(
            path,
            database_path=tmp_path / "restored.db",
        )


def test_restore_of_an_encrypted_backup_keeps_the_safety_copy(tmp_path, seeded_database, seeded_embeddings):
    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    target = tmp_path / "existing.db"
    target.write_bytes(b"existing content")

    result = restore_backup(
        path,
        database_path=target,
        passphrase=PASSPHRASE,
        overwrite=True,
    )

    assert result["safety_copy"] is not None
    assert target.with_suffix(".db.pre_restore").is_file()


# =========================================================
# THE RETENTION POLICY WITH ENCRYPTED BACKUPS
# =========================================================


def test_the_retention_policy_works_with_encrypted_backups(tmp_path, seeded_database, seeded_embeddings):
    from app.database.backup import prune_backups

    path = make_backup(tmp_path, seeded_database, seeded_embeddings)

    assert len(list_backups(tmp_path / "backups")) == 1

    removed = prune_backups(
        backup_dir=tmp_path / "backups",
        retention_days=0,
        max_count=0,
    )

    # The newest backup is always kept.
    assert removed == []
    assert len(list_backups(tmp_path / "backups")) == 1
