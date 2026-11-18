"""Tests for the scheduled backup command.

The schedule command prints configuration; it does not create a backup.
These tests cover the generated cron entry, the generated systemd units,
and the command line interface.
"""

import sys

import pytest

from app.core.config import PROJECT_ROOT, get_settings
from app.database import backup as backup_module
from app.database.backup import schedule_backup


def schedule_paths(tmp_path):
    return {
        "database_path": tmp_path / "attendance.db",
        "embedding_dir": tmp_path / "embeddings",
        "backup_dir": tmp_path / "backups",
    }


def test_cron_entry_uses_absolute_paths_and_the_configured_limits(tmp_path):
    paths = schedule_paths(tmp_path)

    result = schedule_backup(
        schedule_type="cron",
        retention_days=7,
        max_count=3,
        encrypt=False,
        **paths,
    )

    assert result.startswith("0 2 * * * cd ")
    assert str(PROJECT_ROOT) in result
    assert sys.executable in result
    assert "-m app.database.backup create" in result
    assert str(paths["database_path"].resolve()) in result
    assert str(paths["embedding_dir"].resolve()) in result
    assert str(paths["backup_dir"].resolve()) in result
    assert "--retention-days 7" in result
    assert "--max-count 3" in result
    assert "--no-encryption" in result
    assert "BACKUP_PASSPHRASE" not in result


def test_cron_entry_mentions_the_passphrase_when_encryption_is_enabled(tmp_path):
    result = schedule_backup(
        schedule_type="cron",
        encrypt=True,
        **schedule_paths(tmp_path),
    )

    assert "BACKUP_PASSPHRASE" in result
    assert "--no-encryption" not in result


def test_cron_entry_can_exclude_the_embeddings(tmp_path):
    result = schedule_backup(
        schedule_type="cron",
        include_embeddings=False,
        encrypt=False,
        **schedule_paths(tmp_path),
    )

    assert "--no-embeddings" in result


def test_systemd_output_contains_a_service_and_a_timer(tmp_path):
    result = schedule_backup(
        schedule_type="systemd",
        include_embeddings=False,
        encrypt=False,
        **schedule_paths(tmp_path),
    )

    assert "# Save this block as attendance-backup.service." in result
    assert "# Save this block as attendance-backup.timer." in result
    assert "[Unit]" in result
    assert "[Service]" in result
    assert "[Timer]" in result
    assert "Type=oneshot" in result
    assert f"WorkingDirectory={PROJECT_ROOT}" in result
    assert "EnvironmentFile=-/etc/attendance/backup.env" in result
    assert "ExecStart=" in result
    assert "OnCalendar=*-*-* 02:00:00" in result
    assert "Persistent=true" in result
    assert "WantedBy=timers.target" in result
    assert "--no-embeddings" in result
    assert "--no-encryption" in result


def test_schedule_uses_the_configured_encryption_default(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION", "false")
    get_settings.cache_clear()

    result = schedule_backup(
        schedule_type="cron",
        **schedule_paths(tmp_path),
    )

    assert "--no-encryption" in result


def test_schedule_rejects_an_unknown_format():
    with pytest.raises(ValueError):
        schedule_backup("launchd")


def test_schedule_rejects_a_non_positive_retention_age(tmp_path):
    with pytest.raises(ValueError):
        schedule_backup(
            schedule_type="cron",
            retention_days=0,
            **schedule_paths(tmp_path),
        )


def test_schedule_rejects_a_non_positive_backup_count(tmp_path):
    with pytest.raises(ValueError):
        schedule_backup(
            schedule_type="cron",
            max_count=0,
            **schedule_paths(tmp_path),
        )


def test_cli_schedule_prints_the_cron_entry_to_stdout(capsys, tmp_path):
    exit_code = backup_module.main(
        [
            "schedule",
            "cron",
            "--database-path",
            str(tmp_path / "attendance.db"),
            "--embedding-dir",
            str(tmp_path / "embeddings"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--no-encryption",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "0 2 * * *" in captured.out
    assert captured.err == ""


def test_cli_schedule_defaults_to_cron(capsys, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION", "false")
    get_settings.cache_clear()

    exit_code = backup_module.main(["schedule"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "0 2 * * *" in captured.out


def test_cli_schedule_rejects_an_unknown_format(tmp_path):
    with pytest.raises(SystemExit) as error:
        backup_module.main(
            [
                "schedule",
                "launchd",
                "--database-path",
                str(tmp_path / "attendance.db"),
            ]
        )

    assert error.value.code == 2
