import asyncio
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.mcp_weather_client import (
    MCP_WEATHER_SERVER_URL,
    WeatherMcpClientError,
    WeatherLocationResolutionError,
    get_sun_times_for_location_via_mcp,
    get_weather_forecast_by_coordinates_via_mcp,
    get_weather_forecast_via_mcp,
)
from app.services.openai_client import (
    CHAT_DEPLOYMENT,
    LOG_LLM_PROMPTS,
    get_langchain_chat_model,
)
from app.services.rag import (
    LOCAL_EMBEDDING_MODEL,
    format_retrieved_context,
    retrieve_relevant_chunks,
)

DEPLOYMENT = CHAT_DEPLOYMENT
RAG_RETRIEVAL_TIMEOUT_SECONDS = float(os.getenv("RAG_RETRIEVAL_TIMEOUT_SECONDS", "8"))
LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "20"))
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
    "cateringEnabled",
    "cateringBudget",
    "cateringItems",
    "cateringServingTime",
    "cateringDietaryNotes",
}
# Anthropic structured output is tool-calling based (not OpenAI's "json_schema").
LANGCHAIN_STRUCTURED_METHOD = os.getenv("LANGCHAIN_STRUCTURED_METHOD", "function_calling")
logger = logging.getLogger("uvicorn.error")


class StaffingState(BaseModel):
    volunteers: int = 0
    staff: int = 0


class TournamentState(BaseModel):
    id: str = ""
    name: str = ""
    date: str = ""
    venue: str = ""
    format: str = ""
    numberOfDays: int = 0
    playerCount: int = 0
    eventType: str = ""
    teamSize: int = 0
    registrationDeadline: str = ""
    entryFee: int = 0
    description: str = ""
    teeTimeStart: str = "08:00"
    teeTimeInterval: int = 12
    sponsors: List[str] = Field(default_factory=list)
    catering: str = ""
    budget: int = 0
    cateringEnabled: bool = False
    cateringBudget: int = 0
    cateringItems: str = ""
    cateringServingTime: str = ""
    cateringDietaryNotes: str = ""
    staffing: StaffingState = Field(default_factory=StaffingState)
    accessibility: str = ""
    notes: str = ""
    constraints: List[str] = Field(default_factory=list)


class ToolPlan(BaseModel):
    requires_tool: bool = False
    tool_name: Literal[
        "none",
        "get_weather_forecast",
        "get_weather_forecast_by_coordinates",
        "get_sun_times_for_location",
    ] = "none"
    tool_purpose: Literal[
        "none",
        "weather_reply",
        "sun_time_reply",
        "set_tournament_time_from_sun_event",
    ] = "none"
    location_query: str = ""
    use_candidate_venue: bool = False
    target_date: str = ""
    use_candidate_date: bool = False
    forecast_days: int = 3
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target_field: str = ""
    sun_event: Literal["none", "sunrise", "sunset"] = "none"
    offset_minutes: int = 0


class WorkflowAnalysisOutput(BaseModel):
    response_mode: Literal["planner_workflow", "live_data_reply"] = "planner_workflow"
    workflow_action: Literal["update", "clarify"] = "update"
    reasoning_summary: str = ""
    clarifying_focus: str = ""
    clarifying_question: str = ""
    candidate_tournament: TournamentState = Field(default_factory=TournamentState)
    user_requested_regeneration: bool = False
    is_general_question: bool = False
    tool_plan: ToolPlan = Field(default_factory=ToolPlan)


class WorkflowFinalizerOutput(BaseModel):
    message: str = ""
    tournament: TournamentState = Field(default_factory=TournamentState)
    ready_for_generation: bool = False
    needs_regeneration: bool = False


class PendingActionState(BaseModel):
    active: bool = False
    summary: str = ""
    missing_requirements: List[str] = Field(default_factory=list)
    tool_plan: ToolPlan = Field(default_factory=ToolPlan)


class WorkingMemoryState(BaseModel):
    active_goal: str = ""
    open_question: str = ""
    pending_action: PendingActionState = Field(default_factory=PendingActionState)
    last_tool_result: str = ""

PLANNING_SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant.

You will be given:
1. The full conversation history
2. The current tournament object
3. Retrieved knowledge snippets from the local planning library

REQUIRED FIELDS — you must collect ALL of these before generation can begin:
  1.  name                 — tournament name
  2.  date                 — event start date (first day)
  3.  venue                — course / location name (MUST be a real, existing golf course)
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

VENUE VALIDATION — The venue MUST be a real, existing golf course:
- If the user provides a venue name you don't recognize as a real golf course, ask for confirmation
- Common golf course names include: Augusta National, Pebble Beach, St. Andrews, Pine Valley, etc.
- If unsure about a venue name, ask the user to confirm it's a real golf course
- Do not accept generic locations like "city park", "backyard", or non-golf venues
- Always verify venue is golf-related before proceeding

OPTIONAL but useful: entryFee, description, sponsors, staffing, accessibility, notes, constraints.

CATERING WORKFLOW — Follow this sub-sequence when the user mentions catering or food:
  1. Set cateringEnabled = true.
  2. Ask for cateringBudget (REQUIRED once catering is enabled — a positive number in dollars).
  3. Ask for cateringItems — prompt the user for specific example menu items the caterer should provide
     (e.g. "burgers, hot dogs, garden salad, soft drinks, dessert table"). Store as a comma-separated string.
  4. Ask for cateringServingTime (e.g. post-round banquet, at the turn, before the round).
  5. Optionally ask for cateringDietaryNotes (any known dietary requirements).
IMPORTANT: cateringBudget is REQUIRED once cateringEnabled is true — do not mark the event ready
           for generation while cateringEnabled is true and cateringBudget is still 0.

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
tournament object, decide whether clarification is needed, and determine whether a
live-data MCP tool is needed before the final answer is generated.

You will also receive a working-memory object summarizing any still-open question
or pending tool-dependent action from the previous turn.

Return structured output with exactly these top-level fields:
  response_mode              - "planner_workflow" or "live_data_reply"
  workflow_action            - "update" or "clarify"
  reasoning_summary          - one short sentence summarizing the decision
  clarifying_focus           - field name or issue label, or "" if none
  clarifying_question        - one short question if clarification is needed, else ""
  candidate_tournament       - the full drafted tournament object
  user_requested_regeneration - boolean
  tool_plan                  - nested tool plan object

Rules:
- Preserve the existing object structure.
- Apply only explicit user requests and high-confidence inferences.
- If the request is ambiguous, conflicting, or underspecified for a risky change,
  set workflow_action to "clarify" and leave uncertain fields unchanged.
- Do not use workflow_action="clarify" just because other required tournament fields
  are still missing. Missing planning fields can be handled later in a natural follow-up.
- Use retrieved knowledge snippets only as guidance.
- If eventType is "individual", set teamSize to 1 in the candidate object.
- If the user mentions catering or food, set cateringEnabled to true and set
  clarifying_focus to "cateringBudget" if cateringBudget is still 0.
- Always include cateringEnabled (boolean), cateringBudget (number), cateringItems,
  cateringServingTime, and cateringDietaryNotes (strings) in the candidateTournament.
- If the user is asking for live weather, sunrise, or sunset information without changing
  tournament fields, set response_mode to "live_data_reply".
- If the user is asking for golf course verification or information about a specific
  golf course without changing tournament fields, set response_mode to "live_data_reply".
- If the user is asking to search for golf courses in an area without changing
  tournament fields, set response_mode to "live_data_reply".
- If the user is setting a tournament field based on sunrise or sunset, keep
  response_mode as "planner_workflow", preserve any explicit field updates in the
  candidate_tournament, and use tool_plan to describe the required MCP lookup.
- If the user is asking a general question (e.g., requesting advice, suggestions,
  recommendations, or information about catering, vendors, formats, rules, logistics,
  or any other planning topic) rather than purely providing tournament field values,
  set is_general_question to true. This allows the response to answer the question
  using retrieved knowledge even when all required fields are already filled.
- If the user greets you, responds casually, or asks if you are aware of a venue,
  treat that as normal conversation within planning, not as a reason to force a
  missing-field question.
