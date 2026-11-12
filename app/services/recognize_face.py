import argparse
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.validation import validate_student_id


logger = get_logger("services.recognize_face")

DEFAULT_THRESHOLD = 0.4


class RecognitionError(RuntimeError):
    """Raised when a recognition request cannot be completed."""


def resolve_embedding_path(
    student_id: str,
    embedding_dir: str | Path | None = None,
) -> Path:
    """Return the embedding path for a student inside the embedding directory.

    The student identifier is validated and the resolved path must remain
    inside the embedding directory, so a crafted identifier cannot read a
    file outside the configured location.
    """

    try:
        validated_student_id = validate_student_id(student_id)

    except ValueError:
        raise RecognitionError("Invalid student identifier") from None

    if embedding_dir is None:
        embedding_dir = get_settings().embedding_dir

    root = Path(embedding_dir).resolve()
    candidate = (root / f"{validated_student_id}.npy").resolve()

    try:
        candidate.relative_to(root)

    except ValueError:
        raise RecognitionError(
            "Embedding path escapes the configured embedding directory"
        ) from None

    return candidate


def load_face_analyzer(
    model_name: str | None = None,
) -> FaceAnalysis:
    """Create and prepare the InsightFace analyzer."""

    if model_name is None:
        model_name = get_settings().insightface_model_name

    app = FaceAnalysis(
        name=model_name,
        providers=["CPUExecutionProvider"],
    )

    app.prepare(ctx_id=0, det_size=(640, 640))

    return app


def detect_single_face(app: FaceAnalysis, image) -> np.ndarray:
    """Return the embedding of the single face found in ``image``.

    Raises :class:`RecognitionError` when the image contains no face or
    more than one face, because neither case can be matched reliably.
    """

    faces = app.get(image)

    if len(faces) == 0:
        raise RecognitionError("No face detected in the source image")

    if len(faces) > 1:
        raise RecognitionError(
            "More than one face detected in the source image"
        )

    return faces[0].embedding


def cosine_similarity(
    registered_embedding: np.ndarray,
    new_embedding: np.ndarray,
) -> float:
    """Return the cosine similarity between two embedding vectors."""

    registered_norm = np.linalg.norm(registered_embedding)
    new_norm = np.linalg.norm(new_embedding)

    if registered_norm == 0 or new_norm == 0:
        raise RecognitionError("Embedding vector has zero magnitude")

    return float(
        np.dot(registered_embedding, new_embedding)
        / (registered_norm * new_norm)
    )


def recognize_face(
    student_id: str,
    image_path: str,
    embedding_dir: str | Path | None = None,
    threshold: float | None = None,
    analyzer: FaceAnalysis | None = None,
) -> dict:
    """Recognize a face against a registered student embedding.

    Args:
        student_id: Student identifier. Validated before use.
        image_path: Path to the image that should be recognized.
        embedding_dir: Directory holding the ``.npy`` embeddings. Defaults
            to the configured embedding directory.
        threshold: Similarity threshold. Defaults to the configured
            face match threshold.
        analyzer: Pre-built InsightFace analyzer. When omitted the analyzer
            is created, which loads the model.

    Returns:
        Dict with ``student_id``, ``similarity``, ``threshold`` and
        ``is_match``.

    Raises:
        RecognitionError: When the image, the embedding, or the detected
            faces prevent a comparison.
    """

    try:
        validated_student_id = validate_student_id(student_id)

    except ValueError:
        raise RecognitionError("Invalid student identifier") from None

    if threshold is None:
        threshold = get_settings().face_match_threshold

    embedding_path = resolve_embedding_path(
        validated_student_id,
        embedding_dir,
    )

    if not embedding_path.is_file():
        raise RecognitionError(
            "No registered embedding found for the requested student"
        )

    registered_embedding = np.load(str(embedding_path))

    image = cv2.imread(str(image_path))

    if image is None:
        raise RecognitionError("Source image could not be opened")

    if analyzer is None:
        analyzer = load_face_analyzer()

    new_embedding = detect_single_face(analyzer, image)

    similarity = cosine_similarity(
        registered_embedding,
        new_embedding,
    )

    is_match = similarity >= threshold

    logger.info(
        "Face recognition result: student_id=%s similarity=%s threshold=%s match=%s",
        validated_student_id,
        round(similarity, 4),
        threshold,
        is_match,
    )

    return {
        "student_id": validated_student_id,
        "similarity": similarity,
        "threshold": threshold,
        "is_match": is_match,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recognize a face against a registered student embedding",
    )

    parser.add_argument(
        "--student-id",
        required=True,
        help="Student identifier of the registered embedding",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the image that should be recognized",
    )
    parser.add_argument(
        "--embedding-dir",
        default=None,
        help="Directory holding the .npy embeddings "
        "(defaults to the configured embedding directory)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Similarity threshold "
        "(defaults to the configured face match threshold)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        recognize_face(
            student_id=args.student_id,
            image_path=args.image,
            embedding_dir=args.embedding_dir,
            threshold=args.threshold,
        )

    except RecognitionError as error:
        logger.error("Recognition failed: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
