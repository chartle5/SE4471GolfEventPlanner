from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


# ─────────────────────────── existing chat / generate ────────────────────


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    tournament: Dict[str, Any]
    history: List[HistoryMessage] = []
    phase: str = "planning"


class ChatResponse(BaseModel):
    message: str
    tournament: Dict[str, Any]
    ready_for_generation: bool = False
    needs_regeneration: bool = False


class GenerateRequest(BaseModel):
    tournament: Dict[str, Any]


class GenerateResponse(BaseModel):
    schedule: List[Dict[str, Any]]
    brochure: Dict[str, Any]


# ─────────────────────────── tournament persistence ──────────────────────


class SaveTournamentRequest(BaseModel):
    tournament: Dict[str, Any]
    schedule: List[Dict[str, Any]]
    brochure: Dict[str, Any]


class SaveTournamentResponse(BaseModel):
    tournament_id: str
    registration_token: str


class ShuffleResponse(BaseModel):
    schedule: List[Dict[str, Any]]


# ─────────────────────────── player registration ─────────────────────────


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str

    @field_validator("first_name", "last_name")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name fields cannot be empty")
        return v


class RegisterResponse(BaseModel):
    success: bool
    message: str
    slot_description: Optional[str] = None
    players_registered: int = 0
    total_players: int = 0


# ─────────────────────────── email ───────────────────────────────────────


class SendBrochureRequest(BaseModel):
    emails: List[str]

    @field_validator("emails")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendBrochureResponse(BaseModel):
    success: bool
    message: str


# ─────────────────────────── direct email send ───────────────────────────


class SendEmailDirectRequest(BaseModel):
    recipients: List[str]
    subject: str
    body: str

    @field_validator("recipients")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendEmailDirectResponse(BaseModel):
    success: bool
    message: str


# ─────────────────────────── auth ────────────────────────────────────────


class AuthRegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    @field_validator("email", "username", "password")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class AuthLoginRequest(BaseModel):
    identifier: str   # username OR email
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    username: str
    email: str