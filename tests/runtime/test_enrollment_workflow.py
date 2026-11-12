"""Tests for the parameterized enrollment and recognition workflows.

The tests use synthetic data and a stub analyzer so that no model asset or
camera is required. They cover identifier validation, path containment,
overwrite refusal, atomic writes, and the argument parsing of the manual
client.
"""

import argparse
import importlib
import sys

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def clear_modules():
    """Remove the service modules so each test gets a fresh import."""

    for name in (
        "app.services.register_face",
        "app.services.recognize_face",
    ):
        sys.modules.pop(name, None)

    yield

    for name in (
        "app.services.register_face",
        "app.services.recognize_face",
    ):
        sys.modules.pop(name, None)


class StubFace:
    def __init__(self, embedding):
        self.embedding = np.asarray(embedding, dtype=np.float32)


class StubAnalyzer:
    """Stand-in for the InsightFace analyzer."""

    def __init__(self, faces):
        self._faces = faces
        self.calls = 0

    def get(self, image):
        self.calls += 1
        return self._faces


class StubRegistrationAnalyzer(StubAnalyzer):
    """Stub analyzer used by the enrollment workflow."""


# =========================================================
# RECOGNITION: PATH RESOLUTION AND VALIDATION
# =========================================================


def test_resolve_embedding_path_stays_inside_embedding_dir(tmp_path):
    from app.services.recognize_face import resolve_embedding_path

    path = resolve_embedding_path("STU001", tmp_path)

    assert path == (tmp_path / "STU001.npy").resolve()


def test_resolve_embedding_path_rejects_invalid_identifier(tmp_path):
    from app.services.recognize_face import RecognitionError, resolve_embedding_path

    with pytest.raises(RecognitionError):
        resolve_embedding_path("../../evil", tmp_path)


def test_register_face_resolve_rejects_output_outside_embedding_dir(tmp_path):
    """The output directory may narrow the embedding directory, not escape it."""

    from app.services.register_face import (
        EnrollmentError,
        resolve_embedding_path,
    )

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(EnrollmentError):
        resolve_embedding_path(
            "STU001",
            output_dir=str(outside),
            embedding_dir=str(embedding_dir),
        )


def test_register_face_resolve_allows_narrowed_output_dir(tmp_path):
    """A subdirectory of the embedding directory is accepted."""

    from app.services.register_face import resolve_embedding_path

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    narrowed = embedding_dir / "current"
    narrowed.mkdir()

    path = resolve_embedding_path(
        "STU001",
        output_dir=str(narrowed),
        embedding_dir=str(embedding_dir),
    )

    assert path == (narrowed / "STU001.npy").resolve()


def test_recognize_face_rejects_invalid_identifier(tmp_path):
    from app.services.recognize_face import RecognitionError, recognize_face

    with pytest.raises(RecognitionError):
        recognize_face(
            student_id="../../evil",
            image_path=str(tmp_path / "face.jpg"),
            embedding_dir=tmp_path,
            analyzer=StubAnalyzer([]),
        )


def test_recognize_face_requires_registered_embedding(tmp_path):
    from app.services.recognize_face import RecognitionError, recognize_face

    with pytest.raises(RecognitionError):
        recognize_face(
            student_id="STU001",
            image_path=str(tmp_path / "face.jpg"),
            embedding_dir=tmp_path,
            analyzer=StubAnalyzer([]),
        )


def test_recognize_face_requires_readable_image(tmp_path):
    from app.services.recognize_face import RecognitionError, recognize_face

    np.save(tmp_path / "STU001.npy", np.zeros(4, dtype=np.float32))

    with pytest.raises(RecognitionError):
        recognize_face(
            student_id="STU001",
            image_path=str(tmp_path / "missing.jpg"),
            embedding_dir=tmp_path,
            analyzer=StubAnalyzer([]),
        )


def test_recognize_face_rejects_multiple_faces(tmp_path, monkeypatch):
    import cv2

    from app.services import recognize_face as module

    np.save(tmp_path / "STU001.npy", np.zeros(4, dtype=np.float32))

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubAnalyzer([StubFace([1.0, 0.0]), StubFace([0.0, 1.0])])

    with pytest.raises(module.RecognitionError):
        module.recognize_face(
            student_id="STU001",
            image_path=str(image_path),
            embedding_dir=tmp_path,
            analyzer=analyzer,
        )


def test_recognize_face_returns_match_result(tmp_path, monkeypatch):
    import cv2

    from app.services import recognize_face as module

    np.save(tmp_path / "STU001.npy", np.array([1.0, 0.0], dtype=np.float32))

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubAnalyzer([StubFace([1.0, 0.0])])

    result = module.recognize_face(
        student_id="STU001",
        image_path=str(image_path),
        embedding_dir=tmp_path,
        threshold=0.4,
        analyzer=analyzer,
    )

    assert result["student_id"] == "STU001"
    assert result["is_match"] is True
    assert result["similarity"] == pytest.approx(1.0, abs=1e-5)
    assert result["threshold"] == 0.4
    assert analyzer.calls == 1


def test_recognize_face_reports_mismatch(tmp_path, monkeypatch):
    import cv2

    from app.services import recognize_face as module

    np.save(tmp_path / "STU001.npy", np.array([1.0, 0.0], dtype=np.float32))

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubAnalyzer([StubFace([0.0, 1.0])])

    result = module.recognize_face(
        student_id="STU001",
        image_path=str(image_path),
        embedding_dir=tmp_path,
        threshold=0.4,
        analyzer=analyzer,
    )

    assert result["is_match"] is False
    assert result["similarity"] == pytest.approx(0.0, abs=1e-5)


