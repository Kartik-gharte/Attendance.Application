"""Deterministic tests for AntiSpoofingService.check_frame.

These tests use synthetic BGR images and normalized landmark objects;
no MediaPipe or actual camera is required.
"""

import cv2
import numpy as np
import pytest

from app.services.anti_spoofing import AntiSpoofingService


class SimpleLandmark:
    """A minimal landmark with .x and .y (normalized 0‑1)."""
    def __init__(self, x, y):
        self.x = x
        self.y = y


def make_good_frame():
    """A 200×200 BGR image with brightness ≈127 and high detail."""
    # Random-ish pixel values give variance >10 and brightness ≈127.
    img = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
    return img


def make_small_face_frame():
    """A frame where the detected face region is < MIN_FACE_SIZE (80)."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # simulate a tiny face at the centre, 40×40 px
    img[80:120, 80:120] = (100, 100, 100)
    return img


def make_dark_frame():
    """A completely dark frame."""
    return np.zeros((200, 200, 3), dtype=np.uint8)


def make_bright_frame():
    """A completely bright (overexposed) frame."""
    return np.full((200, 200, 3), 255, dtype=np.uint8)


def make_blur_frame():
    """A frame with very low Laplacian variance (blurred)."""
    # Constant image gives variance 0
    return np.full((200, 200, 3), 127, dtype=np.uint8)


def make_landmarks_normalized(x_min, x_max, y_min, y_max):
    """Return a single landmark with normalized coordinates covering the box."""
    # Use the centre of the box as the landmark position.
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    return SimpleLandmark(cx, cy)


def test_check_frame_passed():
    """A good frame with a normal‑sized face should pass."""
    img = make_good_frame()
    lm = make_landmarks_normalized(0, 1, 0, 1)
    result = AntiSpoofingService.check_frame(img, [lm])
    assert result["passed"] is True
    assert result["score"] == 1.0


def test_check_frame_small_face():
    """A very small face should be rejected."""
    img = make_small_face_frame()
    lm = make_landmarks_normalized(0, 1, 0, 1)
    result = AntiSpoofingService.check_frame(img, [lm])
    assert result["passed"] is False
    assert "Face is too small" in result["reason"]


def test_check_frame_dark():
    """A dark frame should be rejected."""
    img = make_dark_frame()
    lm = make_landmarks_normalized(0, 1, 0, 1)
    result = AntiSpoofingService.check_frame(img, [lm])
    assert result["passed"] is False
    assert "Face is too dark" in result["reason"]


def test_check_frame_bright():
    """An overexposed frame should be rejected."""
    img = make_bright_frame()
    lm = make_landmarks_normalized(0, 1, 0, 1)
    result = AntiSpoofingService.check_frame(img, [lm])
    assert result["passed"] is False
    assert "Face is overexposed" in result["reason"]


def test_check_frame_blurry():
    """A constant‑color frame (very low Laplacian variance) should be rejected."""
    img = make_blur_frame()
    lm = make_landmarks_normalized(0, 1, 0, 1)
    result = AntiSpoofingService.check_frame(img, [lm])
    assert result["passed"] is False
    assert "Image quality is too low" in result["reason"]