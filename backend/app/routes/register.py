"""
Public player registration endpoints.
These routes are accessed by players clicking the link in the brochure email
and therefore have no authentication requirement — they use the opaque
registration_token (UUID) as a shared secret.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.database import get_database
from app.models import RegisterRequest, RegisterResponse

router = APIRouter(prefix="/register", tags=["registration"])

DB = Annotated[object, Depends(get_database)]


@router.get("/{token}")
async def get_registration_info(token: str, db: DB):
    """
    Return public-safe tournament details for the registration landing page.
    Called on mount so the page can display the event name, date, and current
    slot availability without exposing internal tournament_id.
    """
    doc = await crud.get_tournament_by_token(db, token)
    if doc is None:
        raise HTTPException(status_code=404, detail="Registration link not found")

    registered = await crud.count_registrations(db, doc["tournament_id"])
    slots_remaining = max(0, doc["player_count"] - registered)

    return {
        "tournament_id": doc["tournament_id"],
        "name": doc["name"],
        "date": doc["date"],
        "venue": doc["venue"],
        "format": doc["format"],
        "slots_remaining": slots_remaining,
        "total_slots": doc["player_count"],
        "players_registered": registered,
        "is_full": slots_remaining == 0,
        "status": doc["status"],
    }


@router.post("/{token}", response_model=RegisterResponse)
async def register_player(token: str, payload: RegisterRequest, db: DB):
    """
    Accept a player's first and last name and assign them to the next
    open placeholder slot in the schedule.
    """
    doc = await crud.get_tournament_by_token(db, token)
    if doc is None:
        raise HTTPException(status_code=404, detail="Registration link not found")

    if doc["status"] == "finalized":
        return RegisterResponse(
            success=False,
            message="Registration is closed — this tournament has been finalized.",
        )

    result = await crud.register_player(
        db,
        doc["tournament_id"],
        payload.first_name,
        payload.last_name,
    )

    if result is None:
        return RegisterResponse(
            success=False,
            message="Registration is closed — all spots are filled.",
        )

    return RegisterResponse(
        success=True,
        message=(
            f"You're registered! See you on the course. "
            f"You've been placed in {result['slot_description']}."
        ),
        slot_description=result["slot_description"],
        players_registered=result["players_registered"],
        total_players=result["total_players"],
    )
