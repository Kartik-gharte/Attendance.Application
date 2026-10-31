import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT, Settings


def test_defaults_use_project_root_paths():

    settings = Settings(_env_file=None)

    assert (
        settings.mediapipe_face_landmarker_model
        == PROJECT_ROOT
        / "models"
        / "mediapipe"
        / "face_landmarker.task"
    )

    assert (
        settings.embedding_dir
        == PROJECT_ROOT / "data" / "face_embeddings"
    )

    assert (
        settings.database_path
        == PROJECT_ROOT / "data" / "attendance.db"
    )
    assert settings.auth_token_ttl_seconds == 3600


def test_environment_overrides_relative_paths(monkeypatch, tmp_path):

    absolute_embeddings = tmp_path / "embeddings"

    monkeypatch.setenv(
        "MEDIAPIPE_FACE_LANDMARKER_MODEL",
        "custom/face_landmarker.task",
    )
    monkeypatch.setenv("FACE_EMBEDDING_DIR", str(absolute_embeddings))
    monkeypatch.setenv("ATTENDANCE_DB_PATH", "custom/attendance.db")
    monkeypatch.setenv("FACE_MATCH_THRESHOLD", "0.55")
    monkeypatch.setenv("LIVENESS_VALIDITY_SECONDS", "15")
    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "90")
    monkeypatch.setenv("INSIGHTFACE_MODEL_NAME", "test-model")
    monkeypatch.setenv("INSIGHTFACE_ROOT", "custom/insightface")

    settings = Settings(_env_file=None)

    assert (
        settings.mediapipe_face_landmarker_model
        == (PROJECT_ROOT / "custom" / "face_landmarker.task").resolve()
    )
    assert settings.embedding_dir == absolute_embeddings.resolve()
    assert (
        settings.database_path
        == (PROJECT_ROOT / "custom" / "attendance.db").resolve()
    )
    assert settings.face_match_threshold == 0.55
    assert settings.liveness_validity_seconds == 15
    assert settings.auth_token_ttl_seconds == 90
    assert settings.insightface_model_name == "test-model"
    assert (
        settings.insightface_root
        == (PROJECT_ROOT / "custom" / "insightface").resolve()
    )


def test_cors_origins_are_parsed_from_comma_separated_value(monkeypatch):

    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000, http://127.0.0.1:8000 ,",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ]


def test_invalid_threshold_is_rejected(monkeypatch):

    monkeypatch.setenv("FACE_MATCH_THRESHOLD", "1.5")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_auth_token_ttl_is_rejected(monkeypatch):

    monkeypatch.setenv("AUTH_TOKEN_TTL_SECONDS", "10")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_missing_model_fails_with_actionable_setting_name(tmp_path):

    from app.services.liveness import LivenessService

    missing_model = tmp_path / "missing.task"

    with pytest.raises(
        RuntimeError,
        match="MEDIAPIPE_FACE_LANDMARKER_MODEL",
    ):
        LivenessService(missing_model)
