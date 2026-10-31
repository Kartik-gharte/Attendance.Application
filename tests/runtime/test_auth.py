import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.liveness_routes import sessions
from app.auth.models import UserPrincipal
from app.auth.service import (
    authenticate_user,
    create_user,
    deactivate_user,
    initialize_auth_database,
    issue_token,
    revoke_token,
    set_password,
    verify_token,
)
from app.core.config import Settings
from app.core.services import AppServices
from app.main import create_app


TEST_PASSWORD = "test-password-123"
TEST_SESSION_ID = "123e4567-e89b-42d3-a456-426614174000"


class FakeLivenessService:

    def close(self):
        pass


class FakeFaceService:
    pass


class FakeAttendanceService:

    def __init__(self):

        self.verify_calls = 0

    def verify_face(self, image_path, student_id):

        self.verify_calls += 1

        return {
            "result": "MATCH",
            "similarity": 0.9,
            "threshold": 0.4,
        }

    def create_attendance_result(
        self,
        student_id,
        liveness_verified,
        face_result,
    ):

        return {
            "student_id": student_id,
            "liveness": "VERIFIED",
            "face": "MATCH",
            "similarity": face_result["similarity"],
            "threshold": face_result["threshold"],
            "attendance": "VERIFIED",
        }


@dataclass
class AuthContext:
    app: object
    database_path: Path
    services: AppServices
    student: UserPrincipal
    other_student: UserPrincipal
    admin: UserPrincipal
    student_headers: dict[str, str]
    other_headers: dict[str, str]
    admin_headers: dict[str, str]


@pytest.fixture(autouse=True)
def clear_sessions():

    sessions.clear()

    yield

    sessions.clear()


def create_image_bytes() -> bytes:

    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    ok, buffer = cv2.imencode(".jpg", frame)

    assert ok

    return buffer.tobytes()


def build_auth_app(tmp_path) -> AuthContext:

    database_path = tmp_path / "attendance.db"

    initialize_auth_database(database_path)

    student = create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=database_path,
    )
    other_student = create_user(
        "other-student",
        TEST_PASSWORD,
        "student",
        student_id="STU002",
        database_path=database_path,
    )
    admin = create_user(
        "admin-test",
        TEST_PASSWORD,
        "admin",
        database_path=database_path,
    )

    tokens = {}

    for name, user in (
        ("student", student),
        ("other", other_student),
        ("admin", admin),
    ):
        token, _ = issue_token(user.id, database_path=database_path)
        tokens[name] = token

    services = AppServices(
        liveness_service=FakeLivenessService(),
        face_service=FakeFaceService(),
        attendance_service=FakeAttendanceService(),
    )

    app = create_app(
        settings=Settings(
            _env_file=None,
            database_path=database_path,
        ),
        service_factory=lambda settings: services,
    )

    return AuthContext(
        app=app,
        database_path=database_path,
        services=services,
        student=student,
        other_student=other_student,
        admin=admin,
        student_headers={
            "Authorization": f"Bearer {tokens['student']}",
        },
        other_headers={
            "Authorization": f"Bearer {tokens['other']}",
        },
        admin_headers={
            "Authorization": f"Bearer {tokens['admin']}",
        },
    )


def seed_liveness_session(user_id, session_id=TEST_SESSION_ID):

    sessions[session_id] = {
        "user_id": user_id,
        "closed_frames": 0,
        "eyes_closed": False,
        "liveness_verified": True,
        "verified_at": time.time(),
    }


def verify_attendance_request(
    client,
    headers,
    student_id="STU001",
    session_id=TEST_SESSION_ID,
):

    return client.post(
        "/attendance/verify",
        headers=headers,
        data={
            "student_id": student_id,
            "session_id": session_id,
            "subject": "Test Subject",
            "lecture_id": "TEST-LECTURE",
        },
        files={
            "image": (
                "face.jpg",
                create_image_bytes(),
                "image/jpeg",
            )
        },
    )


