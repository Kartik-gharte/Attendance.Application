import cv2
import numpy as np
from insightface.app import FaceAnalysis

# -----------------------------
# Student to compare against
# -----------------------------

student_id = "STU001"

# -----------------------------
# Load InsightFace
# -----------------------------

print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=0, det_size=(640, 640))

print("InsightFace loaded")

# -----------------------------
# Load registered embedding
# -----------------------------

registered_path = f"../../data/face_embeddings/{student_id}.npy"

registered_embedding = np.load(registered_path)

print("Registered embedding loaded")
print("Embedding length:", len(registered_embedding))

# -----------------------------
# Load NEW image
# -----------------------------

image = cv2.imread("test.jpg")

if image is None:
    print("ERROR: test2.jpg could not be opened")
    exit()

print("New image loaded")

# -----------------------------
# Detect face
# -----------------------------

faces = app.get(image)

if len(faces) == 0:
    print("ERROR: No face detected")
    exit()

if len(faces) > 1:
    print("ERROR: More than one face detected")
    exit()

# -----------------------------
# Get new face embedding
# -----------------------------

new_embedding = faces[0].embedding

print("New face detected")
print("New embedding length:", len(new_embedding))

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

print()
print("================================")
print("FACE RECOGNITION RESULT")
print("================================")
print("Student ID:", student_id)
print("Similarity:", similarity)

# -----------------------------
# Decide match
# -----------------------------

threshold = 0.4

if similarity >= threshold:
    print("RESULT: MATCH ✅")
else:
    print("RESULT: UNKNOWN ❌")