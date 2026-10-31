import cv2
import getpass
import os
import requests
import time


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = os.getenv(
    "ATTENDANCE_API_URL",
    "http://127.0.0.1:8000",
)

USERNAME = os.getenv(
    "ATTENDANCE_USERNAME",
    "student1",
)

STUDENT_ID = "STU001"
SUBJECT = "Java Programming"

# Use a NEW lecture ID for this test.
# Your existing database already contains JAVA-LECTURE-001.
LECTURE_ID = "JAVA-LECTURE-API-001"


# =========================================================
# START LIVENESS SESSION
# =========================================================

print()
print("======================================")
print("       API ATTENDANCE TEST")
print("======================================")
print()

print("Authenticating...")

password = getpass.getpass("Password: ")

auth_response = requests.post(
    f"{BASE_URL}/auth/token",
    data={
        "username": USERNAME,
        "password": password,
    },
    timeout=10,
)

if auth_response.status_code != 200:

    print("ERROR: Could not authenticate")
    print(auth_response.text)
    exit()

access_token = auth_response.json()["access_token"]

AUTH_HEADERS = {
    "Authorization": f"Bearer {access_token}",
}

print("Authenticated as:", USERNAME)
print()

print("Starting liveness session...")

response = requests.post(
    f"{BASE_URL}/liveness/start",
    headers=AUTH_HEADERS,
)

if response.status_code != 200:

    print("ERROR: Could not start liveness session")
    print(response.text)
    exit()

session_data = response.json()

if session_data.get("status") != "success":

    print("ERROR:", session_data)
    exit()

session_id = session_data["session_id"]

print("Liveness session started")
print("Session ID:", session_id)


# =========================================================
# OPEN CAMERA
# =========================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("ERROR: Could not open camera")
    exit()

print()
print("Camera opened")
print()
print("Look at the camera.")
print("Blink ONCE.")
print()
print("Press Q to quit.")


# =========================================================
# LIVENESS VARIABLES
# =========================================================

liveness_verified = False
last_send_time = 0

final_frame = None


# =========================================================
# CAMERA LOOP
# =========================================================

while True:

    success, frame = camera.read()

    if not success:

        print("ERROR: Could not read camera")
        break

    # -----------------------------------------------------
    # SEND FRAME TO API
    # -----------------------------------------------------

    current_time = time.time()

    # Send approximately 8 frames per second.
    if (
        not liveness_verified
        and current_time - last_send_time >= 0.12
    ):

        last_send_time = current_time

        success_encode, encoded_image = cv2.imencode(
            ".jpg",
            frame
        )

        if success_encode:

            try:

                files = {
                    "image": (
                        "frame.jpg",
                        encoded_image.tobytes(),
                        "image/jpeg"
                    )
                }

                response = requests.post(
                    f"{BASE_URL}/liveness/frame",
                    params={
                        "session_id": session_id
                    },
                    headers=AUTH_HEADERS,
                    files=files,
                    timeout=10
                )

                result = response.json()

                if result.get("status") == "success":

                    face_detected = result.get(
                        "face_detected",
                        False
                    )

                    ear = result.get(
                        "ear"
                    )

                    eyes_closed = result.get(
                        "eyes_closed",
                        False
                    )

                    blink_detected = result.get(
                        "blink_detected",
                        False
                    )

                    liveness_verified = result.get(
                        "liveness_verified",
                        False
                    )

                    # -------------------------------------
                    # DISPLAY STATUS
                    # -------------------------------------

                    if face_detected:

                        if ear is not None:

                            cv2.putText(
                                frame,
                                f"EAR: {ear:.3f}",
                                (30, 40),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0, 255, 0),
                                2
                            )

                        if eyes_closed:

                            cv2.putText(
                                frame,
                                "EYES CLOSED",
                                (30, 80),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0, 255, 255),
                                2
                            )

                        else:

                            cv2.putText(
                                frame,
                                "EYES OPEN",
                                (30, 80),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0, 255, 0),
                                2
                            )

                    else:

                        cv2.putText(
                            frame,
                            "NO FACE",
                            (30, 40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2
                        )

                    # -------------------------------------
                    # BLINK
                    # -------------------------------------

                    if blink_detected:

                        print()
                        print("======================================")
                        print("BLINK DETECTED!")
                        print("LIVENESS VERIFIED!")
                        print("======================================")
                        print()

                    # -------------------------------------
                    # LIVENESS VERIFIED
                    # -------------------------------------

                    if liveness_verified:

                        cv2.putText(
                            frame,
                            "LIVENESS VERIFIED",
                            (30, 130),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 255, 0),
                            3
                        )

                        final_frame = frame.copy()

                        break

                else:

                    print(
                        "Liveness API error:",
                        result
                    )

                    break

            except Exception as error:

                print()
                print("API request error:")
                print(error)
                break

    # -----------------------------------------------------
    # DISPLAY CAMERA
    # -----------------------------------------------------

    cv2.imshow(
        "API Attendance - Liveness",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# =========================================================
# CAMERA CLEANUP
# =========================================================

camera.release()
cv2.destroyAllWindows()


# =========================================================
# CHECK LIVENESS
# =========================================================

if not liveness_verified:

    print()
    print("Liveness was not verified.")
    print("Attendance verification cancelled.")
    exit()


# =========================================================
# CAPTURE FINAL FACE
# =========================================================

print()
print("Liveness verified successfully.")
print()
print("Starting attendance face verification...")


if final_frame is None:

    print("ERROR: No final frame available.")
    exit()


success_encode, encoded_image = cv2.imencode(
    ".jpg",
    final_frame
)

if not success_encode:

    print("ERROR: Could not encode final image.")
    exit()


# =========================================================
# SEND ATTENDANCE VERIFICATION
# =========================================================

files = {
    "image": (
        "attendance.jpg",
        encoded_image.tobytes(),
        "image/jpeg"
    )
}

data = {
    "student_id": STUDENT_ID,
    "session_id": session_id,
    "subject": SUBJECT,
    "lecture_id": LECTURE_ID
}


try:

    response = requests.post(
        f"{BASE_URL}/attendance/verify",
        data=data,
        headers=AUTH_HEADERS,
        files=files,
        timeout=30
    )

    result = response.json()

except Exception as error:

    print()
    print("Attendance API error:")
    print(error)
    exit()


# =========================================================
# FINAL RESULT
# =========================================================

print()
print("======================================")
print("       FINAL API RESULT")
print("======================================")
print()

print(result)

print()
print("======================================")