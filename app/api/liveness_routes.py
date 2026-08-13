from fastapi import APIRouter, UploadFile, File
import cv2
import numpy as np
import uuid
import time

from app.services.liveness import LivenessService


router = APIRouter()

liveness_service = LivenessService()


# =========================================================
# LIVENESS SESSIONS
# =========================================================

sessions = {}

# How long a successful liveness session remains valid
LIVENESS_VALIDITY_SECONDS = 30


# =========================================================
# START LIVENESS SESSION
# =========================================================

@router.post("/liveness/start")
async def start_liveness():

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
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
    session_id: str,
    image: UploadFile = File(...)
):

    # -----------------------------------------------------
    # CHECK SESSION
    # -----------------------------------------------------

    if session_id not in sessions:

        return {
            "status": "error",
            "message": "Invalid or expired liveness session"
        }


    session = sessions[session_id]


    # -----------------------------------------------------
    # CHECK IF ALREADY VERIFIED
    # -----------------------------------------------------

    if session["liveness_verified"]:

        verified_at = session["verified_at"]

        if (
            verified_at is not None
            and time.time() - verified_at
            <= LIVENESS_VALIDITY_SECONDS
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

    image_bytes = await image.read()

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
            "message": "Could not decode image"
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