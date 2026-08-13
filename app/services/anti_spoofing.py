import cv2
import numpy as np


class AntiSpoofingService:

    """
    Basic presentation-attack screening service.

    IMPORTANT:
    This is NOT a trained face anti-spoofing model.
    It provides basic frame-quality / presentation screening
    to complement the existing blink-based liveness check.
    """

    def __init__(self):

        print("Initializing Anti-Spoofing Service...")

        self.MIN_FACE_SIZE = 80
        self.MIN_BRIGHTNESS = 35
        self.MAX_BRIGHTNESS = 235

        print("Anti-Spoofing Service ready")

    # =========================================================
    # CHECK FRAME
    # =========================================================

    def check_frame(self, frame, face_landmarks):

        if frame is None:

            return {
                "passed": False,
                "score": 0.0,
                "reason": "Invalid camera frame"
            }

        if face_landmarks is None:

            return {
                "passed": False,
                "score": 0.0,
                "reason": "Face landmarks not available"
            }

        height, width = frame.shape[:2]

        # -----------------------------------------------------
        # Convert landmarks to pixel coordinates
        # -----------------------------------------------------

        points = []

        for landmark in face_landmarks:

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            points.append((x, y))

        if len(points) == 0:

            return {
                "passed": False,
                "score": 0.0,
                "reason": "No face landmarks"
            }

        # -----------------------------------------------------
        # Face bounding box
        # -----------------------------------------------------

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]

        x_min = max(min(xs), 0)
        x_max = min(max(xs), width - 1)

        y_min = max(min(ys), 0)
        y_max = min(max(ys), height - 1)

        face_width = x_max - x_min
        face_height = y_max - y_min

        # -----------------------------------------------------
        # Face size check
        # -----------------------------------------------------

        if (
            face_width < self.MIN_FACE_SIZE
            or
            face_height < self.MIN_FACE_SIZE
        ):

            return {
                "passed": False,
                "score": 0.20,
                "reason": "Face is too small"
            }

        # -----------------------------------------------------
        # Crop face
        # -----------------------------------------------------

        face = frame[
            y_min:y_max,
            x_min:x_max
        ]

        if face.size == 0:

            return {
                "passed": False,
                "score": 0.0,
                "reason": "Could not crop face"
            }

        # -----------------------------------------------------
        # Brightness check
        # -----------------------------------------------------

        gray = cv2.cvtColor(
            face,
            cv2.COLOR_BGR2GRAY
        )

        brightness = float(
            np.mean(gray)
        )

        # Too dark
        if brightness < self.MIN_BRIGHTNESS:

            return {
                "passed": False,
                "score": 0.30,
                "reason": "Face is too dark"
            }

        # Too bright
        if brightness > self.MAX_BRIGHTNESS:

            return {
                "passed": False,
                "score": 0.30,
                "reason": "Face is overexposed"
            }

        # -----------------------------------------------------
        # Image detail / texture check
        # -----------------------------------------------------

        laplacian_variance = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F
            ).var()
        )

        # Very low variance generally indicates
        # an extremely blurred frame.
        if laplacian_variance < 10:

            return {
                "passed": False,
                "score": 0.35,
                "reason": "Image quality is too low"
            }

        # -----------------------------------------------------
        # Basic screening score
        # -----------------------------------------------------

        score = 1.0

        # Slight penalty for extremely low detail
        if laplacian_variance < 25:

            score -= 0.10

        # Slight penalty for poor lighting
        if (
            brightness < 50
            or
            brightness > 220
        ):

            score -= 0.10

        score = max(
            0.0,
            min(1.0, score)
        )

        return {
            "passed": True,
            "score": round(score, 3),
            "reason": "Basic presentation screening passed",
            "brightness": round(brightness, 2),
            "sharpness": round(
                laplacian_variance,
                2
            )
        }