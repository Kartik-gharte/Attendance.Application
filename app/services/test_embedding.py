import cv2
from insightface.app import FaceAnalysis

print("Starting InsightFace...")

# Create InsightFace model
app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=0, det_size=(640, 640))

print("InsightFace model loaded")

# Load image
image = cv2.imread("test.jpg")

if image is None:
    print("ERROR: Image could not be opened")
    exit()

print("Image loaded")

# Detect face and create embedding
faces = app.get(image)

print("Number of faces:", len(faces))

if len(faces) == 0:
    print("No face detected")
else:
    face = faces[0]

    print("Face detected!")
    print("Embedding length:", len(face.embedding))
    print("Embedding created successfully!")

    print("First 5 values:")
    print(face.embedding[:5])