import json
import os
from datetime import date, datetime
from typing import Any, Dict, List

from app.services.openai_client import CHAT_DEPLOYMENT, client
from app.services.rag import format_retrieved_context, retrieve_relevant_chunks

DEPLOYMENT = CHAT_DEPLOYMENT


PLANNING_SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant.

You will be given the full conversation history plus the current tournament object.

REQUIRED FIELDS — you must collect ALL of these before generation can begin:
  1.  name                 — tournament name
  2.  date                 — event start date (first day)
  3.  venue                — course / location name
  4.  format               — play format (e.g. scramble, stroke play, match play)
  5.  numberOfDays         — how many days the tournament runs (integer ≥ 1)
  6.  playerCount          — total number of players competing (must be > 0)
  7.  eventType            — "individual" or "team"
  8.  teamSize             — players per team:
                               • If eventType is "individual": set teamSize = 1 automatically, do NOT ask the user.
                               • If eventType is "team" and format is stroke play or match play: ask; valid values 2.
                               • If eventType is "team" and format is scramble or other: ask; valid values 2–4.
  9.  registrationDeadline — final date by which players must register (must be before the event date)
  10. teeTimeStart         — first tee time (HH:MM 24-hour, default 08:00 but ASK the user)
  11. teeTimeInterval      — minutes between consecutive tee times (default 12, user can override)

OPTIONAL but useful: entryFee, description, sponsors, catering, budget, staffing, accessibility, notes, constraints.

Field rules:
- teamSize for an individual event must be 1; set it automatically and do not ask.
- teamSize for a team event in stroke play or match play must be exactly 2.
- teamSize for a team event in any other format (scramble, etc.) can be 2, 3, or 4.
- registrationDeadline must be earlier than or equal to date.

Your job:
- Extract any information from the user's message and update the tournament object
- Preserve ALL existing fields unless the user explicitly changes them
- Ask for ONE missing required field at a time — keep questions short and natural
- Once ALL required fields are filled (including teamSize if event is "team"):
  - Set "readyForGeneration": true
  - Set "needsRegeneration": false
  - In "message", say only:
      "Great — I have all the information I need. Would you like me to start generating your tournament documents?"
  - Do NOT repeat the tournament details in the message — the UI already displays them.
- If not all required fields are filled, set "readyForGeneration": false

Return ONLY valid JSON with exactly these top-level fields:
  "message"            — natural-language response string
  "tournament"         — full updated tournament object
  "readyForGeneration" — boolean
  "needsRegeneration"  — boolean (always false in planning phase)

Rules:
- Do NOT wrap the JSON in markdown code fences
- Do NOT return any text outside the JSON
- Keep the same object structure; unknown fields stay as their current value
"""

REFINEMENT_SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant in REFINEMENT MODE.

Tournament documents have already been generated. The user may now request changes
to any aspect of the tournament.

Field rules (same as planning):
- teamSize for an individual event must be 1; if the user changes eventType to
  individual, automatically set teamSize = 1.
- teamSize for a team event in stroke play or match play must be exactly 2.
- teamSize for a team event in any other format can be 2, 3, or 4.
- registrationDeadline must be earlier than or equal to the event start date.

Your job:
- Apply the requested changes to the tournament object
- Confirm what was changed in the "message" field
- Set "needsRegeneration": true if any of these changed:
    teeTimeStart, teeTimeInterval, playerCount, format, date, venue, name,
    numberOfDays, eventType, teamSize
  (these all affect the schedule or brochure content)
- Set "needsRegeneration": false for changes that don't affect documents
    (e.g. notes, accessibility, entryFee, description, registrationDeadline
    — unless user specifically asks to regenerate)
- Set "readyForGeneration": true always (documents already exist)

Return ONLY valid JSON with exactly these top-level fields:
  "message"            — natural-language confirmation of the change
  "tournament"         — full updated tournament object
  "readyForGeneration" — boolean (always true in refinement mode)
  "needsRegeneration"  — boolean

Rules:
- Do NOT wrap the JSON in markdown code fences
- Do NOT return any text outside the JSON
"""

