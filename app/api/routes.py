from fastapi import APIRouter, Request, UploadFile, File, Form
import tempfile
import os
import time

from app.api.liveness_routes import sessions
from app.services.validation import (
    DATABASE_ERROR,
    IMAGE_TOO_LARGE,
    INVALID_IMAGE,
    INVALID_LIVENESS_SESSION,
    INVALID_STUDENT_ID,
    INVALID_SUBJECT,
    INVALID_LECTURE_ID,
    INTERNAL_ERROR,
    validate_image_bytes,
    validate_image_content_type,
    validate_lecture_id,
    validate_session_id,
    validate_student_id,
    validate_subject,
)

from app.database.attendance_db import (
    mark_attendance
)


router = APIRouter()


# =========================================================
# VERIFY ATTENDANCE
# =========================================================

@router.post("/attendance/verify")
async def verify_attendance(
    request: Request,
    student_id: str = Form(...),
    session_id: str = Form(...),
    subject: str = Form(...),
    lecture_id: str = Form(...),
    image: UploadFile = File(...)
):

    attendance_service = request.app.state.attendance_service
    settings = request.app.state.settings

    liveness_validity_seconds = (
        settings.liveness_validity_seconds
    )

    temp_path = None

    try:

        validated_session_id = validate_session_id(session_id)

    except ValueError:

        return {
            "status": "error",
            "message": INVALID_LIVENESS_SESSION,
        }

    if validated_session_id != session_id or session_id not in sessions:

        return {
            "status": "error",
            "message": "Invalid or expired liveness session",
        }

    session = sessions[session_id]

    try:

        validated_student_id = validate_student_id(student_id)

    except ValueError:

        return {
            "status": "error",
            "message": INVALID_STUDENT_ID,
        }

    try:

        validated_subject = validate_subject(subject)

    except ValueError:

        return {
            "status": "error",
            "message": INVALID_SUBJECT,
        }

    try:

        validated_lecture_id = validate_lecture_id(lecture_id)

    except ValueError:

        return {
            "status": "error",
            "message": INVALID_LECTURE_ID,
        }

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

    if time.time() - verified_at > liveness_validity_seconds:

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

    image_bytes = await image.read(
        settings.max_upload_size_bytes + 1
    )

    if len(image_bytes) > settings.max_upload_size_bytes:

        return {
            "status": "error",
            "message": IMAGE_TOO_LARGE,
        }

    if not image_bytes or not validate_image_content_type(
        image.content_type
    ):

        return {
            "status": "error",
            "message": INVALID_IMAGE,
        }

    try:

        validate_image_bytes(
            image_bytes,
            settings.max_upload_size_bytes,
            settings.max_image_width,
            settings.max_image_height,
            settings.max_image_pixels,
        )

    except ValueError as error:

        return {
            "status": "error",
            "message": str(error),
        }

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

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
            validated_student_id
        )

        print("Face result:")
        print(face_result)
        print()

        # =================================================
        # CREATE FINAL RESULT
        # =================================================

        result = attendance_service.create_attendance_result(
            student_id=validated_student_id,
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
                "student_id": validated_student_id,
                "subject": validated_subject,
                "lecture_id": validated_lecture_id,
                "liveness": result.get("liveness"),
                "face": result.get("face"),
                "similarity": result.get("similarity"),
            }

        # =================================================
        # SAVE ATTENDANCE
        # =================================================

        attendance_record = mark_attendance(
            student_id=validated_student_id,
            subject=validated_subject,
            lecture_id=validated_lecture_id,
            liveness_status=result.get("liveness"),
            face_status=result.get("face"),
            similarity=result.get("similarity"),
            attendance_status="PRESENT",
            database_path=request.app.state.settings.database_path
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

                "student_id": validated_student_id,
                "subject": validated_subject,
                "lecture_id": validated_lecture_id,

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

            "student_id": validated_student_id,
            "subject": validated_subject,
            "lecture_id": validated_lecture_id,

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
            "message": INTERNAL_ERROR
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
    request: Request,
    student_id: str
):

    from app.database.attendance_db import (
        get_student_attendance as fetch_student_attendance
    )

    try:

        records = fetch_student_attendance(
            student_id,
            database_path=request.app.state.settings.database_path
        )

    except Exception:

        return {
            "status": "error",
            "message": DATABASE_ERROR
        }

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
def get_all_attendance(request: Request):

    from app.database.attendance_db import (
        get_all_attendance as fetch_all_attendance
    )

    try:

        records = fetch_all_attendance(
            database_path=request.app.state.settings.database_path
        )

    except Exception:

        return {
            "status": "error",
            "message": DATABASE_ERROR
        }

    return {
        "status": "success",
        "count": len(records),
        "attendance": records
    }