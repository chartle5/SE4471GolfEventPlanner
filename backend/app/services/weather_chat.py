from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.mcp_weather_client import (
    MCP_WEATHER_SERVER_URL,
    WeatherMcpClientError,
    WeatherLocationResolutionError,
    get_sun_times_for_location_via_mcp,
    get_weather_forecast_by_coordinates_via_mcp,
    get_weather_forecast_via_mcp,
)

WEATHER_KEYWORD_PATTERN = re.compile(
    r"\b(?:weather|temperature|temp|forecast|sunrise|sunset|humidity|wind|rain|snow|conditions|daylight)\b",
    re.IGNORECASE,
)
LOCATION_SUFFIX_PATTERN = re.compile(
    r"\b(?:right now|now|currently|today|tomorrow|tonight|please|for me)\b",
    re.IGNORECASE,
)
COORDINATE_PATTERN = re.compile(
    r"(?P<lat>-?\d{1,2}(?:\.\d+)?)\s*,\s*(?P<lon>-?\d{1,3}(?:\.\d+)?)"
)
TEE_TIME_FIELD_PATTERN = re.compile(
    r"\b(?:first\s+tee\s+time|tee\s+time|start\s+time)\b",
    re.IGNORECASE,
)
TEE_TIME_UPDATE_VERB_PATTERN = re.compile(
    r"\b(?:set|make|change|move|update|use|schedule|adjust)\b",
    re.IGNORECASE,
)
GENERIC_LOCATION_REFERENCE_PATTERN = re.compile(
    r"^(?:there|here|the venue|the course|that venue)$",
    re.IGNORECASE,
)
NON_LOCATION_PHRASE_PATTERN = re.compile(
    r"\b(?:first\s+tee\s+time|tee\s+time|start\s+time|tournament|event)\b",
    re.IGNORECASE,
)


def _contains_weather_keyword(message: str) -> bool:
    return WEATHER_KEYWORD_PATTERN.search(message) is not None


def _normalize_location_candidate(candidate: str) -> str:
    cleaned = candidate.strip(" .,!?:;")
    cleaned = LOCATION_SUFFIX_PATTERN.sub("", cleaned)
    cleaned = cleaned.strip(" .,!?:;")
    return cleaned


def _extract_coordinates(message: str) -> Optional[tuple[float, float]]:
    match = COORDINATE_PATTERN.search(message)
    if not match:
        return None

    latitude = float(match.group("lat"))
    longitude = float(match.group("lon"))
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _extract_location_query(message: str, tournament: Dict[str, Any]) -> Optional[str]:
    explicit_patterns = (
        r"\b(?:in|for|at)\s+(.+)$",
        r"^(.+?)\s+(?:weather|forecast|temperature|temp|conditions|humidity|wind|rain|snow)\b",
    )

    for pattern in explicit_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            continue
        candidate = _normalize_location_candidate(match.group(1))
        if not candidate:
            continue
        if GENERIC_LOCATION_REFERENCE_PATTERN.fullmatch(candidate):
            venue = str(tournament.get("venue", "")).strip()
            if venue:
                return venue
            continue
        if NON_LOCATION_PHRASE_PATTERN.search(candidate):
            continue
        return candidate

    lowered = message.lower()
    if any(phrase in lowered for phrase in ("there", "the venue", "the course", "that venue")):
        venue = str(tournament.get("venue", "")).strip()
        if venue:
            return venue

    return None


def _format_value(value: Any, suffix: str = "") -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value)}{suffix}"
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _format_timestamp(value: Any) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(value)


