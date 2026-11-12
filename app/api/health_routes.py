"""Health and readiness routes.

These endpoints are unauthenticated so that a process supervisor or a load
balancer can reach them without credentials. They deliberately expose only
operational status and never personal data.

- ``GET /health/live`` reports whether the process is running.
- ``GET /health/ready`` reports whether the service can serve requests.
"""

from fastapi import APIRouter, Request, Response, status

from app.api.health import (
    build_liveness_report,
    build_readiness_report,
)


router = APIRouter()


@router.get("/health/live")
def liveness():
    """Report whether the process is alive.

    A failure of this check means the process should be restarted. It does
    not inspect the database or the models, so a dependency outage never
    causes a restart loop.
    """

    report = build_liveness_report()

    return report.to_dict()


@router.get("/health/ready")
def readiness(request: Request, response: Response):
    """Report whether the service is ready to serve requests.

    Returns ``503`` when a dependency is not ready. A failure of this
    check means the instance should be taken out of rotation, not
    restarted.
    """

    report = build_readiness_report(request)

    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return report.to_dict()
