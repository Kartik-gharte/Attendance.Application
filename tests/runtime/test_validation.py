from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.validation import (
    IMAGE_TOO_LARGE,
    INVALID_IMAGE,
    INVALID_LECTURE_ID,
    INVALID_LIVENESS_SESSION,
    INVALID_STUDENT_ID,
    INVALID_SUBJECT,
    validate_image_bytes,
    validate_lecture_id,
    validate_session_id,
    validate_student_id,
    validate_subject,
)


def test_validate_student_id_accepts_safe_identifier():

    assert validate_student_id(
        "STU001",
        embedding_dir=Path("/tmp/embeddings"),
    ) == "STU001"


def test_validate_student_id_rejects_path_traversal_and_unsafe_characters():

    for student_id in (
        "../evil",
        "/tmp/evil",
        "STU/001",
        "STU.001",
        "STU*001",
        "..%2F..%2Fevil",
        "x" * 65,
    ):
        with pytest.raises(ValueError, match=INVALID_STUDENT_ID):
            validate_student_id(
                student_id,
                embedding_dir=Path("/tmp/embeddings"),
            )


def test_validate_session_id_rejects_non_uuid_values():

    for session_id in (
        "",
        "not-a-uuid",
        "123e4567-e89b-42d3-a456-42661417400",
        "123e4567-e89b-42d3-a456-4266141740000",
    ):
        with pytest.raises(
            ValueError,
            match=INVALID_LIVENESS_SESSION,
        ):
            validate_session_id(session_id)


def test_validate_lecture_id_rejects_unsafe_identifier():

    with pytest.raises(
        ValueError,
        match=INVALID_LECTURE_ID,
    ):
        validate_lecture_id("../evil")


def test_validate_subject_rejects_empty_and_overlong_values():

    with pytest.raises(ValueError, match=INVALID_SUBJECT):
        validate_subject("")

    with pytest.raises(ValueError, match=INVALID_SUBJECT):
        validate_subject("x" * 121)


def test_validate_image_bytes_rejects_invalid_image():

    with pytest.raises(ValueError, match=INVALID_IMAGE):
        validate_image_bytes(
            b"not-an-image",
            1024,
            4096,
            4096,
            16 * 1024 * 1024,
        )


def test_validate_image_bytes_rejects_oversized_image():

    with pytest.raises(ValueError, match=IMAGE_TOO_LARGE):
        validate_image_bytes(
            b"x" * 1025,
            1024,
            4096,
            4096,
            16 * 1024 * 1024,
        )


def test_validate_image_bytes_rejects_excessive_dimensions():

    frame = np.zeros(
        (64, 64, 3),
        dtype=np.uint8,
    )
    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
    )

    assert ok

    with pytest.raises(ValueError, match="Image dimensions exceed maximum allowed size"):
        validate_image_bytes(
            buffer.tobytes(),
            1024 * 1024,
            8,
            8,
            64,
        )
