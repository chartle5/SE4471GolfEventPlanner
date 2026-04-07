from __future__ import annotations

import asyncio
import json
import os
from typing import Any

MCP_WEATHER_SERVER_URL = os.getenv(
    "MCP_WEATHER_SERVER_URL",
    "http://127.0.0.1:8001/mcp",
)
WEATHER_MCP_TIMEOUT_SECONDS = float(os.getenv("WEATHER_MCP_TIMEOUT_SECONDS", "10"))


class WeatherMcpClientError(RuntimeError):
    """Raised when the backend cannot complete a weather MCP request."""


class WeatherLocationResolutionError(WeatherMcpClientError):
    """Raised when the weather service is reachable but the place name cannot be resolved."""


def _extract_structured_payload(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}

    raise WeatherMcpClientError("The MCP weather server returned no usable content.")


def _raise_for_tool_error(payload: Any) -> None:
    if not isinstance(payload, dict) or not payload.get("error"):
        return

    suggestion = str(payload.get("suggestion", "")).strip()
    message = str(payload["error"]).strip()
    if suggestion:
        message = f"{message} {suggestion}"
    if "No location matches were found" in message:
        raise WeatherLocationResolutionError(message)
    raise WeatherMcpClientError(message)


async def _call_weather_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except ModuleNotFoundError as exc:
        raise WeatherMcpClientError(
            "The MCP client dependency is not installed. Run `pip install -r backend/requirements.txt`."
        ) from exc

    async def _run_tool_call():
        async with streamable_http_client(MCP_WEATHER_SERVER_URL) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)

    try:
        result = await asyncio.wait_for(
            _run_tool_call(),
            timeout=WEATHER_MCP_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise WeatherMcpClientError(
            "The live weather MCP server timed out before returning a result."
        ) from exc
    except Exception as exc:
        raise WeatherMcpClientError(
            "The live weather MCP server is unavailable. Make sure it is running at "
            f"`{MCP_WEATHER_SERVER_URL}`."
        ) from exc

    payload = _extract_structured_payload(result)
    _raise_for_tool_error(payload)
    return payload


async def get_weather_forecast_via_mcp(
    location_query: str,
    forecast_days: int = 3,
) -> dict[str, Any]:
    payload = await _call_weather_tool(
        "get_weather_forecast",
        {
            "location_query": location_query,
            "forecast_days": forecast_days,
        },
    )
    if not isinstance(payload, dict):
        raise WeatherMcpClientError("The weather MCP server returned an invalid response.")
    return payload


async def get_weather_forecast_by_coordinates_via_mcp(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timezone: str = "auto",
) -> dict[str, Any]:
    payload = await _call_weather_tool(
        "get_weather_forecast_by_coordinates",
        {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": forecast_days,
            "timezone": timezone,
        },
    )
    if not isinstance(payload, dict):
        raise WeatherMcpClientError("The weather MCP server returned an invalid response.")
    return payload


async def get_sun_times_for_location_via_mcp(
    location_query: str,
    target_date: str,
) -> dict[str, Any]:
    payload = await _call_weather_tool(
        "get_sun_times_for_location",
        {
            "location_query": location_query,
            "target_date": target_date,
        },
    )
    if not isinstance(payload, dict):
        raise WeatherMcpClientError("The weather MCP server returned an invalid response.")
    return payload
