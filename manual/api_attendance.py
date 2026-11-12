"""Manual client that exercises the attendance verification API.

Every value is configurable through an environment variable or a command
line argument, so the script is not tied to one student, lecture, or server.

Environment variables
---------------------
``ATTENDANCE_API_URL``
    Base URL of the running API. Default ``http://127.0.0.1:8000``.
``ATTENDANCE_USERNAME``
    Account username used to request a bearer token.
``ATTENDANCE_STUDENT_ID``
    Student identifier that the attendance is recorded for.
``ATTENDANCE_SUBJECT``
    Subject name recorded with the attendance.
``ATTENDANCE_LECTURE_ID``
    Lecture identifier recorded with the attendance.
``ATTENDANCE_PASSWORD``
    Optional. When set, the password is read from this variable instead of
    being prompted for. Prefer the prompt.

The password is never taken from a command line argument, because process
arguments are visible to other users on the machine.

Usage::

    python -m manual.api_attendance --student-id STU001 --subject "Java Programming"
"""

import argparse
import getpass
import os
import sys
import time

import cv2
import requests

from app.core.logging_config import get_logger


logger = get_logger("manual.api_attendance")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SUBJECT = "Java Programming"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the manual attendance verification client",
    )

    parser.add_argument(
        "--base-url",
        default=os.getenv("ATTENDANCE_API_URL", DEFAULT_BASE_URL),
        help="Base URL of the running API",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("ATTENDANCE_USERNAME"),
        help="Account username used to request a bearer token",
    )
    parser.add_argument(
        "--student-id",
        default=os.getenv("ATTENDANCE_STUDENT_ID"),
        help="Student identifier the attendance is recorded for",
    )
    parser.add_argument(
        "--subject",
        default=os.getenv("ATTENDANCE_SUBJECT", DEFAULT_SUBJECT),
        help="Subject name recorded with the attendance",
    )
    parser.add_argument(
        "--lecture-id",
        default=os.getenv("ATTENDANCE_LECTURE_ID"),
        help="Lecture identifier recorded with the attendance",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=int(os.getenv("ATTENDANCE_CAMERA_INDEX", "0")),
        help="Camera device index",
    )

    return parser


def resolve_password(username: str) -> str | None:
    """Return the account password, prompting when it is not configured."""

    configured = os.getenv("ATTENDANCE_PASSWORD")

    if configured:
        return configured

    if not sys.stdin.isatty():
        logger.error(
            "No password available. Set ATTENDANCE_PASSWORD or run from a "
            "terminal."
        )
        return None

    return getpass.getpass(f"Password for {username}: ")


def authenticate(
    base_url: str,
    username: str,
    password: str,
    timeout: int = 10,
) -> str | None:
    """Request a bearer token and return it."""

    try:
        response = requests.post(
            f"{base_url}/auth/token",
            data={
                "username": username,
                "password": password,
            },
            timeout=timeout,
        )

    except requests.RequestException as error:
        logger.error("Authentication request failed: %s", error)
        return None

    if response.status_code != 200:
        logger.error("Authentication failed with status %s", response.status_code)
        return None

    return response.json().get("access_token")


def start_liveness_session(
    base_url: str,
    headers: dict[str, str],
    timeout: int = 10,
) -> str | None:
    """Start a liveness session and return its identifier."""

    try:
        response = requests.post(
            f"{base_url}/liveness/start",
            headers=headers,
            timeout=timeout,
        )

    except requests.RequestException as error:
        logger.error("Liveness session request failed: %s", error)
        return None

    if response.status_code != 200:
        logger.error(
            "Could not start a liveness session (status %s)",
            response.status_code,
        )
        return None

    payload = response.json()

    if payload.get("status") != "success":
        logger.error("Liveness session was not started")
        return None

    return payload.get("session_id")


def send_liveness_frame(
    base_url: str,
    headers: dict[str, str],
    session_id: str,
    frame,
    timeout: int = 10,
) -> dict | None:
    """Send one camera frame to the liveness endpoint."""

    encoded, buffer = cv2.imencode(".jpg", frame)

    if not encoded:
        logger.error("Could not encode the camera frame")
        return None

    files = {
        "image": ("frame.jpg", buffer.tobytes(), "image/jpeg"),
    }

    try:
        response = requests.post(
            f"{base_url}/liveness/frame",
            params={"session_id": session_id},
            headers=headers,
            files=files,
            timeout=timeout,
        )

    except requests.RequestException as error:
        logger.error("Liveness frame request failed: %s", error)
        return None

    try:
        return response.json()

    except ValueError:
        logger.error("Liveness endpoint returned a non JSON response")
        return None


