"""Enroll a face embedding for a student.

The module exposes a :func:`register_face` function and a command line
entry point. Every value is supplied by the caller; nothing about the
student, the source image, or the destination is hardcoded.

The destination is always the configured embedding directory. A caller may
narrow it with ``output_dir`` but cannot point it outside that directory.
"""

import argparse
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.validation import validate_student_id


logger = get_logger("services.register_face")

DEFAULT_EMBEDDING_DIR = get_settings().embedding_dir


class EnrollmentError(RuntimeError):
    """Raised when an enrollment request cannot be completed."""


def load_face_analyzer(model_name: str | None = None):
    """Create and prepare the InsightFace analyzer."""

    from insightface.app import FaceAnalysis

    if model_name is None:
        model_name = get_settings().insightface_model_name

    app = FaceAnalysis(
        name=model_name,
        providers=["CPUExecutionProvider"],
    )

    app.prepare(ctx_id=0, det_size=(640, 640))

    return app


def detect_single_face(app, image) -> np.ndarray:
    """Return the embedding of the single face found in ``image``.

    Raises :class:`EnrollmentError` when the image contains no face or
    more than one face, because neither case identifies a single student.
    """

    faces = app.get(image)

    if len(faces) == 0:
        raise EnrollmentError("No face detected in the source image")

    if len(faces) > 1:
        raise EnrollmentError(
            "More than one face detected in the source image"
        )

    return faces[0].embedding


def resolve_embedding_path(
    student_id: str,
    output_dir: str | Path | None = None,
    embedding_dir: str | Path | None = None,
) -> Path:
    """Return the destination path for a student embedding.

    The student identifier is validated and the resolved path must remain
    inside the configured embedding directory.
    """

    validated_student_id = validate_student_id(student_id)

    if embedding_dir is None:
        embedding_dir = DEFAULT_EMBEDDING_DIR

    root = Path(embedding_dir).resolve()

    if output_dir is None:
        target_root = root

    else:
        target_root = Path(output_dir).resolve()

    candidate = (target_root / f"{validated_student_id}.npy").resolve()

    try:
        candidate.relative_to(root)

    except ValueError:
        raise EnrollmentError(
            "Output path escapes the configured embedding directory"
        ) from None

    return candidate


def write_embedding_atomically(
    embedding: np.ndarray,
    destination: Path,
) -> None:
    """Write the embedding to a temporary file and move it into place.

    A failed write therefore never leaves a partial or corrupt ``.npy``
    file behind.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary_name = tempfile.mkstemp(
        dir=str(destination.parent),
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )

    os.close(handle)

    temporary_path = Path(temporary_name)

    try:
        with open(temporary_path, "wb") as temporary_file:
            np.save(temporary_file, embedding)

        os.replace(temporary_path, destination)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def register_face(
    student_id: str,
    image_path: str,
    output_dir: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
    analyzer=None,
) -> str | None:
    """Enroll a face embedding for a student.

    Args:
        student_id: Student identifier. Validated before use.
        image_path: Path to the source image that contains one face.
        output_dir: Directory to write the embedding into. Must stay inside
            the configured embedding directory.
        overwrite: Whether an existing embedding may be replaced. An
            existing embedding is never replaced without this flag.
        dry_run: Validate everything without writing a file.
        analyzer: Pre-built InsightFace analyzer. When omitted the analyzer
            is created, which loads the model.

    Returns:
        The path of the written embedding, or ``None`` when the enrollment
        was refused or failed.
    """

    try:
        validated_student_id = validate_student_id(student_id)

    except ValueError:
        logger.error("Invalid student identifier rejected")
        return None

    image = cv2.imread(str(image_path))

    if image is None:
        logger.error("Source image could not be opened")
        return None

    if analyzer is None:
        analyzer = load_face_analyzer()

    try:
        embedding = detect_single_face(analyzer, image)

    except EnrollmentError as error:
        logger.error("Enrollment aborted: %s", error)
        return None

    try:
        destination = resolve_embedding_path(
            validated_student_id,
            output_dir,
        )

    except EnrollmentError as error:
        logger.error("Enrollment aborted: %s", error)
        return None

    if destination.exists() and not overwrite:
        logger.error(
            "Enrollment refused: an embedding already exists for this "
            "student. Use the overwrite flag to replace it."
        )
        return None

    if dry_run:
        logger.info(
            "Dry run: would write an embedding for student_id=%s",
            validated_student_id,
        )
        return None

    try:
        write_embedding_atomically(embedding, destination)

    except OSError as error:
        logger.error("Enrollment failed to write the embedding: %s", error)
        return None

    logger.info(
        "Face registration completed: student_id=%s",
        validated_student_id,
    )

    return str(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enroll a face embedding for a student",
    )

    parser.add_argument(
        "--student-id",
        required=True,
        help="Student identifier the embedding belongs to",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the source image that contains exactly one face",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write the embedding into. Must stay inside the "
        "configured embedding directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing embedding. Without this flag an existing "
        "embedding is never replaced.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the request without writing a file",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    result = register_face(
        student_id=args.student_id,
        image_path=args.image,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    if result is None:
        return 1

    logger.info("Embedding stored for student_id=%s", args.student_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
