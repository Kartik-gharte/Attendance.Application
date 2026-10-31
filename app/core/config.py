from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MEDIAPIPE_MODEL = (
    PROJECT_ROOT / "models" / "mediapipe" / "face_landmarker.task"
)

DEFAULT_EMBEDDING_DIR = PROJECT_ROOT / "data" / "face_embeddings"

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "attendance.db"

DEFAULT_CORS_ALLOWED_ORIGINS = ",".join(
    [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
)


def _resolve_path(value):
    path = Path(str(value)).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


class Settings(BaseSettings):
    """
    Validated application settings loaded from environment variables
    and an optional project-root .env file.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    mediapipe_face_landmarker_model: Path = Field(
        default=DEFAULT_MEDIAPIPE_MODEL,
        validation_alias="MEDIAPIPE_FACE_LANDMARKER_MODEL",
    )

    embedding_dir: Path = Field(
        default=DEFAULT_EMBEDDING_DIR,
        validation_alias="FACE_EMBEDDING_DIR",
    )

    database_path: Path = Field(
        default=DEFAULT_DATABASE_PATH,
        validation_alias="ATTENDANCE_DB_PATH",
    )

    cors_allowed_origins: str = Field(
        default=DEFAULT_CORS_ALLOWED_ORIGINS,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    face_match_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        validation_alias="FACE_MATCH_THRESHOLD",
    )

    liveness_validity_seconds: int = Field(
        default=30,
        gt=0,
        validation_alias="LIVENESS_VALIDITY_SECONDS",
    )

    max_upload_size_bytes: int = Field(
        default=5 * 1024 * 1024,
        ge=1,
        validation_alias="MAX_UPLOAD_SIZE_BYTES",
    )

    max_image_width: int = Field(
        default=4096,
        ge=1,
        le=8192,
        validation_alias="MAX_IMAGE_WIDTH",
    )

    max_image_height: int = Field(
        default=4096,
        ge=1,
        le=8192,
        validation_alias="MAX_IMAGE_HEIGHT",
    )

    max_image_pixels: int = Field(
        default=16 * 1024 * 1024,
        ge=1,
        le=64 * 1024 * 1024,
        validation_alias="MAX_IMAGE_PIXELS",
    )

    insightface_model_name: str = Field(
        default="buffalo_l",
        min_length=1,
        validation_alias="INSIGHTFACE_MODEL_NAME",
    )

    insightface_root: Path = Field(
        default=Path.home() / ".insightface",
        validation_alias="INSIGHTFACE_ROOT",
    )

    @field_validator(
        "mediapipe_face_landmarker_model",
        "embedding_dir",
        "database_path",
        "insightface_root",
        mode="before",
    )
    @classmethod
    def resolve_paths(cls, value):
        return _resolve_path(value)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
