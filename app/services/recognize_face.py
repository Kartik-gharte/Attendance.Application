import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.core.logging_config import get_logger

# -----------------------------
# Student to compare against
# -----------------------------

student_id = "STU001"

# -----------------------------
# Load InsightFace
# -----------------------------

logger.info("Loading InsightFace")

logger = get_logger("services.recognize_face")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=0, det_size=(640, 640))

logger.info("InsightFace loaded")

# -----------------------------
# Load registered embedding
# -----------------------------

registered_path = f"../../data/face_embeddings/{student_id}.npy"

registered_embedding = np.load(registered_path)

logger.debug(
    "Registered embedding loaded: length=%d",
    len(registered_embedding),
)

# -----------------------------
# Load NEW image
# -----------------------------

image = cv2.imread("test.jpg")

if image is None:
    logger.error("Source image could not be opened")
    exit()

logger.debug("Source image loaded")

# -----------------------------
# Detect face
# -----------------------------

faces = app.get(image)

if len(faces) == 0:
    logger.error("Recognition aborted: no face detected")
    exit()

if len(faces) > 1:
    logger.error("Recognition aborted: more than one face detected")
    exit()

# -----------------------------
# Get new face embedding
# -----------------------------

new_embedding = faces[0].embedding

logger.debug(
    "Face detected: embedding_length=%d",
    len(new_embedding),
)

# -----------------------------
# Calculate cosine similarity
# -----------------------------

similarity = np.dot(
    registered_embedding,
    new_embedding
) / (
    np.linalg.norm(registered_embedding)
    * np.linalg.norm(new_embedding)
)

logger.info(
    "Face recognition result: student_id=%s similarity=%s",
    student_id,
    similarity,
)

# -----------------------------
# Decide match
# -----------------------------

threshold = 0.4

if similarity >= threshold:
    logger.info("Recognition outcome: match")
else:
    logger.info("Recognition outcome: unknown")