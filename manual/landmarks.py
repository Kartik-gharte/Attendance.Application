import cv2
import mediapipe as mp
import math
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "mediapipe"
    / "face_landmarker.task"
)

IMAGE_PATH = (
    BASE_DIR
    / "tests"
    / "fixtures"
    / "closed_eye.jpeg"
)


# =========================================================
# CHECK PATHS
# =========================================================

print("Model path:")
print(MODEL_PATH)

print()

print("Image path:")
print(IMAGE_PATH)

print()


if not MODEL_PATH.exists():

    print(
        "ERROR: Face Landmarker model does not exist"
    )

    exit()


if not IMAGE_PATH.exists():

    print(
        "ERROR: Test image does not exist"
    )

    exit()


# =========================================================
# LOAD MEDIAPIPE
# =========================================================

base_options = python.BaseOptions(
    model_asset_path=str(
        MODEL_PATH
    )
)


options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    num_faces=1
)


detector = (
    vision.FaceLandmarker.create_from_options(
        options
    )
)


print(
    "Face Landmarker loaded"
)


# =========================================================
# OPEN IMAGE
# =========================================================

image = cv2.imread(
    str(IMAGE_PATH)
)


if image is None:

    print(
        "ERROR: Could not open image"
    )

    exit()


print(
    "Image opened successfully"
)


# =========================================================
# CONVERT IMAGE
# =========================================================

rgb_image = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2RGB
)


mp_image = mp.Image(
    image_format=(
        mp.ImageFormat.SRGB
    ),
    data=rgb_image
)


# =========================================================
# DETECT LANDMARKS
# =========================================================

result = detector.detect(
    mp_image
)


if len(result.face_landmarks) == 0:

    print(
        "No face detected"
    )

    exit()


print(
    "Face detected"
)


landmarks = (
    result.face_landmarks[0]
)


print(
    "Number of landmarks:",
    len(landmarks)
)


# =========================================================
# DISTANCE FUNCTION
# =========================================================

def distance(
    point1,
    point2
):

    return math.sqrt(

        (
            point1.x -
            point2.x
        ) ** 2

        +

        (
            point1.y -
            point2.y
        ) ** 2

    )


# =========================================================
# EYE ASPECT RATIO
# =========================================================

def eye_aspect_ratio(
    p1,
    p2,
    p3,
    p4,
    p5,
    p6
):

    vertical_1 = distance(
        p2,
        p6
    )

    vertical_2 = distance(
        p3,
        p5
    )

    horizontal = distance(
        p1,
        p4
    )

    ear = (
        vertical_1 +
        vertical_2
    ) / (
        2.0 *
        horizontal
    )

    return ear


# =========================================================
# LEFT EYE LANDMARKS
# =========================================================

left_p1 = landmarks[33]
left_p2 = landmarks[160]
left_p3 = landmarks[158]
left_p4 = landmarks[133]
left_p5 = landmarks[153]
left_p6 = landmarks[144]


# =========================================================
# RIGHT EYE LANDMARKS
# =========================================================

right_p1 = landmarks[263]
right_p2 = landmarks[387]
right_p3 = landmarks[385]
right_p4 = landmarks[362]
right_p5 = landmarks[380]
right_p6 = landmarks[373]


# =========================================================
# CALCULATE EAR
# =========================================================

left_ear = eye_aspect_ratio(
    left_p1,
    left_p2,
    left_p3,
    left_p4,
    left_p5,
    left_p6
)


right_ear = eye_aspect_ratio(
    right_p1,
    right_p2,
    right_p3,
    right_p4,
    right_p5,
    right_p6
)


average_ear = (
    left_ear +
    right_ear
) / 2


# =========================================================
# PRINT RESULT
# =========================================================

print()
print(
    "=============================="
)

print(
    "EYE ASPECT RATIO"
)

print(
    "=============================="
)

print(
    "Left EAR :",
    left_ear
)

print(
    "Right EAR:",
    right_ear
)

print(
    "Average EAR:",
    average_ear
)