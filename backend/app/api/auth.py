import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.config import settings
from app.db import get_db
from app.models import Student
from app.schemas import AdminLoginRequest, StudentLoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/student/login", response_model=TokenResponse)
async def student_login(
    body: StudentLoginRequest, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    student = await session.get(Student, body.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown student_id")
    token = create_access_token(sub=student.student_id, role="student")
    return TokenResponse(access_token=token)


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest) -> TokenResponse:
    valid = secrets.compare_digest(body.username, settings.ADMIN_USERNAME) and secrets.compare_digest(
        body.password, settings.ADMIN_PASSWORD
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(sub=body.username, role="admin")
    return TokenResponse(access_token=token)
