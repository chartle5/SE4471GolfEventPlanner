"""
SMTP email helpers (replaces SendGrid).

Both functions are async; they delegate the blocking SMTP call to a
thread executor via asyncio.to_thread so the FastAPI event loop stays free.

Environment variables required
───────────────────────────────
  SMTP_HOST        – SMTP server hostname  (e.g. smtp.gmail.com)
  SMTP_PORT        – SMTP port             (default: 587, TLS/STARTTLS)
  SMTP_USERNAME    – login username / email address
  SMTP_PASSWORD    – login password or app-password
  SMTP_FROM_EMAIL  – sender address shown to recipients
  SMTP_FROM_NAME   – display name shown to recipients (optional)

Gmail quick-start
─────────────────
  1. Enable 2-Step Verification on your Google account.
  2. Go to myaccount.google.com → Security → App Passwords.
  3. Generate an app password for "Mail / Other device".
  4. Use that 16-character password as SMTP_PASSWORD.
"""

import asyncio
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

_SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
_SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "")


def _from_header() -> str:
    """Return a formatted From header string."""
    if _FROM_NAME:
        return f"{_FROM_NAME} <{_FROM_EMAIL}>"
    return _FROM_EMAIL


def _build_schedule_html(
    schedule: List[dict],
    tournament_name: str,
    tournament_date: str = "",
    tournament_venue: str = "",
) -> Optional[str]:
    """Generate an HTML tee-time schedule string, or None if schedule is empty."""
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
    return f"""<!DOCTYPE html>
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


def _add_html_attachment(msg: MIMEMultipart, html_content: str, filename: str) -> None:
    """Attach an HTML string as a file attachment to a MIMEMultipart message."""
    part = MIMEBase("text", "html")
    part.set_payload(html_content.encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    part.add_header("Content-Type", "text/html; charset=utf-8")
    msg.attach(part)


def _send_messages(messages: List[MIMEMultipart]) -> None:
    """Synchronous helper — runs inside asyncio.to_thread."""
    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(_SMTP_USERNAME, _SMTP_PASSWORD)
        for msg in messages:
            server.send_message(msg)


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

    schedule_html = _build_schedule_html(
        schedule or [], tournament_name, tournament_date, tournament_venue
    )

    messages = []
    for recipient in to_emails:
        msg = MIMEMultipart()
        msg["From"] = _from_header()
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(full_body, "plain"))
        if schedule_html:
            _add_html_attachment(msg, schedule_html, "tee-time-schedule.html")
        if rule_sheet_html:
            _add_html_attachment(msg, rule_sheet_html, "player-guide.html")
        messages.append(msg)

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
    messages = []
    for recipient in to_emails:
        msg = MIMEMultipart("alternative")
        msg["From"] = _from_header()
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        messages.append(msg)
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

    schedule_html = _build_schedule_html(
        schedule, tournament_name, tournament_date, tournament_venue
    )

    messages = []
    for recipient in to_emails:
        msg = MIMEMultipart()
        msg["From"] = _from_header()
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        if schedule_html:
            _add_html_attachment(msg, schedule_html, "tee-time-schedule.html")
        messages.append(msg)

    await asyncio.to_thread(_send_messages, messages)
