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

        # Slightly lower detection threshold so
        # faces are easier to detect in webcam frames.
        try:
            self.app.det_model.det_thresh = 0.35
        except Exception:
            pass

        # Face similarity threshold
        self.threshold = 0.40

        print("InsightFace model loaded")
        print("Face Recognition Service ready")

    # =========================================================
    # GET EMBEDDING FROM IMAGE FILE
    # =========================================================

    def get_embedding(self, image_path):

        image = cv2.imread(
            str(image_path)
        )

        if image is None:

            raise ValueError(
                "Could not open image"
            )

        print(
            "Image loaded:",
            image.shape
        )

        return self.get_embedding_from_frame(
            image
        )

    # =========================================================
    # RUN INSIGHTFACE DETECTION
    # =========================================================

    def detect_faces(
        self,
        frame,
        attempt_name,
        det_size=(640, 640)
    ):

        print(
            f"Trying detection: {attempt_name}"
        )

        try:

            # Change detector size temporarily
            self.app.det_model.input_size = det_size

            faces = self.app.get(
                frame
            )

            print(
                f"Faces detected ({attempt_name}):",
                len(faces)
            )

            return faces

        except Exception as error:

            print(
                f"Detection error ({attempt_name}):",
                str(error)
            )

            return []

    # =========================================================
    # GET SINGLE FACE EMBEDDING
    # =========================================================

    def extract_single_face(
        self,
        faces
    ):

        if len(faces) == 0:

            return None

        if len(faces) > 1:

            raise ValueError(
                "More than one face detected"
            )

        return faces[0].embedding

    # =========================================================
    # GET EMBEDDING FROM CAMERA FRAME
    # =========================================================

    def get_embedding_from_frame(
        self,
        frame
    ):

        if frame is None:

            raise ValueError(
                "Invalid camera frame"
            )

        if not isinstance(
            frame,
            np.ndarray
        ):

            raise ValueError(
                "Camera frame is not a valid image"
            )

        if frame.size == 0:

            raise ValueError(
                "Camera frame is empty"
            )

        print()
        print("======================================")
        print("INSIGHTFACE FRAME DETECTION")
        print("======================================")

        print(
            "Original frame shape:",
            frame.shape
        )

        # -----------------------------------------------------
        # Make sure image is uint8
        # -----------------------------------------------------

        if frame.dtype != np.uint8:

            frame = frame.astype(
                np.uint8
            )

        # -----------------------------------------------------
        # Make sure frame has 3 channels
        # -----------------------------------------------------

        if len(frame.shape) != 3:

            raise ValueError(
                "Camera frame must have 3 color channels"
            )

        if frame.shape[2] != 3:

            raise ValueError(
                "Camera frame must be a BGR image"
            )

        # =====================================================
        # ATTEMPT 1
        # ORIGINAL FRAME
        # =====================================================

        faces = self.detect_faces(
            frame,
            "original",
            det_size=(640, 640)
        )

        embedding = self.extract_single_face(
            faces
        )

        if embedding is not None:

            print(
                "Face successfully detected on original frame"
            )

            return embedding

        # =====================================================
        # ATTEMPT 2
        # UPSCALE 2X
        # =====================================================

        height, width = frame.shape[:2]

        upscale_factor = 2

        upscaled = cv2.resize(
            frame,
            (
                width * upscale_factor,
                height * upscale_factor
            ),
            interpolation=cv2.INTER_CUBIC
        )

        print(
            "Upscaled frame shape:",
            upscaled.shape
        )

        faces = self.detect_faces(
            upscaled,
            "2x upscaled",
            det_size=(640, 640)
        )

        embedding = self.extract_single_face(
            faces
        )

        if embedding is not None:

            print(
                "Face successfully detected on 2x upscaled frame"
            )

            return embedding

        # =====================================================
        # ATTEMPT 3
        # LARGE DETECTION SIZE
        # =====================================================

        faces = self.detect_faces(
            upscaled,
            "2x upscaled + large detector",
            det_size=(1024, 1024)
        )

        embedding = self.extract_single_face(
            faces
        )

        if embedding is not None:

            print(
                "Face successfully detected with large detector"
            )

            return embedding

        # =====================================================
        # ATTEMPT 4
        # CONTRAST ENHANCEMENT
        # =====================================================

        print(
            "Creating contrast-enhanced frame..."
        )

        lab = cv2.cvtColor(
            upscaled,
            cv2.COLOR_BGR2LAB
        )

        l_channel, a_channel, b_channel = cv2.split(
            lab
        )

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        enhanced_l = clahe.apply(
            l_channel
        )

        enhanced_lab = cv2.merge(
            (
                enhanced_l,
                a_channel,
                b_channel
            )
        )

        enhanced = cv2.cvtColor(
            enhanced_lab,
            cv2.COLOR_LAB2BGR
        )

        faces = self.detect_faces(
            enhanced,
            "contrast enhanced",
            det_size=(1024, 1024)
        )

        embedding = self.extract_single_face(
            faces
        )

        if embedding is not None:

            print(
                "Face successfully detected after contrast enhancement"
            )

            return embedding

        # =====================================================
        # ATTEMPT 5
        # SHARPEN IMAGE
        # =====================================================

        print(
            "Creating sharpened frame..."
        )

        gaussian = cv2.GaussianBlur(
            enhanced,
            (0, 0),
            3
        )

        sharpened = cv2.addWeighted(
            enhanced,
            1.5,
            gaussian,
            -0.5,
            0
        )

        faces = self.detect_faces(
            sharpened,
            "sharpened",
            det_size=(1024, 1024)
        )

        embedding = self.extract_single_face(
            faces
        )

        if embedding is not None:

            print(
                "Face successfully detected after sharpening"
            )

            return embedding

        # =====================================================
        # NO FACE FOUND
        # =====================================================

        print()
        print("======================================")
        print("NO FACE DETECTED")
        print("======================================")

        print(
            "Original width:",
            width
        )

        print(
            "Original height:",
            height
        )

        print(
            "Tried:",
            "original, 2x upscale, large detector,"
            " contrast enhancement, sharpening"
        )

        raise ValueError(
            "No face detected by InsightFace"
        )

    # =========================================================
    # COMPARE TWO FACE EMBEDDINGS
    # =========================================================

    def compare_faces(
        self,
        registered_embedding,
        new_embedding
    ):

        registered_embedding = np.asarray(
            registered_embedding,
            dtype=np.float32
        )

        new_embedding = np.asarray(
            new_embedding,
            dtype=np.float32
        )

        registered_norm = np.linalg.norm(
            registered_embedding
        )

        new_norm = np.linalg.norm(
            new_embedding
        )

        if registered_norm == 0:

            raise ValueError(
                "Registered embedding has zero magnitude"
            )

        if new_norm == 0:

            raise ValueError(
                "New embedding has zero magnitude"
            )

        similarity = np.dot(
            registered_embedding,
            new_embedding
        ) / (
            registered_norm *
            new_norm
        )

        return float(
            similarity
        )

    # =========================================================
    # LOAD REGISTERED EMBEDDING
    # =========================================================

    def load_registered_embedding(
        self,
        student_id
    ):

        base_dir = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        registered_path = (
            base_dir
            / "data"
            / "face_embeddings"
            / f"{student_id}.npy"
        )

        if not registered_path.exists():

            raise FileNotFoundError(
                "Registered face not found "
                f"for student: {student_id}"
            )

        embedding = np.load(
            str(registered_path)
        )

        if embedding.size == 0:

            raise ValueError(
                "Registered embedding is empty"
            )

        print(
            "Registered embedding loaded:",
            student_id
        )

        print(
            "Embedding shape:",
            embedding.shape
        )

        return embedding

    # =========================================================
    # CREATE RECOGNITION RESULT
    # =========================================================

    def create_recognition_result(
        self,
        student_id,
        similarity
    ):

        result = (
            "MATCH"
            if similarity >= self.threshold
            else "UNKNOWN"
        )

        return {
            "student_id": student_id,
            "similarity": similarity,
            "threshold": self.threshold,
            "result": result
        }

    # =========================================================
    # RECOGNIZE IMAGE FILE
    # =========================================================

    def recognize(
        self,
        image_path,
        student_id
    ):

        print()
        print("======================================")
        print("FACE RECOGNITION")
        print("======================================")

        print(
            "Recognizing image:",
            image_path
        )

        new_embedding = self.get_embedding(
            image_path
        )

        registered_embedding = (
            self.load_registered_embedding(
                student_id
            )
        )

        similarity = self.compare_faces(
            registered_embedding,
            new_embedding
        )

        print(
            "Face similarity:",
            similarity
        )

        print(
            "Face threshold:",
            self.threshold
        )

        return self.create_recognition_result(
            student_id,
            similarity
        )

    # =========================================================
    # RECOGNIZE LIVE CAMERA FRAME
    # =========================================================

    def recognize_frame(
        self,
        frame,
        student_id
    ):

        print()
        print("======================================")
        print("LIVE FACE RECOGNITION")
        print("======================================")

        new_embedding = (
            self.get_embedding_from_frame(
                frame
            )
        )

        registered_embedding = (
            self.load_registered_embedding(
                student_id
            )
        )

        similarity = self.compare_faces(
            registered_embedding,
            new_embedding
        )

        print(
            "Student ID:",
            student_id
        )

        print(
            "Similarity:",
            similarity
        )

        print(
            "Threshold:",
            self.threshold
        )

        return self.create_recognition_result(
            student_id,
            similarity
        )