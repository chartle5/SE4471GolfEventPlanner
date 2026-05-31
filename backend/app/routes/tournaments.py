"""
Tournament persistence, schedule management, email sending, and finalization.
All routes are prefixed with /tournaments.
"""

import logging
import os
import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app import crud
from app.database import get_database
from app.dependencies import get_current_user
from app.models import (
    ReorderScheduleRequest,
    SaveTournamentRequest,
    SaveTournamentResponse,
    SeedPlayersRequest,
    SeedPlayersResponse,
    SendBrochureRequest,
    SendBrochureResponse,
    SendClubSheetRequest,
    SendClubSheetResponse,
    ShuffleResponse,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

# Name pools for synthetic test players — mirrors register_test_players.sh.
_SEED_FIRST_NAMES = [
    "Jack", "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James", "Isabella",
    "Oliver", "Mia", "Benjamin", "Charlotte", "Elijah", "Amelia", "Lucas", "Harper", "Mason", "Evelyn",
    "Logan", "Abigail", "Ethan", "Emily", "Aiden", "Elizabeth", "Ryan", "Sofia", "Michael", "Victoria",
]
_SEED_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Robinson", "Clark", "Rodriguez",
    "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King", "Wright", "Scott",
]

# Dependency aliases for cleaner function signatures
DB = Annotated[object, Depends(get_database)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


# ─────────────────────────── create / list ───────────────────────────────


@router.post("", response_model=SaveTournamentResponse, status_code=201)
async def save_tournament(payload: SaveTournamentRequest, db: DB, current_user: CurrentUser):
    """
    Persist a newly generated tournament to MongoDB, scoped to the logged-in user.
    Returns the tournament_id and a registration_token for the sign-up link.
    """
    result = await crud.create_tournament(
        db, payload.tournament, payload.schedule, payload.brochure,
        user_id=current_user["user_id"],
    )
    print(
        f"\n📋 Tournament saved — Registration token: {result['registration_token']}\n"
        f"   ./register_test_players.sh  →  token: {result['registration_token']}\n",
        flush=True,
    )
    return result


@router.get("")
async def list_tournaments(db: DB, current_user: CurrentUser):
    """Return tournaments belonging to the logged-in user (newest first)."""
    return await crud.list_tournaments(db, user_id=current_user["user_id"])


# ─────────────────────────── schedule ────────────────────────────────────


@router.get("/{tournament_id}/schedule")
async def get_schedule(tournament_id: str, db: DB):
    """
    Return the live schedule merged with registrations, plus progress counts.
    Poll this endpoint every 5 s from the Reservations page.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    registered = await crud.count_registrations(db, tournament_id)
    return {
        "schedule": doc["schedule"],
        "registration_token": doc.get("registration_token", ""),
        "players_registered": registered,
        "total_players": doc["player_count"],
        "status": doc["status"],
    }


# ─────────────────────────── registrations ───────────────────────────────


@router.get("/{tournament_id}/registrations")
async def get_registrations(tournament_id: str, db: DB, current_user: CurrentUser):
    """
    Return all registered players for a tournament, including all form fields
    supplied at registration time (phone, rental clubs, team name, tee slot).
    Scoped to the logged-in organizer.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    registrations = await crud.get_registrations(db, tournament_id)
    return {
        "tournament_id": tournament_id,
        "event_type": doc.get("event_type", "individual"),
        "registrations": registrations,
    }


@router.post("/{tournament_id}/send-club-sheet", response_model=SendClubSheetResponse)
async def send_club_sheet(
    tournament_id: str,
    payload: SendClubSheetRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Build and email a full operations sheet to golf club staff.
    Includes: event overview, headcount, cart estimate, rental club breakdown,
    confirmed tee pairings, and organizer contact info.
    """
    from app.services.document_generator import generate_club_ops_html
    from app.services.email_service import send_email_direct

    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    registrations = await crud.get_registrations(db, tournament_id)
    players_registered = await crud.count_registrations(db, tournament_id)

    name = doc.get("name", "Golf Tournament")
    date = doc.get("date", "TBD")

    html_body = generate_club_ops_html(
        doc=doc,
        registrations=registrations,
        players_registered=players_registered,
        organizer_name=payload.organizer_name or "",
        organizer_email=payload.organizer_email or "",
        organizer_phone=payload.organizer_phone or "",
    )

    plain_text = (
        f"Golf Club Operations Sheet — {name} ({date})\n\n"
        f"Players Registered: {players_registered} / {doc.get('player_count', '?')}\n"
        f"Please view the HTML version for full pairings and equipment breakdown."
    )

    await send_email_direct(
        to_emails=payload.emails,
        subject=f"Operations Sheet — {name} ({date})",
        body=plain_text,
        html_body=html_body,
    )

    n = len(payload.emails)
    return SendClubSheetResponse(
        success=True,
        message=f"Club operations sheet sent to {n} recipient(s).",
    )


@router.get("/{tournament_id}/cart-placards")
async def get_cart_placards(tournament_id: str, db: DB, current_user: CurrentUser):
    """
    Generate and return a print-ready PDF of cart placards.
    One A5-landscape page per cart (2 players each).
    Partners are kept together for team-of-2 events; all other event types
    use sequential pairing within each schedule group.
    """
    from app.services.document_generator import generate_cart_placards_pdf

    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    registrations = await crud.get_registrations(db, tournament_id)
    pdf_bytes = generate_cart_placards_pdf(doc=doc, registrations=registrations)

    safe_name = doc.get("name", "tournament").replace(" ", "-").lower()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="cart-placards-{safe_name}.pdf"'
        },
    )


# ─────────────────────────── shuffle ─────────────────────────────────────


@router.post("/{tournament_id}/shuffle", response_model=ShuffleResponse)
async def shuffle_schedule(tournament_id: str, db: DB):
    """
    Randomly redistribute all player names and placeholders across the
    existing tee-time groups. Only allowed while status is 'pending'.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if doc["status"] == "finalized":
        raise HTTPException(
            status_code=400, detail="Cannot shuffle a finalized tournament"
        )

    new_schedule = await crud.shuffle_schedule(db, tournament_id)
    return {"schedule": new_schedule}


# ─────────────────────────── reorder (drag & drop) ───────────────────────


@router.post("/{tournament_id}/reorder", response_model=ShuffleResponse)
async def reorder_schedule(
    tournament_id: str, payload: ReorderScheduleRequest, db: DB, current_user: CurrentUser
):
    """
    Persist a manually reordered schedule from the drag-and-drop editor.
    Validates that no players were added/removed and that teammates stay grouped.
    """
    try:
        new_schedule = await crud.reorder_schedule(db, tournament_id, payload.schedule)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if new_schedule is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return {"schedule": new_schedule}


# ─────────────────────────── seed test players ───────────────────────────


@router.post("/{tournament_id}/seed-players", response_model=SeedPlayersResponse)
async def seed_players(
    tournament_id: str, payload: SeedPlayersRequest, db: DB, current_user: CurrentUser
):
    """
    Register synthetic test players for a tournament — the server-side equivalent
    of register_test_players.sh, exposed so the organizer can seed players from
    the UI without the terminal. Names, phone numbers, ~15% rental clubs, and
    (for team events) sequential team assignment mirror the shell script.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if doc["status"] == "finalized":
        raise HTTPException(status_code=400, detail="Cannot seed a finalized tournament")

    if payload.clear:
        await crud.clear_registrations(db, tournament_id)

    event_type = doc.get("event_type", "individual")
    team_size = max(1, int(doc.get("team_size") or 1))
    already = await crud.count_registrations(db, tournament_id)

    n_first = len(_SEED_FIRST_NAMES)
    n_last = len(_SEED_LAST_NAMES)
    created = 0
    failed = 0

    for i in range(1, payload.count + 1):
        global_num = already + i
        first = _SEED_FIRST_NAMES[(global_num - 1) % n_first]
        last = _SEED_LAST_NAMES[((global_num - 1) * 7 + 3) % n_last]
        phone = f"555-{global_num:04d}"

        rental = random.randint(0, 99) < 15
        club_hand = random.choice(["left", "right"]) if rental else None

        team_name = None
        if event_type == "team":
            team_name = f"Team {((already + i - 1) // team_size) + 1}"

        result = await crud.register_player(
            db,
            tournament_id,
            first,
            last,
            phone_number=phone,
            rental_clubs=rental,
            club_hand=club_hand,
            team_name=team_name,
            event_type=event_type,
        )
        if result is None:
            failed += 1
            break  # schedule is full — stop early
        created += 1

    players_registered = await crud.count_registrations(db, tournament_id)
    return SeedPlayersResponse(
        success=created > 0,
        created=created,
        failed=failed,
        players_registered=players_registered,
        total_players=doc["player_count"],
        message=(
            f"{created} test player{'s' if created != 1 else ''} registered successfully."
            if created > 0
            else "No players were registered — the tournament may be full."
        ),
    )


# ─────────────────────────── send brochure email ─────────────────────────


@router.post(
    "/{tournament_id}/send-brochure", response_model=SendBrochureResponse
)
async def send_brochure(
    tournament_id: str, payload: SendBrochureRequest, db: DB
):
    """
    Store recipient emails and send the tournament brochure via SMTP email.
    The email body automatically includes a registration link.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Persist recipients so they can later receive the finalized schedule
    await crud.update_brochure_recipients(db, tournament_id, payload.emails)

    frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173")
    registration_link = f"{frontend_base}/register/{doc['registration_token']}"

    from app.services.email_service import send_brochure_email  # local import avoids circular
    from app.services.document_generator import generate_rule_sheet as _gen_rule_sheet

    rule_sheet = _gen_rule_sheet(doc.get("original_tournament") or doc)
    rule_sheet_html = rule_sheet.get("html") if rule_sheet else None

    try:
        await send_brochure_email(
            to_emails=payload.emails,
            subject=doc["brochure_subject"],
            body=doc["brochure_body"],
            registration_link=registration_link,
            tournament_name=doc["name"],
            schedule=doc.get("schedule", []),
            tournament_date=doc.get("date", ""),
            tournament_venue=doc.get("venue", ""),
            rule_sheet_html=rule_sheet_html,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Email delivery failed: {exc}"
        ) from exc

    return SendBrochureResponse(
        success=True,
        message=f"Brochure sent to {len(payload.emails)} recipient(s).",
    )


# ─────────────────────────── finalize ────────────────────────────────────


@router.post("/{tournament_id}/finalize")
async def finalize_tournament(tournament_id: str, db: DB):
    """
    Lock the schedule (status → 'finalized') and email the final tee-time
    sheet to all brochure recipients.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if doc["status"] == "finalized":
        raise HTTPException(
            status_code=400, detail="Tournament is already finalized"
        )

    if doc.get("brochure_recipients"):
        from app.services.email_service import send_finalized_schedule_email

        try:
            await send_finalized_schedule_email(
                to_emails=doc["brochure_recipients"],
                tournament_name=doc["name"],
                tournament_date=doc["date"],
                tournament_venue=doc["venue"],
                schedule=doc["schedule"],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Finalization email delivery failed: {exc}",
            ) from exc

    await crud.finalize_tournament(db, tournament_id)
    return {
        "success": True,
        "message": "Tournament finalized and confirmation emails sent.",
    }


# ─────────────────────────── delete ──────────────────────────────────────


@router.delete("/{tournament_id}", status_code=200)
async def delete_tournament(tournament_id: str, db: DB):
    deleted = await crud.delete_tournament(db, tournament_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return {"success": True}
