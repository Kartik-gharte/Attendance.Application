"""Backup and restore for the attendance database and the face embeddings.

The project keeps two kinds of local state that cannot be regenerated from
the repository:

- the SQLite database, which holds accounts, tokens, and attendance records;
- the face embeddings, which are biometric templates.

This module provides a consistent way to copy that state to a safe place
and to put it back.

Safety rules
------------

- A backup is made with the SQLite online backup API, so it is consistent
  even while the application is serving requests.
- A backup never contains credentials in plaintext. Password hashes are
  Argon2id hashes, and bearer tokens are stored as SHA-256 hashes, so a
  backup does not reveal either.
- A restore refuses to overwrite an existing database unless it is asked
  to, and it always takes a safety copy of the current database first.
- A restore verifies the backup before it touches the live database, and
  it verifies the restored database afterwards.
- Backups contain biometric templates and personal data. They must be
  stored with the same care as the live data.
"""

import hashlib
import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger


logger = get_logger("database.backup")

MANIFEST_NAME = "manifest.json"
MANIFEST_VERSION = 1


class BackupError(RuntimeError):
    """Raised when a backup or restore operation cannot be completed."""


@dataclass
class BackupManifest:
    """Describes the contents of a backup."""

    version: int
    created_at: str
    database_file: str
    database_sha256: str
    schema_version: int
    embedding_files: list[str] = field(default_factory=list)
    embedding_count: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "BackupManifest":
        data = json.loads(payload)

        return cls(
            version=data["version"],
            created_at=data["created_at"],
            database_file=data["database_file"],
            database_sha256=data["database_sha256"],
            schema_version=data["schema_version"],
            embedding_files=data.get("embedding_files", []),
            embedding_count=data.get("embedding_count", 0),
        )


# =========================================================
# HELPERS
# =========================================================

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _default_backup_dir() -> Path:
    settings = get_settings()

    return Path(settings.database_path).parent / "backups"


def _resolve_database_path(database_path=None) -> Path:
    if database_path is None:
        database_path = get_settings().database_path

    return Path(database_path)


def _resolve_embedding_dir(embedding_dir=None) -> Path:
    if embedding_dir is None:
        embedding_dir = get_settings().embedding_dir

    return Path(embedding_dir)


def list_backups(backup_dir=None) -> list[Path]:
    """Return the backup directories in the backup root, oldest first."""

    if backup_dir is None:
        root = _default_backup_dir()

    else:
        root = Path(backup_dir)

    if not root.is_dir():
        return []

    return sorted(
        entry
        for entry in root.iterdir()
        if entry.is_dir()
    )


def _current_schema_version(database_path: Path) -> int:
    from app.database.migrations import get_current_schema_version

    try:
        return get_current_schema_version(database_path)

    except sqlite3.Error:
        return 0


# =========================================================
# BACKUP
# =========================================================

def create_backup(
    backup_dir=None,
    database_path=None,
    embedding_dir=None,
    include_embeddings: bool = True,
) -> Path:
    """Create a backup and return the path of the backup directory.

    Args:
        backup_dir: Directory to write the backup into. Defaults to a
            ``backups`` directory next to the database.
        database_path: Database to back up. Defaults to the configured
            database.
        embedding_dir: Embedding directory to back up. Defaults to the
            configured embedding directory.
        include_embeddings: Whether to include the face embeddings.

    Returns:
        The path of the created backup directory.
    """

    source_database = _resolve_database_path(database_path)

    if not source_database.is_file():
        raise BackupError("The database does not exist")

    if backup_dir is None:
        target_root = _default_backup_dir()

    else:
        target_root = Path(backup_dir)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    target_root.mkdir(parents=True, exist_ok=True)

    backup_path = target_root / f"backup_{timestamp}"

    if backup_path.exists():
        raise BackupError(
            f"A backup already exists at {backup_path}. Backups are never "
            "overwritten."
        )

    backup_path.mkdir(parents=True)

    database_copy = backup_path / "attendance.db"

    try:

        _backup_database(source_database, database_copy)

        embedding_files: list[str] = []

        if include_embeddings:

            embedding_files = _backup_embeddings(
                _resolve_embedding_dir(embedding_dir),
                backup_path / "embeddings",
            )

        manifest = BackupManifest(
            version=MANIFEST_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            database_file=database_copy.name,
            database_sha256=_sha256(database_copy),
            schema_version=_current_schema_version(source_database),
            embedding_files=embedding_files,
            embedding_count=len(embedding_files),
        )

        (backup_path / MANIFEST_NAME).write_text(
            manifest.to_json(),
            encoding="utf-8",
        )

    except Exception:

        shutil.rmtree(backup_path, ignore_errors=True)
        raise

    logger.info(
        "Backup created: path=%s embeddings=%d",
        backup_path,
        manifest.embedding_count,
    )

    return backup_path


