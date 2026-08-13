from pathlib import Path

from app.services.liveness import LivenessService
from app.services.face_recognition import FaceRecognitionService


class AttendanceVerificationService:

    def __init__(self):

        print("Initializing Attendance Verification Service...")

        self.liveness_service = LivenessService()
        self.face_service = FaceRecognitionService()

        print("Attendance Verification Service ready")

    # =========================================================
    # VERIFY FACE
    # =========================================================

    def verify_face(self, image_path, student_id):

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
    # FINAL ATTENDANCE DECISION
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
            "attendance": (
                "VERIFIED"
                if attendance_verified
                else "REJECTED"
            )
        }