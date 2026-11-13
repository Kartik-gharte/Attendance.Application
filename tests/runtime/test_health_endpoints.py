"""Tests for the health and readiness endpoints.

The tests verify that liveness and readiness answer different questions,
that readiness reflects the real state of the database and the models,
and that neither endpoint requires authentication or exposes personal data.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.services import AppServices
from app.main import create_app


TEST_PASSWORD = "test-password-123"


class FakeLivenessService:

    def __init__(self, detector=None):
        self.detector = detector

    def close(self):
        pass


class FakeFaceService:

    def __init__(self, analyzer=None):
        self.app = analyzer


class FakeAttendanceService:

    def verify_face(self, image_path, student_id):
        return {
            "result": "MATCH",
            "similarity": 0.9,
            "threshold": 0.4,
        }

    def create_attendance_result(self, student_id, liveness_verified, face_result):
        return {
            "student_id": student_id,
            "liveness": "VERIFIED" if liveness_verified else "FAILED",
            "face": "MATCH",
            "similarity": face_result["similarity"],
            "threshold": face_result["threshold"],
            "attendance": "VERIFIED",
        }


@dataclass
class HealthTestContext:
    app: object
    database_path: Path


def build_health_app(
    tmp_path,
    liveness_detector=object(),
    face_analyzer=object(),
    initialize_database=True,
) -> HealthTestContext:
    from app.auth.service import initialize_auth_database
    from app.database.attendance_db import initialize_database as init_db

    database_path = tmp_path / "attendance.db"

    if initialize_database:
        init_db(database_path)

    initialize_auth_database(database_path)

    services = AppServices(
        liveness_service=FakeLivenessService(liveness_detector),
        face_service=FakeFaceService(face_analyzer),
        attendance_service=FakeAttendanceService(),
    )

    app = create_app(
        settings=Settings(
            _env_file=None,
            database_path=database_path,
        ),
        service_factory=lambda settings: services,
    )

    return HealthTestContext(
        app=app,
        database_path=database_path,
    )


# =========================================================
# LIVENESS
# =========================================================


def test_liveness_reports_ok(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"]["process"]["alive"] is True


def test_liveness_does_not_require_authentication(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/health/live")

    assert response.status_code == 200


def test_liveness_stays_ok_when_the_database_is_missing(tmp_path):
    """A dependency failure must not fail the liveness check."""

    context = build_health_app(
        tmp_path,
        initialize_database=False,
    )

    with TestClient(context.app) as client:

        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_liveness_stays_ok_when_the_models_are_not_loaded(tmp_path):
    context = build_health_app(
        tmp_path,
        liveness_detector=None,
        face_analyzer=None,
    )

    with TestClient(context.app) as client:

        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# =========================================================
# READINESS
# =========================================================


def test_readiness_reports_ok_when_everything_is_ready(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/health/ready")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["checks"]["database"]["reachable"] is True
    assert payload["checks"]["models"]["loaded"] is True


def test_readiness_does_not_require_authentication(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/health/ready")

    assert response.status_code == 200


def test_readiness_reports_the_schema_version(tmp_path):
    from app.database.migrations import SCHEMA_VERSION

    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/health/ready")

    payload = response.json()

    assert payload["checks"]["database"]["schema_version"] == SCHEMA_VERSION
    assert (
        payload["checks"]["database"]["expected_schema_version"]
        == SCHEMA_VERSION
    )


def test_readiness_fails_when_the_database_is_missing(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        # The lifespan creates the database, so it is removed afterwards to
        # simulate the database disappearing at run time.
        context.database_path.unlink()

        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"]["reachable"] is False


def test_readiness_fails_when_the_attendance_table_is_missing(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        connection = sqlite3.connect(str(context.database_path))
        try:
            connection.execute("DROP TABLE attendance")
            connection.commit()
        finally:
            connection.close()

        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"]["reachable"] is False


def test_readiness_fails_when_the_models_are_not_loaded(tmp_path):
    context = build_health_app(
        tmp_path,
        liveness_detector=None,
    )

    with TestClient(context.app) as client:

        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["models"]["loaded"] is False


def test_readiness_fails_when_the_face_model_is_not_loaded(tmp_path):
    context = build_health_app(
        tmp_path,
        face_analyzer=None,
    )

    with TestClient(context.app) as client:

        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["models"]["loaded"] is False


def test_readiness_reports_a_pending_migration(tmp_path):
    """A database that is behind the expected version is not ready."""

    from app.database.migrations import SCHEMA_VERSION

    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        # The startup migrates the database, so the version records are
        # removed afterwards to simulate a database that is behind.
        connection = sqlite3.connect(str(context.database_path))
        try:
            connection.execute("DELETE FROM schema_migrations")
            connection.commit()
        finally:
            connection.close()

        response = client.get("/health/ready")

    assert response.status_code == 503

    payload = response.json()

    assert payload["checks"]["database"]["schema_version"] == 0
    assert "Pending migrations" in payload["checks"]["database"]["detail"]


# =========================================================
# INFORMATION DISCLOSURE
# =========================================================


def test_health_endpoints_do_not_expose_personal_data(tmp_path):
    from app.auth.service import create_user
    from app.database.attendance_db import mark_attendance

    context = build_health_app(tmp_path)

    create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=context.database_path,
    )

    mark_attendance(
        student_id="STU001",
        subject="Confidential Subject",
        lecture_id="CONF-001",
        liveness_status="VERIFIED",
        face_status="MATCH",
        similarity=0.91,
        attendance_status="PRESENT",
        database_path=context.database_path,
    )

    with TestClient(context.app) as client:

        live = client.get("/health/live")
        ready = client.get("/health/ready")

    for response in (live, ready):

        body = response.text

        assert "STU001" not in body
        assert "Confidential Subject" not in body
        assert "CONF-001" not in body
        assert TEST_PASSWORD not in body


def test_health_endpoints_do_not_expose_the_database_path(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        live = client.get("/health/live")
        ready = client.get("/health/ready")

    for response in (live, ready):

        assert "attendance.db" not in response.text


def test_health_endpoints_do_not_expose_the_embedding_directory(tmp_path):
    context = build_health_app(tmp_path)

    with TestClient(context.app) as client:

        ready = client.get("/health/ready")

    assert "face_embeddings" not in ready.text
