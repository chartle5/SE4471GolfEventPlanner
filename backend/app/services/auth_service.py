"""
Auth helpers: password hashing and JWT creation/verification.
"""

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SECRET: str = os.getenv("JWT_SECRET", "change_me")
_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days


# ── passwords ─────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── tokens ────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES)
    payload = {"sub": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises jose.JWTError on invalid / expired tokens.
    """
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
