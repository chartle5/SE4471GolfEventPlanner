from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
SUNRISE_SUNSET_API_URL = "https://api.sunrise-sunset.org/json"
HTTP_TIMEOUT_SECONDS = 20.0
USER_AGENT = "SE4471GolfEventPlanner/1.0"
MAX_LOCATION_RESULTS = 10
MAX_FORECAST_DAYS = 16

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

CURRENT_VARIABLES = ",".join(
    [
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "precipitation",
        "weather_code",
        "cloud_cover",
        "surface_pressure",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
        "is_day",
    ]
)

DAILY_VARIABLES = ",".join(
    [
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "sunrise",
        "sunset",
        "daylight_duration",
        "precipitation_probability_max",
        "precipitation_sum",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
    ]
)


class WeatherServiceError(RuntimeError):
    """Raised when the upstream weather provider request fails."""


class LocationNotFoundError(WeatherServiceError):
    """Raised when the provider cannot resolve a location query."""


def _normalize_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _normalized_query_variants(query: str) -> list[str]:
    raw = query.strip()
    if not raw:
        return []

    variants: list[str] = []

    def add(candidate: str) -> None:
        normalized = re.sub(r"\s+", " ", candidate).strip(" ,")
        if normalized and normalized not in variants:
            variants.append(normalized)

    add(raw)
    add(raw.replace(",", " "))

    comma_parts = [part.strip() for part in raw.split(",") if part.strip()]
    if comma_parts:
        add(comma_parts[0])
        if len(comma_parts) >= 2:
            add(" ".join(comma_parts[:2]))

    words = raw.replace(",", " ").split()
    if len(words) == 2:
        add(" ".join(words[:2]))
    if words and len(words) == 1:
        add(words[0])

    return variants


def _looks_like_specific_venue_query(query: str) -> bool:
    normalized = _normalize_text(query)
    venue_markers = (
        "golf course",
        "golf club",
        "country club",
        "club",
        "course",
        "municipal",
        "public",
        "national",
        "resort",
        "links",
    )
    return any(marker in normalized for marker in venue_markers)


def _query_segments(query: str) -> list[str]:
    segments = [_normalize_text(part) for part in query.split(",")]
    return [segment for segment in segments if segment]


def _location_match_score(query: str, location: dict[str, Any]) -> tuple[int, int]:
    segments = _query_segments(query)
    primary_segment = segments[0] if segments else _normalize_text(query)
    qualifier_segments = segments[1:]

    name = _normalize_text(location.get("name"))
    country = _normalize_text(location.get("country"))
    country_code = _normalize_text(location.get("country_code"))
    admin_regions = [_normalize_text(region) for region in location.get("admin_regions", [])]
    timezone = _normalize_text(location.get("timezone"))
    display_name = _normalize_text(location.get("display_name"))

    score = 0

    if primary_segment:
        if name == primary_segment:
            score += 500
        elif primary_segment in name:
            score += 250
        elif primary_segment in display_name:
            score += 150

    searchable_fields = [country, country_code, timezone, display_name, *admin_regions]

    for qualifier in qualifier_segments:
        matched = False
        if qualifier == country or qualifier == country_code:
            score += 300
            matched = True
        elif qualifier in admin_regions:
            score += 300
            matched = True
        elif any(qualifier and qualifier in field for field in searchable_fields):
            score += 180
            matched = True

        if not matched:
            score -= 120

    population = int(location.get("population") or 0)
    return score, population


async def _search_locations_exact(query: str, count: int) -> list[dict[str, Any]]:
    payload = await _get_json(
        OPEN_METEO_GEOCODING_URL,
        {
            "name": query,
            "count": count,
            "language": "en",
            "format": "json",
        },
    )
    results = payload.get("results") or []
    return [_format_location(result) for result in results if isinstance(result, dict)]


def _weather_description(code: Any) -> str:
    try:
        normalized = int(code)
    except (TypeError, ValueError):
        return "Unknown"
    return WMO_WEATHER_CODES.get(normalized, f"Unknown weather code ({normalized})")


def _daylight_hours(seconds: Any) -> float | None:
    try:
        return round(float(seconds) / 3600, 2)
    except (TypeError, ValueError):
        return None


