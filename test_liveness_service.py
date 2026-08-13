import cv2

from liveness import LivenessService


print("======================================")
print("       LIVENESS SERVICE TEST")
print("======================================")

service = LivenessService()

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera")
    exit()

print("Camera opened")
print("Blink once.")
print("Press Q to quit.")

closed_frames = 0
eyes_closed = False
liveness_verified = False


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera")
        break

    if not liveness_verified:

        result = service.process_frame(
            frame,
            closed_frames,
            eyes_closed
        )

        closed_frames = result["closed_frames"]
        eyes_closed = result["eyes_closed"]

        # ---------------------------------------------
        # SHOW FACE STATUS
        # ---------------------------------------------

        if result["face_detected"]:

            ear = result["ear"]

            cv2.putText(
                frame,
                f"EAR: {ear:.3f}",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            if result["blink_detected"]:

                print()
                print("================================")
                print("BLINK DETECTED! ✅")
                print("LIVENESS VERIFIED! ✅")
                print("================================")

                liveness_verified = True

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

    # ---------------------------------------------
    # VERIFIED
    # ---------------------------------------------

    if liveness_verified:

        cv2.putText(
            frame,
            "LIVENESS VERIFIED",
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3
        )

        cv2.putText(
            frame,
            "REAL PERSON DETECTED",
            (30, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    else:

        cv2.putText(
            frame,
            "BLINK ONCE",
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 0),
            2
        )

    cv2.imshow(
        "Liveness Service Test",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()

print()
print("======================================")
print("FINAL RESULT")
print("======================================")

if liveness_verified:
    print("Liveness: VERIFIED ✅")
else:
    print("Liveness: NOT VERIFIED ❌")