def submit_attendance(
    base_url: str,
    headers: dict[str, str],
    session_id: str,
    student_id: str,
    subject: str,
    lecture_id: str,
    frame,
    timeout: int = 30,
) -> dict | None:
    """Submit the final attendance verification request."""

    encoded, buffer = cv2.imencode(".jpg", frame)

    if not encoded:
        logger.error("Could not encode the final frame")
        return None

    files = {
        "image": ("attendance.jpg", buffer.tobytes(), "image/jpeg"),
    }

    data = {
        "student_id": student_id,
        "session_id": session_id,
        "subject": subject,
        "lecture_id": lecture_id,
    }

    try:
        response = requests.post(
            f"{base_url}/attendance/verify",
            data=data,
            headers=headers,
            files=files,
            timeout=timeout,
        )

    except requests.RequestException as error:
        logger.error("Attendance request failed: %s", error)
        return None

    try:
        return response.json()

    except ValueError:
        logger.error("Attendance endpoint returned a non JSON response")
        return None


def run_camera_liveness(
    base_url: str,
    headers: dict[str, str],
    session_id: str,
    camera_index: int = 0,
    frame_interval: float = 0.12,
):
    """Open the camera and drive the liveness session.

    Returns the final captured frame when liveness was verified, otherwise
    ``None``.
    """

    camera = cv2.VideoCapture(camera_index)

    if not camera.isOpened():
        logger.error("Could not open camera %s", camera_index)
        return None

    liveness_verified = False
    last_send_time = 0.0
    final_frame = None

    try:

        while True:

            success, frame = camera.read()

            if not success:
                logger.error("Could not read a frame from the camera")
                break

            current_time = time.time()

            if (
                not liveness_verified
                and current_time - last_send_time >= frame_interval
            ):

                last_send_time = current_time

                result = send_liveness_frame(
                    base_url,
                    headers,
                    session_id,
                    frame,
                )

                if result is None:
                    break

                if result.get("status") != "success":
                    logger.error("Liveness request was rejected")
                    break

                liveness_verified = bool(
                    result.get("liveness_verified", False)
                )

                if liveness_verified:
                    final_frame = frame.copy()

                draw_status(frame, result)

            cv2.imshow("API Attendance - Liveness", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        camera.release()
        cv2.destroyAllWindows()

    if not liveness_verified:
        return None

    return final_frame


def draw_status(frame, result: dict) -> None:
    """Overlay the liveness result onto the camera frame."""

    face_detected = result.get("face_detected", False)
    ear = result.get("ear")
    eyes_closed = result.get("eyes_closed", False)
    blink_detected = result.get("blink_detected", False)

    if face_detected:

        if ear is not None:
            cv2.putText(
                frame,
                f"EAR: {ear:.3f}",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

        cv2.putText(
            frame,
            "EYES CLOSED" if eyes_closed else "EYES OPEN",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255) if eyes_closed else (0, 255, 0),
            2,
        )

    else:

        cv2.putText(
            frame,
            "NO FACE",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

    if blink_detected:
        logger.info("Blink detected")

    if result.get("liveness_verified"):
        cv2.putText(
            frame,
            "LIVENESS VERIFIED",
            (30, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3,
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    missing = [
        name
        for name, value in (
            ("--username", args.username),
            ("--student-id", args.student_id),
            ("--lecture-id", args.lecture_id),
        )
        if not value
    ]

    if missing:
        logger.error(
            "Missing required value(s): %s. Set the matching environment "
            "variable or pass the argument.",
            ", ".join(missing),
        )
        return 2

    password = resolve_password(args.username)

    if not password:
        return 2

    access_token = authenticate(
        args.base_url,
        args.username,
        password,
    )

    if not access_token:
        return 1

    headers = {"Authorization": f"Bearer {access_token}"}

    session_id = start_liveness_session(args.base_url, headers)

    if not session_id:
        return 1

    logger.info("Liveness session started")

    final_frame = run_camera_liveness(
        args.base_url,
        headers,
        session_id,
        camera_index=args.camera_index,
    )

    if final_frame is None:
        logger.error("Liveness was not verified. Cancelling attendance.")
        return 1

    result = submit_attendance(
        args.base_url,
        headers,
        session_id,
        args.student_id,
        args.subject,
        args.lecture_id,
        final_frame,
    )

    if result is None:
        return 1

    logger.info("Attendance result: %s", result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
