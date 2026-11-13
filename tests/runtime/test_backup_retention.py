"""Tests for the backup retention policy.

The policy keeps the newest backups and removes the ones that are past
the age limit. These tests cover both limits, the safety rules, and the
command line interface.
"""

from pathlib import Path

import pytest

from app.database import backup as backup_module
from app.database.backup import (
    MANIFEST_NAME,
    create_backup,
    list_backups,
    parse_backup_timestamp,
    prune_backups,
)


def make_backup(backup_dir: Path, age_days: float = 0.0) -> Path:
    """Create a backup directory with a timestamped name.

    The age is applied to the directory name so that the retention policy
    can be tested without waiting.
    """

    from datetime import datetime, timedelta, timezone

    stamp = datetime.now(timezone.utc) - timedelta(days=age_days)

    name = stamp.strftime("%Y%m%dT%H%M%SZ")

    path = backup_dir / f"backup_{name}"

    path.mkdir(parents=True)

    (path / MANIFEST_NAME).write_text(
        '{"version": 1, "created_at": "", "database_file": "attendance.db",'
        ' "database_sha256": "", "schema_version": 1,'
        ' "embedding_files": [], "embedding_count": 0}',
        encoding="utf-8",
    )

    return path


def create_plain_backup(**kwargs):
    """Create a backup without encryption.

    The encrypted path is covered in test_encrypted_backup.py. These tests
    exercise the plaintext path.
    """

    return create_backup(encrypt=False, **kwargs)


@pytest.fixture
def seeded_database(tmp_path):
    from app.auth.service import initialize_auth_database
    from app.database.attendance_db import initialize_database

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)
    initialize_auth_database(database_path)

    return database_path


# =========================================================
# TIMESTAMP PARSING
# =========================================================


def test_parse_backup_timestamp_reads_the_name():
    from datetime import datetime, timezone

    parsed = parse_backup_timestamp(Path("/tmp/backup_20260101T120000Z"))

    assert parsed is not None
    assert parsed == datetime(
        2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc
    )


def test_parse_backup_timestamp_rejects_other_names():
    assert parse_backup_timestamp(Path("/tmp/not-a-backup")) is None
    assert parse_backup_timestamp(Path("/tmp/backup_notadate")) is None


# =========================================================
# RETENTION POLICY
# =========================================================


def test_prune_removes_backups_past_the_age_limit(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=90)
    make_backup(backup_dir, age_days=60)
    make_backup(backup_dir, age_days=1)

    # The count limit is set high so that only the age limit applies.
    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=30,
        max_count=10,
    )

    assert len(removed) == 2
    assert len(list_backups(backup_dir)) == 1


def test_prune_keeps_backups_within_the_age_limit(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=5)
    make_backup(backup_dir, age_days=2)
    make_backup(backup_dir, age_days=1)

    # The count limit is set high so that only the age limit applies.
    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=30,
        max_count=10,
    )

    assert removed == []
    assert len(list_backups(backup_dir)) == 3


def test_prune_always_keeps_the_newest_backup(tmp_path):
    """An aggressive policy must not destroy every backup at once."""

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=365)
    make_backup(backup_dir, age_days=300)
    make_backup(backup_dir, age_days=200)

    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=1,
        max_count=2,
    )

    # The newest backup survives even though it is far past the age limit.
    assert len(removed) == 2
    assert len(list_backups(backup_dir)) == 1


def test_prune_enforces_the_maximum_count(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    for index in range(6):
        make_backup(backup_dir, age_days=index)

    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=3650,
        max_count=2,
    )

    assert len(removed) == 4
    assert len(list_backups(backup_dir)) == 2


def test_prune_never_deletes_a_directory_that_is_not_a_backup(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    unrelated = backup_dir / "notes"
    unrelated.mkdir()
    (unrelated / "readme.txt").write_text("keep me", encoding="utf-8")

    no_manifest = backup_dir / "backup_20200101T000000Z"
    no_manifest.mkdir()

    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=1,
        max_count=0,
    )

    assert removed == []
    assert unrelated.is_dir()
    assert no_manifest.is_dir()


def test_prune_dry_run_reports_without_deleting(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=90)
    make_backup(backup_dir, age_days=1)

    removed = prune_backups(
        backup_dir=backup_dir,
        retention_days=30,
        max_count=1,
        dry_run=True,
    )

    assert removed == []
    assert len(list_backups(backup_dir)) == 2


def test_prune_on_a_missing_directory_is_a_no_op(tmp_path):
    assert prune_backups(backup_dir=tmp_path / "nope") == []


# =========================================================
# PRUNING AFTER A BACKUP
# =========================================================


def test_create_backup_prunes_expired_backups(tmp_path, seeded_database):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)

    create_plain_backup(
        backup_dir=backup_dir,
        database_path=seeded_database,
        prune=True,
    )

    remaining = list_backups(backup_dir)

    # Only the new backup survives; the old one is past the age limit.
    assert len(remaining) == 1


def test_create_backup_can_skip_pruning(tmp_path, seeded_database):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)

    create_plain_backup(
        backup_dir=backup_dir,
        database_path=seeded_database,
        prune=False,
    )

    assert len(list_backups(backup_dir)) == 2


def test_pruning_never_removes_the_backup_just_created(tmp_path, seeded_database):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    path = create_plain_backup(
        backup_dir=backup_dir,
        database_path=seeded_database,
        prune=True,
    )

    assert path.is_dir()
    assert (path / MANIFEST_NAME).is_file()


# =========================================================
# COMMAND LINE INTERFACE
# =========================================================


def test_cli_prune_removes_backups_outside_the_policy(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)
    make_backup(backup_dir, age_days=1)

    exit_code = backup_module.main(
        [
            "prune",
            "--backup-dir",
            str(backup_dir),
            "--retention-days",
            "30",
            "--max-count",
            "10",
        ]
    )

    assert exit_code == 0
    assert len(list_backups(backup_dir)) == 1


def test_cli_prune_removes_expired_backups(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)
    make_backup(backup_dir, age_days=90)
    make_backup(backup_dir, age_days=1)

    exit_code = backup_module.main(
        [
            "prune",
            "--backup-dir",
            str(backup_dir),
            "--retention-days",
            "30",
            "--max-count",
            "1",
        ]
    )

    assert exit_code == 0
    assert len(list_backups(backup_dir)) == 1


def test_cli_prune_dry_run_keeps_everything(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)
    make_backup(backup_dir, age_days=1)

    exit_code = backup_module.main(
        [
            "prune",
            "--backup-dir",
            str(backup_dir),
            "--retention-days",
            "30",
            "--max-count",
            "1",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert len(list_backups(backup_dir)) == 2


def test_cli_create_can_skip_pruning(
    tmp_path,
    seeded_database,
    monkeypatch,
):
    monkeypatch.setenv("BACKUP_PASSPHRASE", "test-passphrase")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    make_backup(backup_dir, age_days=120)

    exit_code = backup_module.main(
        [
            "create",
            "--backup-dir",
            str(backup_dir),
            "--database-path",
            str(seeded_database),
            "--no-prune",
        ]
    )

    assert exit_code == 0
    assert len(list_backups(backup_dir)) == 2
