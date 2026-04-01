import json
from typing import Any, Dict, List

from app.services.openai_client import CHAT_DEPLOYMENT, client
from app.services.rag import format_retrieved_context, retrieve_relevant_chunks

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


async def handle_chat(user_message: str, tournament: Dict[str, Any]) -> Dict[str, Any]:
    tournament = _normalize_tournament(tournament)
    retrieved_chunks = []

    try:
        retrieved_chunks = await retrieve_relevant_chunks(
            _build_retrieval_query(user_message, tournament)
        )
    except Exception:
        retrieved_chunks = []

    user_prompt = f"""
User message:
{user_message}

Current tournament object:
{json.dumps(tournament, indent=2)}

Retrieved knowledge snippets:
{format_retrieved_context(retrieved_chunks)}
"""

    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
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