def test_cosine_similarity_rejects_zero_vector():
    from app.services.recognize_face import RecognitionError, cosine_similarity

    with pytest.raises(RecognitionError):
        cosine_similarity(
            np.zeros(4, dtype=np.float32),
            np.ones(4, dtype=np.float32),
        )


# =========================================================
# ENROLLMENT: VALIDATION AND OVERWRITE PROTECTION
# =========================================================


def test_register_face_rejects_invalid_identifier(tmp_path):
    from app.services.register_face import register_face

    assert (
        register_face(
            student_id="../../evil",
            image_path=str(tmp_path / "face.jpg"),
            output_dir=str(tmp_path),
        )
        is None
    )


def test_register_face_requires_readable_image(tmp_path):
    from app.services.register_face import register_face

    assert (
        register_face(
            student_id="STU001",
            image_path=str(tmp_path / "missing.jpg"),
            output_dir=str(tmp_path),
        )
        is None
    )


def test_register_face_refuses_to_overwrite_existing_embedding(tmp_path):
    from app.services.register_face import register_face

    existing = tmp_path / "STU001.npy"
    np.save(str(existing), np.zeros(4, dtype=np.float32))

    assert (
        register_face(
            student_id="STU001",
            image_path=str(tmp_path / "face.jpg"),
            output_dir=str(tmp_path),
        )
        is None
    )

    # The existing embedding must be untouched.
    assert np.load(str(existing)).shape == (4,)


def test_register_face_writes_embedding_atomically(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubRegistrationAnalyzer([StubFace([0.5, 0.25, 0.125])])

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: analyzer,
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
    )

    assert result is not None

    saved = embedding_dir / "STU001.npy"
    assert saved.is_file()
    assert np.load(str(saved)).shape == (3,)

    # No temporary files may be left behind.
    leftovers = [
        entry.name
        for entry in embedding_dir.iterdir()
        if entry.name != "STU001.npy"
    ]
    assert leftovers == []


def test_register_face_dry_run_does_not_write(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubRegistrationAnalyzer([StubFace([0.5, 0.25, 0.125])])

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: analyzer,
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    result = module.register_face(
        student_id="STU001",
        image_path=str(image_path),
        output_dir=str(embedding_dir),
        dry_run=True,
    )

    assert result is None
    assert list(embedding_dir.iterdir()) == []


def test_register_face_output_must_stay_inside_embedding_dir(tmp_path, monkeypatch):
    import cv2

    from app.services import register_face as module

    embedding_dir = tmp_path / "embeddings"
    embedding_dir.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    image_path = tmp_path / "face.jpg"
    cv2.imwrite(str(image_path), np.zeros((8, 8, 3), dtype=np.uint8))

    monkeypatch.setattr(
        module.cv2,
        "imread",
        lambda path: np.zeros((8, 8, 3), dtype=np.uint8),
    )

    analyzer = StubRegistrationAnalyzer([StubFace([0.5, 0.25, 0.125])])

    monkeypatch.setattr(
        module,
        "load_face_analyzer",
        lambda *args, **kwargs: analyzer,
    )

    monkeypatch.setattr(
        module,
        "DEFAULT_EMBEDDING_DIR",
        embedding_dir,
    )

    assert (
        module.register_face(
            student_id="STU001",
            image_path=str(image_path),
            output_dir=str(outside),
        )
        is None
    )

    assert list(outside.iterdir()) == []


# =========================================================
# CLI SURFACES
# =========================================================


def test_register_face_cli_exposes_required_arguments():
    from app.services.register_face import build_parser

    parser = build_parser()

    args = parser.parse_args(
        ["--student-id", "STU001", "--image", "face.jpg"]
    )

    assert args.student_id == "STU001"
    assert args.image == "face.jpg"
    assert args.overwrite is False
    assert args.dry_run is False


def test_recognize_face_cli_exposes_required_arguments():
    from app.services.recognize_face import build_parser

    parser = build_parser()

    args = parser.parse_args(
        ["--student-id", "STU001", "--image", "face.jpg"]
    )

    assert args.student_id == "STU001"
    assert args.image == "face.jpg"
    assert args.embedding_dir is None
    assert args.threshold is None


def test_manual_client_reads_values_from_environment(monkeypatch):
    monkeypatch.setenv("ATTENDANCE_API_URL", "http://example.test:9000")
    monkeypatch.setenv("ATTENDANCE_USERNAME", "env-user")
    monkeypatch.setenv("ATTENDANCE_STUDENT_ID", "ENV001")
    monkeypatch.setenv("ATTENDANCE_SUBJECT", "Env Subject")
    monkeypatch.setenv("ATTENDANCE_LECTURE_ID", "ENV-LECTURE")

    module = importlib.import_module("manual.api_attendance")

    args = module.build_parser().parse_args([])

    assert args.base_url == "http://example.test:9000"
    assert args.username == "env-user"
    assert args.student_id == "ENV001"
    assert args.subject == "Env Subject"
    assert args.lecture_id == "ENV-LECTURE"


def test_manual_client_arguments_override_environment(monkeypatch):
    monkeypatch.setenv("ATTENDANCE_API_URL", "http://example.test:9000")
    monkeypatch.setenv("ATTENDANCE_USERNAME", "env-user")

    module = importlib.import_module("manual.api_attendance")

    args = module.build_parser().parse_args(
        [
            "--base-url",
            "http://other.test:8000",
            "--username",
            "arg-user",
        ]
    )

    assert args.base_url == "http://other.test:8000"
    assert args.username == "arg-user"


def test_manual_client_requires_missing_values(monkeypatch):
    for name in (
        "ATTENDANCE_USERNAME",
        "ATTENDANCE_STUDENT_ID",
        "ATTENDANCE_LECTURE_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    module = importlib.import_module("manual.api_attendance")

    assert module.main([]) == 2
