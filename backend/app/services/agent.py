import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.openai_client import CHAT_DEPLOYMENT, LOG_LLM_PROMPTS, client
from app.services.rag import (
    LOCAL_EMBEDDING_MODEL,
    format_retrieved_context,
    retrieve_relevant_chunks,
)

DEPLOYMENT = CHAT_DEPLOYMENT
READY_MESSAGE = (
    "Great — I have all the information I need. Click the green button on the "
    "right to start generating your documents."
)
DOCUMENT_IMPACT_FIELDS = {
    "teeTimeStart",
    "teeTimeInterval",
    "playerCount",
    "format",
    "date",
    "venue",
    "name",
    "numberOfDays",
    "eventType",
    "teamSize",
}

PLANNING_SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant.

You will be given:
1. The full conversation history
2. The current tournament object
3. Retrieved knowledge snippets from the local planning library

REQUIRED FIELDS — you must collect ALL of these before generation can begin:
  1.  name                 — tournament name
  2.  date                 — event start date (first day)
  3.  venue                — course / location name
  4.  format               — play format (e.g. scramble, stroke play, match play)
  5.  numberOfDays         — how many days the tournament runs (integer >= 1)
  6.  playerCount          — total number of players competing (must be > 0)
  7.  eventType            — "individual" or "team"
  8.  teamSize             — players per team:
                               - If eventType is "individual": set teamSize = 1 automatically, do NOT ask the user.
                               - If eventType is "team" and format is stroke play or match play: ask; valid values 2.
                               - If eventType is "team" and format is scramble or other: ask; valid values 2-4.
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
- Use retrieved knowledge when it helps answer the user's question or suggest next steps
- Treat retrieved knowledge as guidance, not as user-provided facts about this tournament
- If retrieved knowledge conflicts with the user's direct instructions, prefer the user's instructions
- Ask for ONE missing required field at a time and keep questions short and natural
- Once ALL required fields are filled, be ready to move into generation
"""

REFINEMENT_SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant in REFINEMENT MODE.

Tournament documents have already been generated. The user may now request changes
to any aspect of the tournament.

You will also receive retrieved knowledge snippets from the local planning library.
Use them as guidance when helpful, but do not treat them as user-provided facts.

Field rules:
- teamSize for an individual event must be 1; if the user changes eventType to individual, set teamSize = 1.
- teamSize for a team event in stroke play or match play must be exactly 2.
- teamSize for a team event in any other format can be 2, 3, or 4.
- registrationDeadline must be earlier than or equal to the event start date.

Your job:
- Apply the requested changes to the tournament object
- Preserve unrelated existing fields
- Flag clarifications when the user's request is ambiguous or would violate a field rule
- Use retrieved knowledge only as guidance
"""

WORKFLOW_ANALYZER_SYSTEM_PROMPT = """
You are step 1 in a multi-step workflow for a golf tournament assistant.

Your task is to analyze the latest user message, draft the safest possible updated
tournament object, and decide whether clarification is needed before a final answer
is generated.

Return ONLY valid JSON with exactly these top-level fields:
  "workflowAction"           - "update" or "clarify"
  "reasoningSummary"         - one short sentence summarizing the decision
  "clarifyingFocus"          - field name or issue label, or "" if none
  "clarifyingQuestion"       - one short question if clarification is needed, else ""
  "candidateTournament"      - the full drafted tournament object
  "userRequestedRegeneration" - boolean

Rules:
- Preserve the existing object structure.
- Apply only explicit user requests and high-confidence inferences.
- If the request is ambiguous, conflicting, or underspecified for a risky change,
  set "workflowAction" to "clarify" and leave uncertain fields unchanged.
- Use retrieved knowledge snippets only as guidance.
- If eventType is "individual", set teamSize to 1 in the candidate object.
- Do not output markdown or extra text.
"""

