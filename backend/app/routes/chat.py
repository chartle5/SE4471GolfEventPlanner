from fastapi import APIRouter
from app.models import ChatRequest, ChatResponse
from app.services.agent import handle_chat

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    result = await handle_chat(
        user_message=payload.message,
        tournament=payload.tournament,
        history=history,
        phase=payload.phase,
    )
    return ChatResponse(
        message=result["message"],
        tournament=result["tournament"],
        ready_for_generation=result.get("ready_for_generation", False),
        needs_regeneration=result.get("needs_regeneration", False),
        sources=result.get("sources", []),
    )
