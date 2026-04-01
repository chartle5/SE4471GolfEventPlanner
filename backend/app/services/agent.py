import json
from typing import Any, Dict, List, Optional

from app.services.openai_client import CHAT_DEPLOYMENT, LOG_LLM_PROMPTS, client
from app.services.rag import (
    LOCAL_EMBEDDING_MODEL,
    format_retrieved_context,
    retrieve_relevant_chunks,
)

DEPLOYMENT = CHAT_DEPLOYMENT


SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant.

You will be given:
1. The user's latest message
2. The current tournament object
3. Retrieved knowledge snippets from the local planning library

Your job:
- Update the tournament object using any new information from the user
- Preserve existing information unless the user changes it
- Ask for missing important details when needed 
- Use retrieved knowledge when it helps answer the user's question or suggest next steps
- Return ONLY valid JSON
- The JSON must contain exactly these two top-level fields:
  "message": a helpful natural-language response to the user
  "tournament": the full updated tournament object

Rules:
- Treat retrieved knowledge as guidance, not as user-provided facts about this tournament
- If retrieved knowledge conflicts with the user's direct instructions, prefer the user's instructions
- Do not wrap the JSON in markdown
- Do not return extra text
- Keep the same general object structure
- If a field is unknown, leave it as its current value
- When asking for missing details, only ask about one missing field at a time
"""

EXAMPLE_EMPTY_TOURNAMENT = {
    "id": "",
    "name": "",
    "date": "",
    "venue": "",
    "format": "",
    "playerCount": 0,
    "sponsors": [],
    "catering": "",
    "budget": 0,
    "staffing": {
        "volunteers": 0,
        "staff": 0
    },
    "accessibility": "",
    "notes": "",
    "constraints": []
}


def _normalize_tournament(tournament: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the basic expected structure exists before sending to the model.
    """
    merged = dict(EXAMPLE_EMPTY_TOURNAMENT)
    merged.update(tournament or {})

    if not isinstance(merged.get("sponsors"), list):
        merged["sponsors"] = []

    if not isinstance(merged.get("constraints"), list):
        merged["constraints"] = []

    if not isinstance(merged.get("staffing"), dict):
        merged["staffing"] = {"volunteers": 0, "staff": 0}

    merged["staffing"].setdefault("volunteers", 0)
    merged["staffing"].setdefault("staff", 0)

    return merged


def _build_retrieval_query(user_message: str, tournament: Dict[str, Any]) -> str:
    query_parts = [user_message.strip()]

    if tournament.get("format"):
        query_parts.append(f'Tournament format: {tournament["format"]}')

    if tournament.get("constraints"):
        query_parts.append(
            "Constraints: " + ", ".join(str(item) for item in tournament["constraints"])
        )

    if tournament.get("accessibility"):
        query_parts.append(f'Accessibility needs: {tournament["accessibility"]}')

    return "\n".join(part for part in query_parts if part)


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _serialize_sources(chunks: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "title": chunk.title,
            "chunk_id": chunk.chunk_id,
            "score": round(chunk.score, 3),
            "preview": _preview_text(chunk.text),
        }
        for chunk in chunks
    ]


def _serialize_debug_chunks(chunks: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "title": chunk.title,
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "score": round(chunk.score, 3),
            "text": chunk.text,
        }
        for chunk in chunks
    ]


def _log_llm_request(
    retrieval_query: str,
    retrieved_chunks: List[Any],
    messages: List[Dict[str, str]],
    retrieval_error: Optional[str] = None,
) -> None:
    if not LOG_LLM_PROMPTS:
        return

    debug_payload = {
        "deployment": DEPLOYMENT,
        "embedding_model": LOCAL_EMBEDDING_MODEL,
        "retrieval_query": retrieval_query,
        "retrieval_error": retrieval_error,
        "retrieved_chunks": _serialize_debug_chunks(retrieved_chunks),
        "messages": messages,
    }

    print("=== LLM PROMPT DEBUG START ===")
    print(json.dumps(debug_payload, indent=2, ensure_ascii=False))
    print("=== LLM PROMPT DEBUG END ===")


async def handle_chat(user_message: str, tournament: Dict[str, Any]) -> Dict[str, Any]:
    tournament = _normalize_tournament(tournament)
    retrieved_chunks = []
    retrieval_query = _build_retrieval_query(user_message, tournament)
    retrieval_error = None

    try:
        retrieved_chunks = await retrieve_relevant_chunks(retrieval_query)
    except Exception as exc:
        retrieval_error = str(exc)
        retrieved_chunks = []

    user_prompt = f"""
User message:
{user_message}

Current tournament object:
{json.dumps(tournament, indent=2)}

Retrieved knowledge snippets:
{format_retrieved_context(retrieved_chunks)}
"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    _log_llm_request(retrieval_query, retrieved_chunks, messages, retrieval_error)

    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT,
            temperature=0.2,
            messages=messages,
        )

        content = (response.choices[0].message.content or "").strip()
        parsed = json.loads(content)

        message = parsed.get("message", "I updated the tournament.")
        updated_tournament = _normalize_tournament(parsed.get("tournament", tournament))

        return {
            "message": message,
            "tournament": updated_tournament,
            "sources": _serialize_sources(retrieved_chunks),
        }

    except Exception as exc:
        return {
            "message": f"I ran into an error while updating the tournament: {str(exc)}",
            "tournament": tournament,
            "sources": _serialize_sources(retrieved_chunks),
        }
