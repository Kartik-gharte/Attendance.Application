"""Verification of the pipeline against the real biometric models.

The rest of the runtime suite deliberately uses fake model services, so
that it runs without the model assets. These tests cover the other half:
they load the real models and drive the actual pipeline.

They are skipped when the model assets are not provisioned, which is the
case in CI. See docs/SETUP.md for the provisioning steps and
docs/TESTING.md for the manual invocation.
"""

import numpy as np
import pytest

from app.core.config import get_settings


def _model_assets_available() -> bool:
    """Return whether both model assets are provisioned."""

    settings = get_settings()

    if not settings.mediapipe_face_landmarker_model.is_file():
        return False

    if not settings.insightface_root.is_dir():
        return False

    buffalo = settings.insightface_root / "models" / settings.insightface_model_name

    return buffalo.is_dir()


pytestmark = pytest.mark.skipif(
    not _model_assets_available(),
    reason=(
        "The biometric model assets are not provisioned. "
        "See docs/SETUP.md."
    ),
)


@pytest.fixture(scope="module")
def services():
    """Load the real biometric services once for the module."""

    from app.core.services import build_services

    built = build_services(get_settings())

    try:
        yield built

    finally:
        built.close()


def test_the_real_models_load(services):
    detector = getattr(services.liveness_service, "detector", None)
    analyzer = getattr(services.face_service, "app", None)

    assert detector is not None
    assert analyzer is not None


def test_the_real_liveness_path_runs_on_a_frame(services):
    from manual.verify_model_pipeline import synthetic_frame

    result = services.liveness_service.process_frame(
        synthetic_frame(),
        0,
        False,
    )

    assert "liveness_verified" in result
    assert result["liveness_verified"] is False
    assert result["face_detected"] is False


def test_the_real_face_service_refuses_an_image_with_no_face(services, tmp_path):
    import cv2

    from manual.verify_model_pipeline import synthetic_frame

    image_path = tmp_path / "synthetic.jpg"

    cv2.imwrite(str(image_path), synthetic_frame())

    with pytest.raises(ValueError) as error:
        services.face_service.recognize(str(image_path), "STU001")

    assert "face" in str(error.value).lower()


def test_the_real_pipeline_rejects_a_face_less_image(services):
    """The whole request path, with the real models, rejects the image."""

    from manual.verify_model_pipeline import (
        check_api_rejects_a_face_less_image,
    )

    payload = check_api_rejects_a_face_less_image(services)

    assert payload["status"] == "rejected"
    assert payload["face"] == "NO_FACE"
    assert payload["attendance_status"] == "ABSENT"


def test_the_pipeline_verification_script_passes():
    from manual.verify_model_pipeline import run

    summary = run()

    assert "models" in summary["checks"]
    assert "liveness" in summary["checks"]
    assert "face" in summary["checks"]
    assert "api" in summary["checks"]