- If working memory shows an open question or pending action, treat short replies
  like "Chicago, Illinois", "June 10", or similar as likely answers to that open
  question when they fit the context.
- If the user provides the missing venue, location, or date needed to complete a
  pending sunrise/sunset-based field update, preserve that update in the candidate
  tournament and describe the required tool lookup in tool_plan so it can resume.
- If the user both updates tournament state and asks a direct question, preserve the
  updates and leave enough information in the result for the final response to answer
  the question naturally.
- When a tool-dependent value such as "10 minutes after sunrise" is requested, do not
  invent the final clock time. Leave the unresolved target field unchanged in
  candidate_tournament until the tool result is available.
- Never treat phrases like "10 minutes after sunrise", "30 minutes before sunset",
  or similar offset expressions as locations.
- If a tool is needed, populate tool_plan precisely:
  requires_tool, tool_name, tool_purpose, location_query, use_candidate_venue,
  target_date, use_candidate_date, forecast_days, latitude, longitude, target_field,
  sun_event, offset_minutes.
- For sunrise/sunset offsets:
  "10 minutes after sunrise" => sun_event="sunrise", offset_minutes=10
  "30 minutes before sunset" => sun_event="sunset", offset_minutes=-30
- If no tool is needed, set tool_plan.requires_tool to false and tool_name to "none".
"""

WORKFLOW_FINALIZER_SYSTEM_PROMPT = """
You are step 2 in a multi-step workflow for a golf tournament assistant.

A previous step already drafted a candidate tournament update. A deterministic
validation step has already checked missing fields, rule violations, regeneration
impact, and the required next action.

Return structured output with exactly these top-level fields:
  message               - natural-language response
  tournament            - full updated tournament object
  ready_for_generation  - boolean
  needs_regeneration    - boolean

Rules:
- Use the supplied target boolean values exactly.
- The assistant should feel like a real planning partner, not a form validator.
- Always react to the user's latest message first.
- If the user greeted you, greet them naturally before moving the conversation forward.
- If the user asked a direct question, answer it clearly even if other planning fields
  are still missing.
- If tournament state changed, confirm the important updates in natural language.
- If a live-data tool result is provided, explicitly say what was found and how it was
  used. For sunrise or sunset calculations, explain the calculation briefly.
- If working memory shows a pending action that is still waiting on one missing input,
  ask only for that missing input and keep the conversation focused on completing the
  user's original request.
- If the user just supplied information that answers the previous open question, make
  that continuity obvious in your response instead of treating it like a brand-new topic.
- If finalAction is "clarify", ask one focused clarification question while preserving
  any safe candidate updates already made.
- If finalAction is "respond", do not sound like a checklist. After acknowledging and
  answering, you may guide the conversation toward one useful next detail.
- When the tournament is still incomplete, prefer one contextual next-step suggestion
  over a rigid required-field interrogation.
- Do not list every missing field unless the user explicitly asks.
- Do not ignore the user's actual request just because format or other required fields
  are still missing.
- If responseMode is "live_data_reply", answer the live-data question directly and do
  not add an unrelated planning follow-up question.
- If a live-data tool result is provided, use that data directly and do not guess.
- If planning mode is ready for generation AND the user is NOT asking a general
  question (is_general_question is false in the workflow analysis), the message must
  be exactly: "Great — I have all the information I need. Click the green button on
  the right to start generating your documents."
- If planning mode is ready for generation AND the user IS asking a general question
  (is_general_question is true), answer their question fully using retrieved knowledge
  snippets, then end with a brief natural sentence such as "Whenever you're ready,
  click the green button on the right to generate your documents."
- Use retrieved knowledge only as guidance.
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
    "cateringEnabled": False,
    "cateringBudget": 0,
    "cateringItems": "",
    "cateringServingTime": "",
    "cateringDietaryNotes": "",
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
        "cateringItems",
        "cateringServingTime",
        "cateringDietaryNotes",
    ):
        if not isinstance(merged.get(text_field), str):
            merged[text_field] = ""

    # cateringEnabled — coerce to bool
    raw_ce = merged.get("cateringEnabled")
    if isinstance(raw_ce, str):
        merged["cateringEnabled"] = raw_ce.strip().lower() in {"true", "yes", "1"}
    else:
        merged["cateringEnabled"] = bool(raw_ce)

    # cateringBudget — coerce to int
    try:
        merged["cateringBudget"] = int(merged.get("cateringBudget") or 0)
    except (TypeError, ValueError):
        merged["cateringBudget"] = 0

    merged["date"] = _normalize_date(merged.get("date", ""))
    merged["registrationDeadline"] = _normalize_date(merged.get("registrationDeadline", ""))

    if merged["eventType"].strip().lower() == "individual":
        merged["teamSize"] = 1

    return merged


def _normalize_working_memory(payload: Any) -> Dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}
    pending_raw = raw.get("pending_action", {})
    if isinstance(pending_raw, BaseModel):
        pending_raw = pending_raw.model_dump()
    if not isinstance(pending_raw, dict):
        pending_raw = {}

    tool_plan = _normalize_tool_plan(pending_raw.get("tool_plan"))
    missing_requirements = []
    for item in pending_raw.get("missing_requirements", []):
        value = str(item).strip().lower()
        if value in {"venue", "location", "date"} and value not in missing_requirements:
            missing_requirements.append(value)

    active = bool(pending_raw.get("active")) and tool_plan.get("requires_tool")
    if not active:
        tool_plan = _normalize_tool_plan({})
        missing_requirements = []

    return {
        "active_goal": str(raw.get("active_goal", "")).strip(),
        "open_question": str(raw.get("open_question", "")).strip(),
        "pending_action": {
            "active": active,
            "summary": str(pending_raw.get("summary", "")).strip(),
            "missing_requirements": missing_requirements,
            "tool_plan": tool_plan,
        },
        "last_tool_result": str(raw.get("last_tool_result", "")).strip(),
    }


def _summarize_working_memory(working_memory: Dict[str, Any]) -> str:
    pending = working_memory.get("pending_action", {})
    bits = []
    if working_memory.get("active_goal"):
        bits.append(f"goal={working_memory['active_goal']}")
    if working_memory.get("open_question"):
        bits.append(f"open_question={working_memory['open_question']}")
    if pending.get("active"):
        bits.append(f"pending={pending.get('summary', '')}")
        if pending.get("missing_requirements"):
            bits.append(
                "missing=" + ",".join(str(item) for item in pending["missing_requirements"])
            )
    if working_memory.get("last_tool_result"):
        bits.append(f"last_tool={working_memory['last_tool_result']}")
    return " | ".join(bit for bit in bits if bit) or "empty"


def _build_retrieval_query(
    user_message: str,
    tournament: Dict[str, Any],
    working_memory: Optional[Dict[str, Any]] = None,
) -> str:
    query_parts = [user_message.strip()]
    working_memory = _normalize_working_memory(working_memory)

    if working_memory.get("active_goal"):
        query_parts.append(f'Active goal: {working_memory["active_goal"]}')
    if working_memory.get("open_question"):
        query_parts.append(f'Open question: {working_memory["open_question"]}')
    pending = working_memory.get("pending_action", {})
    if pending.get("active") and pending.get("summary"):
        query_parts.append(f'Pending action: {pending["summary"]}')

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


def _working_memory_block(working_memory: Dict[str, Any]) -> str:
    return json.dumps(_normalize_working_memory(working_memory), indent=2)


def _pending_action_summary(tool_plan: Dict[str, Any]) -> str:
    purpose = str(tool_plan.get("tool_purpose", "none"))
    if purpose == "set_tournament_time_from_sun_event":
        target_field = str(tool_plan.get("target_field", "")).strip() or "teeTimeStart"
        sun_event = str(tool_plan.get("sun_event", "sunrise")).strip() or "sunrise"
        offset_minutes = int(tool_plan.get("offset_minutes", 0) or 0)
        relation = "after" if offset_minutes >= 0 else "before"
        offset_abs = abs(offset_minutes)
        field_label = _human_field_label(target_field)
        if offset_abs == 0:
            return f"Set {field_label} to {sun_event}"
        return f"Set {field_label} to {offset_abs} minutes {relation} {sun_event}"

    if purpose == "weather_reply":
        return "Answer the live weather question"
    if purpose == "sun_time_reply":
        return "Answer the live sunrise or sunset question"
    if purpose == "verify_course_reply":
        return "Answer the golf course verification question"
    if purpose == "search_courses_reply":
        return "Answer the golf course search question"
    if purpose == "course_details_reply":
        return "Provide detailed golf course information"
    if purpose == "nearby_courses_reply":
        return "Find golf courses near a location"
    return "Complete the pending live-data request"


