import argparse
import cv2
import os
import sys
import numpy as np
from pathlib import Path

from insightface.app import FaceAnalysis

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger("services.register_face")

DEFAULT_EMBEDDING_DIR = get_settings().embedding_dir


def register_face(student_id: str, image_path: str, output_dir: str | None = None,
                  overwrite: bool = False, dry_run: bool = False) -> str | None:
    """Register a student's face embedding.
    
    Args:
        student_id: Student identifier (validated against pattern)
        image_path: Path to source image
        output_dir: Output directory for .npy file (defaults to configured embedding dir)
        overwrite: Whether to overwrite existing embedding
        dry_run: If True, validate everything without writing
    
    Returns:
        Path to saved .npy file, or None on failure
    """
    # Validate student identifier
    import re
    pattern = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
    if not pattern.fullmatch(student_id):
        logger.error("Invalid student identifier rejected: %s", student_id)
        return None
    
    # Load source image
    image = cv2.imread(image_path)
    if image is None:
        logger.error("Source image could not be opened: %s", image_path)
        return None
    
    # Detect faces
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    faces = app.get(image)
    if len(faces) == 0:
        logger.error("Enrollment aborted: no face detected in the source image")
        return None
    if len(faces) > 1:
        logger.error("Enrollment aborted: more than one face detected in the source image")
        return None
    
    embedding = faces[0].embedding
    
    # Determine output path
    if output_dir is None:
        output_dir = str(DEFAULT_EMBEDDING_DIR)
    
    output_path = Path(output_dir) / f"{student_id}.npy"
    output_path = output_path.resolve()
    
    # Validate path containment
    embedding_dir = Path(DEFAULT_EMBEDDING_DIR).resolve()
    try:
        output_path.relative_to(embedding_dir)
    except ValueError:
        logger.error("Enrollment aborted: output path escapes the embedding directory")
        return None
    
    # Check for existing embedding
    if output_path.exists() and not overwrite:
        logger.error("Enrollment refused: an embedding already exists for this student")
        return None
    
    if dry_run:
        logger.info("Dry run: would write the embedding for student_id=%s", student_id)
        logger.info("Dry run: embedding vector length=%d", len(embedding))
        return None
    
    # Save embedding
    np.save(str(output_path), embedding)
    logger.info("Face registration completed: student_id=%s", student_id)
    logger.info("Registered student identifier: %s", student_id)
    logger.info("Embedding stored in the configured embedding directory")
    return str(output_path)


def main():
    """CLI entry point for face registration."""
    parser = argparse.ArgumentParser(description='Register a student face embedding')
    parser.add_argument('--student-id', required=True,
                        help='Student identifier (e.g., STU001)')
    parser.add_argument('--image', required=True,
                        help='Path to source image file')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory for .npy file')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing embedding')
    parser.add_argument('--dry-run', action='store_true',
                        help='Validate without writing')
    
    args = parser.parse_args()
    
    register_face(
        student_id=args.student_id,
        image_path=args.image,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
