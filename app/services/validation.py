import re
from pathlib import Path

import cv2
import numpy as np


STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
LECTURE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SESSION_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

INVALID_STUDENT_ID = "Invalid student identifier"
INVALID_SUBJECT = "Invalid subject"
INVALID_LECTURE_ID = "Invalid lecture identifier"
INVALID_LIVENESS_SESSION = "Invalid liveness session"
INVALID_IMAGE = "Invalid or unsupported image"
IMAGE_TOO_LARGE = "Image exceeds maximum allowed size"
IMAGE_TOO_LARGE_DIMENSIONS = "Image dimensions exceed maximum allowed size"
DATABASE_ERROR = "Attendance database error"
INTERNAL_ERROR = "Internal attendance verification error"


def validate_student_id(
    student_id: str,
    embedding_dir: Path | None = None,
) -> str:
    if (
        not isinstance(student_id, str)
        or not STUDENT_ID_PATTERN.fullmatch(student_id)
    ):
        raise ValueError(INVALID_STUDENT_ID)

    if embedding_dir is not None:

        root = Path(embedding_dir).resolve()
        candidate = (root / f"{student_id}.npy").resolve()

        try:
            candidate.relative_to(root)
        except ValueError:
            raise ValueError(INVALID_STUDENT_ID) from None

    return student_id


def validate_lecture_id(
    lecture_id: str,
    max_length: int = 64,
) -> str:
    if (
        not isinstance(lecture_id, str)
        or not LECTURE_ID_PATTERN.fullmatch(lecture_id)
        or len(lecture_id) > max_length
    ):
        raise ValueError(INVALID_LECTURE_ID)

    return lecture_id


def validate_subject(
    subject: str,
    max_length: int = 120,
) -> str:
    if (
        not isinstance(subject, str)
        or not subject
        or len(subject) > max_length
        or any(ord(char) < 32 or ord(char) == 127 for char in subject)
    ):
        raise ValueError(INVALID_SUBJECT)

    return subject


def validate_session_id(session_id: str) -> str:
    if (
        not isinstance(session_id, str)
        or not SESSION_ID_PATTERN.fullmatch(session_id)
    ):
        raise ValueError(INVALID_LIVENESS_SESSION)

    return session_id


def validate_image_content_type(content_type: str | None) -> bool:
    return (
        isinstance(content_type, str)
        and content_type.startswith("image/")
    )


def validate_image_bytes(
    image_bytes: bytes,
    max_upload_size_bytes: int,
    max_width: int,
    max_height: int,
    max_pixels: int,
) -> None:
    if len(image_bytes) > max_upload_size_bytes:
        raise ValueError(IMAGE_TOO_LARGE)

    if not image_bytes:
        raise ValueError(INVALID_IMAGE)

    frame = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if frame is None:
        raise ValueError(INVALID_IMAGE)

    height, width = frame.shape[:2]

    if (
        width > max_width
        or height > max_height
        or width * height > max_pixels
    ):
        raise ValueError(IMAGE_TOO_LARGE_DIMENSIONS)
