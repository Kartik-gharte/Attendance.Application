from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
import cv2
import numpy as np
import uuid
import time

from app.auth.dependencies import require_student
from app.auth.models import UserPrincipal
from app.services.validation import (
    IMAGE_TOO_LARGE,
    INVALID_IMAGE,
    INVALID_LIVENESS_SESSION,
    validate_image_bytes,
    validate_image_content_type,
    validate_session_id,
)


router = APIRouter()


# =========================================================
# LIVENESS SESSIONS
# =========================================================

sessions = {}


# =========================================================
# START LIVENESS SESSION
# =========================================================

@router.post("/liveness/start")
async def start_liveness(
    current_user: UserPrincipal = Depends(require_student),
):

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "user_id": current_user.id,
        "closed_frames": 0,
        "eyes_closed": False,
        "liveness_verified": False,
        "verified_at": None
    }

    return {
        "status": "success",
        "session_id": session_id,
        "message": "Liveness session started"
    }


# =========================================================
# PROCESS LIVENESS FRAME
# =========================================================

@router.post("/liveness/frame")
async def process_liveness_frame(
    request: Request,
    session_id: str,
    image: UploadFile = File(...),
    current_user: UserPrincipal = Depends(require_student),
):

    liveness_service = request.app.state.liveness_service
    settings = request.app.state.settings

    liveness_validity_seconds = (
        settings.liveness_validity_seconds
    )

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
            "message": "Invalid or expired liveness session"
        }

    session = sessions[session_id]

    if session.get("user_id") != current_user.id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


    # -----------------------------------------------------
    # CHECK IF ALREADY VERIFIED
    # -----------------------------------------------------

    if session["liveness_verified"]:

        verified_at = session["verified_at"]

        if (
            verified_at is not None
            and time.time() - verified_at
            <= liveness_validity_seconds
        ):

            return {
                "status": "success",
                "session_id": session_id,
                "face_detected": True,
                "ear": None,
                "eyes_closed": False,
                "closed_frames": 0,
                "blink_detected": False,
                "liveness_verified": True
            }

        else:

            del sessions[session_id]

            return {
                "status": "error",
                "message": "Liveness session expired"
            }


    # -----------------------------------------------------
    # READ IMAGE
    # -----------------------------------------------------

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

    image_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:

        return {
            "status": "error",
            "message": INVALID_IMAGE,
        }


    # -----------------------------------------------------
    # PROCESS FRAME
    # -----------------------------------------------------

    result = liveness_service.process_frame(
        frame,
        session["closed_frames"],
        session["eyes_closed"]
    )


    # -----------------------------------------------------
    # UPDATE SESSION STATE
    # -----------------------------------------------------

    session["closed_frames"] = (
        result["closed_frames"]
    )

    session["eyes_closed"] = (
        result["eyes_closed"]
    )


    # -----------------------------------------------------
    # LIVENESS SUCCESS
    # -----------------------------------------------------

    if result["liveness_verified"]:

        session["liveness_verified"] = True

        session["verified_at"] = time.time()


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "status": "success",
        "session_id": session_id,
        "face_detected": result["face_detected"],
        "ear": result["ear"],
        "eyes_closed": result["eyes_closed"],
        "closed_frames": result["closed_frames"],
        "blink_detected": result["blink_detected"],
        "liveness_verified": (
            session["liveness_verified"]
        )
    }