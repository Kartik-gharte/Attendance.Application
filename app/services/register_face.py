import cv2
import os
import numpy as np
from insightface.app import FaceAnalysis

# -----------------------------
# Student information
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
# Load student's image
# -----------------------------

image = cv2.imread("test.jpg")

if image is None:
    print("ERROR: Image could not be opened")
    exit()

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
# Get embedding
# -----------------------------

embedding = faces[0].embedding

print("Face detected")
print("Embedding length:", len(embedding))

# -----------------------------
# Create registration folder
# -----------------------------

os.makedirs("../../data/face_embeddings", exist_ok=True)

# -----------------------------
# Save embedding
# -----------------------------

file_path = f"../../data/face_embeddings/{student_id}.npy"

np.save(file_path, embedding)

print("Face registration successful!")
print("Student ID:", student_id)
print("Saved to:", file_path)