def _backup_database(source: Path, destination: Path) -> None:
    """Copy the database with the SQLite online backup API.

    The online backup API produces a consistent copy even when the
    application is writing to the database at the same time.
    """

    source_connection = sqlite3.connect(str(source))

    try:

        destination_connection = sqlite3.connect(str(destination))

        try:
            source_connection.backup(destination_connection)

        finally:
            destination_connection.close()

    finally:
        source_connection.close()


def _backup_embeddings(source: Path, destination: Path) -> list[str]:
    """Copy the embedding files and return their relative names."""

    if not source.is_dir():
        return []

    destination.mkdir(parents=True, exist_ok=True)

    copied = []

    for entry in sorted(source.glob("*.npy")):

        if not entry.is_file():
            continue

        shutil.copy2(entry, destination / entry.name)

        copied.append(entry.name)

    return copied


# =========================================================
# VERIFICATION
# =========================================================

def verify_backup(backup_path) -> BackupManifest:
    """Verify a backup and return its manifest.

    Raises:
        BackupError: When the backup is missing, incomplete, or corrupt.
    """

    path = Path(backup_path)

    if not path.is_dir():
        raise BackupError(f"No backup found at {path}")

    manifest_file = path / MANIFEST_NAME

    if not manifest_file.is_file():
        raise BackupError(
            f"The backup at {path} has no manifest and cannot be verified"
        )

    try:
        manifest = BackupManifest.from_json(
            manifest_file.read_text(encoding="utf-8")
        )

    except (ValueError, KeyError) as error:
        raise BackupError(
            f"The backup manifest at {manifest_file} could not be read"
        ) from error

    database_file = path / manifest.database_file

    if not database_file.is_file():
        raise BackupError(
            f"The backup at {path} does not contain {manifest.database_file}"
        )

    actual_digest = _sha256(database_file)

    if actual_digest != manifest.database_sha256:
        raise BackupError(
            "The backup database does not match its manifest checksum. "
            "The backup is incomplete or corrupt."
        )

    _verify_backup_database(database_file, manifest)

    for name in manifest.embedding_files:
        if not (path / "embeddings" / name).is_file():
            raise BackupError(
                f"The backup at {path} is missing the embedding {name}"
            )

    return manifest


def _verify_backup_database(
    database_file: Path,
    manifest: BackupManifest,
) -> None:
    """Check that the backed up database is readable and has the schema."""

    connection = sqlite3.connect(str(database_file))

    try:

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if not integrity or integrity[0] != "ok":
            raise BackupError(
                "The backup database failed the SQLite integrity check"
            )

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        if "attendance" not in tables:
            raise BackupError(
                "The backup database does not contain the attendance table"
            )

        if "schema_migrations" in tables:
            version = connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0]

            if version is not None and version < manifest.schema_version:
                raise BackupError(
                    "The backup database has an older schema than its "
                    "manifest records"
                )

    except sqlite3.Error as error:
        raise BackupError(
            f"The backup database could not be verified: {error}"
        ) from error

    finally:
        connection.close()


# =========================================================
# RESTORE
# =========================================================

