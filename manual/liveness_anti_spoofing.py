import cv2

from app.services.liveness import LivenessService


# ============================================================
# LOAD LIVENESS SERVICE
# ============================================================

print("Starting Liveness Service...")

liveness_service = LivenessService()

print("Liveness service ready")


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("ERROR: Could not open camera")

    exit()


print("Camera opened")

print()
print("======================================")
print("       LIVENESS SERVICE TEST")
print("======================================")
print()
print("Look at the camera.")
print("Blink ONCE.")
print("Press Q to quit.")
print()


# ============================================================
# STATE
# ============================================================

closed_frames = 0

eyes_closed = False

liveness_verified = False


# ============================================================
# CAMERA LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print(
            "ERROR: Could not read camera"
        )

        break


    # ========================================================
    # STOP PROCESSING AFTER SUCCESS
    # ========================================================

    if liveness_verified:

        cv2.putText(
            frame,
            "LIVENESS VERIFIED",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3
        )

        cv2.putText(
            frame,
            "REAL PERSON",
            (30, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "Liveness Service Test",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):

            break

        continue


    # ========================================================
    # PROCESS FRAME
    # ========================================================

    result = liveness_service.process_frame(
        frame,
        closed_frames,
        eyes_closed
    )


    # ========================================================
    # UPDATE STATE
    # ========================================================

    closed_frames = result[
        "closed_frames"
    ]

    eyes_closed = result[
        "eyes_closed"
    ]


    # ========================================================
    # FACE STATUS
    # ========================================================

    if not result["face_detected"]:

        cv2.putText(
            frame,
            "NO FACE DETECTED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2
        )

    else:

        ear = result["ear"]

        cv2.putText(
            frame,
            f"EAR: {ear:.3f}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )


        # ====================================================
        # ANTI-SPOOFING STATUS
        # ====================================================

        anti_spoof = result.get(
            "anti_spoofing",
            {}
        )

        anti_spoof_passed = anti_spoof.get(
            "passed",
            False
        )

        anti_spoof_score = anti_spoof.get(
            "score",
            0.0
        )

        cv2.putText(
            frame,
            f"Anti-Spoof: "
            f"{'PASS' if anti_spoof_passed else 'CHECK'} "
            f"({anti_spoof_score:.2f})",
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (
                (0, 255, 0)
                if anti_spoof_passed
                else (0, 165, 255)
            ),
            2
        )


        # ====================================================
        # BLINK
        # ====================================================

        if result["blink_detected"]:

            print()
            print(
                "================================"
            )
            print(
                "BLINK DETECTED!"
            )
            print(
                "ANTI-SPOOF STATUS:",
                "PASS"
                if anti_spoof_passed
                else "FAILED"
            )
            print(
                "LIVENESS VERIFIED:",
                "YES"
                if result["liveness_verified"]
                else "NO"
            )
            print(
                "================================"
            )
            print()

            if result["liveness_verified"]:

                liveness_verified = True

        elif result["eyes_closed"]:

            cv2.putText(
                frame,
                "EYES CLOSED",
                (30, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 255),
                2
            )

        else:

            cv2.putText(
                frame,
                "BLINK ONCE",
                (30, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 0),
                2
            )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "Liveness Service Test",
        frame
    )


    # ========================================================
    # QUIT
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()

print()
print("======================================")
print("Liveness test stopped.")
print("======================================")