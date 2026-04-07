"""
Tournament persistence, schedule management, email sending, and finalization.
All routes are prefixed with /tournaments.
"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app import crud
from app.database import get_database
from app.dependencies import get_current_user
from app.models import (
    SaveTournamentRequest,
    SaveTournamentResponse,
    SendBrochureRequest,
    SendBrochureResponse,
    SendClubSheetRequest,
    SendClubSheetResponse,
    ShuffleResponse,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

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


# ─────────────────────────── send brochure email ─────────────────────────


@router.post(
    "/{tournament_id}/send-brochure", response_model=SendBrochureResponse
)
async def send_brochure(
    tournament_id: str, payload: SendBrochureRequest, db: DB
):
    """
    Store recipient emails and send the tournament brochure via SendGrid.
    The email body automatically includes a registration link.
    """
    doc = await crud.get_tournament(db, tournament_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Persist recipients so they can later receive the finalized schedule
    await crud.update_brochure_recipients(db, tournament_id, payload.emails)

    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
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
