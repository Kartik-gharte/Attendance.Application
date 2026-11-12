import cv2
import mediapipe as mp
import os
from pathlib import Path


# =========================================================
# PATHS
#
# Override with FACE_DETECTOR_IMAGE_PATH and
# MEDIAPIPE_FACE_LANDMARKER_MODEL.
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

IMAGE_PATH = Path(
    os.getenv(
        "FACE_DETECTOR_IMAGE_PATH",
        str(
            BASE_DIR
            / "tests"
            / "fixtures"
            / "test.jpg"
        ),
    )
)

MODEL_PATH = Path(
    os.getenv(
        "MEDIAPIPE_FACE_LANDMARKER_MODEL",
        str(
            BASE_DIR
            / "models"
            / "mediapipe"
            / "blaze_face_short_range.tflite"
        ),
    )
)


# =========================================================
# CHECK PATHS
# =========================================================

print("Image path:")
print(IMAGE_PATH)

print()

print("Model path:")
print(MODEL_PATH)

print()


if not IMAGE_PATH.exists():

    print(
        "ERROR: Test image does not exist"
    )

    exit()


if not MODEL_PATH.exists():

    print(
        "ERROR: MediaPipe model does not exist"
    )

    exit()


# =========================================================
# LOAD IMAGE
# =========================================================

image = cv2.imread(
    str(IMAGE_PATH)
)


if image is None:

    print(
        "ERROR: Image could not be opened"
    )

    exit()


print(
    "Image opened successfully"
)


# =========================================================
# MEDIAPIPE FACE DETECTOR
# =========================================================

BaseOptions = (
    mp.tasks.BaseOptions
)

FaceDetector = (
    mp.tasks.vision.FaceDetector
)

FaceDetectorOptions = (
    mp.tasks.vision.FaceDetectorOptions
)

VisionRunningMode = (
    mp.tasks.vision.RunningMode
)


options = FaceDetectorOptions(

    base_options=BaseOptions(
        model_asset_path=str(
            MODEL_PATH
        )
    ),

    running_mode=(
        VisionRunningMode.IMAGE
    ),

    min_detection_confidence=0.5

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
# DETECT FACE
# =========================================================

with FaceDetector.create_from_options(
    options
) as detector:

    result = detector.detect(
        mp_image
    )


# =========================================================
# RESULT
# =========================================================

if result.detections:

    print()
    print(
        "======================================"
    )

    print(
        "FACE DETECTION SUCCESS"
    )

    print(
        "======================================"
    )

    print(
        "Number of faces:",
        len(result.detections)
    )


    for i, detection in enumerate(
        result.detections
    ):

        confidence = (
            detection.categories[0].score
        )

        print(
            f"Face {i + 1} confidence:",
            confidence
        )


else:

    print()
    print(
        "======================================"
    )

    print(
        "NO FACE DETECTED"
    )

    print(
        "======================================"
    )