import cv2
import mediapipe as mp
import math
import numpy as np
import insightface

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = r"C:\AI-Attendance-System\ai-service\models\mediapipe\face_landmarker.task"

REGISTERED_EMBEDDING = r"C:\AI-Attendance-System\ai-service\data\face_embeddings\STU001.npy"

STUDENT_ID = "STU001"

# Liveness threshold
EAR_THRESHOLD = 0.10

# Face recognition threshold
RECOGNITION_THRESHOLD = 0.40


# ============================================================
# LOAD MEDIAPIPE FACE LANDMARKER
# ============================================================

print("Starting MediaPipe...")

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    num_faces=1
)

landmarker = vision.FaceLandmarker.create_from_options(
    options
)

print("MediaPipe Face Landmarker loaded")


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print("Starting InsightFace...")

face_app = insightface.app.FaceAnalysis(
    name="buffalo_l"
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("InsightFace loaded")


# ============================================================
# LOAD REGISTERED EMBEDDING
# ============================================================

print("Loading registered face...")

registered_embedding = np.load(
    REGISTERED_EMBEDDING
)

print("Registered embedding loaded")
print("Embedding length:", len(registered_embedding))


# ============================================================
# DISTANCE BETWEEN LANDMARKS
# ============================================================

def distance(p1, p2):

    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )


# ============================================================
# CALCULATE EYE ASPECT RATIO
# ============================================================

def calculate_ear(landmarks):

    # --------------------------------------------------------
    # LEFT EYE
    # --------------------------------------------------------

    left_p1 = landmarks[33]
    left_p2 = landmarks[160]
    left_p3 = landmarks[158]
    left_p4 = landmarks[133]
    left_p5 = landmarks[153]
    left_p6 = landmarks[144]

    left_ear = (
        distance(left_p2, left_p6)
        +
        distance(left_p3, left_p5)
    ) / (
        2 * distance(left_p1, left_p4)
    )


    # --------------------------------------------------------
    # RIGHT EYE
    # --------------------------------------------------------

    right_p1 = landmarks[263]
    right_p2 = landmarks[387]
    right_p3 = landmarks[385]
    right_p4 = landmarks[362]
    right_p5 = landmarks[380]
    right_p6 = landmarks[373]

    right_ear = (
        distance(right_p2, right_p6)
        +
        distance(right_p3, right_p5)
    ) / (
        2 * distance(right_p1, right_p4)
    )


    # Average EAR

    return (
        left_ear + right_ear
    ) / 2


# ============================================================
# OPEN CAMERA
# ============================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("ERROR: Could not open camera")

    exit()


print()
print("Camera opened")

print()
print("======================================")
print("     AI ATTENDANCE VERIFICATION")
print("======================================")

print()
print("Look at the camera.")
print("Blink once.")
print("After liveness verification,")
print("your face will be recognized.")

print()
print("Press Q to quit.")

print()


# ============================================================
# LIVENESS VARIABLES
# ============================================================

eyes_closed = False

liveness_verified = False

recognition_completed = False


# ============================================================
# MAIN CAMERA LOOP
# ============================================================

