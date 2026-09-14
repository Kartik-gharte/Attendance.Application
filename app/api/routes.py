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

from app.database.attendance_db import (
    mark_attendance
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
    subject: str = Form(...),
    lecture_id: str = Form(...),
    image: UploadFile = File(...)
):

    temp_path = None

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

        sessions.pop(session_id, None)

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

    if not suffix:
        suffix = ".jpg"

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            image_bytes = await image.read()

            temp_file.write(image_bytes)

            temp_path = temp_file.name

        # =================================================
        # LOG REQUEST
        # =================================================

        print()
        print("======================================")
        print("ATTENDANCE FACE VERIFICATION")
        print("======================================")
        print("Student ID:", student_id)
        print("Subject:", subject)
        print("Lecture ID:", lecture_id)
        print("Image:", image.filename)
        print("Image size:", len(image_bytes), "bytes")
        print()

        # =================================================
        # FACE VERIFICATION
        # =================================================

        face_result = attendance_service.verify_face(
            temp_path,
            student_id
        )

        print("Face result:")
        print(face_result)
        print()

        # =================================================
        # CREATE FINAL RESULT
        # =================================================

        result = attendance_service.create_attendance_result(
            student_id=student_id,
            liveness_verified=True,
            face_result=face_result
        )

        print("Final attendance result:")
        print(result)
        print()

        # =================================================
        # CHECK FACE VERIFICATION
        # =================================================

        if result.get("attendance") != "VERIFIED":

            sessions.pop(session_id, None)

            return {
                "status": "rejected",
                "message": "Face verification failed",
                "attendance_status": "ABSENT",
                "student_id": student_id,
                "subject": subject,
                "lecture_id": lecture_id,
                "liveness": result.get("liveness"),
                "face": result.get("face"),
                "similarity": result.get("similarity"),
            }

        # =================================================
        # SAVE ATTENDANCE
        # =================================================

        attendance_record = mark_attendance(
            student_id=student_id,
            subject=subject,
            lecture_id=lecture_id,
            liveness_status=result.get("liveness"),
            face_status=result.get("face"),
            similarity=result.get("similarity"),
            attendance_status="PRESENT"
        )

        print("======================================")
        print("ATTENDANCE DATABASE RESULT")
        print("======================================")
        print(attendance_record)
        print("======================================")
        print()

        # =================================================
        # CONSUME LIVENESS SESSION
        # =================================================

        sessions.pop(session_id, None)

        # =================================================
        # DUPLICATE ATTENDANCE
        # =================================================

        if attendance_record.get("duplicate", False):

            return {
                "status": "duplicate",
                "message": "Attendance already marked for this lecture",
                "attendance_status": "ALREADY_MARKED",

                "student_id": student_id,
                "subject": subject,
                "lecture_id": lecture_id,

                "liveness_status": result.get("liveness"),
                "face_status": result.get("face"),

                "liveness": result.get("liveness"),
                "face": result.get("face"),

                "similarity": result.get("similarity"),

                "duplicate": True,

                "attendance_record": attendance_record
            }

        # =================================================
        # SUCCESS
        # =================================================

        return {
            "status": "success",
            "message": "Attendance marked successfully",

            "attendance_status": "PRESENT",

            "student_id": student_id,
            "subject": subject,
            "lecture_id": lecture_id,

            "liveness_status": result.get("liveness"),
            "face_status": result.get("face"),

            "liveness": result.get("liveness"),
            "face": result.get("face"),

            "similarity": result.get("similarity"),

            "duplicate": False,

            "attendance_record": attendance_record
        }

    except Exception as error:

        print()
        print("======================================")
        print("ATTENDANCE VERIFICATION ERROR")
        print("======================================")
        print(type(error).__name__)
        print(str(error))
        print("======================================")
        print()

        return {
            "status": "error",
            "message": str(error)
        }

    finally:

        # =================================================
        # DELETE TEMP IMAGE
        # =================================================

        if temp_path and os.path.exists(temp_path):

            try:
                os.remove(temp_path)
            except Exception:
                pass


# =========================================================
# GET STUDENT ATTENDANCE
# =========================================================

@router.get("/attendance/student/{student_id}")
def get_student_attendance(
    student_id: str
):

    from app.database.attendance_db import (
        get_student_attendance as fetch_student_attendance
    )

    records = fetch_student_attendance(student_id)

    return {
        "status": "success",
        "student_id": student_id,
        "count": len(records),
        "attendance": records
    }


# =========================================================
# GET ALL ATTENDANCE
# =========================================================

@router.get("/attendance/all")
def get_all_attendance():

    from app.database.attendance_db import (
        get_all_attendance as fetch_all_attendance
    )

    records = fetch_all_attendance()

    return {
        "status": "success",
        "count": len(records),
        "attendance": records
    }