import cv2
import mediapipe as mp
import math

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from app.services.anti_spoofing import AntiSpoofingService


class LivenessService:

    MODEL_PATH = (
        r"C:\AI-Attendance-System\ai-service"
        r"\models\mediapipe\face_landmarker.task"
    )

    CLOSED_THRESHOLD = 0.10
    REQUIRED_CLOSED_FRAMES = 4

    def __init__(self):

        print("Loading MediaPipe Face Landmarker...")

        base_options = python.BaseOptions(
            model_asset_path=self.MODEL_PATH
        )

        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=1
        )

        self.detector = (
            vision.FaceLandmarker.create_from_options(
                options
            )
        )

        # -------------------------------------------------
        # ANTI-SPOOFING SERVICE
        # -------------------------------------------------

        self.anti_spoofing = AntiSpoofingService()

        print("MediaPipe Face Landmarker loaded")
        print("Liveness Service ready")

    # =====================================================
    # DISTANCE
    # =====================================================

    @staticmethod
    def distance(p1, p2):

        return math.sqrt(
            (p1.x - p2.x) ** 2 +
            (p1.y - p2.y) ** 2
        )

    # =====================================================
    # EYE ASPECT RATIO
    # =====================================================

    def calculate_ear(self, landmarks):

        # -------------------------------------------------
        # LEFT EYE
        # -------------------------------------------------

        left_p1 = landmarks[33]
        left_p2 = landmarks[160]
        left_p3 = landmarks[158]
        left_p4 = landmarks[133]
        left_p5 = landmarks[153]
        left_p6 = landmarks[144]

        # -------------------------------------------------
        # RIGHT EYE
        # -------------------------------------------------

        right_p1 = landmarks[263]
        right_p2 = landmarks[387]
        right_p3 = landmarks[385]
        right_p4 = landmarks[362]
        right_p5 = landmarks[380]
        right_p6 = landmarks[373]

        left_ear = (
            self.distance(left_p2, left_p6)
            + self.distance(left_p3, left_p5)
        ) / (
            2 * self.distance(
                left_p1,
                left_p4
            )
        )

        right_ear = (
            self.distance(right_p2, right_p6)
            + self.distance(right_p3, right_p5)
        ) / (
            2 * self.distance(
                right_p1,
                right_p4
            )
        )

        return (
            left_ear + right_ear
        ) / 2

    # =====================================================
    # PROCESS ONE FRAME
    # =====================================================

    def process_frame(
        self,
        frame,
        closed_frames=0,
        eyes_closed=False
    ):

        if frame is None:

            return {
                "face_detected": False,
                "ear": None,
                "eyes_closed": eyes_closed,
                "closed_frames": closed_frames,
                "blink_detected": False,
                "liveness_verified": False,
                "anti_spoofing": {
                    "passed": False,
                    "score": 0.0,
                    "reason": "Invalid frame"
                }
            }

        # =================================================
        # CONVERT BGR → RGB
        # =================================================

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        # =================================================
        # MEDIA PIPE DETECTION
        # =================================================

        result = self.detector.detect(
            mp_image
        )

        # =================================================
        # NO FACE
        # =================================================

        if not result.face_landmarks:

            return {
                "face_detected": False,
                "ear": None,
                "eyes_closed": eyes_closed,
                "closed_frames": 0,
                "blink_detected": False,
                "liveness_verified": False,
                "anti_spoofing": {
                    "passed": False,
                    "score": 0.0,
                    "reason": "No face detected"
                }
            }

        # =================================================
        # FACE FOUND
        # =================================================

        landmarks = result.face_landmarks[0]

        # =================================================
        # ANTI-SPOOFING SCREENING
        # =================================================

        anti_spoof_result = (
            self.anti_spoofing.check_frame(
                frame,
                landmarks
            )
        )

        # =================================================
        # CALCULATE EAR
        # =================================================

        ear = self.calculate_ear(
            landmarks
        )

        blink_detected = False
        liveness_verified = False

        # =================================================
        # EYES CLOSED
        # =================================================

        if ear < self.CLOSED_THRESHOLD:

            closed_frames += 1

            if (
                closed_frames
                >= self.REQUIRED_CLOSED_FRAMES
            ):

                eyes_closed = True
                closed_frames = 0

        # =================================================
        # EYES OPEN
        # =================================================

        else:

            if eyes_closed:

                blink_detected = True

                # -----------------------------------------
                # IMPORTANT
                # -----------------------------------------
                # Blink proves active interaction.
                # Anti-spoofing screening must also pass.
                # -----------------------------------------

                if anti_spoof_result.get(
                    "passed",
                    False
                ):

                    liveness_verified = True

                eyes_closed = False
                closed_frames = 0

            else:

                closed_frames = 0

        # =================================================
        # FINAL RESULT
        # =================================================

        return {
            "face_detected": True,

            "ear": float(
                ear
            ),

            "eyes_closed": eyes_closed,

            "closed_frames": closed_frames,

            "blink_detected": blink_detected,

            "liveness_verified": (
                liveness_verified
            ),

            "anti_spoofing": (
                anti_spoof_result
            )
        }