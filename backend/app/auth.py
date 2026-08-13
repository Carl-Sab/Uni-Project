"""JWT issuing/verification and the auth dependencies every scoped route
depends on.

CRITICAL security model: get_current_student is the ONLY source of a
student_id anywhere in the API layer. It reads the id out of a signed JWT's
`sub` claim - never from a path parameter, query string, or request body.
No route in this codebase may declare a `student_id` path/query/body
parameter; every "which student" question is answered by this dependency,
not by trusting the caller.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=12)

_bearer = HTTPBearer(auto_error=False)


def create_access_token(*, sub: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _credentials_or_401(
    credentials: HTTPAuthorizationCredentials | None,
) -> HTTPAuthorizationCredentials:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials


async def get_current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """The only place a student_id enters the request-handling layer."""
    creds = _credentials_or_401(credentials)
    payload = _decode(creds.credentials)
    if payload.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student token required")
    return payload["sub"]


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    creds = _credentials_or_401(credentials)
    payload = _decode(creds.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    return payload["sub"]
