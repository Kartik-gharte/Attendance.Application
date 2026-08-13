from app.services.liveness import LivenessService
from app.services.face_recognition import FaceRecognitionService


class AttendanceVerificationService:

    def __init__(self):

        print("Initializing Attendance Verification Service...")

        self.liveness_service = LivenessService()
        self.face_service = FaceRecognitionService()

        print("Attendance Verification Service ready")

    # =========================================================
    # VERIFY FACE FROM IMAGE
    # =========================================================

    def verify_face(
        self,
        image_path,
        student_id
    ):

        print()
        print("======================================")
        print("        FACE VERIFICATION")
        print("======================================")

        result = self.face_service.recognize(
            image_path,
            student_id
        )

        return result

    # =========================================================
    # VERIFY FACE FROM CAMERA FRAME
    # =========================================================

    def verify_face_from_frame(
        self,
        frame,
        student_id
    ):

        print()
        print("======================================")
        print("    LIVE FACE VERIFICATION")
        print("======================================")

        result = self.face_service.recognize_frame(
            frame,
            student_id
        )

        return result

    # =========================================================
    # CREATE FINAL ATTENDANCE RESULT
    # =========================================================

    def create_attendance_result(
        self,
        student_id,
        liveness_verified,
        face_result
    ):

        face_matched = (
            face_result.get("result") == "MATCH"
        )

        attendance_verified = (
            liveness_verified
            and face_matched
        )

        return {
            "student_id": student_id,

            "liveness": (
                "VERIFIED"
                if liveness_verified
                else "FAILED"
            ),

            "face": (
                "MATCH"
                if face_matched
                else "UNKNOWN"
            ),

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
                "attendance": "REJECTED"
            }

        # -----------------------------------------------------
        # FACE RECOGNITION
        #
        # IMPORTANT:
        # InsightFace is called ONLY ONCE here,
        # after liveness has already been verified.
        # -----------------------------------------------------

        try:

            face_result = (
                self.verify_face_from_frame(
                    frame,
                    student_id
                )
            )

        except ValueError as error:

            return {
                "student_id": student_id,
                "liveness": "VERIFIED",
                "face": "ERROR",
                "similarity": None,
                "threshold": self.face_service.threshold,
                "attendance": "REJECTED",
                "error": str(error)
            }

        # -----------------------------------------------------
        # FINAL DECISION
        # -----------------------------------------------------

        return self.create_attendance_result(
            student_id,
            liveness_verified,
            face_result
        )