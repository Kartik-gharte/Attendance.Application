"""Health and readiness checks for the attendance service.

Two distinct questions are answered separately:

- **Liveness** — is the process running and able to serve requests at all?
  A failing liveness check means the process should be restarted.
- **Readiness** — are the dependencies ready, so that a request can
  actually be served? A failing readiness check means the instance should
  be taken out of rotation but not restarted.

The readiness check verifies that the database is reachable, that its
schema is at the expected version, and that the biometric models are
loaded.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging_config import get_logger
from app.database.migrations import SCHEMA_VERSION, get_current_schema_version


logger = get_logger("api.health")


@dataclass
class HealthReport:
    """The result of a health or readiness check."""

    status: str
    checks: dict[str, dict] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": self.checks,
        }


def check_database(database_path=None) -> dict:
    """Check that the database is reachable and at the expected version."""

    from app.core.config import get_settings

    if database_path is None:
        database_path = get_settings().database_path

    path = Path(database_path)

    result: dict = {
        "reachable": False,
        "schema_version": None,
        "expected_schema_version": SCHEMA_VERSION,
        "detail": None,
    }

    if not path.is_file():
        result["detail"] = "The database file does not exist"
        return result

    try:

        connection = sqlite3.connect(str(path))

        try:

            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if not integrity or integrity[0] != "ok":
                result["detail"] = "The database failed the integrity check"
                return result

            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }

            if "attendance" not in tables:
                result["detail"] = (
                    "The database does not contain the attendance table"
                )
                return result

            result["reachable"] = True

            version = get_current_schema_version(path)
            result["schema_version"] = version

            if version < SCHEMA_VERSION:
                result["detail"] = (
                    f"The database schema is at version {version} but "
                    f"version {SCHEMA_VERSION} is expected. Pending "
                    "migrations must be applied."
                )

        finally:
            connection.close()

    except sqlite3.Error as error:
        result["detail"] = (
            f"The database could not be read: {type(error).__name__}"
        )

    return result


def check_models(request) -> dict:
    """Check that the biometric models are loaded and usable."""

    result: dict = {
        "loaded": False,
        "detail": None,
    }

    liveness_service = getattr(request.app.state, "liveness_service", None)
    face_service = getattr(request.app.state, "face_service", None)

    if liveness_service is None or face_service is None:
        result["detail"] = "The biometric services are not available"
        return result

    detector = getattr(liveness_service, "detector", None)
    analyzer = getattr(face_service, "app", None)

    if detector is None or analyzer is None:
        result["detail"] = "The biometric models are not loaded"
        return result

    result["loaded"] = True

    return result


def build_liveness_report() -> HealthReport:
    """Report whether the process can serve requests at all.

    The liveness check does not touch the database or the models. It only
    confirms that the application is running and that the routing layer
    can answer. A dependency failure must not cause a restart.
    """

    return HealthReport(
        status="ok",
        checks={
            "process": {
                "alive": True,
                "detail": "The application process is running",
            },
        },
    )


def build_readiness_report(request) -> HealthReport:
    """Report whether the service can serve real requests.

    The readiness check verifies the database and the biometric models.
    """

    checks: dict[str, dict] = {}

    database = check_database(
        getattr(request.app.state.settings, "database_path", None)
    )
    checks["database"] = database

    models = check_models(request)
    checks["models"] = models

    problems = []

    if not database["reachable"]:
        problems.append("The database is not reachable")

    elif database["detail"]:
        problems.append(database["detail"])

    if not models["loaded"]:
        problems.append("The biometric models are not loaded")

    if problems:
        logger.warning("Readiness check failed: %s", "; ".join(problems))

        return HealthReport(status="not_ready", checks=checks)

    return HealthReport(status="ok", checks=checks)
