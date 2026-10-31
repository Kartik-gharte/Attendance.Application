import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.auth.models import (
    ROLES,
    STUDENT_ROLE,
    UserPrincipal,
)
from app.database.attendance_db import get_connection
from app.services.validation import validate_student_id


DEFAULT_TOKEN_TTL_SECONDS = 3600
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,63}$")

_PASSWORD_HASHER = PasswordHasher()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("Invalid username")

    normalized = username.strip().lower()

    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3-64 characters using letters, numbers, '.', '_' or '-'"
        )

    return normalized


def _validate_password(password: str) -> None:
    if (
        not isinstance(password, str)
        or len(password) < MIN_PASSWORD_LENGTH
        or len(password) > MAX_PASSWORD_LENGTH
        or not password.strip()
    ):
        raise ValueError(
            f"Password must be {MIN_PASSWORD_LENGTH}-{MAX_PASSWORD_LENGTH} characters"
        )


def _validate_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError("Role must be 'student' or 'admin'")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _row_to_principal(row: sqlite3.Row) -> UserPrincipal:
    return UserPrincipal(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        student_id=row["student_id"],
    )


def hash_password(password: str) -> str:
    _validate_password(password)
    return _PASSWORD_HASHER.hash(password)


def initialize_auth_database(database_path=None) -> None:
    """Create the authentication tables if they do not exist."""

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
                student_id TEXT UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL,
                CHECK (
                    (role = 'student' AND student_id IS NOT NULL)
                    OR (role = 'admin' AND student_id IS NULL)
                )
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id
            ON auth_tokens (user_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at
            ON auth_tokens (expires_at)
            """
        )

        connection.commit()

    finally:
        connection.close()


def create_user(
    username: str,
    password: str,
    role: str,
    student_id: str | None = None,
    database_path=None,
) -> UserPrincipal:
    """Create a local account. Passwords are stored as Argon2id hashes."""

    normalized_username = _normalize_username(username)
    _validate_role(role)

    if role == STUDENT_ROLE:
        if not student_id:
            raise ValueError("Student accounts require a student identifier")

        student_id = validate_student_id(student_id)

    elif student_id is not None:
        raise ValueError("Admin accounts cannot have a student identifier")

    password_hash = hash_password(password)
    created_at = _isoformat(_utcnow())

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    role,
                    student_id,
                    is_active,
                    created_at
                )
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    normalized_username,
                    password_hash,
                    role,
                    student_id,
                    created_at,
                ),
            )

        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Username or student identifier is already in use"
            ) from error

        connection.commit()

        return UserPrincipal(
            id=cursor.lastrowid,
            username=normalized_username,
            role=role,
            student_id=student_id,
        )

    finally:
        connection.close()


def authenticate_user(
    username: str,
    password: str,
    database_path=None,
) -> UserPrincipal | None:
    """Return the active user when the supplied password is correct."""

    if not isinstance(password, str):
        return None

    try:
        normalized_username = _normalize_username(username)

    except ValueError:
        return None

    connection = get_connection(database_path)

    try:
        row = connection.execute(
            """
            SELECT id, username, password_hash, role, student_id, is_active
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()

    finally:
        connection.close()

    if row is None or not row["is_active"]:
        return None

    try:
        _PASSWORD_HASHER.verify(row["password_hash"], password)

    except VerificationError:
        return None

    return _row_to_principal(row)


def issue_token(
    user_id: int,
    ttl_seconds: int | None = None,
    database_path=None,
) -> tuple[str, datetime]:
    """Issue an opaque bearer token and return it with its expiry."""

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)

    now = _utcnow()

    if ttl_seconds is None:
        ttl_seconds = DEFAULT_TOKEN_TTL_SECONDS

    expires_at = now + timedelta(seconds=int(ttl_seconds))

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        user = cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError("User not found or inactive")

        cursor.execute(
            """
            DELETE FROM auth_tokens
            WHERE expires_at <= ?
            """,
            (_isoformat(now),),
        )

        cursor.execute(
            """
            INSERT INTO auth_tokens (
                user_id,
                token_hash,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                token_hash,
                _isoformat(now),
                _isoformat(expires_at),
            ),
        )

        connection.commit()

    finally:
        connection.close()

    return token, expires_at


def verify_token(
    token: str,
    database_path=None,
) -> UserPrincipal | None:
    """Return the active user for a valid, unexpired, unrevoked token."""

    if not isinstance(token, str) or not token:
        return None

    token_hash = _hash_token(token)

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        row = cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                u.role,
                u.student_id,
                u.is_active,
                t.expires_at,
                t.revoked_at
            FROM auth_tokens AS t
            JOIN users AS u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if (
            row is None
            or row["revoked_at"] is not None
            or not row["is_active"]
        ):
            return None

        try:
            expires_at = datetime.fromisoformat(row["expires_at"])

        except ValueError:
            return None

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= _utcnow():
            cursor.execute(
                """
                DELETE FROM auth_tokens
                WHERE token_hash = ?
                """,
                (token_hash,),
            )
            connection.commit()
            return None

        return _row_to_principal(row)

    finally:
        connection.close()


def revoke_token(token: str, database_path=None) -> bool:
    """Revoke one bearer token. Returns True when a token was revoked."""

    if not isinstance(token, str) or not token:
        return False

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE auth_tokens
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (_isoformat(_utcnow()), _hash_token(token)),
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def _revoke_user_tokens(cursor, user_id: int, revoked_at: str) -> None:
    cursor.execute(
        """
        UPDATE auth_tokens
        SET revoked_at = ?
        WHERE user_id = ? AND revoked_at IS NULL
        """,
        (revoked_at, user_id),
    )


def set_password(
    username: str,
    password: str,
    database_path=None,
) -> None:
    """Replace a password and revoke all of that user's active tokens."""

    normalized_username = _normalize_username(username)
    password_hash = hash_password(password)
    now = _isoformat(_utcnow())

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE username = ?
            """,
            (password_hash, normalized_username),
        )

        if cursor.rowcount == 0:
            raise ValueError("User not found")

        user = cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()

        _revoke_user_tokens(cursor, user["id"], now)

        connection.commit()

    finally:
        connection.close()


def deactivate_user(username: str, database_path=None) -> None:
    """Disable a user and revoke all of their active tokens."""

    normalized_username = _normalize_username(username)
    now = _isoformat(_utcnow())

    connection = get_connection(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET is_active = 0
            WHERE username = ?
            """,
            (normalized_username,),
        )

        if cursor.rowcount == 0:
            raise ValueError("User not found")

        user = cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()

        _revoke_user_tokens(cursor, user["id"], now)

        connection.commit()

    finally:
        connection.close()