def _format_location(result: dict[str, Any]) -> dict[str, Any]:
    admin_parts = [result.get("admin1"), result.get("admin2"), result.get("admin3")]
    admin_parts = [part for part in admin_parts if part]

    display_parts = [result.get("name")]
    display_parts.extend(admin_parts[:1])
    if result.get("country"):
        display_parts.append(result["country"])

    return {
        "name": result.get("name", ""),
        "display_name": ", ".join(part for part in display_parts if part),
        "country": result.get("country", ""),
        "country_code": result.get("country_code", ""),
        "admin_regions": admin_parts,
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "elevation": result.get("elevation"),
        "timezone": result.get("timezone"),
        "population": result.get("population"),
        "geocoding_source": "open-meteo",
    }


def _first_non_empty(*values: Any) -> str:
    for value in values:
        candidate = str(value or "").strip()
        if candidate:
            return candidate
    return ""


def _unique_parts(parts: list[str]) -> list[str]:
    unique: list[str] = []
    for part in parts:
        normalized = part.strip()
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def _format_nominatim_location(result: dict[str, Any]) -> dict[str, Any]:
    address = result.get("address") or {}
    name = _first_non_empty(
        result.get("name"),
        address.get("amenity"),
        address.get("tourism"),
        address.get("leisure"),
        address.get("building"),
        str(result.get("display_name", "")).split(",", 1)[0],
    )
    locality = _first_non_empty(
        address.get("city"),
        address.get("town"),
        address.get("village"),
        address.get("municipality"),
        address.get("hamlet"),
        address.get("county"),
    )
    state = _first_non_empty(address.get("state"), address.get("state_district"))
    country = _first_non_empty(address.get("country"))

    display_parts = [name]
    for candidate in (locality, state, country):
        if candidate and _normalize_text(candidate) != _normalize_text(name):
            display_parts.append(candidate)

    admin_regions = _unique_parts(
        [
            locality,
            address.get("county", ""),
            state,
            address.get("region", ""),
        ]
    )

    try:
        latitude = float(result.get("lat"))
        longitude = float(result.get("lon"))
    except (TypeError, ValueError) as exc:
        raise WeatherServiceError("Location provider returned invalid coordinates.") from exc

    return {
        "name": name,
        "display_name": ", ".join(part for part in display_parts if part),
        "country": country,
        "country_code": str(address.get("country_code", "")).upper(),
        "admin_regions": admin_regions,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": None,
        "timezone": "",
        "population": 0,
        "geocoding_source": "nominatim",
    }


async def _get_payload(url: str, params: dict[str, Any]) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, headers=headers) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(
                f"Weather provider request failed: {exc}"
            ) from exc

    return response.json()


async def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    payload = await _get_payload(url, params)
    if not isinstance(payload, dict):
        raise WeatherServiceError("Weather provider returned an invalid payload.")
    return payload


async def _get_json_list(url: str, params: dict[str, Any]) -> list[Any]:
    payload = await _get_payload(url, params)
    if not isinstance(payload, list):
        raise WeatherServiceError("Weather provider returned an invalid payload.")
    return payload


async def _search_locations_nominatim(query: str, count: int) -> list[dict[str, Any]]:
    payload = await _get_json_list(
        NOMINATIM_SEARCH_URL,
        {
            "q": query,
            "format": "jsonv2",
            "limit": count,
            "addressdetails": 1,
        },
    )
    return [
        _format_nominatim_location(result)
        for result in payload
        if isinstance(result, dict) and result.get("lat") and result.get("lon")
    ]


