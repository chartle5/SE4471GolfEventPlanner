"""
FastAPI dependency that validates the Bearer JWT and returns the current user's ID.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.services.auth_service import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """
    Extract and validate the JWT from the Authorization: Bearer <token> header.
    Returns {"user_id": ..., "username": ...} on success.
    Raises HTTP 401 on missing / invalid / expired tokens.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        username: str = payload.get("username", "")
        if not user_id:
            raise ValueError("Missing sub claim")
        return {"user_id": user_id, "username": username}
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
