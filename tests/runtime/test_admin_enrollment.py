"""Tests for the admin enrollment API.

Enrollment writes a biometric template. The tests cover the
authorization boundary, the validation, the audit trail, and the guarantee
that the source image is not stored.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.services import AppServices
from app.main import create_app


TEST_PASSWORD = "test-password-123"


@dataclass
class AdminContext:
    app: object
    database_path: Path
    admin_headers: dict[str, str]
    student_headers: dict[str, str]


class FakeLivenessService:

    def close(self):
        pass


class FakeFaceService:
    pass


class FakeAttendanceService:
    pass


def build_admin_app(
    tmp_path,
    embedding_dir=None,
    max_upload_size_bytes=None,
) -> AdminContext:
    from app.auth.service import (
        create_user,
        initialize_auth_database,
        issue_token,
    )
    from app.database.attendance_db import initialize_database

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)
    initialize_auth_database(database_path)

    admin = create_user(
        "admin-test",
        TEST_PASSWORD,
        "admin",
        database_path=database_path,
    )
    student = create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=database_path,
    )

    admin_token, _ = issue_token(admin.id, database_path=database_path)
    student_token, _ = issue_token(student.id, database_path=database_path)

    if embedding_dir is None:
        embedding_dir = tmp_path / "face_embeddings"

    embedding_dir.mkdir(parents=True, exist_ok=True)

    services = AppServices(
        liveness_service=FakeLivenessService(),
        face_service=FakeFaceService(),
        attendance_service=FakeAttendanceService(),
    )

    settings_kwargs = {
        "database_path": database_path,
        "embedding_dir": embedding_dir,
    }

    if max_upload_size_bytes is not None:
        settings_kwargs["max_upload_size_bytes"] = max_upload_size_bytes

    app = create_app(
        settings=Settings(
            _env_file=None,
            **settings_kwargs,
        ),
        service_factory=lambda settings: services,
    )

    return AdminContext(
        app=app,
        database_path=database_path,
        admin_headers={"Authorization": f"Bearer {admin_token}"},
        student_headers={"Authorization": f"Bearer {student_token}"},
    )


@pytest.fixture
def fake_face_service(monkeypatch):
    """Replace the face analyzer with one that returns a fixed embedding."""

    import app.services.register_face as module

    class StubFace:
        def __init__(self, embedding):
            self.embedding = np.asarray(embedding, dtype=np.float32)

    class StubAnalyzer:
        def get(self, image):
            return [StubFace([0.5, 0.25, 0.125])]

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: StubAnalyzer(),
    )

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )


def image_bytes() -> bytes:
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", frame)
    assert ok
    return buffer.tobytes()


def enroll_request(context, **overrides):
    data = {
        "student_id": "STU001",
        "consent_reference": "consent-2026-001",
    }
    data.update(overrides)

    return {
        "data": data,
        "files": {
            "image": ("face.jpg", image_bytes(), "image/jpeg"),
        },
    }


# =========================================================
# AUTHORIZATION
# =========================================================


def test_enrollment_requires_authentication(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post("/admin/enrollments", **enroll_request(context))

    assert response.status_code == 401


def test_a_student_cannot_enroll(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.student_headers,
            **enroll_request(context),
        )

    assert response.status_code == 403


def test_an_admin_can_enroll(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["student_id"] == "STU001"
    assert response.json()["operator"] == "admin-test"


def test_the_audit_trail_requires_authentication(tmp_path):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/admin/enrollments")

    assert response.status_code == 401


def test_a_student_cannot_read_the_audit_trail(tmp_path):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get(
            "/admin/enrollments",
            headers=context.student_headers,
        )

    assert response.status_code == 403


# =========================================================
# VALIDATION
# =========================================================


def test_enrollment_rejects_an_invalid_student_identifier(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context, student_id="../../evil"),
        )

    assert response.status_code == 400
    assert "student identifier" in response.json()["detail"].lower()


def test_enrollment_requires_a_consent_reference(tmp_path, fake_face_service):
    """An empty form field is rejected as a missing required field."""

    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context, consent_reference=""),
        )

    assert response.status_code == 422


def test_enrollment_rejects_a_blank_consent_reference(tmp_path, fake_face_service):
    """A value that is present but blank is rejected by the handler."""

    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context, consent_reference="   "),
        )

    assert response.status_code == 400
    assert "consent reference" in response.json()["detail"].lower()


def test_enrollment_requires_an_image(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            data={
                "student_id": "STU001",
                "consent_reference": "consent-2026-001",
            },
        )

    assert response.status_code == 422


def test_enrollment_rejects_an_oversized_image(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path, max_upload_size_bytes=16)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    # The request is rejected before the enrollment is attempted.
    assert response.status_code == 413
    assert "maximum allowed size" in response.json()["detail"].lower()


# =========================================================
# THE AUDIT TRAIL
# =========================================================


def test_a_successful_enrollment_is_audited(tmp_path, fake_face_service):
    from app.services.enrollment_audit import list_enrollments

    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    assert response.status_code == 200

    entries = list_enrollments(database_path=context.database_path)

    assert len(entries) == 1
    assert entries[0].student_id == "STU001"
    assert entries[0].operator == "admin-test"
    assert entries[0].consent_reference == "consent-2026-001"
    assert entries[0].outcome == "enrolled"


def test_a_refused_enrollment_is_audited(tmp_path, fake_face_service):
    from app.services.enrollment_audit import list_enrollments

    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        # The first enrollment succeeds.
        first = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )
        assert first.status_code == 200

        # The second is refused, because the embedding exists.
        second = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    assert second.status_code == 409

    entries = list_enrollments(database_path=context.database_path)

    assert len(entries) == 2
    assert entries[0].outcome == "rejected"


def test_the_audit_trail_can_be_read_by_an_admin(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

        response = client.get(
            "/admin/enrollments",
            headers=context.admin_headers,
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["enrollments"][0]["student_id"] == "STU001"


def test_the_audit_trail_holds_no_biometric_material(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

        response = client.get(
            "/admin/enrollments",
            headers=context.admin_headers,
        )

    body = response.text

    assert "0.5" not in body
    assert "0.25" not in body
    assert ".npy" not in body


def test_the_audit_trail_can_be_filtered_by_student(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

        response = client.get(
            "/admin/enrollments",
            headers=context.admin_headers,
            params={"student_id": "STU999"},
        )

    assert response.status_code == 200
    assert response.json()["count"] == 0


# =========================================================
# THE IMAGE IS NOT STORED
# =========================================================


def test_the_source_image_is_not_stored(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    # Only the embedding is written. The image is not kept anywhere.
    embedding_dir = tmp_path / "face_embeddings"

    stored = sorted(entry.name for entry in embedding_dir.iterdir())

    assert stored == ["STU001.npy"]


def test_the_enrollment_writes_the_embedding(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    assert response.status_code == 200

    embedding = tmp_path / "face_embeddings" / "STU001.npy"

    assert embedding.is_file()

    values = np.load(str(embedding))

    assert np.allclose(values, [0.5, 0.25, 0.125])


def test_the_temporary_image_is_removed(tmp_path, fake_face_service):
    """The uploaded image must not be left in the temporary directory."""

    import tempfile

    context = build_admin_app(tmp_path)

    before = set(Path(tempfile.gettempdir()).glob("tmp*.jpg"))

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    after = set(Path(tempfile.gettempdir()).glob("tmp*.jpg"))

    assert after == before


def test_the_enrollment_does_not_store_the_image_in_the_database(tmp_path, fake_face_service):
    context = build_admin_app(tmp_path)

    with TestClient(context.app) as client:

        client.post(
            "/admin/enrollments",
            headers=context.admin_headers,
            **enroll_request(context),
        )

    connection = sqlite3.connect(str(context.database_path))
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "enrollment_audit" in tables
    assert "enrollment_images" not in tables
