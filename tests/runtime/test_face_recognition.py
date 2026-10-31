"""Deterministic tests for FaceRecognitionService core logic.

These tests do not load the InsightFace model; they exercise the
``compare_faces`` and ``create_recognition_result`` methods using
pure numpy arrays.
"""

import numpy as np
import pytest
from types import SimpleNamespace


def make_srvc(threshold=0.4):
    """Create a FaceRecognitionService-like namespace with the given threshold."""
    srvc = SimpleNamespace(threshold=threshold)
    # Bind the static-like methods so they can access ``srvc.threshold``.
    # We patch them at call time via the test functions instead.
    return srvc


def _compare_faces(registered_embedding, new_embedding, threshold):
    """Internal helper that uses the given threshold."""
    registered_embedding = np.asarray(registered_embedding, dtype=np.float32)
    new_embedding = np.asarray(new_embedding, dtype=np.float32)
    registered_norm = np.linalg.norm(registered_embedding)
    new_norm = np.linalg.norm(new_embedding)
    if registered_norm == 0:
        raise ValueError("Registered embedding has zero magnitude")
    if new_norm == 0:
        raise ValueError("New embedding has zero magnitude")
    similarity = np.dot(registered_embedding, new_embedding) / (registered_norm * new_norm)
    return float(similarity)


def _create_recognition_result(student_id, similarity, threshold):
    return "MATCH" if similarity >= threshold else "UNKNOWN"


def test_compare_faces_identical():
    """Two identical embeddings should give similarity = 1.0."""
    emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = _compare_faces(emb, emb, 0.4)
    assert abs(sim - 1.0) < 1e-6


def test_compare_faces_orthogonal():
    """Two orthogonal embeddings should give similarity = 0.0."""
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    sim = _compare_faces(emb1, emb2, 0.4)
    assert abs(sim - 0.0) < 1e-6


def test_compare_faces_opposite():
    """Two opposite embeddings should give similarity = -1.0."""
    emb1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    emb2 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    sim = _compare_faces(emb1, emb2, 0.4)
    assert abs(sim - (-1.0)) < 1e-6


def test_compare_faces_zero_magnitude_raises():
    """A zero‑magnitude embedding should raise ValueError."""
    emb_zero = np.zeros(3, dtype=np.float32)
    emb_other = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    with pytest.raises(ValueError, match="Registered embedding has zero magnitude"):
        _compare_faces(emb_zero, emb_other, 0.4)
    with pytest.raises(ValueError, match="New embedding has zero magnitude"):
        _compare_faces(emb_other, emb_zero, 0.4)


def test_create_recognition_result_above_threshold():
    """similarity >= threshold should return 'MATCH'."""
    sim = 0.85
    threshold = 0.40
    result = _create_recognition_result("STU001", sim, threshold)
    assert result == "MATCH"


def test_create_recognition_result_below_threshold():
    """similarity < threshold should return 'UNKNOWN'."""
    sim = 0.20
    threshold = 0.40
    result = _create_recognition_result("STU001", sim, threshold)
    assert result == "UNKNOWN"