import cv2
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis


class FaceRecognitionService:

    def __init__(self):

        print("Loading InsightFace model...")

        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        self.app.prepare(
            ctx_id=0,
            det_size=(640, 640)
        )

        print("InsightFace model loaded")

    # =========================================================
    # GET EMBEDDING FROM IMAGE FILE
    # =========================================================

    def get_embedding(self, image_path):

        image = cv2.imread(image_path)

        if image is None:
            raise ValueError("Could not open image")

        return self.get_embedding_from_frame(image)

    # =========================================================
    # GET EMBEDDING FROM CAMERA FRAME
    # =========================================================

    def get_embedding_from_frame(self, frame):

        if frame is None:
            raise ValueError("Invalid camera frame")

        faces = self.app.get(frame)

        if len(faces) == 0:
            raise ValueError("No face detected")

        if len(faces) > 1:
            raise ValueError("More than one face detected")

        return faces[0].embedding

    # =========================================================
    # COMPARE FACES
    # =========================================================

    def compare_faces(
        self,
        registered_embedding,
        new_embedding
    ):

        similarity = np.dot(
            registered_embedding,
            new_embedding
        ) / (
            np.linalg.norm(registered_embedding)
            * np.linalg.norm(new_embedding)
        )

        return float(similarity)

    # =========================================================
    # LOAD REGISTERED EMBEDDING
    # =========================================================

    def load_registered_embedding(self, student_id):

        base_dir = Path(__file__).resolve().parents[2]

        registered_path = (
            base_dir
            / "data"
            / "face_embeddings"
            / f"{student_id}.npy"
        )

        if not registered_path.exists():

            raise FileNotFoundError(
                f"Registered face not found for student: {student_id}"
            )

        return np.load(str(registered_path))

    # =========================================================
    # RECOGNIZE IMAGE FILE
    # =========================================================

    def recognize(self, image_path, student_id):

        new_embedding = self.get_embedding(
            image_path
        )

        registered_embedding = (
            self.load_registered_embedding(student_id)
        )

        similarity = self.compare_faces(
            registered_embedding,
            new_embedding
        )

        threshold = 0.40

        if similarity >= threshold:
            result = "MATCH"
        else:
            result = "UNKNOWN"

        return {
            "student_id": student_id,
            "similarity": similarity,
            "result": result
        }

    # =========================================================
    # RECOGNIZE LIVE CAMERA FRAME
    # =========================================================

    def recognize_frame(self, frame, student_id):

        new_embedding = self.get_embedding_from_frame(
            frame
        )

        registered_embedding = (
            self.load_registered_embedding(student_id)
        )

        similarity = self.compare_faces(
            registered_embedding,
            new_embedding
        )

        threshold = 0.40

        if similarity >= threshold:
            result = "MATCH"
        else:
            result = "UNKNOWN"

        return {
            "student_id": student_id,
            "similarity": similarity,
            "result": result
        }