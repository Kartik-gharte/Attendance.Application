from fastapi import APIRouter, UploadFile, File, Form
import tempfile
import os
import time

from app.services.attendance_verification import (
    AttendanceVerificationService
)

from app.api.liveness_routes import (
    sessions,
    LIVENESS_VALIDITY_SECONDS
)

router = APIRouter()

attendance_service = AttendanceVerificationService()


# =========================================================
# VERIFY ATTENDANCE
# =========================================================

@router.post("/attendance/verify")
async def verify_attendance(
    student_id: str = Form(...),
    session_id: str = Form(...),
    image: UploadFile = File(...)
):

    # =====================================================
    # CHECK LIVENESS SESSION
    # =====================================================

    if session_id not in sessions:
        return {
            "status": "error",
            "message": "Invalid or expired liveness session"
        }

    session = sessions[session_id]

    # =====================================================
    # CHECK LIVENESS VERIFICATION
    # =====================================================

    if not session.get("liveness_verified", False):
        return {
            "status": "error",
            "message": "Liveness verification required"
        }

    # =====================================================
    # CHECK LIVENESS EXPIRATION
    # =====================================================

    verified_at = session.get("verified_at")

    if verified_at is None:
        return {
            "status": "error",
            "message": "Invalid liveness verification"
        }

    if time.time() - verified_at > LIVENESS_VALIDITY_SECONDS:

        del sessions[session_id]

        return {
            "status": "error",
            "message": "Liveness session expired"
        }

    # =====================================================
    # READ IMAGE
    # =====================================================

    suffix = os.path.splitext(
        image.filename or ".jpg"
    )[1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as temp_file:

        temp_file.write(
            await image.read()
        )

        temp_path = temp_file.name

    try:

        # =================================================
        # FACE VERIFICATION
        # =================================================

        print()
        print("======================================")
        print("ATTENDANCE FACE VERIFICATION")
        print("======================================")
        print("Student ID:", student_id)
        print("Image:", image.filename)
        print("Temporary image:", temp_path)

        face_result = attendance_service.verify_face(
            temp_path,
            student_id
        )

        print("Face result:", face_result)

        # =================================================
        # FINAL ATTENDANCE DECISION
        # =================================================

        result = attendance_service.create_attendance_result(
            student_id=student_id,
            liveness_verified=True,
            face_result=face_result
        )

        print("Final attendance result:", result)

        # =================================================
        # CONSUME LIVENESS SESSION
        # =================================================

        del sessions[session_id]

        return {
            "status": "success",
            "message": "Attendance verification completed",
            **result
        }

    except Exception as error:

        print()
        print("======================================")
        print("ATTENDANCE VERIFICATION ERROR")
        print("======================================")
        print(str(error))
        print("======================================")

        return {
            "status": "error",
            "message": str(error)
        }

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)