def _build_history_block(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return ""

    lines = []
    for msg in history:
        label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{label}: {msg['content']}")

    return "[Conversation so far]\n" + "\n".join(lines) + "\n\n"


def _is_direct_field_update(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return False

    if re.search(r"\b(set|change|update|add|remove|use|make)\b.*\b(venue|date|format|player count|team size|registration deadline|tee time|entry fee|catering|staffing|budget|sponsors|accessibility|notes|description)\b", text):
        return True

    if re.search(r"\b(the )?(venue|date|format|player count|team size|registration deadline|tee time|entry fee|catering|staffing|budget|sponsors|accessibility|description)\b.*\b(is|are|will be|should be|must be|should|must)\b", text):
        return True

    if re.search(r"\bmy tournament name is\b|\bit's called\b|\bwe're doing\b|\bwe will have\b|\bwe have\b", text):
        return True

    if "?" not in text and re.search(r"\b(venue|date|format|player count|team size|registration deadline|tee time|entry fee|catering|staffing|budget|sponsors|accessibility|description)\b", text):
        return True

    return False


def _is_general_reference_question(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return False

    question_indicators = [
        r"\bwhat\b",
        r"\bwhy\b",
        r"\bhow\b",
        r"\bwhich\b",
        r"\bwhen\b",
        r"\bwhere\b",
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\badvice\b",
        r"\bbest\b",
        r"\bhelp\b",
        r"\bexample\b",
        r"\bguide\b",
        r"\bshould i\b",
        r"\bcould i\b",
        r"\bcan i\b",
        r"\bdo you\b",
        r"\bdoes this\b",
    ]

    if re.search(r"\?", text):
        return True

    for pattern in question_indicators:
        if re.search(pattern, text):
            return True

    return False


def _should_use_rag(
    user_message: str,
    tournament: Dict[str, Any],
    working_memory: Optional[Dict[str, Any]] = None,
) -> bool:
    if _is_direct_field_update(user_message):
        return False

    if _is_general_reference_question(user_message):
        return True

    if working_memory:
        pending = (working_memory.get("pending_action") or {}).get("active")
        if pending:
            return False

    return False


def _phase_instruction_block(phase: str) -> str:
    return PLANNING_SYSTEM_PROMPT if phase == "planning" else REFINEMENT_SYSTEM_PROMPT


def _preview_text(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _env_flag(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


LOG_CHAT_TRACE = _env_flag("LOG_CHAT_TRACE", "true")


def _short_request_id() -> str:
    return uuid4().hex[:8]


def _summarize_tournament_state(tournament: Dict[str, Any]) -> str:
    interesting_fields = []
    for field in (
        "name",
        "date",
        "venue",
        "format",
        "playerCount",
        "eventType",
        "teamSize",
        "registrationDeadline",
        "teeTimeStart",
        "teeTimeInterval",
    ):
        value = tournament.get(field)
        if value in ("", 0, None):
            continue
        interesting_fields.append(f"{field}={value}")
    return ", ".join(interesting_fields) or "no tournament fields set"


def _changed_fields_summary(
    before: Dict[str, Any],
    after: Dict[str, Any],
    limit: int = 6,
) -> str:
    changed = [
        field
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]
    if not changed:
        return "none"
    if len(changed) <= limit:
        return ", ".join(changed)
    return ", ".join(changed[:limit]) + f", +{len(changed) - limit} more"


def _build_changed_fields_payload(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    payload: Dict[str, Dict[str, Any]] = {}
    for field in sorted(set(before) | set(after)):
        if before.get(field) == after.get(field):
            continue
        payload[field] = {
            "before": before.get(field),
            "after": after.get(field),
        }
    return payload


def _is_greeting(message: str) -> bool:
    return re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", message, re.IGNORECASE) is not None


def _human_field_label(field: str) -> str:
    labels = {
        "name": "tournament name",
        "date": "start date",
        "venue": "venue",
        "format": "format",
        "numberOfDays": "number of days",
        "playerCount": "player count",
        "eventType": "event type",
        "teamSize": "team size",
        "registrationDeadline": "registration deadline",
        "teeTimeStart": "first tee time",
        "teeTimeInterval": "tee time interval",
    }
    return labels.get(field, field)


def _format_changed_field_statement(field: str, change: Dict[str, Any]) -> str:
    after = change.get("after")
    if field == "name":
        return f"set the tournament name to {after}"
    if field == "date":
        return f"set the start date to {after}"
    if field == "venue":
        return f"set the venue to {after}"
    if field == "format":
        return f"set the format to {after}"
    if field == "numberOfDays":
        return f"set the tournament to run for {after} day{'s' if after != 1 else ''}"
    if field == "playerCount":
        return f"set the player count to {after}"
    if field == "eventType":
        return f"set the event type to {after}"
    if field == "teamSize":
        return f"set the team size to {after}"
    if field == "registrationDeadline":
        return f"set the registration deadline to {after}"
    if field == "teeTimeStart":
        return f"set the first tee time to {after}"
    if field == "teeTimeInterval":
        return f"set the tee time interval to {after} minutes"
    return f"updated {field} to {after}"


def _join_phrases(phrases: List[str]) -> str:
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"


def _safe_parse_tool_context(tool_context: str) -> Dict[str, Any]:
    try:
        payload = json.loads(tool_context)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    return {}


def _fallback_conversational_response(
    user_message: str,
    original_tournament: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
    validation_result: Dict[str, Any],
    analysis_result: Dict[str, Any],
    tool_context: str,
    phase: str,
) -> str:
    lowered = user_message.lower()
    changes = _build_changed_fields_payload(original_tournament, candidate_tournament)
    tool_payload = _safe_parse_tool_context(tool_context)
    response_parts: List[str] = []

    if _is_greeting(user_message) and not changes:
        response_parts.append("Hi! Happy to help you plan your tournament.")
    elif changes:
        ordered_fields = [
            field
            for field in (
                "name",
                "date",
                "venue",
                "format",
                "numberOfDays",
                "playerCount",
                "eventType",
                "teamSize",
                "registrationDeadline",
                "teeTimeStart",
                "teeTimeInterval",
            )
            if field in changes
        ]
        update_bits = [_format_changed_field_statement(field, changes[field]) for field in ordered_fields]
        if update_bits:
            response_parts.append(f"I've {_join_phrases(update_bits)}.")

    if "aware of this course" in lowered or "aware of this venue" in lowered:
        venue = str(candidate_tournament.get("venue", "")).strip()
        if venue:
            response_parts.append(
                f"Yes, I can work with {venue} as your venue and use that location for planning details like tee times, sunrise, and logistics."
            )

    if (
        analysis_result.get("tool_plan", {}).get("tool_purpose") == "set_tournament_time_from_sun_event"
        and tool_payload
    ):
        sun_event = str(analysis_result.get("tool_plan", {}).get("sun_event", "sunrise"))
        base_value = tool_payload.get(f"{sun_event}_hm", "")
        applied_value = tool_payload.get("applied_value", "")
        offset_minutes = int(analysis_result.get("tool_plan", {}).get("offset_minutes", 0) or 0)
        if base_value and applied_value:
            relation = "after" if offset_minutes >= 0 else "before"
            offset_abs = abs(offset_minutes)
            response_parts.append(
                f"{sun_event.capitalize()} for that date is {base_value}, so I set the first tee time to {applied_value} by applying {offset_abs} minutes {relation} {sun_event}."
            )

    if not response_parts:
        if validation_result["final_action"] == "clarify":
            response_parts.append(validation_result["suggested_question"])
        else:
            response_parts.append("I updated the tournament details.")

    if validation_result["final_action"] == "clarify":
        if response_parts[-1] != validation_result["suggested_question"]:
            response_parts.append(validation_result["suggested_question"])
    elif phase == "planning" and validation_result["missing_fields"]:
        next_field = validation_result["missing_fields"][0]
        if _is_greeting(user_message) and not changes:
            response_parts.append("What would you like to set up first?")
        else:
            response_parts.append(
                f"Next, we can sort out the {_human_field_label(next_field)} when you're ready."
            )

    return " ".join(part.strip() for part in response_parts if part.strip())


def _summarize_tool_plan(tool_plan: Dict[str, Any]) -> str:
    if not tool_plan.get("requires_tool"):
        return "no MCP tool needed"

    parts = [
        f"tool={tool_plan.get('tool_name')}",
        f"purpose={tool_plan.get('tool_purpose')}",
    ]
    if tool_plan.get("location_query"):
        parts.append(f"location={tool_plan['location_query']}")
    elif tool_plan.get("use_candidate_venue"):
        parts.append("location=<candidate venue>")
    if tool_plan.get("target_date"):
        parts.append(f"date={tool_plan['target_date']}")
    elif tool_plan.get("use_candidate_date"):
        parts.append("date=<candidate date>")
    if tool_plan.get("sun_event") and tool_plan.get("sun_event") != "none":
        parts.append(f"sun_event={tool_plan['sun_event']}")
    if tool_plan.get("offset_minutes"):
        parts.append(f"offset={tool_plan['offset_minutes']}m")
    if tool_plan.get("target_field"):
        parts.append(f"target_field={tool_plan['target_field']}")
    if tool_plan.get("latitude") is not None and tool_plan.get("longitude") is not None:
        parts.append(f"coords={tool_plan['latitude']},{tool_plan['longitude']}")
    return ", ".join(parts)


def _trace(request_id: str, step: str, **details: Any) -> None:
    if not LOG_CHAT_TRACE:
        return

    parts = [f"[chat:{request_id}] {step}"]
    for key, value in details.items():
        if value in (None, "", [], {}):
            continue
        if isinstance(value, str):
            rendered = value
        else:
            rendered = str(value)
        parts.append(f"{key}={rendered}")
    logger.info(" | ".join(parts))


def _serialize_sources(chunks: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "title": chunk.title,
            "chunk_id": chunk.chunk_id,
            "score": round(chunk.score, 3),
            "preview": _preview_text(chunk.text),
            "content": chunk.text,
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


def _structured_output_to_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump()
    if isinstance(payload, dict):
        return payload
    raise TypeError("Structured LLM step returned an invalid payload type.")


async def _call_structured_step(
    step_name: str,
    system_prompt: str,
    user_prompt: str,
    schema: type[BaseModel],
    retrieval_query: str,
    retrieved_chunks: List[Any],
    retrieval_error: Optional[str] = None,
    extra_debug: Optional[Dict[str, Any]] = None,
    request_id: str = "",
) -> Dict[str, Any]:
    log_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    model_messages = [
        ("system", system_prompt),
        ("human", user_prompt),
    ]
    _log_llm_step(
        step_name,
        log_messages,
        retrieval_query,
        retrieved_chunks,
        retrieval_error,
        extra_debug,
    )
    _trace(
        request_id,
        f"LLM {step_name.upper()} START",
        retrieval_chunks=len(retrieved_chunks),
        retrieval_error=retrieval_error or "",
    )

    llm = get_langchain_chat_model(temperature=0.2)
    try:
        structured_llm = llm.with_structured_output(
            schema,
            method=LANGCHAIN_STRUCTURED_METHOD,
        )
        parsed = await asyncio.wait_for(
            structured_llm.ainvoke(model_messages),
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )
    except Exception:
        if LANGCHAIN_STRUCTURED_METHOD != "json_schema":
            raise
        structured_llm = llm.with_structured_output(schema)
        parsed = await asyncio.wait_for(
            structured_llm.ainvoke(model_messages),
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
        )

    parsed_payload = _structured_output_to_dict(parsed)
    _log_debug_block(
        f"LLM STEP {step_name.upper()} RESULT",
        {"step": step_name, "parsed": parsed_payload},
    )
    _trace(
        request_id,
        f"LLM {step_name.upper()} RESULT",
        preview=_preview_text(json.dumps(parsed_payload, ensure_ascii=False), 220),
    )
    return parsed_payload


def _normalize_iso_date(value: str) -> str:
    if not value or not value.strip():
        return ""

    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _normalize_tool_plan(payload: Any) -> Dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}
    tool_name = str(raw.get("tool_name", "none")).strip()
    if tool_name not in {
        "none",
        "get_weather_forecast",
        "get_weather_forecast_by_coordinates",
        "get_sun_times_for_location",
    }:
        tool_name = "none"

    tool_purpose = str(raw.get("tool_purpose", "none")).strip()
    if tool_purpose not in {
        "none",
        "weather_reply",
        "sun_time_reply",
        "set_tournament_time_from_sun_event",
    }:
        tool_purpose = "none"

    sun_event = str(raw.get("sun_event", "none")).strip().lower()
    if sun_event not in {"none", "sunrise", "sunset"}:
        sun_event = "none"

    def _float_or_none(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    try:
        forecast_days = int(raw.get("forecast_days", 3) or 3)
    except (TypeError, ValueError):
        forecast_days = 3

    try:
        offset_minutes = int(raw.get("offset_minutes", 0) or 0)
    except (TypeError, ValueError):
        offset_minutes = 0

    return {
        "requires_tool": bool(raw.get("requires_tool")) and tool_name != "none",
        "tool_name": tool_name,
        "tool_purpose": tool_purpose,
        "location_query": str(raw.get("location_query", "")).strip(),
        "use_candidate_venue": bool(raw.get("use_candidate_venue")),
        "target_date": _normalize_iso_date(str(raw.get("target_date", "")).strip()),
        "use_candidate_date": bool(raw.get("use_candidate_date")),
        "forecast_days": max(1, min(forecast_days, 16)),
        "latitude": _float_or_none(raw.get("latitude")),
        "longitude": _float_or_none(raw.get("longitude")),
        "target_field": str(raw.get("target_field", "")).strip(),
        "sun_event": sun_event,
        "offset_minutes": offset_minutes,
    }


def _normalize_analysis_result(
    analysis: Dict[str, Any],
    tournament: Dict[str, Any],
) -> Dict[str, Any]:
    workflow_action = str(analysis.get("workflow_action", "update")).strip().lower()
    if workflow_action not in {"update", "clarify"}:
        workflow_action = "update"

    response_mode = str(analysis.get("response_mode", "planner_workflow")).strip().lower()
    if response_mode not in {"planner_workflow", "live_data_reply"}:
        response_mode = "planner_workflow"

    candidate_raw = analysis.get("candidate_tournament", tournament)
    if isinstance(candidate_raw, BaseModel):
        candidate_raw = candidate_raw.model_dump()
    if not isinstance(candidate_raw, dict):
        candidate_raw = tournament

    return {
        "response_mode": response_mode,
        "workflow_action": workflow_action,
        "reasoning_summary": str(analysis.get("reasoning_summary", "")).strip(),
        "clarifying_focus": str(analysis.get("clarifying_focus", "")).strip(),
        "clarifying_question": str(analysis.get("clarifying_question", "")).strip(),
        "candidate_tournament": _normalize_tournament(candidate_raw),
        "user_requested_regeneration": bool(
            analysis.get("user_requested_regeneration", False)
        ),
        "is_general_question": bool(analysis.get("is_general_question", False)),
        "tool_plan": _normalize_tool_plan(analysis.get("tool_plan")),
    }


def _format_value(value: Any, suffix: str = "") -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value)}{suffix}"
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _format_timestamp(value: Any) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(value)


def _build_weather_source(weather: Dict[str, Any]) -> Dict[str, Any]:
    resolved_location = weather.get("resolved_location") or {}
    current = weather.get("current_weather") or {}
    today = (weather.get("daily_forecast") or [{}])[0]
    preview_bits = []

    if current.get("weather_summary") and current.get("temperature_c") is not None:
        preview_bits.append(
            f"{current['weather_summary']}, {_format_value(current['temperature_c'], 'C')}"
        )
    sunrise = _format_timestamp(today.get("sunrise"))
    sunset = _format_timestamp(today.get("sunset"))
    if sunrise and sunset:
        preview_bits.append(f"sunrise {sunrise}, sunset {sunset}")

    return {
        "title": f"Live Weather via MCP: {resolved_location.get('display_name', 'Resolved Location')}",
        "chunk_id": "weather_live",
        "score": 1.0,
        "preview": " | ".join(preview_bits)[:160] or "Live weather lookup via local MCP server.",
        "content": json.dumps(
            {
                "resolved_location": weather.get("resolved_location"),
                "current_weather": weather.get("current_weather"),
                "daily_forecast": (weather.get("daily_forecast") or [])[:1],
            },
            indent=2,
        ),
    }


def _build_sun_times_source(sun_times: Dict[str, Any]) -> Dict[str, Any]:
    resolved_location = sun_times.get("resolved_location") or {}
    preview_bits = []

    sunrise = _format_timestamp(sun_times.get("sunrise"))
    sunset = _format_timestamp(sun_times.get("sunset"))
    if sunrise:
        preview_bits.append(f"sunrise {sunrise}")
    if sunset:
        preview_bits.append(f"sunset {sunset}")
    if sun_times.get("date"):
        preview_bits.append(str(sun_times["date"]))

    return {
        "title": f"Live Sun Times via MCP: {resolved_location.get('display_name', 'Resolved Location')}",
        "chunk_id": "weather_sun_times_live",
        "score": 1.0,
        "preview": " | ".join(preview_bits)[:160] or "Live sunrise and sunset lookup via local MCP server.",
        "content": json.dumps(
            {
                "resolved_location": sun_times.get("resolved_location"),
                "date": sun_times.get("date"),
                "sunrise": sun_times.get("sunrise"),
                "sunset": sun_times.get("sunset"),
                "sunrise_hm": sun_times.get("sunrise_hm"),
                "sunset_hm": sun_times.get("sunset_hm"),
            },
            indent=2,
        ),
    }


def _resolve_tool_location_query(
    tool_plan: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
) -> str:
    if tool_plan.get("location_query"):
        return str(tool_plan["location_query"]).strip()
    if tool_plan.get("use_candidate_venue"):
        return str(candidate_tournament.get("venue", "")).strip()
    return ""


def _resolve_tool_target_date(
    tool_plan: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
) -> str:
    if tool_plan.get("target_date"):
        return str(tool_plan["target_date"]).strip()
    if tool_plan.get("use_candidate_date"):
        return _normalize_iso_date(str(candidate_tournament.get("date", "")).strip())
    return ""


def _tool_missing_requirements(
    tool_plan: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
) -> List[str]:
    tool_name = str(tool_plan.get("tool_name", "none"))
    if tool_name == "none" or not tool_plan.get("requires_tool"):
        return []

    missing: List[str] = []

    if tool_name in {"get_weather_forecast", "get_sun_times_for_location"}:
        location_query = _resolve_tool_location_query(tool_plan, candidate_tournament)
        if not location_query:
            missing.append("venue" if tool_plan.get("use_candidate_venue") else "location")

    if tool_name == "get_sun_times_for_location":
        target_date = _resolve_tool_target_date(tool_plan, candidate_tournament)
        if not target_date:
            missing.append("date")

    return missing


def _tool_follow_up_question(
    tool_plan: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
    missing_requirements: List[str],
) -> str:
    purpose = str(tool_plan.get("tool_purpose", "none"))
    sun_event = str(tool_plan.get("sun_event", "sunrise") or "sunrise")
    date_label = str(candidate_tournament.get("date", "")).strip()
    venue_label = str(candidate_tournament.get("venue", "")).strip()

    if purpose == "set_tournament_time_from_sun_event":
        if missing_requirements == ["venue"]:
            if date_label:
                return f"What venue or location should I use to calculate {sun_event} on {date_label}?"
            return f"What venue or location should I use to calculate {sun_event} for that tee time?"
        if missing_requirements == ["date"]:
            if venue_label:
                return f"What date should I use to calculate {sun_event} for {venue_label}?"
            return f"What date should I use to calculate {sun_event} for that tee time?"
        if set(missing_requirements) == {"venue", "date"}:
            return f"What venue or location should I use, and what date should I calculate {sun_event} for?"

    if str(tool_plan.get("tool_name", "none")) in {
        "get_weather_forecast",
        "get_weather_forecast_by_coordinates",
    }:
        if "location" in missing_requirements or "venue" in missing_requirements:
            return "What location should I use for the live weather lookup?"

    if missing_requirements:
        if len(missing_requirements) == 1:
            return f"What {missing_requirements[0]} should I use?"
        return "What missing details should I use to finish that request?"

    return ""


def _build_tool_status_context(
    tool_name: str,
    tool_purpose: str,
    status: str,
    message: str = "",
    missing_requirements: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    payload = {
        "tool_name": tool_name,
        "tool_purpose": tool_purpose,
        "status": status,
        "message": message,
        "missing_requirements": list(missing_requirements or []),
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, indent=2)


def _should_resume_pending_action(
    working_memory: Dict[str, Any],
    original_tournament: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
    current_tool_plan: Dict[str, Any],
) -> bool:
    if current_tool_plan.get("requires_tool"):
        return False

    pending = (working_memory.get("pending_action") or {})
    if not pending.get("active"):
        return False

    pending_tool_plan = pending.get("tool_plan") or {}
    if not pending_tool_plan.get("requires_tool"):
        return False

    changed_fields = set(_build_changed_fields_payload(original_tournament, candidate_tournament).keys())
    required_fields = {
        "venue" if item == "location" else item
        for item in (pending.get("missing_requirements") or [])
    }
    if required_fields and not changed_fields.intersection(required_fields):
        return False

    current_missing = set(_tool_missing_requirements(pending_tool_plan, candidate_tournament))
    return not current_missing


def _build_next_working_memory(
    previous_working_memory: Dict[str, Any],
    original_tournament: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
    analysis_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    tool_result: Dict[str, Any],
) -> Dict[str, Any]:
    working_memory = _normalize_working_memory(previous_working_memory)
    pending = dict(working_memory.get("pending_action", {}))
    pending_tool_plan = dict(pending.get("tool_plan", {}))
    changed_fields = _build_changed_fields_payload(original_tournament, candidate_tournament)
    tool_status = str(tool_result.get("tool_status", "skipped"))
    tool_summary = ""

    tool_payload = _safe_parse_tool_context(str(tool_result.get("tool_context", "")))
    if tool_status == "success":
        if tool_payload.get("applied_value"):
            tool_summary = f"Applied {tool_payload['applied_value']} using live {tool_payload.get('tool_name', 'tool')} data"
        elif tool_payload.get("resolved_location"):
            resolved = tool_payload.get("resolved_location") or {}
            display_name = resolved.get("display_name", "") if isinstance(resolved, dict) else ""
            tool_summary = display_name or "Live data lookup completed"
        pending = {
            "active": False,
            "summary": "",
            "missing_requirements": [],
            "tool_plan": _normalize_tool_plan({}),
        }
        working_memory["open_question"] = ""
    elif tool_status == "pending_input":
        missing_requirements = list(tool_result.get("missing_requirements") or [])
        tool_plan = _normalize_tool_plan(tool_result.get("pending_tool_plan") or analysis_result.get("tool_plan"))
        pending = {
            "active": tool_plan.get("requires_tool", False),
            "summary": _pending_action_summary(tool_plan),
            "missing_requirements": missing_requirements,
            "tool_plan": tool_plan,
        }
        working_memory["open_question"] = (
            str(tool_result.get("follow_up_question", "")).strip()
            or str(analysis_result.get("clarifying_question", "")).strip()
            or str(validation_result.get("suggested_question", "")).strip()
        )
    else:
        target_field = str(pending_tool_plan.get("target_field", "")).strip()
        if target_field and target_field in changed_fields and tool_status != "success":
            pending = {
                "active": False,
                "summary": "",
                "missing_requirements": [],
                "tool_plan": _normalize_tool_plan({}),
            }
            working_memory["open_question"] = ""
        elif validation_result["final_action"] == "clarify":
            working_memory["open_question"] = (
                str(analysis_result.get("clarifying_question", "")).strip()
                or str(validation_result.get("suggested_question", "")).strip()
            )
        elif not pending.get("active"):
            working_memory["open_question"] = ""

    working_memory["pending_action"] = pending
    if pending.get("active"):
        working_memory["active_goal"] = pending.get("summary", "")
    elif changed_fields:
        changed_phrases = [
            _format_changed_field_statement(field, payload)
            for field, payload in changed_fields.items()
        ]
        working_memory["active_goal"] = _join_phrases(changed_phrases)
    elif validation_result["final_action"] == "clarify":
        working_memory["active_goal"] = str(validation_result.get("primary_focus", "")).strip()
    else:
        working_memory["active_goal"] = ""

    if tool_summary:
        working_memory["last_tool_result"] = tool_summary
    elif tool_status == "error":
        working_memory["last_tool_result"] = str(tool_result.get("error_message", "")).strip()
    elif tool_status == "pending_input" or tool_status == "skipped":
        if not pending.get("active"):
            working_memory["last_tool_result"] = ""

    return _normalize_working_memory(working_memory)

def _offset_clock_time(value: str, offset_minutes: int) -> str:
    base = datetime.strptime(value, "%H:%M")
    shifted = base + timedelta(minutes=offset_minutes)
    return shifted.strftime("%H:%M")


def _build_tool_error_response(
    message: str,
    tournament: Dict[str, Any],
    phase: str,
) -> Dict[str, Any]:
    return {
        "message": message,
        "tournament": tournament,
        "ready_for_generation": False,
        "needs_regeneration": phase == "refinement",
        "sources": [],
    }


async def _execute_tool_plan(
    tool_plan: Dict[str, Any],
    candidate_tournament: Dict[str, Any],
    phase: str,
    request_id: str = "",
) -> Dict[str, Any]:
    if not tool_plan.get("requires_tool"):
        _trace(request_id, "MCP SKIPPED", reason="no tool needed")
        return {
            "used": False,
            "tool_status": "skipped",
            "candidate_tournament": candidate_tournament,
            "tool_context": "No live-data MCP tool was used.",
            "sources": [],
        }

    tool_name = str(tool_plan.get("tool_name", "none"))
    tool_purpose = str(tool_plan.get("tool_purpose", "none"))
    _trace(
        request_id,
        "MCP PLAN",
        summary=_summarize_tool_plan(tool_plan),
    )

    try:
        if tool_name == "get_weather_forecast_by_coordinates":
            latitude = tool_plan.get("latitude")
            longitude = tool_plan.get("longitude")
            if latitude is None or longitude is None:
                return {
                    "used": False,
                    "tool_status": "pending_input",
                    "candidate_tournament": candidate_tournament,
                    "tool_context": _build_tool_status_context(
                        tool_name,
                        tool_purpose,
                        "pending_input",
                        "I can look up live weather, but I need valid coordinates first.",
                        ["location"],
                    ),
                    "follow_up_question": "What coordinates should I use for the live weather lookup?",
                    "missing_requirements": ["location"],
                    "pending_tool_plan": tool_plan,
                    "sources": [],
                }

            weather = await get_weather_forecast_by_coordinates_via_mcp(
                latitude=float(latitude),
                longitude=float(longitude),
                forecast_days=int(tool_plan.get("forecast_days", 3) or 3),
            )
            resolved_location = (weather.get("resolved_location") or {}).get("display_name", "")
            current_weather = weather.get("current_weather") or {}
            _trace(
                request_id,
                "MCP RESULT",
                tool=tool_name,
                resolved_location=resolved_location or f"{latitude},{longitude}",
                weather=f"{current_weather.get('weather_summary', '')} {_format_value(current_weather.get('temperature_c'), 'C')}".strip(),
            )
            tool_context = json.dumps(
                {
                    "tool_name": tool_name,
                    "tool_purpose": tool_purpose,
                    "resolved_location": weather.get("resolved_location"),
                    "current_weather": weather.get("current_weather"),
                    "daily_forecast": (weather.get("daily_forecast") or [])[:3],
                },
                indent=2,
            )
            return {
                "used": True,
                "tool_status": "success",
                "candidate_tournament": candidate_tournament,
                "tool_context": tool_context,
                "sources": [_build_weather_source(weather)],
            }

        if tool_name == "get_weather_forecast":
            location_query = _resolve_tool_location_query(tool_plan, candidate_tournament)
            if not location_query:
                missing_requirements = _tool_missing_requirements(tool_plan, candidate_tournament)
                return {
                    "used": False,
                    "tool_status": "pending_input",
                    "candidate_tournament": candidate_tournament,
                    "tool_context": _build_tool_status_context(
                        tool_name,
                        tool_purpose,
                        "pending_input",
                        "I can look up live weather, but I need a location first.",
                        missing_requirements,
                    ),
                    "follow_up_question": _tool_follow_up_question(
                        tool_plan,
                        candidate_tournament,
                        missing_requirements,
                    ),
                    "missing_requirements": missing_requirements,
                    "pending_tool_plan": tool_plan,
                    "sources": [],
                }

            weather = await get_weather_forecast_via_mcp(
                location_query=location_query,
                forecast_days=int(tool_plan.get("forecast_days", 3) or 3),
            )
            resolved_location = (weather.get("resolved_location") or {}).get("display_name", "")
            current_weather = weather.get("current_weather") or {}
            _trace(
                request_id,
                "MCP RESULT",
                tool=tool_name,
                resolved_location=resolved_location or location_query,
                weather=f"{current_weather.get('weather_summary', '')} {_format_value(current_weather.get('temperature_c'), 'C')}".strip(),
            )
            tool_context = json.dumps(
                {
                    "tool_name": tool_name,
                    "tool_purpose": tool_purpose,
                    "resolved_location": weather.get("resolved_location"),
                    "current_weather": weather.get("current_weather"),
                    "daily_forecast": (weather.get("daily_forecast") or [])[:3],
                },
                indent=2,
            )
            return {
                "used": True,
                "tool_status": "success",
                "candidate_tournament": candidate_tournament,
                "tool_context": tool_context,
                "sources": [_build_weather_source(weather)],
            }

        if tool_name == "get_sun_times_for_location":
            location_query = _resolve_tool_location_query(tool_plan, candidate_tournament)
            target_date = _resolve_tool_target_date(tool_plan, candidate_tournament)
            if not location_query or not target_date:
                missing_requirements = _tool_missing_requirements(tool_plan, candidate_tournament)
                follow_up_question = _tool_follow_up_question(
                    tool_plan,
                    candidate_tournament,
                    missing_requirements,
                )
                return {
                    "used": False,
                    "tool_status": "pending_input",
                    "candidate_tournament": candidate_tournament,
                    "tool_context": _build_tool_status_context(
                        tool_name,
                        tool_purpose,
                        "pending_input",
                        "I can use sunrise or sunset for that request, but I still need more information.",
                        missing_requirements,
                    ),
                    "follow_up_question": follow_up_question,
                    "missing_requirements": missing_requirements,
                    "pending_tool_plan": tool_plan,
                    "sources": [],
                }

            sun_times = await get_sun_times_for_location_via_mcp(
                location_query=location_query,
                target_date=target_date,
            )
            updated_tournament = dict(candidate_tournament)
            applied_value = ""
            if tool_purpose == "set_tournament_time_from_sun_event":
                sun_event = str(tool_plan.get("sun_event", "none"))
                target_field = str(tool_plan.get("target_field", "")).strip() or "teeTimeStart"
                base_value = str(sun_times.get(f"{sun_event}_hm", "")).strip()
                if not base_value:
                    return {
                        "used": False,
                        "tool_status": "error",
                        "candidate_tournament": candidate_tournament,
                        "tool_context": _build_tool_status_context(
                            tool_name,
                            tool_purpose,
                            "error",
                            f"I found the location, but I couldn't determine the {sun_event} time for that date.",
                        ),
                        "error_message": f"I found the location, but I couldn't determine the {sun_event} time for that date.",
                        "sources": [],
                    }
                applied_value = _offset_clock_time(
                    base_value,
                    int(tool_plan.get("offset_minutes", 0) or 0),
                )
                updated_tournament[target_field] = applied_value
            resolved_location = (sun_times.get("resolved_location") or {}).get("display_name", "")
            _trace(
                request_id,
                "MCP RESULT",
                tool=tool_name,
                resolved_location=resolved_location or location_query,
                sunrise=sun_times.get("sunrise_hm", ""),
                sunset=sun_times.get("sunset_hm", ""),
                applied_value=applied_value,
            )

            tool_context = json.dumps(
                {
                    "tool_name": tool_name,
                    "tool_purpose": tool_purpose,
                    "resolved_location": sun_times.get("resolved_location"),
                    "date": sun_times.get("date"),
                    "sunrise": sun_times.get("sunrise"),
                    "sunset": sun_times.get("sunset"),
                    "sunrise_hm": sun_times.get("sunrise_hm"),
                    "sunset_hm": sun_times.get("sunset_hm"),
                    "target_field": tool_plan.get("target_field", ""),
                    "offset_minutes": tool_plan.get("offset_minutes", 0),
                    "applied_value": applied_value,
                },
                indent=2,
            )
            return {
                "used": True,
                "tool_status": "success",
                "candidate_tournament": _normalize_tournament(updated_tournament),
                "tool_context": tool_context,
                "sources": [_build_sun_times_source(sun_times)],
            }

        return {
            "used": False,
            "tool_status": "error",
            "candidate_tournament": candidate_tournament,
            "tool_context": _build_tool_status_context(
                tool_name,
                tool_purpose,
                "error",
                "I identified a live-data request, but the requested tool is not supported yet.",
            ),
            "error_message": "I identified a live-data request, but the requested tool is not supported yet.",
            "sources": [],
        }
    except WeatherLocationResolutionError as exc:
        if tool_purpose == "set_tournament_time_from_sun_event":
            message = f"I couldn't resolve the venue for the sunrise or sunset lookup. {exc}"
        else:
            message = f"I couldn't resolve that location for live weather lookup. {exc}"
        _trace(request_id, "MCP ERROR", tool=tool_name, error=message)
        return {
            "used": False,
            "tool_status": "error",
            "candidate_tournament": candidate_tournament,
            "tool_context": _build_tool_status_context(
                tool_name,
                tool_purpose,
                "error",
                message,
            ),
            "error_message": message,
            "sources": [],
        }
    except WeatherMcpClientError as exc:
        message = (
            f"I couldn't reach the live weather service. {exc} "
            f"Make sure the local MCP server is running at `{MCP_WEATHER_SERVER_URL}`."
        )
        _trace(request_id, "MCP ERROR", tool=tool_name, error=message)
        return {
            "used": False,
            "tool_status": "error",
            "candidate_tournament": candidate_tournament,
            "tool_context": _build_tool_status_context(
                tool_name,
                tool_purpose,
                "error",
                message,
            ),
            "error_message": message,
            "sources": [],
        }

        return {
            "used": False,
            "tool_status": "error",
            "candidate_tournament": candidate_tournament,
            "tool_context": _build_tool_status_context(
                tool_name,
                tool_purpose,
                "error",
                f"Unsupported tool: {tool_name}",
            ),
            "error_message": f"Unsupported tool: {tool_name}",
            "sources": [],
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

    if tournament.get("cateringEnabled") is True and not int(tournament.get("cateringBudget") or 0) > 0:
        issues.append(
            {
                "code": "catering_budget_required",
                "field": "cateringBudget",
                "message": "A catering budget is required when catering is enabled.",
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
        if first_issue["field"] == "cateringBudget":
            return "You've indicated catering is needed — what is the catering budget?"

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


def _build_direct_update_response(
    original_tournament: Dict[str, Any],
    custom_result: Dict[str, Any],
    phase: str,
) -> Dict[str, Any]:
    analysis_result = {
        "workflow_action": str(custom_result.get("workflow_action", "update")).strip().lower()
        or "update",
        "reasoning_summary": "",
        "clarifying_focus": "",
        "clarifying_question": "",
        "candidate_tournament": _normalize_tournament(
            custom_result.get("candidate_tournament", original_tournament)
        ),
        "user_requested_regeneration": False,
    }
    validation_result = _build_validation_result(original_tournament, analysis_result, phase)

    message = str(custom_result.get("message", "")).strip()
    if phase == "planning" and validation_result["ready_for_generation"]:
        message = READY_MESSAGE
    elif custom_result.get("append_follow_up_question") and validation_result["final_action"] == "clarify":
        follow_up = validation_result["suggested_question"].strip()
        if follow_up:
            message = f"{message} {follow_up}".strip()

    return {
        "message": message,
        "tournament": analysis_result["candidate_tournament"],
        "ready_for_generation": validation_result["ready_for_generation"],
        "needs_regeneration": validation_result["needs_regeneration"],
        "sources": list(custom_result.get("sources") or []),
    }


async def handle_chat(
    user_message: str,
    tournament: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
    phase: str = "planning",
    working_memory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request_id = _short_request_id()
    phase = "refinement" if phase == "refinement" else "planning"
    tournament = _normalize_tournament(tournament)
    working_memory = _normalize_working_memory(working_memory)
    analysis_failed = False
    analysis_failure_error = ""
    _trace(
        request_id,
        "REQUEST",
        phase=phase,
        user=_preview_text(user_message, 180),
        tournament=_summarize_tournament_state(tournament),
        memory=_summarize_working_memory(working_memory),
    )

    use_rag = _should_use_rag(user_message, tournament, working_memory)
    retrieval_query = _build_retrieval_query(user_message, tournament, working_memory)
    retrieved_chunks: List[Any] = []
    retrieval_error = None

    if use_rag:
        try:
            retrieved_chunks = await asyncio.wait_for(
                retrieve_relevant_chunks(retrieval_query),
                timeout=RAG_RETRIEVAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            retrieval_error = (
                "RAG retrieval timed out before the local embedding model became ready."
            )
            retrieved_chunks = []
        except Exception as exc:
            retrieval_error = str(exc)
            retrieved_chunks = []
    else:
        retrieval_query = ""

    _trace(
        request_id,
        "RETRIEVAL",
        rag_used=use_rag,
        chunks=len(retrieved_chunks),
        error=retrieval_error or "",
    )

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
        f"[Working memory]\n{_working_memory_block(working_memory)}\n\n"
        f"[Retrieved knowledge snippets]\n{retrieved_context}\n"
    )

    try:
        raw_analysis = await _call_structured_step(
            "workflow_analysis",
            WORKFLOW_ANALYZER_SYSTEM_PROMPT,
            analysis_prompt,
            WorkflowAnalysisOutput,
            retrieval_query,
            retrieved_chunks,
            retrieval_error,
            extra_debug={"phase": phase},
            request_id=request_id,
        )
        analysis_result = _normalize_analysis_result(raw_analysis, tournament)
    except Exception as exc:
        analysis_failed = True
        analysis_failure_error = str(exc)
        analysis_result = {
            "response_mode": "planner_workflow",
            "workflow_action": "clarify",
            "reasoning_summary": "Analysis step failed because the model service was unavailable.",
            "clarifying_focus": "",
            "clarifying_question": "",
            "candidate_tournament": tournament,
            "user_requested_regeneration": False,
            "is_general_question": False,
            "tool_plan": _normalize_tool_plan({}),
        }
        _log_debug_block(
            "WORKFLOW ANALYSIS FALLBACK",
            {"error": str(exc), "analysis_result": analysis_result},
        )
    _trace(
        request_id,
        "ANALYSIS",
        mode=analysis_result["response_mode"],
        action=analysis_result["workflow_action"],
        reason=analysis_result["reasoning_summary"],
        tool=_summarize_tool_plan(analysis_result.get("tool_plan", {})),
        candidate_changes=_changed_fields_summary(tournament, analysis_result["candidate_tournament"]),
    )

    if _should_resume_pending_action(
        working_memory,
        tournament,
        analysis_result["candidate_tournament"],
        analysis_result.get("tool_plan", {}),
    ):
        pending_tool_plan = _normalize_tool_plan(
            ((working_memory.get("pending_action") or {}).get("tool_plan") or {})
        )
        analysis_result["tool_plan"] = pending_tool_plan
        analysis_result["workflow_action"] = "update"
        analysis_result["response_mode"] = (
            "planner_workflow"
            if pending_tool_plan.get("tool_purpose") == "set_tournament_time_from_sun_event"
            else analysis_result["response_mode"]
        )
        analysis_result["reasoning_summary"] = (
            analysis_result["reasoning_summary"] + " "
            + "Resumed the pending tool-dependent request after receiving the missing details."
        ).strip()
        _trace(
            request_id,
            "PENDING ACTION RESUMED",
            tool=_summarize_tool_plan(pending_tool_plan),
            memory=_summarize_working_memory(working_memory),
        )

    tool_result = await _execute_tool_plan(
        analysis_result.get("tool_plan", {}),
        analysis_result["candidate_tournament"],
        phase,
        request_id=request_id,
    )

    analysis_result["candidate_tournament"] = _normalize_tournament(
        tool_result.get("candidate_tournament", analysis_result["candidate_tournament"])
    )
    live_data_context = str(tool_result.get("tool_context", "No live-data MCP tool was used."))
    live_data_sources = list(tool_result.get("sources") or [])
    tool_status = str(tool_result.get("tool_status", "skipped"))
    if tool_status == "pending_input":
        analysis_result["workflow_action"] = "clarify"
        missing_requirements = list(tool_result.get("missing_requirements") or [])
        analysis_result["clarifying_focus"] = (
            ",".join(missing_requirements) if missing_requirements else analysis_result["clarifying_focus"]
        )
        analysis_result["clarifying_question"] = (
            str(tool_result.get("follow_up_question", "")).strip()
            or analysis_result["clarifying_question"]
        )
    elif tool_status == "error" and analysis_result["response_mode"] == "live_data_reply":
        analysis_result["workflow_action"] = "update"

    if analysis_result["response_mode"] == "live_data_reply":
        validation_result = {
            "required_status": {},
            "missing_fields": [],
            "constraint_issues": [],
            "changed_impact_fields": [],
            "final_action": "respond",
            "primary_focus": "",
            "suggested_question": "",
            "ready_for_generation": False,
            "needs_regeneration": False,
        }
    else:
        validation_result = _build_validation_result(tournament, analysis_result, phase)
    _trace(
        request_id,
        "VALIDATION",
        final_action=validation_result["final_action"],
        missing=", ".join(validation_result["missing_fields"]) or "none",
        issues=", ".join(issue["field"] for issue in validation_result["constraint_issues"]) or "none",
        ready=validation_result["ready_for_generation"],
        regenerate=validation_result["needs_regeneration"],
    )

    _log_debug_block(
        "WORKFLOW VALIDATION",
        {
            "phase": phase,
            "analysis_result": analysis_result,
            "validation_result": validation_result,
        },
    )
    changed_fields_payload = _build_changed_fields_payload(
        tournament,
        analysis_result["candidate_tournament"],
    )
    updated_working_memory = _build_next_working_memory(
        previous_working_memory=working_memory,
        original_tournament=tournament,
        candidate_tournament=analysis_result["candidate_tournament"],
        analysis_result=analysis_result,
        validation_result=validation_result,
        tool_result=tool_result,
    )

    finalizer_prompt = (
        f"Phase: {phase}\n"
        f"Response mode: {analysis_result['response_mode']}\n"
        f"Today's date: {today_str}\n"
        f"Final action: {validation_result['final_action']}\n"
        f"Target ready_for_generation: {str(validation_result['ready_for_generation']).lower()}\n"
        f"Target needs_regeneration: {str(validation_result['needs_regeneration']).lower()}\n\n"
        f"[Phase instructions]\n{phase_instructions}\n\n"
        f"{history_block}"
        f"[Latest user message]\n{user_message}\n\n"
        f"[Current tournament state]\n{json.dumps(tournament, indent=2)}\n\n"
        f"[Working memory at start of turn]\n{_working_memory_block(working_memory)}\n\n"
        f"[Candidate tournament state]\n"
        f"{json.dumps(analysis_result['candidate_tournament'], indent=2)}\n\n"
        f"[State changes from this turn]\n"
        f"{json.dumps(changed_fields_payload, indent=2)}\n\n"
        f"[Workflow analysis]\n{json.dumps(analysis_result, indent=2)}\n\n"
        f"[Validation summary]\n{json.dumps(validation_result, indent=2)}\n\n"
        f"[Live data tool result]\n{live_data_context}\n\n"
        f"[Working memory for next turn]\n{_working_memory_block(updated_working_memory)}\n\n"
        f"[Retrieved knowledge snippets]\n{retrieved_context}\n"
    )
    _trace(
        request_id,
        "FINALIZER INPUT",
        mode=analysis_result["response_mode"],
        final_action=validation_result["final_action"],
        tool_used=analysis_result.get("tool_plan", {}).get("tool_name", "none"),
        candidate_changes=_changed_fields_summary(tournament, analysis_result["candidate_tournament"]),
    )

    if analysis_failed:
        final_tournament = analysis_result["candidate_tournament"]
        if "LangChain dependencies are not installed" in analysis_failure_error:
            final_message = (
                "The backend LangChain dependencies are not installed. "
                "Run `pip install -r backend/requirements.txt` and restart the backend."
            )
        else:
            final_message = "I'm having trouble reaching the planning model right now. Please try again in a moment."
        _log_debug_block(
            "WORKFLOW FINALIZER SKIPPED",
            {
                "reason": "analysis_step_failed",
                "message": final_message,
            },
        )
    else:
        try:
            raw_final = await _call_structured_step(
                "workflow_finalizer",
                WORKFLOW_FINALIZER_SYSTEM_PROMPT,
                finalizer_prompt,
                WorkflowFinalizerOutput,
                retrieval_query,
                retrieved_chunks,
                retrieval_error,
                extra_debug={"phase": phase, "validation": validation_result},
                request_id=request_id,
            )
            final_tournament_raw = raw_final.get(
                "tournament",
                analysis_result["candidate_tournament"],
            )
            if isinstance(final_tournament_raw, BaseModel):
                final_tournament_raw = final_tournament_raw.model_dump()
            if not isinstance(final_tournament_raw, dict):
                final_tournament_raw = analysis_result["candidate_tournament"]

            final_tournament = _normalize_tournament(final_tournament_raw)
            final_message = str(raw_final.get("message", "")).strip()
        except Exception as exc:
            final_tournament = analysis_result["candidate_tournament"]
            final_message = _fallback_conversational_response(
                user_message=user_message,
                original_tournament=tournament,
                candidate_tournament=final_tournament,
                validation_result=validation_result,
                analysis_result=analysis_result,
                tool_context=live_data_context,
                phase=phase,
            )
            _log_debug_block(
                "WORKFLOW FINALIZER FALLBACK",
                {"error": str(exc), "message": final_message},
            )

    if validation_result["final_action"] == "clarify" and not final_message:
        final_message = validation_result["suggested_question"]
    if (
        analysis_result["response_mode"] != "live_data_reply"
        and validation_result["final_action"] == "clarify"
        and phase == "planning"
    ):
        ready_for_generation = False
    else:
        ready_for_generation = validation_result["ready_for_generation"]

    if (
        analysis_result["response_mode"] != "live_data_reply"
        and phase == "planning"
        and ready_for_generation
        and not analysis_result.get("is_general_question", False)
    ):
        final_message = READY_MESSAGE

    if not final_message:
        final_message = "I updated the tournament."

    response_payload = {
        "message": final_message,
        "tournament": final_tournament,
        "ready_for_generation": ready_for_generation,
        "needs_regeneration": validation_result["needs_regeneration"],
        "sources": live_data_sources + _serialize_sources(retrieved_chunks),
        "working_memory": updated_working_memory,
    }
    _trace(
        request_id,
        "RESPONSE",
        message=_preview_text(final_message, 180),
        changed_fields=_changed_fields_summary(tournament, final_tournament),
        ready=ready_for_generation,
        regenerate=validation_result["needs_regeneration"],
    )
    return response_payload
