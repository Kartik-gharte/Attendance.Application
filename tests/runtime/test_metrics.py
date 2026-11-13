"""Tests for the metrics endpoint and the redaction of metric labels.

The central property under test is that a student identifier never
reaches the metrics. The route label must always be the route template.
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.metrics import (
    DURATION_BUCKETS,
    UNMATCHED_ROUTE,
    MetricsRegistry,
    _collect_route_paths,
    get_registry,
)
from app.core.services import AppServices
from app.main import create_app


TEST_PASSWORD = "test-password-123"
SECRET_STUDENT_ID = "SECRETSTUDENT42"


class FakeLivenessService:

    detector = object()

    def close(self):
        pass


class FakeFaceService:

    app = object()


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
            "liveness": "VERIFIED",
            "face": "MATCH",
            "similarity": face_result["similarity"],
            "threshold": face_result["threshold"],
            "attendance": "VERIFIED",
        }


@dataclass
class MetricsTestContext:
    app: object
    database_path: Path


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the process-wide registry around every test."""

    registry = get_registry()

    registry.reset()

    yield

    registry.reset()


def build_metrics_app(tmp_path) -> MetricsTestContext:
    from app.auth.service import initialize_auth_database
    from app.database.attendance_db import initialize_database

    database_path = tmp_path / "attendance.db"

    initialize_database(database_path)
    initialize_auth_database(database_path)

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

    return MetricsTestContext(app=app, database_path=database_path)


# =========================================================
# THE ENDPOINT
# =========================================================


def test_metrics_endpoint_is_reachable(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_metrics_endpoint_does_not_require_authentication(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_report_that_the_service_is_up(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        body = client.get("/metrics").text

    assert "attendance_up 1" in body


# =========================================================
# LABEL REDACTION
# =========================================================


def test_student_identifier_never_appears_in_the_metrics(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get(f"/attendance/student/{SECRET_STUDENT_ID}")
        body = client.get("/metrics").text

    assert SECRET_STUDENT_ID not in body


def test_the_route_template_is_used_as_the_label(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get(f"/attendance/student/{SECRET_STUDENT_ID}")
        body = client.get("/metrics").text

    assert "/attendance/student/{student_id}" in body


def test_an_unmatched_path_is_not_recorded_verbatim(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get(f"/nothing/here/{SECRET_STUDENT_ID}")
        body = client.get("/metrics").text

    assert SECRET_STUDENT_ID not in body
    assert f'route="{UNMATCHED_ROUTE}"' in body


def test_the_request_count_is_recorded(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get("/health/live")
        client.get("/health/live")
        body = client.get("/metrics").text

    assert 'attendance_http_requests_total{method="GET",route="/health/live",status="200"} 2.0' in body


def test_the_status_code_is_recorded(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get("/attendance/all")
        body = client.get("/metrics").text

    assert 'status="401"' in body


def test_the_duration_histogram_is_recorded(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        client.get("/health/live")
        body = client.get("/metrics").text

    assert "attendance_http_request_duration_seconds_bucket" in body
    assert "attendance_http_request_duration_seconds_count" in body
    assert "attendance_http_request_duration_seconds_sum" in body


# =========================================================
# GAUGES
# =========================================================


def test_the_database_gauge_is_reported(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        body = client.get("/metrics").text

    assert "attendance_database_reachable 1.0" in body


def test_the_models_gauge_is_reported(tmp_path):
    context = build_metrics_app(tmp_path)

    with TestClient(context.app) as client:

        body = client.get("/metrics").text

    assert "attendance_models_loaded 1.0" in body


def test_the_liveness_session_gauge_is_reported(tmp_path):
    from app.auth.service import create_user, issue_token

    context = build_metrics_app(tmp_path)

    user = create_user(
        "student-test",
        TEST_PASSWORD,
        "student",
        student_id="STU001",
        database_path=context.database_path,
    )

    token, _ = issue_token(user.id, database_path=context.database_path)

    with TestClient(context.app) as client:

        client.post(
            "/liveness/start",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = client.get("/metrics").text

    assert "attendance_liveness_sessions_active 1.0" in body


# =========================================================
# THE REGISTRY
# =========================================================


def test_the_registry_counts_a_metric():
    registry = MetricsRegistry()

    registry.increment("test_counter", route="/a")

    assert 'test_counter{route="/a"} 1.0' in registry.render()


def test_the_registry_accumulates_a_counter():
    registry = MetricsRegistry()

    registry.increment("test_counter")
    registry.increment("test_counter", value=2.0)

    assert "test_counter 3.0" in registry.render()


def test_the_registry_sets_a_gauge():
    registry = MetricsRegistry()

    registry.set_gauge("test_gauge", 1.0)

    assert "test_gauge 1.0" in registry.render()

    registry.set_gauge("test_gauge", 0.0)

    assert "test_gauge 0.0" in registry.render()


def test_the_registry_buckets_a_duration():
    registry = MetricsRegistry()

    registry.observe_duration("test_histogram", 0.005)
    registry.observe_duration("test_histogram", 5.0)

    output = registry.render()

    assert 'test_histogram_bucket{le="0.01"} 1.0' in output
    assert 'test_histogram_bucket{le="0.025"} 1.0' in output
    assert 'test_histogram_bucket{le="5.0"} 2.0' in output
    assert 'test_histogram_bucket{le="+Inf"} 2.0' in output
    assert "test_histogram_count 2.0" in output


def test_the_registry_counts_a_duration_above_every_bucket():
    registry = MetricsRegistry()

    registry.observe_duration("test_histogram", 100.0)

    output = registry.render()

    assert 'test_histogram_bucket{le="+Inf"} 1.0' in output
    assert 'test_histogram_bucket{le="10.0"} 0.0' in output


def test_the_registry_escapes_a_label_value():
    registry = MetricsRegistry()

    registry.increment("test_counter", route='/a"b\\c')

    output = registry.render()

    assert '\\"' in output
    assert "\\\\" in output


def test_reset_clears_the_registry():
    registry = MetricsRegistry()

    registry.increment("test_counter")
    registry.set_gauge("test_gauge", 1.0)

    registry.reset()

    output = registry.render()

    assert "test_counter" not in output
    assert "test_gauge" not in output


def test_the_duration_buckets_are_ordered():
    assert list(DURATION_BUCKETS) == sorted(DURATION_BUCKETS)


# =========================================================
# ROUTE TEMPLATE COLLECTION
# =========================================================


def test_collect_route_paths_finds_the_templates(tmp_path):
    context = build_metrics_app(tmp_path)

    paths = _collect_route_paths(context.app.routes)

    assert "/attendance/student/{student_id}" in paths
    assert "/health/live" in paths


def test_collect_route_paths_returns_no_concrete_path(tmp_path):
    context = build_metrics_app(tmp_path)

    paths = _collect_route_paths(context.app.routes)

    for path in paths:
        assert SECRET_STUDENT_ID not in path
