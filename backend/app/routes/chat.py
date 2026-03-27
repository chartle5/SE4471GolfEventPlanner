from fastapi import APIRouter
from app.models import ChatRequest, ChatResponse
from app.services.agent import handle_chat

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    result = await handle_chat(payload.message, payload.tournament)
    return ChatResponse(
        message=result["message"],
        tournament=result["tournament"]
    )