def test_create_user_hashes_password_and_authenticates(tmp_path):

    database_path = tmp_path / "auth.db"

    initialize_auth_database(database_path)

    user = create_user(
        "Student.One",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    assert user.username == "student.one"
    assert user.role == "student"
    assert user.student_id == "STU001"

    with sqlite3.connect(database_path) as connection:

        password_hash = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = 'student.one'
            """
        ).fetchone()[0]

    assert password_hash != TEST_PASSWORD
    assert password_hash.startswith("$argon2")

    assert authenticate_user(
        "student.one",
        TEST_PASSWORD,
        database_path=database_path,
    ) == user
    assert authenticate_user(
        "student.one",
        "wrong-password",
        database_path=database_path,
    ) is None


def test_create_user_rejects_invalid_accounts(tmp_path):

    database_path = tmp_path / "auth.db"

    initialize_auth_database(database_path)

    with pytest.raises(ValueError):
        create_user(
            "ab",
            TEST_PASSWORD,
            "student",
            student_id="STU001",
            database_path=database_path,
        )

    with pytest.raises(ValueError):
        create_user(
            "student-test",
            "short",
            "student",
            student_id="STU001",
            database_path=database_path,
        )

    with pytest.raises(ValueError):
        create_user(
            "student-test",
            TEST_PASSWORD,
            "teacher",
            student_id="STU001",
            database_path=database_path,
        )

    with pytest.raises(ValueError):
        create_user(
            "student-test",
            TEST_PASSWORD,
            "student",
            database_path=database_path,
        )

    with pytest.raises(ValueError):
        create_user(
            "admin-test",
            TEST_PASSWORD,
            "admin",
            student_id="STU001",
            database_path=database_path,
        )

    create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    with pytest.raises(ValueError):
        create_user(
            "student-test",
            TEST_PASSWORD,
            "student",
            student_id="STU002",
            database_path=database_path,
        )

    with pytest.raises(ValueError):
        create_user(
            "other-student",
            TEST_PASSWORD,
            "student",
            student_id="STU001",
            database_path=database_path,
        )


def test_token_lifecycle_and_credential_rotation(tmp_path):

    database_path = tmp_path / "auth.db"

    initialize_auth_database(database_path)

    user = create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    token, expires_at = issue_token(
        user.id,
        ttl_seconds=3600,
        database_path=database_path,
    )

    assert expires_at.tzinfo is not None
    assert verify_token(token, database_path=database_path) == user
    assert revoke_token(token, database_path=database_path) is True
    assert verify_token(token, database_path=database_path) is None

    expired_token, _ = issue_token(
        user.id,
        ttl_seconds=0,
        database_path=database_path,
    )

    assert verify_token(expired_token, database_path=database_path) is None

    active_token, _ = issue_token(
        user.id,
        ttl_seconds=3600,
        database_path=database_path,
    )

    set_password(
        "student-test",
        "new-test-password-456",
        database_path=database_path,
    )

    assert verify_token(active_token, database_path=database_path) is None
    assert authenticate_user(
        "student-test",
        TEST_PASSWORD,
        database_path=database_path,
    ) is None
    assert authenticate_user(
        "student-test",
        "new-test-password-456",
        database_path=database_path,
    ) == user

    deactivated_token, _ = issue_token(
        user.id,
        ttl_seconds=3600,
        database_path=database_path,
    )

    deactivate_user("student-test", database_path=database_path)

    assert verify_token(
        deactivated_token,
        database_path=database_path,
    ) is None
    assert authenticate_user(
        "student-test",
        "new-test-password-456",
        database_path=database_path,
    ) is None


def test_protected_endpoints_require_authentication(tmp_path):

    context = build_auth_app(tmp_path)

    with TestClient(context.app) as client:

        assert client.get("/auth/me").status_code == 401
        assert client.get("/attendance/all").status_code == 401
        assert client.get("/attendance/student/STU001").status_code == 401
        assert client.post("/liveness/start").status_code == 401
        assert client.post("/attendance/verify").status_code == 401
        assert client.post("/auth/logout").status_code == 401


def test_login_me_and_logout(tmp_path):

    context = build_auth_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/auth/token",
            data={
                "username": "Student-Test",
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]

        headers = {
            "Authorization": (
                f"Bearer {response.json()['access_token']}"
            )
        }

        me = client.get("/auth/me", headers=headers)

        assert me.status_code == 200
        assert me.json() == {
            "username": "student-test",
            "role": "student",
            "student_id": "STU001",
        }

        logout = client.post("/auth/logout", headers=headers)

        assert logout.status_code == 200
        assert client.get("/auth/me", headers=headers).status_code == 401


def test_login_rejects_bad_credentials(tmp_path):

    context = build_auth_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/auth/token",
            data={
                "username": "student-test",
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_expired_token_is_rejected_by_api(tmp_path):

    context = build_auth_app(tmp_path)

    expired_token, _ = issue_token(
        context.student.id,
        ttl_seconds=0,
        database_path=context.database_path,
    )

    with TestClient(context.app) as client:

        response = client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {expired_token}",
            },
        )

    assert response.status_code == 401


def test_liveness_start_binds_session_to_authenticated_student(tmp_path):

    context = build_auth_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/liveness/start",
            headers=context.student_headers,
        )

    session = sessions[response.json()["session_id"]]

    assert response.status_code == 200
    assert session["user_id"] == context.student.id


def test_student_cannot_read_another_students_attendance(tmp_path):

    context = build_auth_app(tmp_path)

    with TestClient(context.app) as client:

        own = client.get(
            "/attendance/student/STU001",
            headers=context.student_headers,
        )
        other = client.get(
            "/attendance/student/STU002",
            headers=context.student_headers,
        )
        all_records = client.get(
            "/attendance/all",
            headers=context.student_headers,
        )

    assert own.status_code == 200
    assert other.status_code == 403
    assert all_records.status_code == 403


def test_admin_can_read_attendance_but_cannot_mark_it(tmp_path):

    context = build_auth_app(tmp_path)
    seed_liveness_session(context.student.id)

    with TestClient(context.app) as client:

        student_records = client.get(
            "/attendance/student/STU001",
            headers=context.admin_headers,
        )
        all_records = client.get(
            "/attendance/all",
            headers=context.admin_headers,
        )
        start_liveness = client.post(
            "/liveness/start",
            headers=context.admin_headers,
        )
        verify = verify_attendance_request(
            client,
            headers=context.admin_headers,
        )

    assert student_records.status_code == 200
    assert all_records.status_code == 200
    assert start_liveness.status_code == 403
    assert verify.status_code == 403
    assert context.services.attendance_service.verify_calls == 0


def test_student_cannot_mark_attendance_for_another_student(tmp_path):

    context = build_auth_app(tmp_path)
    seed_liveness_session(context.student.id)

    with TestClient(context.app) as client:

        response = verify_attendance_request(
            client,
            headers=context.student_headers,
            student_id="STU002",
        )

    assert response.status_code == 403
    assert context.services.attendance_service.verify_calls == 0


def test_student_cannot_use_another_students_liveness_session(tmp_path):

    context = build_auth_app(tmp_path)
    seed_liveness_session(context.other_student.id)

    with TestClient(context.app) as client:

        frame_response = client.post(
            "/liveness/frame",
            params={"session_id": TEST_SESSION_ID},
            headers=context.student_headers,
            files={
                "image": (
                    "frame.jpg",
                    create_image_bytes(),
                    "image/jpeg",
                )
            },
        )
        verify_response = verify_attendance_request(
            client,
            headers=context.student_headers,
        )

    assert frame_response.status_code == 403
    assert verify_response.status_code == 403
    assert context.services.attendance_service.verify_calls == 0
