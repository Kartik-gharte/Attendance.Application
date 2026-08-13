import cv2
import mediapipe as mp
import math

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MODEL_PATH = r"C:\AI-Attendance-System\ai-service\models\mediapipe\face_landmarker.task"
IMAGE_PATH = r"C:\AI-Attendance-System\ai-service\app\services\closed_eye.jpeg"

# -----------------------------
# Load MediaPipe
# -----------------------------

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    num_faces=1
)

detector = vision.FaceLandmarker.create_from_options(options)

print("Face Landmarker loaded")


# -----------------------------
# Open image
# -----------------------------

image = cv2.imread(IMAGE_PATH)

if image is None:
    print("ERROR: Could not open image")
    exit()

print("Image opened successfully")


# -----------------------------
# Convert image
# -----------------------------

rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

mp_image = mp.Image(
    image_format=mp.ImageFormat.SRGB,
    data=rgb_image
)


# -----------------------------
# Detect landmarks
# -----------------------------

result = detector.detect(mp_image)

if len(result.face_landmarks) == 0:

    print("No face detected ❌")
    exit()

print("Face detected ✅")

landmarks = result.face_landmarks[0]

print("Number of landmarks:", len(landmarks))


# -----------------------------
# Distance function
# -----------------------------

def distance(point1, point2):

    return math.sqrt(
        (point1.x - point2.x) ** 2 +
        (point1.y - point2.y) ** 2
    )


# -----------------------------
# Eye Aspect Ratio
# -----------------------------

def eye_aspect_ratio(p1, p2, p3, p4, p5, p6):

    vertical_1 = distance(p2, p6)
    vertical_2 = distance(p3, p5)

    horizontal = distance(p1, p4)

    ear = (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)

    return ear


# -----------------------------
# Left eye landmarks
# -----------------------------

left_p1 = landmarks[33]
left_p2 = landmarks[160]
left_p3 = landmarks[158]
left_p4 = landmarks[133]
left_p5 = landmarks[153]
left_p6 = landmarks[144]


# -----------------------------
# Right eye landmarks
# -----------------------------

right_p1 = landmarks[263]
right_p2 = landmarks[387]
right_p3 = landmarks[385]
right_p4 = landmarks[362]
right_p5 = landmarks[380]
right_p6 = landmarks[373]


# -----------------------------
# Calculate EAR
# -----------------------------

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
    left_ear + right_ear
) / 2


# -----------------------------
# Print result
# -----------------------------

print("\n==============================")
print("EYE ASPECT RATIO")
print("==============================")

print("Left EAR :", left_ear)
print("Right EAR:", right_ear)
print("Average EAR:", average_ear)