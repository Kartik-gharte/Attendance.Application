import cv2
from pathlib import Path
from insightface.app import FaceAnalysis


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

IMAGE_PATH = (
    BASE_DIR
    / "tests"
    / "fixtures"
    / "test.jpg"
)


# =========================================================
# START INSIGHTFACE
# =========================================================

print("Starting InsightFace...")


# Create InsightFace model

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)


print("InsightFace model loaded")


# =========================================================
# LOAD IMAGE
# =========================================================

print()
print("Image path:")
print(IMAGE_PATH)


image = cv2.imread(
    str(IMAGE_PATH)
)


if image is None:

    print(
        "ERROR: Image could not be opened"
    )

    exit()


print("Image loaded")


# =========================================================
# DETECT FACE AND CREATE EMBEDDING
# =========================================================

faces = app.get(
    image
)


print(
    "Number of faces:",
    len(faces)
)


if len(faces) == 0:

    print(
        "No face detected"
    )

else:

    face = faces[0]

    print()
    print(
        "Face detected!"
    )

    print(
        "Embedding length:",
        len(face.embedding)
    )

    print(
        "Embedding created successfully!"
    )

    print()
    print(
        "First 5 values:"
    )

    print(
        face.embedding[:5]
    )