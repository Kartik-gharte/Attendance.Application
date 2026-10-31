from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import (
    get_access_token,
    get_current_user,
)
from app.auth.models import UserPrincipal
from app.auth.service import (
    authenticate_user,
    issue_token,
    revoke_token,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    settings = request.app.state.settings

    user = authenticate_user(
        form_data.username,
        form_data.password,
        database_path=settings.database_path,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_at = issue_token(
        user.id,
        ttl_seconds=settings.auth_token_ttl_seconds,
        database_path=settings.database_path,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(timespec="seconds"),
    }


@router.get("/me")
def read_current_user(
    current_user: UserPrincipal = Depends(get_current_user),
):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "student_id": current_user.student_id,
    }


@router.post("/logout")
def logout(
    request: Request,
    token: str = Depends(get_access_token),
    current_user: UserPrincipal = Depends(get_current_user),
):
    revoke_token(
        token,
        database_path=request.app.state.settings.database_path,
    )

    return {
        "status": "success",
        "message": "Logged out",
    }