async def search_locations(query: str, count: int = 5) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Location query cannot be empty.")

    normalized_count = max(1, min(count, MAX_LOCATION_RESULTS))
    collected_matches: dict[tuple[Any, Any, str], dict[str, Any]] = {}
    venue_like_query = _looks_like_specific_venue_query(normalized_query)

    if venue_like_query:
        nominatim_matches = await _search_locations_nominatim(
            normalized_query,
            count=normalized_count,
        )
        for match in nominatim_matches:
            dedupe_key = (
                match.get("latitude"),
                match.get("longitude"),
                match.get("display_name", ""),
            )
            collected_matches[dedupe_key] = match

    for candidate_query in _normalized_query_variants(normalized_query):
        matches = await _search_locations_exact(candidate_query, count=normalized_count)
        for match in matches:
            dedupe_key = (
                match.get("latitude"),
                match.get("longitude"),
                match.get("display_name", ""),
            )
            existing = collected_matches.get(dedupe_key)
            if existing is None:
                collected_matches[dedupe_key] = match
                continue

            if _location_match_score(normalized_query, match) > _location_match_score(
                normalized_query, existing
            ):
                collected_matches[dedupe_key] = match

    if not collected_matches:
        nominatim_matches = await _search_locations_nominatim(
            normalized_query,
            count=normalized_count,
        )
        for match in nominatim_matches:
            dedupe_key = (
                match.get("latitude"),
                match.get("longitude"),
                match.get("display_name", ""),
            )
            collected_matches[dedupe_key] = match

    ranked_matches = sorted(
        collected_matches.values(),
        key=lambda match: _location_match_score(normalized_query, match),
        reverse=True,
    )

    return ranked_matches[:normalized_count]


async def _get_timezone_for_coordinates(latitude: float, longitude: float) -> str:
    payload = await _get_json(
        OPEN_METEO_FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": 1,
            "timezone": "auto",
            "current": "temperature_2m",
        },
    )
    timezone_name = str(payload.get("timezone", "")).strip()
    return timezone_name or "UTC"


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_hhmm(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%H:%M")


def _duration_to_seconds(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)

    raw = str(value or "").strip()
    if not raw:
        return None

    parts = raw.split(":")
    if len(parts) != 3:
        return None

    try:
        hours, minutes, seconds = [int(part) for part in parts]
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _geocoding_source_url(location: dict[str, Any]) -> str:
    if location.get("geocoding_source") == "nominatim":
        return NOMINATIM_SEARCH_URL
    return OPEN_METEO_GEOCODING_URL


def _build_current_weather(current: dict[str, Any]) -> dict[str, Any]:
    weather_code = current.get("weather_code")
    return {
        "time": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "apparent_temperature_c": current.get("apparent_temperature"),
        "relative_humidity_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "cloud_cover_percent": current.get("cloud_cover"),
        "surface_pressure_hpa": current.get("surface_pressure"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_gusts_kmh": current.get("wind_gusts_10m"),
        "wind_direction_degrees": current.get("wind_direction_10m"),
        "is_day": bool(current.get("is_day")),
        "weather_code": weather_code,
        "weather_summary": _weather_description(weather_code),
    }


def _build_daily_forecast(daily: dict[str, Any]) -> list[dict[str, Any]]:
    dates = daily.get("time") or []
    forecast: list[dict[str, Any]] = []

    for index, forecast_date in enumerate(dates):
        weather_code = (daily.get("weather_code") or [None] * len(dates))[index]
        daylight_duration = (daily.get("daylight_duration") or [None] * len(dates))[index]

        forecast.append(
            {
                "date": forecast_date,
                "weather_code": weather_code,
                "weather_summary": _weather_description(weather_code),
                "temperature_max_c": (daily.get("temperature_2m_max") or [None] * len(dates))[index],
                "temperature_min_c": (daily.get("temperature_2m_min") or [None] * len(dates))[index],
                "sunrise": (daily.get("sunrise") or [None] * len(dates))[index],
                "sunset": (daily.get("sunset") or [None] * len(dates))[index],
                "daylight_duration_seconds": daylight_duration,
                "daylight_duration_hours": _daylight_hours(daylight_duration),
                "precipitation_probability_max_percent": (
                    (daily.get("precipitation_probability_max") or [None] * len(dates))[index]
                ),
                "precipitation_sum_mm": (
                    (daily.get("precipitation_sum") or [None] * len(dates))[index]
                ),
                "wind_speed_max_kmh": (daily.get("wind_speed_10m_max") or [None] * len(dates))[index],
                "wind_gusts_max_kmh": (daily.get("wind_gusts_10m_max") or [None] * len(dates))[index],
            }
        )

    return forecast


async def get_weather_by_coordinates(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timezone: str = "auto",
) -> dict[str, Any]:
    normalized_days = max(1, min(forecast_days, MAX_FORECAST_DAYS))
    payload = await _get_json(
        OPEN_METEO_FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": normalized_days,
            "timezone": timezone or "auto",
            "current": CURRENT_VARIABLES,
            "daily": DAILY_VARIABLES,
        },
    )

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}

    return {
        "coordinates": {
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "elevation": payload.get("elevation"),
        },
        "timezone": payload.get("timezone"),
        "timezone_abbreviation": payload.get("timezone_abbreviation"),
        "utc_offset_seconds": payload.get("utc_offset_seconds"),
        "current_weather": _build_current_weather(current),
        "daily_forecast": _build_daily_forecast(daily),
        "source": {
            "provider": "Open-Meteo",
            "forecast_url": OPEN_METEO_FORECAST_URL,
        },
    }


