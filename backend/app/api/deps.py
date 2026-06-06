"""Auth dependencies — current user + project ownership guard."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_access_token
from app.db.models import Project, User
from app.db.session import get_db

# tokenUrl dipakai Swagger UI untuk form login di /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token tidak valid atau kadaluarsa",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as e:
        raise _CREDENTIALS_EXC from e
    sub = payload.get("sub")
    if sub is None:
        raise _CREDENTIALS_EXC
    user = await db.get(User, int(sub))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


async def get_current_superuser(
    user: User = Depends(get_current_user),
) -> User:
    """Hanya superuser (untuk endpoint admin: seeding, manajemen)."""
    if not user.is_superuser:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Butuh hak superuser."
        )
    return user


async def get_owned_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Ambil project milik current user, atau 404 (jangan bocorkan keberadaan)."""
    project = await db.get(Project, project_id)
    if project is None or (project.owner_id is not None and project.owner_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project
