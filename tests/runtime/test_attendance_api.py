import sqlite3
import time

import cv2
import numpy as np
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


def create_image_bytes(width: int = 64, height: int = 64) -> bytes:

    frame = np.zeros(
        (height, width, 3),
        dtype=np.uint8,
    )

    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
    )

    assert ok

    return buffer.tobytes()


def build_test_app(
    tmp_path,
    max_upload_size_bytes: int = 1024 * 1024,
    max_image_width: int = 4096,
    max_image_height: int = 4096,
    max_image_pixels: int = 16 * 1024 * 1024,
):

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
            max_upload_size_bytes=max_upload_size_bytes,
            max_image_width=max_image_width,
            max_image_height=max_image_height,
            max_image_pixels=max_image_pixels,
        ),
        service_factory=lambda settings: services,
    )

    return app, database_path, services

def seed_liveness_session(session_id="123e4567-e89b-42d3-a456-426614174000"):


    sessions[session_id] = {
        "closed_frames": 0,
        "eyes_closed": False,
        "liveness_verified": True,
        "verified_at": time.time(),
    }


def verify_attendance_request(client, session_id="123e4567-e89b-42d3-a456-426614174000"):

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
                create_image_bytes(),
                "image/jpeg",
            )
        },
    )


def test_attendance_rejects_invalid_student_identifier_before_model_inference(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "../../evil",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
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

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid student identifier"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_invalid_subject_before_model_inference(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "x" * 121,
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

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid subject"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_invalid_lecture_identifier_before_model_inference(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "Test Subject",
                "lecture_id": "../evil",
            },
            files={
                "image": (
                    "face.jpg",
                    create_image_bytes(),
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid lecture identifier"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_malformed_image_before_model_inference(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "Test Subject",
                "lecture_id": "TEST-LECTURE",
            },
            files={
                "image": (
                    "face.jpg",
                    b"not-an-image",
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid or unsupported image"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_oversized_image_before_model_inference(
    tmp_path,
):

    app, _, services = build_test_app(
        tmp_path,
        max_upload_size_bytes=16,
    )

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "Test Subject",
                "lecture_id": "TEST-LECTURE",
            },
            files={
                "image": (
                    "face.jpg",
                    b"x" * 17,
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Image exceeds maximum allowed size"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_image_with_excessive_dimensions(
    tmp_path,
):

    app, _, services = build_test_app(
        tmp_path,
        max_upload_size_bytes=1024 * 1024,
        max_image_width=8,
        max_image_height=8,
        max_image_pixels=64,
    )

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "Test Subject",
                "lecture_id": "TEST-LECTURE",
            },
            files={
                "image": (
                    "face.jpg",
                    create_image_bytes(width=64, height=64),
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Image dimensions exceed maximum allowed size"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_invalid_session_identifier(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "not-a-uuid",
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

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid liveness session"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_unknown_session(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
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

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid or expired liveness session"
    assert services.attendance_service.verify_calls == 0


def test_attendance_rejects_invalid_image_content_type(
    tmp_path,
):

    app, _, services = build_test_app(tmp_path)

    with TestClient(app) as client:

        seed_liveness_session()

        response = client.post(
            "/attendance/verify",
            data={
                "student_id": "STU001",
                "session_id": "123e4567-e89b-42d3-a456-426614174000",
                "subject": "Test Subject",
                "lecture_id": "TEST-LECTURE",
            },
            files={
                "image": (
                    "face.jpg",
                    create_image_bytes(),
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Invalid or unsupported image"
    assert services.attendance_service.verify_calls == 0


def test_retrieval_database_error_returns_controlled_error(
    tmp_path,
    monkeypatch,
):

    import app.database.attendance_db as attendance_db


    def _raise(*args, **kwargs):

        raise RuntimeError("database exploded")


    monkeypatch.setattr(
        attendance_db,
        "get_all_attendance",
        _raise,
    )

    app, _, _services = build_test_app(tmp_path)

    with TestClient(app) as client:

        response = client.get("/attendance/all")

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["message"] == "Attendance database error"


def test_fresh_database_retrieval_through_api(tmp_path):

    app, database_path, _services = build_test_app(tmp_path)

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

    app, _, _services = build_test_app(tmp_path)

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
