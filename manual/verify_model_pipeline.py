"""Verify the attendance pipeline against the real biometric models.

The runtime test suite deliberately uses fake model services, so that it
runs without the model assets. This script covers the other half: it loads
the real MediaPipe and InsightFace models and drives the actual pipeline,
so that the model path is exercised rather than assumed.

It uses a synthetic frame with no face. That is enough to prove the parts
that a fake service cannot:

- the real models load and initialize;
- the MediaPipe Face Landmarker runs on a real frame without error;
- the blink detection path executes;
- the InsightFace detector runs on a real image without error;
- the pipeline rejects an image with no face, instead of accepting it;
- the attendance path stores nothing when the face does not match.

What it cannot cover is a successful match, because that needs a real
consented face. See docs/EVALUATION_DATASET_POLICY.md.

Run it from the project root::

    python -m manual.verify_model_pipeline

The script exits nonzero when the pipeline does not behave as expected, so
it can be used as a check.
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import cv2
import numpy as np

from app.core.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.core.services import build_services


logger = get_logger("manual.verify_model_pipeline")


class VerificationFailure(RuntimeError):
    """Raised when the pipeline does not behave as expected."""


def synthetic_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Return a frame with no face.

    A mid-grey frame with a little noise exercises the detector without
    presenting anything that resembles a person.
    """

    rng = np.random.default_rng(20260101)

    frame = rng.integers(
        110,
        140,
        size=(height, width, 3),
        dtype=np.uint8,
    )

    return frame


def check_models_load(services) -> dict:
    """Check that both real models are loaded."""

    detector = getattr(services.liveness_service, "detector", None)
    analyzer = getattr(services.face_service, "app", None)

    if detector is None:
        raise VerificationFailure(
            "The MediaPipe Face Landmarker was not loaded"
        )

    if analyzer is None:
        raise VerificationFailure("The InsightFace model was not loaded")

    logger.info("MediaPipe Face Landmarker: loaded")
    logger.info("InsightFace model: loaded")

    return {"detector": detector, "analyzer": analyzer}


def check_liveness_runs(services, frame) -> dict:
    """Run the real liveness path on a frame with no face."""

    started = time.perf_counter()

    result = services.liveness_service.process_frame(frame, 0, False)

    elapsed = time.perf_counter() - started

    if "liveness_verified" not in result:
        raise VerificationFailure(
            "The liveness service did not return a liveness_verified field"
        )

    if result["liveness_verified"]:
        raise VerificationFailure(
            "The liveness service verified a frame that contains no face"
        )

    if result.get("face_detected"):
        raise VerificationFailure(
            "The liveness service detected a face in a synthetic frame"
        )

    logger.info(
        "Liveness path ran in %.0f ms and correctly found no face",
        elapsed * 1000,
    )

    return result


def check_face_service_runs(services, frame, embedding_dir: Path) -> dict:
    """Run the real face service on an image with no face."""

    image_path = embedding_dir / "synthetic.jpg"

    cv2.imwrite(str(image_path), frame)

    started = time.perf_counter()

    try:
        result = services.face_service.recognize(str(image_path), "STU001")

    except ValueError as error:
        # The service refuses an image with no detectable face, which is
        # the expected behavior for this input.
        logger.info(
            "The face service refused the synthetic image in %.0f ms: %s",
            (time.perf_counter() - started) * 1000,
            error,
        )

        return {"result": "NO_FACE"}

    elapsed = time.perf_counter() - started

    if result.get("result") == "MATCH":
        raise VerificationFailure(
            "The face service matched a synthetic image that has no face"
        )

    logger.info(
        "Face path ran in %.0f ms and correctly found no match (%s)",
        elapsed * 1000,
        result.get("result"),
    )

    return result


def check_api_rejects_a_face_less_image(services) -> dict:
    """Run the API path end to end and confirm the rejection.

    The liveness session is created directly, because creating one
    through the API needs an authenticated student account. The rest of
    the request path is the real one.
    """

    from app.api.liveness_routes import sessions

    from app.auth.service import create_user, issue_token
    from app.core.config import Settings
    from app.main import create_app

    working_dir = Path(tempfile.mkdtemp())
    database_path = working_dir / "verify.db"

    application = create_app(
        settings=Settings(
            _env_file=None,
            database_path=database_path,
        ),
        service_factory=lambda settings: services,
    )

    from fastapi.testclient import TestClient

    session_id = "123e4567-e89b-42d3-a456-426614174000"

    student = None

    try:
        with TestClient(application) as client:

            # The account and the token go through the real auth path.
            student = create_user(
                "verify-student",
                "verification-password-123",
                "student",
                student_id="STU001",
                database_path=database_path,
            )

            token, _ = issue_token(
                student.id,
                database_path=database_path,
            )

            sessions[session_id] = {
                "user_id": student.id,
                "closed_frames": 0,
                "eyes_closed": False,
                "liveness_verified": True,
                "verified_at": time.time(),
                "created_at": time.time(),
                "consumed_at": None,
            }

            image_path = working_dir / "synthetic.jpg"
            cv2.imwrite(str(image_path), synthetic_frame())

            response = client.post(
                "/attendance/verify",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "student_id": "STU001",
                    "session_id": session_id,
                    "subject": "Verification",
                    "lecture_id": "VERIFY-001",
                },
                files={
                    "image": (
                        "synthetic.jpg",
                        image_path.read_bytes(),
                        "image/jpeg",
                    )
                },
            )

    finally:
        sessions.pop(session_id, None)

    if response.status_code != 200:
        raise VerificationFailure(
            f"The attendance endpoint returned {response.status_code}"
        )

    payload = response.json()

    if payload.get("status") != "rejected":
        raise VerificationFailure(
            "The attendance endpoint did not reject an image with no face: "
            f"{payload}"
        )

    import sqlite3

    connection = sqlite3.connect(str(database_path))
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM attendance"
        ).fetchone()[0]
    finally:
        connection.close()

    if count != 0:
        raise VerificationFailure(
            "The attendance endpoint stored a record for an image with no face"
        )

    logger.info(
        "The API path rejected the image and stored no attendance record"
    )

    return payload


def run() -> dict:
    """Run every check and return a summary."""

    settings = get_settings()

    configure_logging(settings)

    logger.info("Verifying the pipeline against the real models")
    logger.info("  MediaPipe model: %s", settings.mediapipe_face_landmarker_model)
    logger.info("  InsightFace model: %s", settings.insightface_model_name)

    working_dir = Path(tempfile.mkdtemp())

    started = time.perf_counter()

    services = build_services(settings)

    try:

        checks = {}

        checks["models"] = check_models_load(services)

        frame = synthetic_frame()

        checks["liveness"] = check_liveness_runs(services, frame)

        checks["face"] = check_face_service_runs(
            services,
            frame,
            working_dir,
        )

        checks["api"] = check_api_rejects_a_face_less_image(services)

    finally:

        services.close()

    elapsed = time.perf_counter() - started

    logger.info("All checks passed in %.1f s", elapsed)

    return {
        "checks": sorted(checks),
        "elapsed_seconds": elapsed,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the attendance pipeline against the real models",
    )

    parser.parse_args(argv)

    try:
        run()

    except VerificationFailure as error:
        logger.error("The pipeline verification failed: %s", error)
        return 1

    except Exception as error:
        logger.error(
            "The pipeline verification could not run: %s: %s",
            type(error).__name__,
            error,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
