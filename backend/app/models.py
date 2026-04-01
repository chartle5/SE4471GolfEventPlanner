from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    tournament: Dict[str, Any]


class ChatSource(BaseModel):
    title: str
    chunk_id: str
    score: float
    preview: str


class ChatResponse(BaseModel):
    message: str
    tournament: Dict[str, Any]
    sources: List[ChatSource] = Field(default_factory=list)
