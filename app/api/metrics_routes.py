"""Metrics middleware and the metrics endpoint.

The middleware records the request count and the request duration for
every request. The route label is the route template, so a request to
``/attendance/student/STU001`` is recorded as
``/attendance/student/{student_id}`` and the student identifier never
reaches the metrics.

The endpoint is unauthenticated so that a scraper can reach it. It
exposes counters, gauges, and histograms only. It contains no personal
data.
"""

import time

from fastapi import APIRouter, Request, Response

from app.core.metrics import get_registry


router = APIRouter()


def install_metrics_middleware(application) -> None:
    """Install the metrics middleware and register the route templates."""

    registry = get_registry()

    registry.register_routes(application)

    @application.middleware("http")
    async def record_metrics(request: Request, call_next):
        """Record the count and the duration of every request."""

        path = request.url.path
        method = request.method

        started = time.perf_counter()

        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        finally:
            duration = time.perf_counter() - started

            route = registry.route_label(path)

            registry.increment(
                "attendance_http_requests_total",
                method=method,
                route=route,
                status=str(status_code),
            )

            registry.observe_duration(
                "attendance_http_request_duration_seconds",
                duration,
                method=method,
                route=route,
            )


def refresh_gauges(request: Request) -> None:
    """Update the operational gauges.

    The gauges describe the state of the dependencies. They are refreshed
    on scrape rather than on a timer, so a scrape always reports the
    current state.
    """

    from app.api.health import check_database, check_models
    from app.api.liveness_routes import sessions

    registry = get_registry()

    database = check_database(
        getattr(request.app.state.settings, "database_path", None)
    )

    registry.set_gauge(
        "attendance_database_reachable",
        1.0 if database["reachable"] else 0.0,
    )

    registry.set_gauge(
        "attendance_database_schema_version",
        float(database["schema_version"] or 0),
    )

    models = check_models(request)

    registry.set_gauge(
        "attendance_models_loaded",
        1.0 if models["loaded"] else 0.0,
    )

    registry.set_gauge(
        "attendance_liveness_sessions_active",
        float(len(sessions)),
    )


@router.get("/metrics")
def metrics(request: Request):
    """Return the service metrics in the Prometheus text format.

    The response contains counters, gauges, and histograms. The route
    labels are route templates, so no student identifier appears.
    """

    registry = get_registry()

    refresh_gauges(request)

    body = registry.render()

    return Response(
        content=body,
        status_code=200,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
