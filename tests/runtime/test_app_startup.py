import sqlite3

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.services import AppServices
from app.main import app as module_app, create_app


def test_importing_app_does_not_load_model_services():

    assert getattr(module_app.state, "liveness_service", None) is None
    assert getattr(module_app.state, "attendance_service", None) is None


class FakeLivenessService:

    def __init__(self):

        self.closed = False

    def close(self):

        self.closed = True


class FakeFaceService:
    pass


class FakeAttendanceService:
    pass


def test_lifespan_initializes_database_and_serves_root_and_docs(
    tmp_path
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
        ),
        service_factory=lambda settings: services,
    )

    with TestClient(app) as client:

        assert client.get("/").json() == {
            "message": "AI Attendance Service is running"
        }
        assert client.get("/docs").status_code == 200
        assert app.state.services is services
        assert app.state.liveness_service is services.liveness_service
        assert (
            app.state.attendance_service
            is services.attendance_service
        )
        assert app.state.database_initialized is True
        assert app.state.auth_initialized is True

    with sqlite3.connect(database_path) as connection:

        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert {"attendance", "users", "auth_tokens"} <= tables
    assert services.liveness_service.closed is True
