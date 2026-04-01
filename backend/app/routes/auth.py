"""
Auth routes: /auth/register and /auth/login.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from app.database import get_database
from app.models import (
    AuthRegisterRequest,
    AuthLoginRequest,
    AuthResponse,
)
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[object, Depends(get_database)]


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: AuthRegisterRequest, db: DB):
    """Create a new user account."""
    # Email uniqueness check
    if await db.users.find_one({"email": payload.email.lower()}):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    # Username uniqueness check
    if await db.users.find_one({"username": payload.username.lower()}):
        raise HTTPException(status_code=409, detail="That username is already taken.")

    user_id = str(uuid.uuid4())
    doc = {
        "user_id": user_id,
        "email": payload.email.lower(),
        "username": payload.username.lower(),
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(doc)

    token = create_access_token(user_id, payload.username.lower())
    return AuthResponse(
        token=token,
        user_id=user_id,
        username=payload.username.lower(),
        email=payload.email.lower(),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthLoginRequest, db: DB):
    """Authenticate with username or email + password."""
    identifier = payload.identifier.lower()
    user = await db.users.find_one(
        {"$or": [{"email": identifier}, {"username": identifier}]},
        {"_id": 0},
    )

    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token(user["user_id"], user["username"])
    return AuthResponse(
        token=token,
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
    )
