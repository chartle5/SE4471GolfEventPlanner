"""
SendGrid email helpers.

Both functions are async; they delegate the blocking SendGrid SDK call to a
thread executor via asyncio.to_thread so the FastAPI event loop stays free.

Environment variables required
───────────────────────────────
  SENDGRID_API_KEY     – your SendGrid API key
  SENDGRID_FROM_EMAIL  – verified sender address in your SendGrid account
"""

import asyncio
import os
from typing import List

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

_SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "")


def _send_messages(messages: List[Mail]) -> None:
    """Synchronous helper — runs inside asyncio.to_thread."""
    sg = SendGridAPIClient(api_key=_SENDGRID_API_KEY)
    for msg in messages:
        sg.send(msg)


async def send_brochure_email(
    to_emails: List[str],
    subject: str,
    body: str,
    registration_link: str,
    tournament_name: str,
) -> None:
    """
    Send the tournament brochure to a list of recipients.
    Appends a prominent registration block to the existing brochure body so
    players know where to sign up.
    """
    registration_block = (
        "\n\n"
        "─────────────────────────────────────────\n"
        "REGISTER FOR THIS TOURNAMENT\n"
        f"Secure your tee-time spot by clicking the link below:\n"
        f"{registration_link}\n\n"
        "Registration is open until all slots are filled.\n"
        "─────────────────────────────────────────"
    )
    full_body = body + registration_block

    messages = [
        Mail(
            from_email=_FROM_EMAIL,
            to_emails=recipient,
            subject=subject,
            plain_text_content=full_body,
        )
        for recipient in to_emails
    ]
    await asyncio.to_thread(_send_messages, messages)


async def send_email_direct(
    to_emails: List[str],
    subject: str,
    body: str,
) -> None:
    """
    Send a raw email body to a list of recipients with no modifications.
    Used by the Reservations page email modal (brochure already composed).
    """
    messages = [
        Mail(
            from_email=_FROM_EMAIL,
            to_emails=recipient,
            subject=subject,
            plain_text_content=body,
        )
        for recipient in to_emails
    ]
    await asyncio.to_thread(_send_messages, messages)


async def send_finalized_schedule_email(
    to_emails: List[str],
    tournament_name: str,
    tournament_date: str,
    tournament_venue: str,
    schedule: List[dict],
) -> None:
    """
    Send the finalised tee-time schedule to all brochure recipients.
    Called automatically when the organiser clicks 'Finalize Schedule'.
    """
    subject = f"Final Tee Time Schedule — {tournament_name} ({tournament_date})"

    lines = [
        "FINAL TEE TIME SCHEDULE",
        "─────────────────────────────────────────",
        f"  Tournament : {tournament_name}",
        f"  Date       : {tournament_date}",
        f"  Venue      : {tournament_venue}",
        "",
        f"{'GROUP':<8}  {'TEE TIME':<12}  PLAYERS",
        "─────────────────────────────────────────",
    ]
    for group in schedule:
        players_str = "  •  ".join(group["players"])
        lines.append(
            f"  Group {group['group']:<4}  {group['teeTime']:<12}  {players_str}"
        )

    lines += [
        "",
        "─────────────────────────────────────────",
        "",
        "This is the final confirmed schedule.",
        "We look forward to seeing you on the course!",
        "",
        f"— The {tournament_name} Organizing Committee",
    ]

    body = "\n".join(lines)

    messages = [
        Mail(
            from_email=_FROM_EMAIL,
            to_emails=recipient,
            subject=subject,
            plain_text_content=body,
        )
        for recipient in to_emails
    ]
    await asyncio.to_thread(_send_messages, messages)
