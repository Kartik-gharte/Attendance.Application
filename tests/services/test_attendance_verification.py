import cv2

from app.services.attendance_verification import AttendanceVerificationService


STUDENT_ID = "STU001"


print()
print("======================================")
print("     AI ATTENDANCE VERIFICATION")
print("======================================")
print()

print("Starting Attendance Verification Service...")

service = AttendanceVerificationService()

print()
print("Service initialized successfully")
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

print("Student ID:", STUDENT_ID)
print()
print("Look at the camera.")
print("Blink ONCE.")
print()
print("After liveness verification,")
print("face recognition will start automatically.")
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

        print("ERROR: Could not read camera")
        break

    frame_count += 1


    # =====================================================
    # DEBUG
    # =====================================================

    if frame_count % 30 == 0:

        print(
            f"Camera frames received: {frame_count}"
        )


    # =====================================================
    # LIVENESS
    # =====================================================

    if not liveness_verified:

        try:

            result = service.liveness_service.process_frame(
                frame,
                closed_frames,
                eyes_closed
            )

        except Exception as error:

            print()
            print("LIVENESS ERROR:")
            print(error)
            print()

            break


        closed_frames = result["closed_frames"]

        eyes_closed = result["eyes_closed"]


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

    # =====================================================
    # FACE RECOGNITION
    # =====================================================

    else:

        cv2.putText(
            frame,
            "LIVENESS VERIFIED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "RECOGNIZING FACE...",
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2
        )


        # =================================================
        # ONLY ONE RECOGNITION ATTEMPT
        # =================================================

        if not recognition_attempted:

            recognition_attempted = True

            print()
            print("======================================")
            print("STARTING FACE RECOGNITION")
            print("======================================")
            print()

            try:

                print("Calling recognize_frame()...")

                recognition = (
                    service.face_service.recognize_frame(
                        frame,
                        STUDENT_ID
                    )
                )

                print("recognize_frame() completed")


                similarity = recognition["similarity"]

                face_result = recognition["result"]


                print()
                print("======================================")
                print("FACE RECOGNITION RESULT")
                print("======================================")

                print(
                    "Student ID:",
                    STUDENT_ID
                )

                print(
                    f"Similarity: {similarity:.4f}"
                )

                print(
                    "Result:",
                    face_result
                )

                print("======================================")


                # =========================================
                # MATCH
                # =========================================

                if face_result == "MATCH":

                    attendance_verified = True

                    print()
                    print("======================================")
                    print("ATTENDANCE VERIFIED!")
                    print("======================================")
                    print()


                    cv2.putText(
                        frame,
                        "FACE MATCH",
                        (30, 150),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        "ATTENDANCE VERIFIED",
                        (30, 200),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        3
                    )


                # =========================================
                # UNKNOWN
                # =========================================

                else:

                    print()
                    print("FACE NOT MATCHED")
                    print()

                    cv2.putText(
                        frame,
                        "UNKNOWN FACE",
                        (30, 150),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2
                    )


            except Exception as error:

                print()
                print("======================================")
                print("FACE RECOGNITION ERROR")
                print("======================================")
                print(error)
                print("======================================")
                print()


                cv2.putText(
                    frame,
                    "FACE RECOGNITION ERROR",
                    (30, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )


    # =====================================================
    # DISPLAY
    # =====================================================

    cv2.imshow(
        "AI Attendance Verification",
        frame
    )


    # =====================================================
    # KEYBOARD
    # =====================================================

    key = cv2.waitKey(1) & 0xFF


    if key == ord("q"):

        print()
        print("Q pressed.")
        print()

        break


    # =====================================================
    # SUCCESS
    # =====================================================

    if attendance_verified:

        print()
        print("Attendance verification successful.")
        print("Closing camera in 3 seconds...")

        cv2.waitKey(3000)

        break


# =========================================================
# CLEANUP
# =========================================================

camera.release()

cv2.destroyAllWindows()


# =========================================================
# FINAL RESULT
# =========================================================

print()
print("======================================")
print("           FINAL RESULT")
print("======================================")

if attendance_verified:

    print("Student ID :", STUDENT_ID)
    print("Liveness   : VERIFIED")
    print("Face       : MATCH")
    print("Attendance : VERIFIED")

else:

    print("Student ID :", STUDENT_ID)
    print(
        "Liveness   :",
        "VERIFIED" if liveness_verified else "FAILED"
    )

    print("Face       : UNKNOWN")
    print("Attendance : REJECTED")