def _format_hhmm_label(value: str) -> str:
    try:
        return datetime.strptime(value, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return value


def _normalize_target_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def _format_date_label(value: str) -> str:
    normalized = _normalize_target_date(value)
    if not normalized:
        return str(value)
    return datetime.strptime(normalized, "%Y-%m-%d").strftime("%B %d, %Y")


def _is_tournament_sun_time_request(message: str) -> bool:
    lowered = message.lower()
    mentions_sun_time = "sunrise" in lowered or "sunset" in lowered
    mentions_tee_time = TEE_TIME_FIELD_PATTERN.search(message) is not None
    mentions_update = TEE_TIME_UPDATE_VERB_PATTERN.search(message) is not None
    return mentions_sun_time and mentions_tee_time and mentions_update


def _format_forecast_line(day: Dict[str, Any]) -> str:
    date_str = str(day.get("date", "")).strip()
    label = date_str
    try:
        label = datetime.fromisoformat(date_str).strftime("%B %d")
    except ValueError:
        pass

    summary = str(day.get("weather_summary", "unknown conditions")).lower()
    high = _format_value(day.get("temperature_max_c"), "C")
    low = _format_value(day.get("temperature_min_c"), "C")

    pieces = [label]
    if high and low:
        pieces.append(f"high {high}, low {low}")
    elif high:
        pieces.append(f"high {high}")
    if summary:
        pieces.append(summary)
    return ": ".join([pieces[0], ", ".join(pieces[1:])]) if len(pieces) > 1 else pieces[0]


def _build_weather_message(user_message: str, weather: Dict[str, Any]) -> str:
    resolved_location = weather.get("resolved_location") or {}
    location_name = resolved_location.get("display_name") or "that location"

    current = weather.get("current_weather") or {}
    daily = weather.get("daily_forecast") or []
    today = daily[0] if daily else {}
    lowered = user_message.lower()

    condition = str(current.get("weather_summary", "unknown conditions")).lower()
    temperature = _format_value(current.get("temperature_c"), "C")
    feels_like = _format_value(current.get("apparent_temperature_c"), "C")
    humidity = _format_value(current.get("relative_humidity_percent"), "%")
    wind = _format_value(current.get("wind_speed_kmh"), " km/h")

    sentences = []
    if temperature:
        sentence = f"It is currently {temperature} in {location_name} with {condition}."
        if feels_like and feels_like != temperature:
            sentence += f" It feels like {feels_like}."
        sentences.append(sentence)
    else:
        sentences.append(f"Here is the latest weather for {location_name}.")

    if humidity or wind:
        detail_bits = []
        if humidity:
            detail_bits.append(f"humidity is {humidity}")
        if wind:
            detail_bits.append(f"wind is {wind}")
        if detail_bits:
            sentences.append(detail_bits[0].capitalize() + (f" and {detail_bits[1]}." if len(detail_bits) > 1 else "."))

    sunrise = _format_timestamp(today.get("sunrise"))
    sunset = _format_timestamp(today.get("sunset"))
    if sunrise or sunset:
        sun_bits = []
        if sunrise:
            sun_bits.append(f"sunrise is {sunrise}")
        if sunset:
            sun_bits.append(f"sunset is {sunset}")
        if any(keyword in lowered for keyword in ("sunrise", "sunset", "daylight", "weather", "forecast")):
            sentences.append("Today, " + " and ".join(sun_bits) + ".")

    if any(keyword in lowered for keyword in ("forecast", "tomorrow", "week", "weekend")) and daily:
        outlook = [_format_forecast_line(day) for day in daily[:3]]
        sentences.append("Short forecast: " + " | ".join(outlook) + ".")

    return " ".join(sentences)


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

    target_date = _format_date_label(str(sun_times.get("date", "")))
    if target_date:
        preview_bits.append(target_date)

    return {
        "title": f"Live Sun Times via MCP: {resolved_location.get('display_name', 'Resolved Location')}",
        "chunk_id": "weather_sun_times_live",
        "score": 1.0,
        "preview": " | ".join(preview_bits)[:160] or "Live sunrise and sunset lookup via local MCP server.",
    }


async def maybe_handle_tournament_sun_time_request(
    user_message: str,
    tournament: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not _is_tournament_sun_time_request(user_message):
        return None

    lowered = user_message.lower()
    requested_sun_event = "sunset" if "sunset" in lowered else "sunrise"
    venue = str(tournament.get("venue", "")).strip()
    target_date = _normalize_target_date(tournament.get("date", ""))

    missing_requirements = []
    if not venue:
        missing_requirements.append("the venue")
    if not target_date:
        missing_requirements.append("the event date")

    if missing_requirements:
        if len(missing_requirements) == 2:
            missing_text = "the venue and event date"
        else:
            missing_text = missing_requirements[0]
        return {
            "message": f"I can set the first tee time to {requested_sun_event}, but I need {missing_text} first.",
            "candidate_tournament": tournament,
            "sources": [],
            "append_follow_up_question": False,
            "workflow_action": "clarify",
        }

    try:
        sun_times = await get_sun_times_for_location_via_mcp(
            location_query=venue,
            target_date=target_date,
        )
    except WeatherLocationResolutionError as exc:
        return {
            "message": (
                f'I can set the first tee time to {requested_sun_event}, but I could not '
                f'resolve the venue "{venue}" to a usable location. {exc}'
            ),
            "candidate_tournament": tournament,
            "sources": [],
            "append_follow_up_question": False,
            "workflow_action": "clarify",
        }
    except WeatherMcpClientError as exc:
        return {
            "message": (
                f"I couldn't reach the live sun-times service. {exc} "
                f"Make sure the local MCP server is running at `{MCP_WEATHER_SERVER_URL}`."
            ),
            "candidate_tournament": tournament,
            "sources": [],
            "append_follow_up_question": False,
            "workflow_action": "clarify",
        }

    tee_time_value = str(sun_times.get(f"{requested_sun_event}_hm", "")).strip()
    if not tee_time_value:
        return {
            "message": f"I found the location, but I couldn't determine the {requested_sun_event} time for that date.",
            "candidate_tournament": tournament,
            "sources": [],
            "append_follow_up_question": False,
            "workflow_action": "clarify",
        }

    updated_tournament = dict(tournament)
    updated_tournament["teeTimeStart"] = tee_time_value

    resolved_location = sun_times.get("resolved_location") or {}
    location_name = resolved_location.get("display_name") or venue
    readable_date = _format_date_label(target_date)
    readable_time = _format_hhmm_label(tee_time_value)

    return {
        "message": (
            f"I set the first tee time to {requested_sun_event} at {readable_time} "
            f"({tee_time_value}) in {location_name} on {readable_date}."
        ),
        "candidate_tournament": updated_tournament,
        "sources": [_build_sun_times_source(sun_times)],
        "append_follow_up_question": True,
        "workflow_action": "update",
    }


async def maybe_handle_weather_query(
    user_message: str,
    tournament: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not _contains_weather_keyword(user_message):
        return None

    coordinates = _extract_coordinates(user_message)
    location_query = _extract_location_query(user_message, tournament)

    if not coordinates and not location_query:
        return None

    try:
        if coordinates:
            weather = await get_weather_forecast_by_coordinates_via_mcp(
                latitude=coordinates[0],
                longitude=coordinates[1],
                forecast_days=3,
            )
        else:
            weather = await get_weather_forecast_via_mcp(
                location_query=location_query or "",
                forecast_days=3,
            )
    except WeatherLocationResolutionError as exc:
        return {
            "message": (
                f"I couldn't resolve that location for live weather lookup. {exc}"
            ),
            "tournament": tournament,
            "ready_for_generation": False,
            "needs_regeneration": False,
            "sources": [],
        }
    except WeatherMcpClientError as exc:
        return {
            "message": (
                f"I couldn't reach the live weather service. {exc} "
                f"Make sure the local MCP server is running at `{MCP_WEATHER_SERVER_URL}`."
            ),
            "tournament": tournament,
            "ready_for_generation": False,
            "needs_regeneration": False,
            "sources": [],
        }

    return {
        "message": _build_weather_message(user_message, weather),
        "tournament": tournament,
        "ready_for_generation": False,
        "needs_regeneration": False,
        "sources": [_build_weather_source(weather)],
    }