def restore_backup(
    backup_path,
    database_path=None,
    embedding_dir=None,
    overwrite: bool = False,
    restore_embeddings: bool = True,
) -> dict:
    """Restore the database and the embeddings from a backup.

    The backup is verified before the live database is touched. The current
    database is copied to a safety file before it is replaced.

    Args:
        backup_path: The backup directory to restore from.
        database_path: Database to restore into. Defaults to the configured
            database.
        embedding_dir: Embedding directory to restore into. Defaults to
            the configured embedding directory.
        overwrite: Whether an existing database may be replaced.
        restore_embeddings: Whether the embeddings are restored.

    Returns:
        A dict describing what was restored.

    Raises:
        BackupError: When the backup is invalid, the target exists and
            ``overwrite`` is not set, or the restore fails.
    """

    manifest = verify_backup(backup_path)

    source = Path(backup_path)

    target_database = _resolve_database_path(database_path)

    if target_database.exists() and not overwrite:
        raise BackupError(
            f"A database already exists at {target_database}. Pass the "
            "overwrite flag to replace it."
        )

    safety_copy: Path | None = None

    if target_database.exists():
        safety_copy = target_database.with_suffix(
            target_database.suffix + ".pre_restore"
        )
        shutil.copy2(target_database, safety_copy)
        logger.info(
            "Safety copy of the current database written to %s",
            safety_copy,
        )

    try:

        target_database.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source / manifest.database_file, target_database)

    except OSError as error:

        if safety_copy is not None:
            shutil.copy2(safety_copy, target_database)

        raise BackupError(
            f"The database could not be restored: {error}"
        ) from error

    restored_embeddings = 0

    if restore_embeddings and manifest.embedding_files:

        target_embedding_dir = _resolve_embedding_dir(embedding_dir)

        restored_embeddings = _restore_embeddings(
            source / "embeddings",
            target_embedding_dir,
            manifest.embedding_files,
        )

    _verify_restored_database(target_database, manifest)

    logger.info(
        "Restore completed: database=%s embeddings=%d",
        target_database,
        restored_embeddings,
    )

    return {
        "database": str(target_database),
        "safety_copy": str(safety_copy) if safety_copy else None,
        "embeddings_restored": restored_embeddings,
        "schema_version": manifest.schema_version,
        "created_at": manifest.created_at,
    }


def _restore_embeddings(
    source: Path,
    destination: Path,
    names: list[str],
) -> int:
    """Copy the listed embedding files into the destination directory."""

    destination.mkdir(parents=True, exist_ok=True)

    restored = 0

    for name in names:

        source_file = source / name

        if not source_file.is_file():
            continue

        shutil.copy2(source_file, destination / name)

        restored += 1

    return restored


def _verify_restored_database(
    database_path: Path,
    manifest: BackupManifest,
) -> None:
    """Check that the restored database is readable and has the schema."""

    connection = sqlite3.connect(str(database_path))

    try:

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if not integrity or integrity[0] != "ok":
            raise BackupError(
                "The restored database failed the SQLite integrity check"
            )

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        if "attendance" not in tables:
            raise BackupError(
                "The restored database does not contain the attendance table"
            )

    except sqlite3.Error as error:

        raise BackupError(
            f"The restored database could not be verified: {error}"
        ) from error

    finally:
        connection.close()


# =========================================================
# COMMAND LINE INTERFACE
# =========================================================

def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Back up and restore the attendance database",
    )

    parser.add_argument(
        "command",
        choices=["create", "list", "verify", "restore"],
        help="Operation to perform",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Directory that holds the backups",
    )
    parser.add_argument(
        "--backup-path",
        default=None,
        help="Backup directory to verify or restore",
    )
    parser.add_argument(
        "--database-path",
        default=None,
        help="Database path (defaults to the configured database path)",
    )
    parser.add_argument(
        "--embedding-dir",
        default=None,
        help="Embedding directory (defaults to the configured directory)",
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Do not include the face embeddings",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow the restore to replace an existing database",
    )

    return parser


def main(argv=None) -> int:
    import argparse

    from app.core.config import get_settings
    from app.core.logging_config import configure_logging

    args = build_parser().parse_args(argv)

    settings = get_settings()

    configure_logging(settings)

    try:

        if args.command == "create":

            path = create_backup(
                backup_dir=args.backup_dir,
                database_path=args.database_path,
                embedding_dir=args.embedding_dir,
                include_embeddings=not args.no_embeddings,
            )

            logger.info("Backup created at %s", path)

            return 0

        if args.command == "list":

            root = (
                Path(args.backup_dir)
                if args.backup_dir
                else _default_backup_dir()
            )

            backups = list_backups(root)

            if not backups:
                logger.info("No backups found in %s", root)
                return 0

            for entry in backups:
                logger.info("%s", entry)

            return 0

        if args.command == "verify":

            if not args.backup_path:
                logger.error("--backup-path is required to verify a backup")
                return 2

            manifest = verify_backup(args.backup_path)

            logger.info(
                "Backup verified: path=%s created_at=%s schema_version=%s "
                "embeddings=%d",
                args.backup_path,
                manifest.created_at,
                manifest.schema_version,
                manifest.embedding_count,
            )

            return 0

        if args.command == "restore":

            if not args.backup_path:
                logger.error("--backup-path is required to restore a backup")
                return 2

            result = restore_backup(
                args.backup_path,
                database_path=args.database_path,
                embedding_dir=args.embedding_dir,
                overwrite=args.overwrite,
                restore_embeddings=not args.no_embeddings,
            )

            logger.info("Restore completed: %s", result)

            return 0

    except BackupError as error:

        logger.error("Backup operation failed: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
