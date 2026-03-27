from typing import Any, Dict
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    tournament: Dict[str, Any]


class ChatResponse(BaseModel):
    message: str
    tournament: Dict[str, Any]