async def get_weather_for_location(
    location_query: str,
    forecast_days: int = 3,
) -> dict[str, Any]:
    matches = await search_locations(location_query, count=5)
    if not matches:
        raise LocationNotFoundError(
            f'No location matches were found for "{location_query}".'
        )

    primary_match = matches[0]
    weather = await get_weather_by_coordinates(
        latitude=float(primary_match["latitude"]),
        longitude=float(primary_match["longitude"]),
        forecast_days=forecast_days,
        timezone=primary_match.get("timezone") or "auto",
    )

    weather["resolved_location"] = primary_match
    weather["alternative_matches"] = matches[1:]
    weather["source"]["geocoding_url"] = _geocoding_source_url(primary_match)
    return weather


async def get_sun_times_by_coordinates(
    latitude: float,
    longitude: float,
    target_date: str,
    timezone: str = "auto",
) -> dict[str, Any]:
    try:
        normalized_date = datetime.strptime(target_date.strip(), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("target_date must be in YYYY-MM-DD format.") from exc

    timezone_name = (timezone or "").strip()
    if not timezone_name or timezone_name == "auto":
        timezone_name = await _get_timezone_for_coordinates(latitude, longitude)

    payload = await _get_json(
        SUNRISE_SUNSET_API_URL,
        {
            "lat": latitude,
            "lng": longitude,
            "date": normalized_date,
            "formatted": 0,
            "tzid": timezone_name,
        },
    )

    if str(payload.get("status", "")).upper() != "OK":
        raise WeatherServiceError("Sunrise and sunset provider returned an error.")

    results = payload.get("results") or {}
    sunrise_dt = _parse_iso_datetime(results.get("sunrise"))
    sunset_dt = _parse_iso_datetime(results.get("sunset"))
    solar_noon_dt = _parse_iso_datetime(results.get("solar_noon"))

    if timezone_name:
        try:
            tzinfo = ZoneInfo(timezone_name)
        except Exception:
            tzinfo = None
        if tzinfo is not None:
            if sunrise_dt is not None:
                sunrise_dt = sunrise_dt.astimezone(tzinfo)
            if sunset_dt is not None:
                sunset_dt = sunset_dt.astimezone(tzinfo)
            if solar_noon_dt is not None:
                solar_noon_dt = solar_noon_dt.astimezone(tzinfo)

    return {
        "date": normalized_date,
        "coordinates": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "timezone": timezone_name,
        "sunrise": sunrise_dt.isoformat() if sunrise_dt else None,
        "sunset": sunset_dt.isoformat() if sunset_dt else None,
        "solar_noon": solar_noon_dt.isoformat() if solar_noon_dt else None,
        "sunrise_hm": _format_hhmm(sunrise_dt),
        "sunset_hm": _format_hhmm(sunset_dt),
        "solar_noon_hm": _format_hhmm(solar_noon_dt),
        "day_length_seconds": _duration_to_seconds(results.get("day_length")),
        "source": {
            "provider": "Sunrise-Sunset.org",
            "sun_times_url": SUNRISE_SUNSET_API_URL,
        },
    }


async def get_sun_times_for_location(
    location_query: str,
    target_date: str,
) -> dict[str, Any]:
    matches = await search_locations(location_query, count=5)
    if not matches:
        raise LocationNotFoundError(
            f'No location matches were found for "{location_query}".'
        )

    primary_match = matches[0]
    sun_times = await get_sun_times_by_coordinates(
        latitude=float(primary_match["latitude"]),
        longitude=float(primary_match["longitude"]),
        target_date=target_date,
        timezone=primary_match.get("timezone") or "auto",
    )

    sun_times["resolved_location"] = primary_match
    sun_times["alternative_matches"] = matches[1:]
    sun_times["source"]["geocoding_url"] = _geocoding_source_url(primary_match)
    return sun_times
