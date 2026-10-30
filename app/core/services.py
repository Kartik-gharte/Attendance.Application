from dataclasses import dataclass

from app.core.config import Settings
from app.services.attendance_verification import AttendanceVerificationService
from app.services.face_recognition import FaceRecognitionService
from app.services.liveness import LivenessService


@dataclass
class AppServices:
    liveness_service: LivenessService
    face_service: FaceRecognitionService
    attendance_service: AttendanceVerificationService

    def close(self) -> None:
        self.liveness_service.close()


def build_services(settings: Settings) -> AppServices:
    liveness_service = LivenessService(
        settings.mediapipe_face_landmarker_model
    )

    face_service = FaceRecognitionService(settings)

    attendance_service = AttendanceVerificationService(
        liveness_service=liveness_service,
        face_service=face_service,
    )

    return AppServices(
        liveness_service=liveness_service,
        face_service=face_service,
        attendance_service=attendance_service,
    )