EXAMPLE_EMPTY_TOURNAMENT = {
    "id": "",
    "name": "",
    "date": "",
    "venue": "",
    "format": "",
    "numberOfDays": 0,
    "playerCount": 0,
    "eventType": "",
    "teamSize": 0,
    "registrationDeadline": "",
    "entryFee": 0,
    "description": "",
    "teeTimeStart": "08:00",
    "teeTimeInterval": 12,
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


def _resolve_year(month: int, day: int) -> int:
    """Return the nearest upcoming year for a given month/day."""
    today = date.today()
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        # Invalid day for month (e.g. Feb 30) — just use current year
        return today.year
    return today.year if candidate >= today else today.year + 1


def _normalize_date(date_str: str) -> str:
    """
    Parse a date string and apply smart year resolution:
    - No year given → pick current year if date is upcoming, else next year.
    - Year given but already past → apply same logic.
    - Year given and current/future → leave unchanged.
    """
    if not date_str or not date_str.strip():
        return date_str

    s = date_str.strip()
    today = date.today()

    # Formats without a year — apply smart resolution
    for fmt in ("%B %d", "%b %d", "%m/%d", "%m-%d"):
        try:
            parsed = datetime.strptime(s, fmt)
            year = _resolve_year(parsed.month, parsed.day)
            return date(year, parsed.month, parsed.day).strftime("%B %d, %Y")
        except ValueError:
            pass

    # Formats with a year
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y",
                "%B %d %Y", "%b %d %Y"):
        try:
            parsed = datetime.strptime(s, fmt)
            if parsed.year < today.year:
                # Stale year (e.g. 2024) — re-apply smart resolution
                year = _resolve_year(parsed.month, parsed.day)
                return date(year, parsed.month, parsed.day).strftime("%B %d, %Y")
            # Current or future year — respect as-is
            return s
        except ValueError:
            pass

    # Unparseable — return unchanged
    return s


def _normalize_tournament(tournament: Dict[str, Any]) -> Dict[str, Any]:
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

    if not isinstance(merged.get("teeTimeInterval"), int):
        try:
            merged["teeTimeInterval"] = int(merged["teeTimeInterval"])
        except (TypeError, ValueError):
            merged["teeTimeInterval"] = 12

    for int_field, default in (("numberOfDays", 0), ("teamSize", 0), ("entryFee", 0)):
        try:
            merged[int_field] = int(merged.get(int_field) or default)
        except (TypeError, ValueError):
            merged[int_field] = default

    if not isinstance(merged.get("eventType"), str):
        merged["eventType"] = ""
    if not isinstance(merged.get("registrationDeadline"), str):
        merged["registrationDeadline"] = ""
    if not isinstance(merged.get("description"), str):
        merged["description"] = ""

    # Smart year resolution for date fields
    merged["date"] = _normalize_date(merged.get("date", ""))
    merged["registrationDeadline"] = _normalize_date(merged.get("registrationDeadline", ""))

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


async def handle_chat(
    user_message: str,
    tournament: Dict[str, Any],
    history: List[Dict[str, str]] = None,
    phase: str = "planning",
) -> Dict[str, Any]:
    tournament = _normalize_tournament(tournament)
    retrieved_chunks = []

    try:
        retrieved_chunks = await retrieve_relevant_chunks(
            _build_retrieval_query(user_message, tournament)
        )
    except Exception:
        retrieved_chunks = []

    today_str = date.today().strftime("%B %d, %Y")
    system_prompt = (
        f"Today's date is {today_str}. Use this to resolve partial dates (e.g. 'June 26') "
        f"to the nearest upcoming occurrence.\n\n"
    ) + (PLANNING_SYSTEM_PROMPT if phase == "planning" else REFINEMENT_SYSTEM_PROMPT)

    # Embed conversation history as a text block in the user prompt rather than injecting
    # it as raw chat turns. This prevents the model from getting confused about its output
    # format when it sees previous plain-text assistant replies in the chat history.
    history_block = ""
    if history:
        lines = []
        for msg in history:
            label = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{label}: {msg['content']}")
        history_block = "[Conversation so far]\n" + "\n".join(lines) + "\n\n"

    user_prompt = (
        f"{history_block}"
        f"User: {user_message}\n\n"
        f"[Current tournament state]\n{json.dumps(tournament, indent=2)}\n\n"
        f"[Retrieved knowledge snippets]\n{format_retrieved_context(retrieved_chunks)}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT,
            temperature=0.2,
            messages=messages,
        )

        content = (response.choices[0].message.content or "").strip()

        # Strip markdown code fences if the model wraps its response despite instructions
        if content.startswith("```"):
            # Remove opening fence (```json or ```)
            content = content.split("\n", 1)[-1]
            # Remove closing fence
            if content.rstrip().endswith("```"):
                content = content.rstrip()[:-3].rstrip()

        parsed = json.loads(content)

        message = parsed.get("message", "I updated the tournament.")
        updated_tournament = _normalize_tournament(parsed.get("tournament", tournament))
        ready_for_generation = bool(parsed.get("readyForGeneration", False))
        needs_regeneration = bool(parsed.get("needsRegeneration", False))

        return {
            "message": message,
            "tournament": updated_tournament,
            "ready_for_generation": ready_for_generation,
            "needs_regeneration": needs_regeneration,
            "sources": _serialize_sources(retrieved_chunks),
        }

    except Exception as exc:
        return {
            "message": f"I ran into an error: {str(exc)}",
            "tournament": tournament,
            "ready_for_generation": False,
            "needs_regeneration": False,
            "sources": _serialize_sources(retrieved_chunks),
        }
