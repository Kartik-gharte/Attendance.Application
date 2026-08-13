import cv2
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

IMAGE_PATH = (
    BASE_DIR
    / "app"
    / "services"
    / "test.jpg"
)

EMBEDDING_PATH = (
    BASE_DIR
    / "data"
    / "face_embeddings"
    / "STU001.npy"
)


# =========================================================
# CHECK FILES
# =========================================================

print("Image:")
print(IMAGE_PATH)

print()

print("Registered embedding:")
print(EMBEDDING_PATH)

print()

if not IMAGE_PATH.exists():

    print("ERROR: Test image not found")
    exit()

if not EMBEDDING_PATH.exists():

    print("ERROR: Registered embedding not found")
    exit()


# =========================================================
# LOAD REGISTERED EMBEDDING
# =========================================================

registered_embedding = np.load(
    str(EMBEDDING_PATH)
)

print(
    "Registered embedding length:",
    len(registered_embedding)
)


# =========================================================
# LOAD INSIGHTFACE
# =========================================================

print()
print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("InsightFace loaded")


# =========================================================
# LOAD IMAGE
# =========================================================

image = cv2.imread(
    str(IMAGE_PATH)
)

if image is None:

    print("ERROR: Image could not be opened")
    exit()


# =========================================================
# DETECT FACE
# =========================================================

faces = app.get(image)


if len(faces) == 0:

    print("ERROR: No face detected")
    exit()


if len(faces) > 1:

    print(
        "ERROR: More than one face detected"
    )

    exit()


print()
print("Face detected successfully")


# =========================================================
# GET NEW EMBEDDING
# =========================================================

new_embedding = faces[0].embedding

print(
    "New embedding length:",
    len(new_embedding)
)


# =========================================================
# CALCULATE COSINE SIMILARITY
# =========================================================

similarity = np.dot(
    registered_embedding,
    new_embedding
) / (
    np.linalg.norm(
        registered_embedding
    )
    *
    np.linalg.norm(
        new_embedding
    )
)


similarity = float(similarity)


# =========================================================
# RESULT
# =========================================================

threshold = 0.40

print()
print("======================================")
print("FACE RECOGNITION TEST")
print("======================================")

print(
    "Student ID:",
    "STU001"
)

print(
    "Similarity:",
    similarity
)

print(
    "Threshold:",
    threshold
)

if similarity >= threshold:

    print(
        "Result: MATCH"
    )

else:

    print(
        "Result: UNKNOWN"
    )

print("======================================")