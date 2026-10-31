from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.models import ADMIN_ROLE, STUDENT_ROLE, UserPrincipal
from app.auth.service import verify_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    auto_error=False,
)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_access_token(
    token: str | None = Depends(oauth2_scheme),
) -> str:
    if not token:
        raise _unauthorized()

    return token


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> UserPrincipal:
    if not token:
        raise _unauthorized()

    user = verify_token(
        token,
        database_path=request.app.state.settings.database_path,
    )

    if user is None:
        raise _unauthorized()

    return user


def require_roles(*roles: str):
    def dependency(
        current_user: UserPrincipal = Depends(get_current_user),
    ) -> UserPrincipal:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        return current_user

    return dependency


require_student = require_roles(STUDENT_ROLE)
require_admin = require_roles(ADMIN_ROLE)
