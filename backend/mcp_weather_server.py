from __future__ import annotations

import contextlib
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.services.weather_service import (
    LocationNotFoundError,
    WeatherServiceError,
    get_sun_times_for_location as lookup_sun_times_for_location,
    get_weather_by_coordinates,
    get_weather_for_location,
    search_locations,
)

SERVER_NAME = "Golf Planner Weather MCP"

mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "Use these tools to resolve locations anywhere on Earth and fetch live "
        "weather, sunrise, and sunset data. If a place name is ambiguous, call "
        "search_weather_locations first and then refine the request."
    ),
    json_response=True,
    stateless_http=True,
)


async def _run_weather_tool(coro):
    try:
        return await coro
    except LocationNotFoundError as exc:
        return {
            "error": str(exc),
            "suggestion": (
                "Try a more specific place name or call search_weather_locations first."
            ),
        }
    except WeatherServiceError as exc:
        return {
            "error": str(exc),
            "suggestion": "Retry in a moment. The upstream weather provider may be unavailable.",
        }
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def search_weather_locations(query: str, max_results: int = 5) -> Any:
    """Resolve a place name into candidate locations worldwide.

    Args:
        query: Free-form place query such as "London", "St Andrews Scotland",
            or "Tokyo Japan".
        max_results: Maximum number of candidate matches to return.
    """

    return await _run_weather_tool(search_locations(query, count=max_results))


@mcp.tool()
async def get_weather_forecast(location_query: str, forecast_days: int = 3) -> Any:
    """Get current weather plus sunrise and sunset data for a named location.

    Args:
        location_query: Free-form place query such as "Augusta, Georgia" or
            "Cape Town South Africa".
        forecast_days: Number of forecast days to return, from 1 to 16.
    """

    return await _run_weather_tool(
        get_weather_for_location(location_query, forecast_days=forecast_days)
    )


@mcp.tool()
async def get_weather_forecast_by_coordinates(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timezone: str = "auto",
) -> Any:
    """Get current weather plus sunrise and sunset data for exact coordinates.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        forecast_days: Number of forecast days to return, from 1 to 16.
        timezone: IANA timezone string such as "America/Toronto", or "auto".
    """

    return await _run_weather_tool(
        get_weather_by_coordinates(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            timezone=timezone,
        )
    )


@mcp.tool()
async def get_sun_times_for_location(location_query: str, target_date: str) -> Any:
    """Get sunrise and sunset times for a named location on a specific date.

    Args:
        location_query: Free-form place query such as "Augusta National" or
            "London, Ontario, Canada".
        target_date: Date in YYYY-MM-DD format.
    """

    return await _run_weather_tool(
        lookup_sun_times_for_location(location_query=location_query, target_date=target_date)
    )


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


async def root(request) -> JSONResponse:
    return JSONResponse(
        {
            "server": SERVER_NAME,
            "status": "ok",
            "transport": "streamable-http",
            "mcp_endpoint": "/mcp",
            "tools": [
                "search_weather_locations",
                "get_weather_forecast",
                "get_weather_forecast_by_coordinates",
                "get_sun_times_for_location",
            ],
        }
    )


async def healthz(request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


app = Starlette(
    routes=[
        Route("/", endpoint=root),
        Route("/healthz", endpoint=healthz),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mcp_weather_server:app", host="127.0.0.1", port=8001, reload=False)
