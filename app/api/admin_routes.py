"""Admin routes for enrolling a face embedding.

Enrollment writes a biometric template. It is deliberately kept off the
student-facing API: only an administrator can enroll, and every enrollment
is recorded in the audit trail with the operator and the consent
reference.

The image is written to a temporary file, passed to the enrollment
service, and removed afterwards. The image itself is never stored.
"""

import os
import tempfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.auth.dependencies import require_admin
from app.auth.models import UserPrincipal
from app.core.logging_config import get_logger
from app.services.enrollment_audit import AuditError, record_enrollment
from app.services.register_face import EnrollmentError, register_face
from app.services.validation import (
    INVALID_IMAGE,
    validate_student_id,
)


router = APIRouter()

logger = get_logger("api.admin")


# =========================================================
# ENROLL A FACE
# =========================================================

@router.post("/admin/enrollments")
async def enroll_face(
    request: Request,
    student_id: str = Form(...),
    consent_reference: str = Form(...),
    image: UploadFile = File(...),
    overwrite: bool = Form(False),
    current_user: UserPrincipal = Depends(require_admin),
):
    """Enroll a face embedding for a student.

    Only an administrator may enroll. The enrollment is recorded in the
    audit trail with the operator and the consent reference. The source
    image is not stored.
    """

    settings = request.app.state.settings

    try:
        validated_student_id = validate_student_id(student_id)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student identifier",
        ) from None

    if not consent_reference or not consent_reference.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consent reference is required",
        )

    image_bytes = await image.read(settings.max_upload_size_bytes + 1)

    if len(image_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image exceeds maximum allowed size",
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_IMAGE,
        )

    suffix = os.path.splitext(image.filename or ".jpg")[1] or ".jpg"

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_file.write(image_bytes)

            temp_path = temp_file.name

        result = register_face(
            student_id=validated_student_id,
            image_path=temp_path,
            overwrite=overwrite,
            operator=current_user.username,
            consent_reference=consent_reference,
            database_path=settings.database_path,
            audit=True,
            embedding_dir=settings.embedding_dir,
        )

    finally:

        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    if result is None:
        # The enrollment service logs the reason. The client is told that
        # the enrollment was refused without being told the internal
        # detail.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The enrollment was refused",
        )

    logger.info(
        "Enrollment completed: student_id=%s operator=%s",
        validated_student_id,
        current_user.username,
    )

    return {
        "status": "success",
        "message": "Face enrollment completed",
        "student_id": validated_student_id,
        "operator": current_user.username,
        "consent_reference": consent_reference,
    }


# =========================================================
# LIST THE AUDIT TRAIL
# =========================================================

@router.get("/admin/enrollments")
def list_enrollments(
    request: Request,
    student_id: str | None = None,
    limit: int = 50,
    current_user: UserPrincipal = Depends(require_admin),
):
    """Return the enrollment audit entries, most recent first.

    The entries hold no biometric material: no image, no embedding, and no
    face crop.
    """

    from app.services.enrollment_audit import list_enrollments as _list

    settings = request.app.state.settings

    try:

        entries = _list(
            student_id=student_id,
            database_path=settings.database_path,
            limit=max(1, min(int(limit), 500)),
        )

    except AuditError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The enrollment audit entries could not be read",
        ) from None

    return {
        "status": "success",
        "count": len(entries),
        "enrollments": [entry.to_dict() for entry in entries],
    }
