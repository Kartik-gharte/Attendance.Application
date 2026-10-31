"""Deterministic tests for FaceRecognitionService core logic.

These tests do not load the InsightFace model; they exercise the
``compare_faces`` and ``create_recognition_result`` methods using
pure numpy arrays.
"""

import numpy as np
import pytest

from app.services.face_recognition import FaceRecognitionService


def test_compare_faces_identical():
    """Two identical embeddings should give similarity = 1.0."""
    emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = FaceRecognitionService.compare_faces(emb, emb)
    assert abs(sim - 1.0) < 1e-6


def test_compare_faces_orthogonal():
    """Two orthogonal embeddings should give similarity = 0.0."""
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    sim = FaceRecognitionService.compare_faces(emb1, emb2)
    assert abs(sim - 0.0) < 1e-6


def test_compare_faces_opposite():
    """Two opposite embeddings should give similarity = -1.0."""
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    sim = FaceRecognitionService.compare_faces(emb1, emb2)
    assert abs(sim - (-1.0)) < 1e-6


def test_compare_faces_zero_magnitude_raises():
    """A zero‑magnitude embedding should raise ValueError."""
    emb_zero = np.zeros(3, dtype=np.float32)
    emb_other = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    with pytest.raises(ValueError, match="Registered embedding has zero magnitude"):
        FaceRecognitionService.compare_faces(emb_zero, emb_other)
    with pytest.raises(ValueError, match="New embedding has zero magnitude"):
        FaceRecognitionService.compare_faces(emb_other, emb_zero)


def test_create_recognition_result_above_threshold():
    """similarity >= threshold should return 'MATCH'."""
    sim = 0.85
    threshold = 0.40
    result = FaceRecognitionService.create_recognition_result("STU001", sim, threshold)
    assert result["result"] == "MATCH"


def test_create_recognition_result_below_threshold():
    """similarity < threshold should return 'UNKNOWN'."""
    sim = 0.20
    threshold = 0.40
    result = FaceRecognitionService.create_recognition_result("STU001", sim, threshold)
    assert result["result"] == "UNKNOWN"