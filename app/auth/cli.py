import argparse
import getpass
import sys
from pathlib import Path

from app.auth.service import (
    create_user,
    deactivate_user,
    initialize_auth_database,
    set_password,
)
from app.database.attendance_db import delete_old_attendance
from app.core.config import get_settings


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        raise ValueError("Passwords do not match")

    return password


def _database_path(value: str | None) -> Path:
    if value is None:
        return get_settings().database_path

    return Path(value).expanduser().resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage local Attendance.Application accounts.",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--database-path",
        help="Override ATTENDANCE_DB_PATH for this command.",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser(
        "create-user",
        parents=[common],
        help="Create a student or admin account.",
    )
    create.add_argument("username")
    create.add_argument(
        "--role",
        choices=("student", "admin"),
        default="student",
    )
    create.add_argument(
        "--student-id",
        help="Required for student accounts; rejected for admins.",
    )

    reset = commands.add_parser(
        "set-password",
        parents=[common],
        help="Replace a password and revoke all active tokens.",
    )
    reset.add_argument("username")

    deactivate = commands.add_parser(
        "deactivate-user",
        parents=[common],
        help="Disable an account and revoke all active tokens.",
    )
    deactivate.add_argument("username")


    cleanup = commands.add_parser(
        "cleanup",
        parents=[common],
        help="Delete old attendance records based on retention policy.",
    )
    cleanup.add_argument(
        "--retention-days",
        type=int,
        default=365,
        help="Delete records older than this many days (default: 365).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    database_path = _database_path(args.database_path)

    try:
        initialize_auth_database(database_path)

        if args.command == "create-user":
            password = _prompt_password()

            user = create_user(
                args.username,
                password,
                args.role,
                student_id=args.student_id,
                database_path=database_path,
            )

            print(
                f"Created {user.role} account '{user.username}'"
                + (
                    f" for student '{user.student_id}'"
                    if user.student_id
                    else ""
                )
            )

        elif args.command == "set-password":
            password = _prompt_password()

            set_password(
                args.username,
                password,
                database_path=database_path,
            )

            print(f"Password updated for '{args.username}'")

        elif args.command == "deactivate-user":
            deactivate_user(
                args.username,
                database_path=database_path,
            )

            print(f"Deactivated '{args.username}'")

    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