while True:

    # --------------------------------------------------------
    # READ CAMERA FRAME
    # --------------------------------------------------------

    success, frame = camera.read()

    if not success:

        print("ERROR: Could not read camera")

        break


    # ========================================================
    # LIVENESS PHASE
    # ========================================================

    if not liveness_verified:

        # ----------------------------------------------------
        # Convert BGR → RGB
        # ----------------------------------------------------

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        # ----------------------------------------------------
        # Create MediaPipe image
        # ----------------------------------------------------

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )


        # ----------------------------------------------------
        # Detect face landmarks
        # ----------------------------------------------------

        result = landmarker.detect(
            mp_image
        )


        # ----------------------------------------------------
        # FACE FOUND
        # ----------------------------------------------------

        if len(result.face_landmarks) > 0:

            landmarks = result.face_landmarks[0]


            # Calculate EAR

            ear = calculate_ear(
                landmarks
            )


            # Show EAR

            cv2.putText(
                frame,
                f"EAR: {ear:.3f}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )


            # ------------------------------------------------
            # EYES CLOSED
            # ------------------------------------------------

            if ear < EAR_THRESHOLD:

                if not eyes_closed:

                    print("Eyes closed")

                eyes_closed = True

                cv2.putText(
                    frame,
                    "Eyes Closed",
                    (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 255),
                    2
                )


            # ------------------------------------------------
            # EYES OPEN
            # ------------------------------------------------

            else:

                # If eyes were closed and are now open,
                # one complete blink has happened.

                if eyes_closed:

                    print()
                    print("================================")
                    print("BLINK DETECTED! ✅")
                    print("================================")

                    liveness_verified = True

                    eyes_closed = False

                    print()
                    print("LIVENESS VERIFIED! ✅")
                    print("Starting face recognition...")

                else:

                    cv2.putText(
                        frame,
                        "BLINK ONCE",
                        (30, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 0),
                        2
                    )


        # ----------------------------------------------------
        # NO FACE
        # ----------------------------------------------------

        else:

            cv2.putText(
                frame,
                "NO FACE",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )


    # ========================================================
    # FACE RECOGNITION PHASE
    # ========================================================

    else:

        # ----------------------------------------------------
        # Show liveness status
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "LIVENESS VERIFIED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )


        # ----------------------------------------------------
        # Detect face using InsightFace
        # ----------------------------------------------------

        faces = face_app.get(
            frame
        )


        # ----------------------------------------------------
        # FACE FOUND
        # ----------------------------------------------------

        if len(faces) > 0:

            face = faces[0]


            # ------------------------------------------------
            # Get new face embedding
            # ------------------------------------------------

            new_embedding = face.embedding


            # ------------------------------------------------
            # Normalize registered embedding
            # ------------------------------------------------

            registered_normalized = (
                registered_embedding /
                np.linalg.norm(
                    registered_embedding
                )
            )


            # ------------------------------------------------
            # Normalize new embedding
            # ------------------------------------------------

            new_normalized = (
                new_embedding /
                np.linalg.norm(
                    new_embedding
                )
            )


            # ------------------------------------------------
            # Calculate cosine similarity
            # ------------------------------------------------

            similarity = np.dot(
                registered_normalized,
                new_normalized
            )


            print()
            print("==============================")
            print("FACE RECOGNITION")
            print("==============================")

            print(
                f"Student ID: {STUDENT_ID}"
            )

            print(
                f"Similarity: {similarity:.4f}"
            )


            # =================================================
            # MATCH
            # =================================================

            if similarity >= RECOGNITION_THRESHOLD:

                print(
                    "RESULT: MATCH ✅"
                )

                print(
                    "ATTENDANCE VERIFICATION SUCCESSFUL ✅"
                )


                # ---------------------------------------------
                # Display result
                # ---------------------------------------------

                cv2.putText(
                    frame,
                    f"FACE MATCH - {STUDENT_ID}",
                    (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    frame,
                    f"Similarity: {similarity:.3f}",
                    (30, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    frame,
                    "ATTENDANCE VERIFIED",
                    (30, 200),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2
                )


                # ---------------------------------------------
                # Show final frame
                # ---------------------------------------------

                cv2.imshow(
                    "AI Attendance Verification",
                    frame
                )


                # Keep result visible for 2 seconds

                cv2.waitKey(2000)


                # ---------------------------------------------
                # Final terminal result
                # ---------------------------------------------

                print()
                print("================================")
                print("        FINAL RESULT")
                print("================================")

                print(
                    f"Student ID: {STUDENT_ID}"
                )

                print(
                    "Liveness: VERIFIED ✅"
                )

                print(
                    "Face: MATCH ✅"
                )

                print(
                    "Attendance: VERIFIED ✅"
                )

                print(
                    "================================"
                )


                recognition_completed = True

                break


            # =================================================
            # UNKNOWN FACE
            # =================================================

            else:

                print(
                    "RESULT: UNKNOWN ❌"
                )


                cv2.putText(
                    frame,
                    "UNKNOWN FACE",
                    (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )


                cv2.putText(
                    frame,
                    f"Similarity: {similarity:.3f}",
                    (30, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )


        # ----------------------------------------------------
        # NO FACE FOUND
        # ----------------------------------------------------

        else:

            print(
                "No face detected by InsightFace"
            )


            cv2.putText(
                frame,
                "NO FACE",
                (30, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )


    # ========================================================
    # DISPLAY CAMERA
    # ========================================================

    cv2.imshow(
        "AI Attendance Verification",
        frame
    )


    # ========================================================
    # QUIT WITH Q
    # ========================================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()


# ============================================================
# PROGRAM FINISHED
# ============================================================

print()

if recognition_completed:

    print("AI verification completed successfully ✅")

else:

    print("AI verification stopped.")

print()