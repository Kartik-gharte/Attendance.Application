from app.core.logging_config import get_logger
from app.services.liveness import LivenessService
from app.services.face_recognition import FaceRecognitionService


logger = get_logger("services.attendance_verification")


class AttendanceVerificationService:

    def __init__(
        self,
        liveness_service=None,
        face_service=None
    ):

        logger.info("Initializing attendance verification service")

        self.liveness_service = (
            liveness_service
            if liveness_service is not None
            else LivenessService()
        )

        self.face_service = (
            face_service
            if face_service is not None
            else FaceRecognitionService()
        )

        logger.info("Attendance verification service ready")

    # =========================================================
    # VERIFY FACE FROM IMAGE
    # =========================================================

    def verify_face(
        self,
        image_path,
        student_id
    ):

        logger.info("Starting face verification")

        try:

            result = self.face_service.recognize(
                image_path,
                student_id
            )

            return result

        except ValueError as error:

            logger.warning("Face verification rejected the input: error=%s", error)

            return {
                "result": "NO_FACE",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "error": str(error)
            }

        except Exception as error:

            logger.error("Face verification failed: error_type=%s error=%s", type(error).__name__, error)

            return {
                "result": "ERROR",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "error": str(error)
            }

    # =========================================================
    # VERIFY FACE FROM CAMERA FRAME
    # =========================================================

    def verify_face_from_frame(
        self,
        frame,
        student_id
    ):

        logger.info("Starting live face verification")

        try:

            result = self.face_service.recognize_frame(
                frame,
                student_id
            )

            return result

        except ValueError as error:

            logger.warning("Face verification rejected the input: error=%s", error)

            return {
                "result": "NO_FACE",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "error": str(error)
            }

        except Exception as error:

            logger.error("Face verification failed: error_type=%s error=%s", type(error).__name__, error)

            return {
                "result": "ERROR",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "error": str(error)
            }

    # =========================================================
    # CREATE FINAL ATTENDANCE RESULT
    # =========================================================

    def create_attendance_result(
        self,
        student_id,
        liveness_verified,
        face_result
    ):

        if face_result is None:
            face_result = {}

        face_matched = (
            face_result.get("result") == "MATCH"
        )

        attendance_verified = (
            liveness_verified
            and face_matched
        )

        face_result_type = face_result.get(
            "result",
            "UNKNOWN"
        )

        # -----------------------------------------------------
        # FACE STATUS
        # -----------------------------------------------------

        if face_result_type == "MATCH":

            face_status = "MATCH"

        elif face_result_type == "NO_FACE":

            face_status = "NO_FACE"

        elif face_result_type == "ERROR":

            face_status = "ERROR"

        else:

            face_status = "UNKNOWN"

        return {
            "student_id": student_id,

            "liveness": (
                "VERIFIED"
                if liveness_verified
                else "FAILED"
            ),

            "face": face_status,

            "similarity": face_result.get(
                "similarity"
            ),

            "threshold": face_result.get(
                "threshold"
            ),

            "attendance": (
                "VERIFIED"
                if attendance_verified
                else "REJECTED"
            ),

            "error": face_result.get(
                "error"
            )
        }

    # =========================================================
    # COMPLETE ATTENDANCE VERIFICATION
    # =========================================================

    def verify_attendance(
        self,
        frame,
        student_id,
        liveness_verified
    ):

        # -----------------------------------------------------
        # LIVENESS CHECK
        # -----------------------------------------------------

        if not liveness_verified:

            return {
                "student_id": student_id,
                "liveness": "FAILED",
                "face": "NOT_CHECKED",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "attendance": "REJECTED",
                "error": "Liveness verification required"
            }

        # -----------------------------------------------------
        # FACE RECOGNITION
        # -----------------------------------------------------

        face_result = self.verify_face_from_frame(
            frame,
            student_id
        )

        # -----------------------------------------------------
        # FINAL DECISION
        # -----------------------------------------------------

        result = self.create_attendance_result(
            student_id,
            liveness_verified,
            face_result
        )

        return result