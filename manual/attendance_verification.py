import cv2

from app.services.attendance_verification import (
    AttendanceVerificationService
)


STUDENT_ID = "STU001"


print()
print("======================================")
print("     AI ATTENDANCE VERIFICATION")
print("======================================")
print()

print(
    "Starting Attendance Verification Service..."
)

service = AttendanceVerificationService()

print()
print(
    "Service initialized successfully"
)
print()


# =========================================================
# CAMERA
# =========================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("ERROR: Could not open camera")
    exit()

print("Camera opened")
print()


# =========================================================
# INSTRUCTIONS
# =========================================================

print("======================================")
print("        ATTENDANCE TEST")
print("======================================")
print()

print(
    "Student ID:",
    STUDENT_ID
)

print()

print("Look at the camera.")
print("Blink ONCE.")
print()

print(
    "After liveness verification,"
)

print(
    "face recognition will run ONCE."
)

print()

print("Press Q to quit.")
print()


# =========================================================
# STATE
# =========================================================

closed_frames = 0
eyes_closed = False

liveness_verified = False
attendance_verified = False

recognition_attempted = False

frame_count = 0


# =========================================================
# CAMERA LOOP
# =========================================================

while True:

    success, frame = camera.read()

    if not success:

        print(
            "ERROR: Could not read camera"
        )

        break

    frame_count += 1


    # =====================================================
    # LIVENESS
    # =====================================================

    if not liveness_verified:

        try:

            result = (
                service.liveness_service.process_frame(
                    frame,
                    closed_frames,
                    eyes_closed
                )
            )

        except Exception as error:

            print()
            print("LIVENESS ERROR:")
            print(error)
            print()

            break


        # -------------------------------------------------
        # UPDATE LIVENESS STATE
        # -------------------------------------------------

        closed_frames = (
            result["closed_frames"]
        )

        eyes_closed = (
            result["eyes_closed"]
        )


        # -------------------------------------------------
        # NO FACE
        # -------------------------------------------------

        if not result["face_detected"]:

            cv2.putText(
                frame,
                "NO FACE",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )


        # -------------------------------------------------
        # FACE DETECTED
        # -------------------------------------------------

        else:

            ear = result["ear"]

            cv2.putText(
                frame,
                f"EAR: {ear:.3f}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "BLINK ONCE",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 0),
                2
            )


        # -------------------------------------------------
        # LIVENESS VERIFIED
        # -------------------------------------------------

        if result["liveness_verified"]:

            liveness_verified = True

            print()
            print("======================================")
            print("BLINK DETECTED!")
            print("LIVENESS VERIFIED!")
            print("======================================")
            print()

            cv2.putText(
                frame,
                "LIVENESS VERIFIED",
                (30, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )


    # =====================================================
    # FACE RECOGNITION
    # =====================================================

    if (
        liveness_verified
        and not recognition_attempted
    ):

        recognition_attempted = True

        print()
        print("======================================")
        print("     FACE RECOGNITION STARTING")
        print("======================================")
        print()

        try:

            final_result = (
                service.verify_attendance(
                    frame,
                    STUDENT_ID,
                    liveness_verified
                )
            )

        except Exception as error:

            print()
            print("FACE RECOGNITION ERROR:")
            print(error)
            print()

            final_result = {
                "student_id": STUDENT_ID,
                "liveness": "VERIFIED",
                "face": "ERROR",
                "similarity": None,
                "threshold": (
                    service.face_service.threshold
                ),
                "attendance": "REJECTED",
                "error": str(error)
            }


        # -------------------------------------------------
        # PRINT FINAL RESULT
        # -------------------------------------------------

        print()
        print("======================================")
        print("       ATTENDANCE RESULT")
        print("======================================")
        print()

        print(
            "Student ID:",
            final_result["student_id"]
        )

        print(
            "Liveness:",
            final_result["liveness"]
        )

        print(
            "Face:",
            final_result["face"]
        )

        print(
            "Similarity:",
            final_result["similarity"]
        )

        print(
            "Threshold:",
            final_result["threshold"]
        )

        print(
            "Attendance:",
            final_result["attendance"]
        )

        if "error" in final_result:

            print(
                "Error:",
                final_result["error"]
            )

        print()
        print("======================================")
        print()


        # -------------------------------------------------
        # FINAL ATTENDANCE STATE
        # -------------------------------------------------

        attendance_verified = (
            final_result["attendance"]
            == "VERIFIED"
        )


    # =====================================================
    # DISPLAY FINAL STATE
    # =====================================================

    if attendance_verified:

        cv2.putText(
            frame,
            "ATTENDANCE VERIFIED",
            (30, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

    elif recognition_attempted:

        cv2.putText(
            frame,
            "ATTENDANCE REJECTED",
            (30, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2
        )


    # =====================================================
    # EXIT
    # =====================================================

    cv2.imshow(
        "AI Attendance Verification",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# =========================================================
# CLEANUP
# =========================================================

camera.release()

cv2.destroyAllWindows()


print()
print("Camera closed")
print("Attendance verification test finished")