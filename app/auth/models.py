from dataclasses import dataclass


STUDENT_ROLE = "student"
ADMIN_ROLE = "admin"
ROLES = frozenset({STUDENT_ROLE, ADMIN_ROLE})


@dataclass(frozen=True)
class UserPrincipal:
    """Authenticated application user without password material."""

    id: int
    username: str
    role: str
    student_id: str | None = None