WORKFLOW_FINALIZER_SYSTEM_PROMPT = """
You are step 2 in a multi-step workflow for a golf tournament assistant.

A previous step already drafted a candidate tournament update. A deterministic
validation step has already checked missing fields, rule violations, regeneration
impact, and the required next action.

Return ONLY valid JSON with exactly these top-level fields:
  "message"            - natural-language response
  "tournament"         - full updated tournament object
  "readyForGeneration" - boolean
  "needsRegeneration"  - boolean

Rules:
- Use the supplied target boolean values exactly.
- If finalAction is "clarify", ask one focused question and preserve any safe
  candidate updates already made.
- If finalAction is "respond", confirm the update concisely.
- If planning mode is ready for generation, the message must be exactly:
  "Great — I have all the information I need. Click the green button on the right to start generating your documents."
- Use retrieved knowledge only as guidance.
- Do not output markdown or extra text.
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
        "staff": 0,
    },
    "accessibility": "",
    "notes": "",
    "constraints": [],
}


def _resolve_year(month: int, day: int) -> int:
    today = date.today()
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return today.year
    return today.year if candidate >= today else today.year + 1


def _normalize_date(date_str: str) -> str:
    if not date_str or not date_str.strip():
        return date_str

    value = date_str.strip()
    today = date.today()

    for fmt in ("%B %d", "%b %d", "%m/%d", "%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            year = _resolve_year(parsed.month, parsed.day)
            return date(year, parsed.month, parsed.day).strftime("%B %d, %Y")
        except ValueError:
            pass

    for fmt in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.year < today.year:
                year = _resolve_year(parsed.month, parsed.day)
                return date(year, parsed.month, parsed.day).strftime("%B %d, %Y")
            return value
        except ValueError:
            pass

    return value


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

    for int_field, default in (
        ("numberOfDays", 0),
        ("playerCount", 0),
        ("teamSize", 0),
        ("entryFee", 0),
        ("teeTimeInterval", 12),
        ("budget", 0),
    ):
        try:
            merged[int_field] = int(merged.get(int_field) or default)
        except (TypeError, ValueError):
            merged[int_field] = default

    for text_field in (
        "id",
        "name",
        "date",
        "venue",
        "format",
        "eventType",
        "registrationDeadline",
        "description",
        "teeTimeStart",
        "catering",
        "accessibility",
        "notes",
    ):
        if not isinstance(merged.get(text_field), str):
            merged[text_field] = ""

    merged["date"] = _normalize_date(merged.get("date", ""))
    merged["registrationDeadline"] = _normalize_date(merged.get("registrationDeadline", ""))

    if merged["eventType"].strip().lower() == "individual":
        merged["teamSize"] = 1

    return merged


def _build_retrieval_query(user_message: str, tournament: Dict[str, Any]) -> str:
    query_parts = [user_message.strip()]

    if tournament.get("format"):
        query_parts.append(f'Tournament format: {tournament["format"]}')
    if tournament.get("eventType"):
        query_parts.append(f'Event type: {tournament["eventType"]}')
    if tournament.get("constraints"):
        query_parts.append(
            "Constraints: " + ", ".join(str(item) for item in tournament["constraints"])
        )
    if tournament.get("accessibility"):
        query_parts.append(f'Accessibility needs: {tournament["accessibility"]}')

    return "\n".join(part for part in query_parts if part)


def _build_history_block(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return ""

    lines = []
    for msg in history:
        label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{label}: {msg['content']}")

    return "[Conversation so far]\n" + "\n".join(lines) + "\n\n"


def _phase_instruction_block(phase: str) -> str:
    return PLANNING_SYSTEM_PROMPT if phase == "planning" else REFINEMENT_SYSTEM_PROMPT


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


def _log_debug_block(label: str, payload: Dict[str, Any]) -> None:
    if not LOG_LLM_PROMPTS:
        return

    print(f"=== {label} START ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"=== {label} END ===")


def _log_llm_step(
    step_name: str,
    messages: List[Dict[str, str]],
    retrieval_query: str,
    retrieved_chunks: List[Any],
    retrieval_error: Optional[str] = None,
    extra_debug: Optional[Dict[str, Any]] = None,
) -> None:
    payload = {
        "step": step_name,
        "deployment": DEPLOYMENT,
        "embedding_model": LOCAL_EMBEDDING_MODEL,
        "retrieval_query": retrieval_query,
        "retrieval_error": retrieval_error,
        "retrieved_chunks": _serialize_debug_chunks(retrieved_chunks),
        "messages": messages,
    }
    if extra_debug:
        payload["extra"] = extra_debug
    _log_debug_block("LLM PROMPT DEBUG", payload)


def _strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3].rstrip()
    return stripped


async def _call_json_step(
    step_name: str,
    system_prompt: str,
    user_prompt: str,
    retrieval_query: str,
    retrieved_chunks: List[Any],
    retrieval_error: Optional[str] = None,
    extra_debug: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    _log_llm_step(
        step_name,
        messages,
        retrieval_query,
        retrieved_chunks,
        retrieval_error,
        extra_debug,
    )

    response = await client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0.2,
        messages=messages,
    )
    content = _strip_code_fences(response.choices[0].message.content or "")
    parsed = json.loads(content)

    _log_debug_block(
        f"LLM STEP {step_name.upper()} RESULT",
        {"step": step_name, "parsed": parsed},
    )

    return parsed


def _normalize_analysis_result(
    analysis: Dict[str, Any],
    tournament: Dict[str, Any],
) -> Dict[str, Any]:
    workflow_action = str(analysis.get("workflowAction", "update")).strip().lower()
    if workflow_action not in {"update", "clarify"}:
        workflow_action = "update"

    candidate_raw = analysis.get("candidateTournament", tournament)
    if not isinstance(candidate_raw, dict):
        candidate_raw = tournament

    return {
        "workflow_action": workflow_action,
        "reasoning_summary": str(analysis.get("reasoningSummary", "")).strip(),
        "clarifying_focus": str(analysis.get("clarifyingFocus", "")).strip(),
        "clarifying_question": str(analysis.get("clarifyingQuestion", "")).strip(),
        "candidate_tournament": _normalize_tournament(candidate_raw),
        "user_requested_regeneration": bool(
            analysis.get("userRequestedRegeneration", False)
        ),
    }


def _parse_date_for_comparison(value: str) -> Optional[date]:
    if not value or not value.strip():
        return None

    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _required_field_status(tournament: Dict[str, Any]) -> Dict[str, bool]:
    event_type = tournament.get("eventType", "").strip().lower()
    format_name = tournament.get("format", "").strip().lower()
    team_size = int(tournament.get("teamSize") or 0)

    status = {
        "name": bool(tournament.get("name", "").strip()),
        "date": bool(tournament.get("date", "").strip()),
        "venue": bool(tournament.get("venue", "").strip()),
        "format": bool(tournament.get("format", "").strip()),
        "numberOfDays": int(tournament.get("numberOfDays") or 0) >= 1,
        "playerCount": int(tournament.get("playerCount") or 0) > 0,
        "eventType": event_type in {"individual", "team"},
        "registrationDeadline": bool(tournament.get("registrationDeadline", "").strip()),
        "teeTimeStart": bool(tournament.get("teeTimeStart", "").strip()),
        "teeTimeInterval": int(tournament.get("teeTimeInterval") or 0) > 0,
    }

    if event_type == "individual":
        status["teamSize"] = True
    elif event_type == "team":
        if format_name in {"stroke play", "match play"}:
            status["teamSize"] = team_size == 2
        else:
            status["teamSize"] = team_size in {2, 3, 4}
    else:
        status["teamSize"] = False

    return status


def _collect_constraint_issues(tournament: Dict[str, Any]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    event_type = tournament.get("eventType", "").strip().lower()
    format_name = tournament.get("format", "").strip().lower()
    team_size = int(tournament.get("teamSize") or 0)

    if event_type == "team":
        if format_name in {"stroke play", "match play"} and team_size not in {0, 2}:
            issues.append(
                {
                    "code": "team_size_invalid_for_match_or_stroke",
                    "field": "teamSize",
                    "message": "For team stroke play or match play events, team size must be 2.",
                }
            )
        if format_name and format_name not in {"stroke play", "match play"} and team_size not in {0, 2, 3, 4}:
            issues.append(
                {
                    "code": "team_size_invalid_for_team_event",
                    "field": "teamSize",
                    "message": "For team events, team size must be between 2 and 4 unless the format requires 2.",
                }
            )

    event_date = _parse_date_for_comparison(tournament.get("date", ""))
    registration_deadline = _parse_date_for_comparison(
        tournament.get("registrationDeadline", "")
    )
    if event_date and registration_deadline and registration_deadline > event_date:
        issues.append(
            {
                "code": "registration_after_event_date",
                "field": "registrationDeadline",
                "message": "The registration deadline must be on or before the event start date.",
            }
        )

    if int(tournament.get("teeTimeInterval") or 0) <= 0:
        issues.append(
            {
                "code": "invalid_tee_time_interval",
                "field": "teeTimeInterval",
                "message": "The tee time interval must be greater than 0 minutes.",
            }
        )

    return issues


def _document_impact_fields(
    original_tournament: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
) -> List[str]:
    return sorted(
        field
        for field in DOCUMENT_IMPACT_FIELDS
        if original_tournament.get(field) != candidate_tournament.get(field)
    )


def _default_clarifying_question(
    focus: str,
    missing_fields: List[str],
    constraint_issues: List[Dict[str, str]],
) -> str:
    if constraint_issues:
        first_issue = constraint_issues[0]
        if first_issue["field"] == "registrationDeadline":
            return (
                "What registration deadline would you like to use? It needs to be "
                "on or before the event start date."
            )
        if first_issue["field"] == "teamSize":
            return (
                "How many players should be on each team? I need a value that fits "
                "the current event format."
            )
        if first_issue["field"] == "teeTimeInterval":
            return "What tee time interval would you like to use in minutes?"

    question_map = {
        "name": "What should the tournament be called?",
        "date": "What date should the tournament start?",
        "venue": "Which course or venue should I use?",
        "format": "What tournament format do you want to run?",
        "numberOfDays": "How many days will the tournament run?",
        "playerCount": "How many players will be participating?",
        "eventType": 'Will this be an "individual" event or a "team" event?',
        "teamSize": "How many players should be on each team?",
        "registrationDeadline": "What registration deadline should I use?",
        "teeTimeStart": "What time should the first tee time start?",
        "teeTimeInterval": "How many minutes should there be between tee times?",
    }

    if focus in question_map:
        return question_map[focus]
    if missing_fields:
        return question_map.get(
            missing_fields[0],
            "What would you like me to clarify next?",
        )
    return "What would you like me to clarify next?"


def _build_validation_result(
    original_tournament: Dict[str, Any],
    analysis_result: Dict[str, Any],
    phase: str,
) -> Dict[str, Any]:
    candidate_tournament = analysis_result["candidate_tournament"]
    required_status = _required_field_status(candidate_tournament)
    missing_fields = [field for field, is_ready in required_status.items() if not is_ready]
    constraint_issues = _collect_constraint_issues(candidate_tournament)
    changed_impact_fields = _document_impact_fields(original_tournament, candidate_tournament)

    final_action = "respond"
    if (
        analysis_result["workflow_action"] == "clarify"
        or constraint_issues
        or (phase == "planning" and missing_fields)
    ):
        final_action = "clarify"

    primary_focus = (
        analysis_result["clarifying_focus"]
        or (constraint_issues[0]["field"] if constraint_issues else "")
        or (missing_fields[0] if missing_fields else "")
    )
    suggested_question = analysis_result["clarifying_question"] or _default_clarifying_question(
        primary_focus,
        missing_fields,
        constraint_issues,
    )

    ready_for_generation = (
        phase != "planning"
        or (final_action == "respond" and not missing_fields and not constraint_issues)
    )
    needs_regeneration = (
        phase == "refinement"
        and (
            bool(changed_impact_fields)
            or analysis_result["user_requested_regeneration"]
        )
    )

    return {
        "required_status": required_status,
        "missing_fields": missing_fields,
        "constraint_issues": constraint_issues,
        "changed_impact_fields": changed_impact_fields,
        "final_action": final_action,
        "primary_focus": primary_focus,
        "suggested_question": suggested_question,
        "ready_for_generation": ready_for_generation,
        "needs_regeneration": needs_regeneration,
    }


async def handle_chat(
    user_message: str,
    tournament: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
    phase: str = "planning",
) -> Dict[str, Any]:
    phase = "refinement" if phase == "refinement" else "planning"
    tournament = _normalize_tournament(tournament)
    retrieved_chunks: List[Any] = []
    retrieval_query = _build_retrieval_query(user_message, tournament)
    retrieval_error = None

    try:
        retrieved_chunks = await retrieve_relevant_chunks(retrieval_query)
    except Exception as exc:
        retrieval_error = str(exc)
        retrieved_chunks = []

    today_str = date.today().strftime("%B %d, %Y")
    history_block = _build_history_block(history)
    phase_instructions = _phase_instruction_block(phase)
    retrieved_context = format_retrieved_context(retrieved_chunks)

    analysis_prompt = (
        f"Phase: {phase}\n"
        f"Today's date: {today_str}\n\n"
        f"[Phase instructions]\n{phase_instructions}\n\n"
        f"{history_block}"
        f"[Latest user message]\n{user_message}\n\n"
        f"[Current tournament state]\n{json.dumps(tournament, indent=2)}\n\n"
        f"[Retrieved knowledge snippets]\n{retrieved_context}\n"
    )

    try:
        raw_analysis = await _call_json_step(
            "workflow_analysis",
            WORKFLOW_ANALYZER_SYSTEM_PROMPT,
            analysis_prompt,
            retrieval_query,
            retrieved_chunks,
            retrieval_error,
            extra_debug={"phase": phase},
        )
        analysis_result = _normalize_analysis_result(raw_analysis, tournament)
    except Exception as exc:
        analysis_result = {
            "workflow_action": "clarify",
            "reasoning_summary": "Analysis step failed, so the request needs clarification.",
            "clarifying_focus": "",
            "clarifying_question": "Could you restate the change you want me to make?",
            "candidate_tournament": tournament,
            "user_requested_regeneration": False,
        }
        _log_debug_block(
            "WORKFLOW ANALYSIS FALLBACK",
            {"error": str(exc), "analysis_result": analysis_result},
        )

    validation_result = _build_validation_result(tournament, analysis_result, phase)
    _log_debug_block(
        "WORKFLOW VALIDATION",
        {
            "phase": phase,
            "analysis_result": analysis_result,
            "validation_result": validation_result,
        },
    )

    finalizer_prompt = (
        f"Phase: {phase}\n"
        f"Today's date: {today_str}\n"
        f"Final action: {validation_result['final_action']}\n"
        f"Target readyForGeneration: {str(validation_result['ready_for_generation']).lower()}\n"
        f"Target needsRegeneration: {str(validation_result['needs_regeneration']).lower()}\n\n"
        f"[Phase instructions]\n{phase_instructions}\n\n"
        f"{history_block}"
        f"[Latest user message]\n{user_message}\n\n"
        f"[Current tournament state]\n{json.dumps(tournament, indent=2)}\n\n"
        f"[Candidate tournament state]\n"
        f"{json.dumps(analysis_result['candidate_tournament'], indent=2)}\n\n"
        f"[Workflow analysis]\n{json.dumps(analysis_result, indent=2)}\n\n"
        f"[Validation summary]\n{json.dumps(validation_result, indent=2)}\n\n"
        f"[Retrieved knowledge snippets]\n{retrieved_context}\n"
    )

    try:
        raw_final = await _call_json_step(
            "workflow_finalizer",
            WORKFLOW_FINALIZER_SYSTEM_PROMPT,
            finalizer_prompt,
            retrieval_query,
            retrieved_chunks,
            retrieval_error,
            extra_debug={"phase": phase, "validation": validation_result},
        )
        final_tournament_raw = raw_final.get(
            "tournament",
            analysis_result["candidate_tournament"],
        )
        if not isinstance(final_tournament_raw, dict):
            final_tournament_raw = analysis_result["candidate_tournament"]

        final_tournament = _normalize_tournament(final_tournament_raw)
        final_message = str(raw_final.get("message", "")).strip()
    except Exception as exc:
        final_tournament = analysis_result["candidate_tournament"]
        final_message = validation_result["suggested_question"]
        _log_debug_block(
            "WORKFLOW FINALIZER FALLBACK",
            {"error": str(exc), "message": final_message},
        )

    if validation_result["final_action"] == "clarify" and not final_message:
        final_message = validation_result["suggested_question"]
    if validation_result["final_action"] == "clarify" and phase == "planning":
        ready_for_generation = False
    else:
        ready_for_generation = validation_result["ready_for_generation"]

    if phase == "planning" and ready_for_generation:
        final_message = READY_MESSAGE

    if not final_message:
        final_message = "I updated the tournament."

    return {
        "message": final_message,
        "tournament": final_tournament,
        "ready_for_generation": ready_for_generation,
        "needs_regeneration": validation_result["needs_regeneration"],
        "sources": _serialize_sources(retrieved_chunks),
    }
