import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.api.liveness_routes import sessions
from app.core.config import Settings
from app.core.services import AppServices
from app.main import create_app


class FakeLivenessService:

    def close(self):
        pass


class FakeFaceService:
    pass


class FakeAttendanceService:

    def verify_face(self, image_path, student_id):

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
            "liveness": "VERIFIED" if liveness_verified else "FAILED",
            "face": "MATCH",
            "similarity": face_result["similarity"],
            "threshold": face_result["threshold"],
            "attendance": "VERIFIED",
        }


@pytest.fixture(autouse=True)
def clear_sessions():

    sessions.clear()

    yield

    sessions.clear()


def build_test_app(tmp_path):

    database_path = tmp_path / "attendance.db"

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

    return app, database_path


def seed_liveness_session(session_id="test-session"):

    sessions[session_id] = {
        "closed_frames": 0,
        "eyes_closed": False,
        "liveness_verified": True,
        "verified_at": time.time(),
    }


def verify_attendance_request(client, session_id="test-session"):

    return client.post(
        "/attendance/verify",
        data={
            "student_id": "STU-TEST",
            "session_id": session_id,
            "subject": "Test Subject",
            "lecture_id": "TEST-LECTURE",
        },
        files={
            "image": (
                "face.jpg",
                b"synthetic-test-image",
                "image/jpeg",
            )
        },
    )


def test_fresh_database_retrieval_through_api(tmp_path):

    app, database_path = build_test_app(tmp_path)

    with TestClient(app) as client:

        response = client.get("/attendance/all")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "count": 0,
            "attendance": [],
        }

        student_response = client.get(
            "/attendance/student/STU-TEST"
        )

        assert student_response.status_code == 200
        assert student_response.json()["count"] == 0

    with sqlite3.connect(database_path) as connection:

        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'attendance'
            """
        ).fetchone()

    assert table == ("attendance",)


def test_duplicate_attendance_is_mapped_to_duplicate_response(tmp_path):

    app, _ = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        first = verify_attendance_request(client)

        seed_liveness_session()

        duplicate = verify_attendance_request(client)

        records = client.get("/attendance/all")

    assert first.status_code == 200
    assert first.json()["status"] == "success"
    assert first.json()["duplicate"] is False

    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["attendance_status"] == "ALREADY_MARKED"

    assert records.status_code == 200
    assert records.json()["count"] == 1
    assert records.json()["attendance"][0]["student_id"] == "STU-TEST"
