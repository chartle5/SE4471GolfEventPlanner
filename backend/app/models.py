from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, field_validator, model_validator, Field


# ─────────────────────────── existing chat / generate ────────────────────


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    tournament: Dict[str, Any]
    history: List[HistoryMessage] = []
    phase: str = "planning"
    working_memory: Dict[str, Any] = Field(default_factory=dict)


class ChatSource(BaseModel):
    title: str
    chunk_id: str
    score: float
    preview: str


class ChatResponse(BaseModel):
    message: str
    tournament: Dict[str, Any]
    ready_for_generation: bool = False
    needs_regeneration: bool = False
    sources: List[ChatSource] = Field(default_factory=list)
    working_memory: Dict[str, Any] = Field(default_factory=dict)


class GenerateRequest(BaseModel):
    tournament: Dict[str, Any]


class GenerateResponse(BaseModel):
    schedule: List[Dict[str, Any]]
    brochure: Dict[str, Any]
    rule_sheet: Optional[Dict[str, Any]] = None
    fnb_summary: Optional[Dict[str, Any]] = None


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
    phone_number: str
    rental_clubs: bool = False
    club_hand: Optional[Literal["left", "right"]] = None
    team_name: Optional[str] = None

    @field_validator("first_name", "last_name", "phone_number")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty")
        return v

    @model_validator(mode="after")
    def _club_hand_required(self) -> "RegisterRequest":
        if self.rental_clubs and self.club_hand is None:
            raise ValueError("club_hand must be 'left' or 'right' when rental_clubs is True")
        return self


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
    # Optional fields — when provided, the backend generates a styled HTML email
    schedule: Optional[List[Dict[str, Any]]] = None
    tournament_name: Optional[str] = None
    tournament_date: Optional[str] = None
    tournament_venue: Optional[str] = None
    tournament_format: Optional[str] = None

    @field_validator("recipients")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendEmailDirectResponse(BaseModel):
    success: bool
    message: str


class SendInviteRequest(BaseModel):
    recipients: List[str]
    tournament_meta: Dict[str, Any]
    registration_link: Optional[str] = ""

    @field_validator("recipients")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendInviteResponse(BaseModel):
    success: bool
    message: str


# ─────────────────────────── club operations sheet ───────────────────────


class SendClubSheetRequest(BaseModel):
    emails: List[str]
    organizer_name: Optional[str] = ""
    organizer_email: Optional[str] = ""
    organizer_phone: Optional[str] = ""

    @field_validator("emails")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendClubSheetResponse(BaseModel):
    success: bool
    message: str


# ─────────────────────────── rule sheet email ────────────────────────────


class SendRuleSheetRequest(BaseModel):
    recipients: List[str]
    tournament_meta: Dict[str, Any]

    @field_validator("recipients")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendRuleSheetResponse(BaseModel):
    success: bool
    message: str


# ─────────────────────────── F&B summary email ───────────────────────────


class SendFnBSummaryRequest(BaseModel):
    recipients: List[str]
    tournament_meta: Dict[str, Any]

    @field_validator("recipients")
    @classmethod
    def _at_least_one(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one recipient email is required")
        return v


class SendFnBSummaryResponse(BaseModel):
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
