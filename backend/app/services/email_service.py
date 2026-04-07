"""
SendGrid email helpers.

Both functions are async; they delegate the blocking SendGrid SDK call to a
thread executor via asyncio.to_thread so the FastAPI event loop stays free.

Environment variables required
───────────────────────────────
  SENDGRID_API_KEY     – your SendGrid API key
  SENDGRID_FROM_EMAIL  – verified sender address in your SendGrid account
  SENDGRID_FROM_NAME   – display name shown to recipients (optional)
"""

import asyncio
import base64
import os
from typing import List, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    Email,
    FileContent,
    FileName,
    FileType,
    Mail,
)

_SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "")
_FROM_NAME: str = os.getenv("SENDGRID_FROM_NAME", "")


def _from_address():
    """Return an Email with display name if configured, otherwise plain address string."""
    if _FROM_NAME:
        return Email(_FROM_EMAIL, _FROM_NAME)
    return _FROM_EMAIL


def _build_schedule_attachment(
    schedule: List[dict],
    tournament_name: str,
    tournament_date: str = "",
    tournament_venue: str = "",
) -> Optional[Attachment]:
    """Generate an HTML tee-time schedule and return it as a SendGrid Attachment."""
    if not schedule:
        return None

    rows = "".join(
        f"<tr>"
        f"<td style='padding:8px 14px;border-bottom:1px solid #d1fae5'>{g['group']}</td>"
        f"<td style='padding:8px 14px;border-bottom:1px solid #d1fae5'>{g['teeTime']}</td>"
        f"<td style='padding:8px 14px;border-bottom:1px solid #d1fae5;white-space:pre-line'>"
        f"{'<br>'.join(g['players'])}</td>"
        f"</tr>"
        for g in schedule
    )
    subtitle = " \u2014 ".join(filter(None, [tournament_date, tournament_venue]))
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body{{font-family:Arial,sans-serif;margin:40px;color:#222}}
  h1{{color:#166534;margin-bottom:4px}}
  .sub{{color:#6b7280;margin-top:0;margin-bottom:20px}}
  table{{border-collapse:collapse;width:100%;margin-top:16px}}
  th{{background:#166534;color:#fff;padding:10px 14px;text-align:left}}
  td{{vertical-align:top}}
  tr:nth-child(even) td{{background:#f0fdf4}}
</style></head><body>
  <h1>Tee Time Schedule &mdash; {tournament_name}</h1>
  <p class="sub">{subtitle}</p>
  <table>
    <thead><tr><th>Group</th><th>Tee Time</th><th>Players</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>"""

    encoded = base64.b64encode(html.encode("utf-8")).decode()
    return Attachment(
        FileContent(encoded),
        FileName("tee-time-schedule.html"),
        FileType("text/html"),
        Disposition("attachment"),
    )


def _build_rule_sheet_attachment(
    html: str,
    tournament_name: str,
) -> Optional[Attachment]:
    """Encode a rule-sheet HTML string as a SendGrid Attachment."""
    if not html:
        return None
    encoded = base64.b64encode(html.encode("utf-8")).decode()
    return Attachment(
        FileContent(encoded),
        FileName("player-guide.html"),
        FileType("text/html"),
        Disposition("attachment"),
    )


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
    schedule: List[dict] = None,
    tournament_date: str = "",
    tournament_venue: str = "",
    rule_sheet_html: Optional[str] = None,
) -> None:
    """
    Send the tournament brochure to a list of recipients.
    Appends a prominent registration block, attaches the tee-time
    schedule as an HTML file, and optionally attaches the player guide.
    """
    registration_block = (
        "\n\n"
        "\u2500" * 41 + "\n"
        "REGISTER FOR THIS TOURNAMENT\n"
        f"Secure your tee-time spot by clicking the link below:\n"
        f"{registration_link}\n\n"
        "Registration is open until all slots are filled.\n"
        "\u2500" * 41
    )
    full_body = body + registration_block

    attachment = _build_schedule_attachment(
        schedule or [], tournament_name, tournament_date, tournament_venue
    )
    rule_sheet_attachment = _build_rule_sheet_attachment(rule_sheet_html or "", tournament_name)

    messages = []
    for recipient in to_emails:
        mail = Mail(
            from_email=_from_address(),
            to_emails=recipient,
            subject=subject,
            plain_text_content=full_body,
        )
        if attachment:
            mail.attachment = attachment
        if rule_sheet_attachment:
            mail.attachment = rule_sheet_attachment
        messages.append(mail)

    await asyncio.to_thread(_send_messages, messages)


async def send_email_direct(
    to_emails: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> None:
    """
    Send an email to a list of recipients.
    When html_body is provided, recipients see a rendered HTML email;
    plain text is kept as a fallback for non-HTML clients.
    """
    messages = [
        Mail(
            from_email=_from_address(),
            to_emails=recipient,
            subject=subject,
            plain_text_content=body,
            html_content=html_body,
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
    The schedule is attached as a clean HTML file.
    """
    subject = f"Final Tee Time Schedule \u2014 {tournament_name} ({tournament_date})"

    body = (
        f"Dear Participant,\n\n"
        f"The final tee time schedule for {tournament_name} is now confirmed.\n\n"
        f"  Tournament : {tournament_name}\n"
        f"  Date       : {tournament_date}\n"
        f"  Venue      : {tournament_venue}\n\n"
        f"Please find the complete tee time schedule attached to this email "
        f"as \u2018tee-time-schedule.html\u2019. Open it in any web browser for a "
        f"clean, printable view.\n\n"
        f"We look forward to seeing you on the course!\n\n"
        f"Warm regards,\n"
        f"The {tournament_name} Organizing Committee"
    )

    attachment = _build_schedule_attachment(
        schedule, tournament_name, tournament_date, tournament_venue
    )

    messages = []
    for recipient in to_emails:
        mail = Mail(
            from_email=_from_address(),
            to_emails=recipient,
            subject=subject,
            plain_text_content=body,
        )
        if attachment:
            mail.attachment = attachment
        messages.append(mail)

    await asyncio.to_thread(_send_messages, messages)
