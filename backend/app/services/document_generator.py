from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def _parse_tee_time(time_str: str) -> datetime:
    """Parse HH:MM string into a datetime object (date part is irrelevant)."""
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_str.strip(), fmt)
        except ValueError:
            continue
    # Fallback to 08:00
    return datetime.strptime("08:00", "%H:%M")


def generate_schedule(tournament: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build a tee-time schedule from the tournament object.
    Players are placeholder names (Player 1 … N), grouped by the tournament's
    tee group size (2 or 4 players per slot; defaults to 4).
    Returns a list of group dicts: {group, teeTime, players}.
    """
    player_count = max(int(tournament.get("playerCount", 0)), 1)
    interval = int(tournament.get("teeTimeInterval", 12))
    tee_start_str = tournament.get("teeTimeStart", "08:00") or "08:00"

    # Players per tee-time slot — only 2 or 4 are valid; anything else means 4.
    try:
        group_size = int(tournament.get("teeGroupSize", 4) or 4)
    except (TypeError, ValueError):
        group_size = 4
    if group_size not in (2, 4):
        group_size = 4

    tee_start = _parse_tee_time(tee_start_str)

    players = [f"Player {i + 1}" for i in range(player_count)]

    groups = []
    group_num = 1
    idx = 0
    while idx < len(players):
        group_players = players[idx: idx + group_size]
        tee_time = tee_start + timedelta(minutes=interval * (group_num - 1))
        groups.append(
            {
                "group": group_num,
                "teeTime": tee_time.strftime("%I:%M %p").lstrip("0"),
                "players": group_players,
            }
        )
        idx += group_size
        group_num += 1

    return groups


def generate_brochure(tournament: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a structured brochure dict — pure template, no LLM call.
    """
    name = tournament.get("name") or "Golf Tournament"
    date = tournament.get("date") or "TBD"
    venue = tournament.get("venue") or "TBD"
    fmt = tournament.get("format") or "TBD"
    number_of_days = int(tournament.get("numberOfDays") or 1)
    player_count = tournament.get("playerCount", 0)
    event_type = tournament.get("eventType") or ""
    team_size = int(tournament.get("teamSize") or 1)
    registration_deadline = tournament.get("registrationDeadline") or ""
    entry_fee = tournament.get("entryFee") or 0
    description = tournament.get("description") or ""
    sponsors = tournament.get("sponsors") or []
    catering = tournament.get("catering") or ""
    accessibility = tournament.get("accessibility") or ""
    notes = tournament.get("notes") or ""
    tee_start = tournament.get("teeTimeStart", "08:00")
    interval = tournament.get("teeTimeInterval", 12)

    schedule = generate_schedule(tournament)

    email_body_lines = [
        f"Dear Participant,",
        "",
        f"We are excited to welcome you to the {name}!",
        "",
        "EVENT DETAILS",
        "─────────────────────────────────────",
        f"  Tournament:  {name}",
        f"  Dates:       {date}" + (f" ({number_of_days} days)" if number_of_days > 1 else ""),
        f"  Venue:       {venue}",
        f"  Format:      {fmt}",
        f"  Event Type:  {event_type.capitalize() if event_type else 'TBD'}" + (f" — {team_size} per team" if event_type == "team" else ""),
        f"  Players:     {player_count}",
        f"  First tee:   {tee_start}  ({interval}-min intervals)",
    ] + ([f"  Entry Fee:   ${entry_fee}"] if entry_fee else []) + ([f"  Reg. Deadline: {registration_deadline}"] if registration_deadline else [])

    if sponsors:
        sponsor_list = ", ".join(sponsors) if isinstance(sponsors, list) else str(sponsors)
        email_body_lines += ["", f"  Sponsors:    {sponsor_list}"]

    if catering:
        email_body_lines += [f"  Catering:    {catering}"]

    if accessibility:
        email_body_lines += [f"  Accessibility: {accessibility}"]

    email_body_lines += [
        "",
        "TEE TIME SCHEDULE",
        "─────────────────────────────────────",
    ]

    for g in schedule:
        players_str = ", ".join(g["players"])
        email_body_lines.append(f"  {g['teeTime']:>8}  |  Group {g['group']}  |  {players_str}")

    if notes:
        email_body_lines += ["", "ADDITIONAL NOTES", "─────────────────────────────────────", f"  {notes}"]

    email_body_lines += [
        "",
        "We look forward to seeing you on the course!",
        "",
        "Warm regards,",
        f"The {name} Organizing Committee",
    ]

    return {
        "subject": f"Tournament Information — {name} ({date})",
        "to": "All Participants",
        "body": "\n".join(email_body_lines),
        "meta": {

            "name": name,
            "date": date,
            "venue": venue,
            "format": fmt,
            "numberOfDays": number_of_days,
            "playerCount": player_count,
            "eventType": event_type,
            "teamSize": team_size,
            "registrationDeadline": registration_deadline,
            "entryFee": entry_fee,
            "description": description,
            "teeTimeStart": tee_start,
            "teeTimeInterval": interval,
            "sponsors": sponsors,
            "catering": catering,
            "accessibility": accessibility,
            "notes": notes,
        },
    }


def generate_brochure_html(
    brochure_body: str,
    schedule: List[Dict[str, Any]],
    tournament_name: str,
    tournament_date: str = "",
    tournament_venue: str = "",
    tournament_format: str = "",
) -> str:
    """
    Build a fully styled HTML email for the schedule brochure.
    The schedule is rendered as a table inside the email body.
    """
    rows = "".join(
        f"<tr style='background:{'#f0fdf4' if i % 2 == 0 else '#fff'}'>"
        f"<td style='padding:10px 14px;color:#374151'>Group {g['group']}</td>"
        f"<td style='padding:10px 14px;font-weight:600;color:#166534'>{g['teeTime']}</td>"
        f"<td style='padding:10px 14px;color:#374151'>{'<br>'.join(g['players'])}</td>"
        f"</tr>"
        for i, g in enumerate(schedule)
    )

    subtitle_parts = [p for p in [tournament_date, tournament_venue, tournament_format] if p]
    subtitle = " &nbsp;&middot;&nbsp; ".join(subtitle_parts)

    # Extract the intro paragraph — everything before the schedule rows
    intro_text = brochure_body.split("TEE TIME SCHEDULE")[0].strip() if "TEE TIME SCHEDULE" in brochure_body else brochure_body.strip()
    intro_html = "".join(
        f"<p style='margin:0 0 6px'>{line if line.strip() else '&nbsp;'}</p>"
        for line in intro_text.split("\n")
        if line.strip() and not line.startswith("─")
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{tournament_name}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">
    <div style="background:#166534;padding:28px 32px;color:#fff">
      <h1 style="margin:0;font-size:22px;font-weight:700">{tournament_name}</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:.85">{subtitle}</p>
    </div>
    <div style="padding:24px 32px;font-size:14px;line-height:1.7;color:#374151;border-bottom:1px solid #e5e7eb">
      {intro_html}
    </div>
    <div style="padding:24px 32px">
      <h2 style="margin:0 0 16px;font-size:16px;color:#166534;font-weight:700">Tee Time Schedule</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;border-radius:8px;overflow:hidden">
        <thead>
          <tr style="background:#166534">
            <th style="padding:10px 14px;text-align:left;color:#fff;font-weight:600">Group</th>
            <th style="padding:10px 14px;text-align:left;color:#fff;font-weight:600">Tee Time</th>
            <th style="padding:10px 14px;text-align:left;color:#fff;font-weight:600">Players</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <div style="padding:20px 32px 28px;background:#f9fafb;font-size:13px;color:#6b7280;border-top:1px solid #e5e7eb">
      We look forward to seeing you on the course!<br>
      <strong style="color:#166534">The {tournament_name} Organizing Committee</strong>
    </div>
  </div>
</body></html>"""


def generate_invite_html(
    tournament_meta: Dict[str, Any],
    registration_link: str = "",
) -> str:
    """
    Build a fully styled HTML invite email with a prominent Register button.
    """
    name = tournament_meta.get("name") or "Golf Tournament"
    date = tournament_meta.get("date") or "TBD"
    venue = tournament_meta.get("venue") or "TBD"
    fmt = tournament_meta.get("format") or "TBD"
    event_type = tournament_meta.get("eventType") or ""
    team_size = int(tournament_meta.get("teamSize") or 1)
    entry_fee = tournament_meta.get("entryFee") or 0
    registration_deadline = tournament_meta.get("registrationDeadline") or ""
    description = tournament_meta.get("description") or ""
    player_count = tournament_meta.get("playerCount", 0)

    event_type_str = (event_type.capitalize() if event_type else "TBD") + (
        f" &mdash; {team_size} per team" if event_type == "team" else ""
    )

    detail_rows = "".join(
        f"<tr style='border-bottom:1px solid #e5e7eb'>"
        f"<td style='padding:8px 14px;font-weight:600;color:#374151;width:145px'>{label}</td>"
        f"<td style='padding:8px 14px;color:#374151'>{value}</td>"
        f"</tr>"
        for label, value in [
            ("Tournament", name),
            ("Date", date),
            ("Venue", venue),
            ("Format", fmt),
            ("Event Type", event_type_str),
            ("Players", str(player_count)),
        ]
        + ([("Entry Fee", f"${entry_fee}")] if entry_fee else [])
        + ([("Reg. Deadline", registration_deadline)] if registration_deadline else [])
    )

    description_block = (
        f"<p style='font-size:14px;color:#374151;line-height:1.7;margin:0 0 16px'>{description}</p>"
        if description else ""
    )

    reg_block = ""
    if registration_link:
        reg_block = f"""
    <div style="padding:0 32px 32px">
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:28px 24px;text-align:center">
        <p style="margin:0 0 6px;font-size:17px;font-weight:700;color:#166534">Secure Your Spot</p>
        <p style="margin:0 0 22px;font-size:13px;color:#374151">Enter your first &amp; last name to claim a tee-time slot. Spots are limited!</p>
        <a href="{registration_link}"
           style="background:#166534;color:#fff;padding:13px 36px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block;letter-spacing:.3px">
          Register Now &rarr;
        </a>
        <p style="margin:16px 0 0;font-size:11px;color:#9ca3af">Or copy this link: {registration_link}</p>
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>You're Invited &mdash; {name}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">
    <div style="background:#166534;padding:28px 32px;color:#fff">
      <h1 style="margin:0;font-size:22px;font-weight:700">You're Invited!</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:.85">{name}</p>
    </div>
    <div style="padding:24px 32px 16px">
      <p style="font-size:15px;color:#374151;margin:0 0 20px;line-height:1.7">
        Dear Golfer,<br><br>
        You are cordially invited to participate in <strong>{name}</strong>!
      </p>
      {description_block}
      <h2 style="margin:0 0 12px;font-size:15px;color:#166534;font-weight:700">Event Details</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px">
        <tbody>{detail_rows}</tbody>
      </table>
    </div>
    {reg_block}
    <div style="padding:20px 32px 28px;background:#f9fafb;font-size:13px;color:#6b7280;border-top:1px solid #e5e7eb">
      We look forward to seeing you on the course!<br>
      <strong style="color:#166534">The {name} Organizing Committee</strong>
    </div>
  </div>
</body></html>"""


def generate_invite_email(
    tournament_meta: Dict[str, Any],
    registration_link: str = "",
) -> Dict[str, Any]:
    """
    Build an invite-only email body — tournament details with a CTA to
    register.  No tee-time schedule is included (players aren't assigned yet).
    """
    name = tournament_meta.get("name") or "Golf Tournament"
    date = tournament_meta.get("date") or "TBD"
    venue = tournament_meta.get("venue") or "TBD"
    fmt = tournament_meta.get("format") or "TBD"
    number_of_days = int(tournament_meta.get("numberOfDays") or 1)
    player_count = tournament_meta.get("playerCount", 0)
    event_type = tournament_meta.get("eventType") or ""
    team_size = int(tournament_meta.get("teamSize") or 1)
    registration_deadline = tournament_meta.get("registrationDeadline") or ""
    entry_fee = tournament_meta.get("entryFee") or 0
    description = tournament_meta.get("description") or ""

    lines = [
        "Dear Golfer,",
        "",
        f"You are cordially invited to participate in the {name}!",
        "",
        "EVENT DETAILS",
        "─" * 41,
        f"  Tournament:  {name}",
        f"  Dates:       {date}" + (f" ({number_of_days} days)" if number_of_days > 1 else ""),
        f"  Venue:       {venue}",
        f"  Format:      {fmt}",
        f"  Event Type:  {event_type.capitalize() if event_type else 'TBD'}"
        + (f" — {team_size} per team" if event_type == "team" else ""),
        f"  Players:     {player_count}",
    ]

    if entry_fee:
        lines.append(f"  Entry Fee:   ${entry_fee}")
    if registration_deadline:
        lines.append(f"  Reg. Deadline: {registration_deadline}")
    if description:
        lines += ["", description]

    if registration_link:
        lines += [
            "",
            "─" * 41,
            "SECURE YOUR SPOT",
            "Click the link below to register for this tournament.",
            "You will be asked for your first and last name to reserve",
            "a tee-time slot.",
            "",
            f"  {registration_link}",
            "",
            "Registration is open until all slots are filled.",
            "─" * 41,
        ]

    lines += [
        "",
        "We look forward to seeing you on the course!",
        "",
        "Warm regards,",
        f"The {name} Organizing Committee",
    ]

    return {
        "subject": f"You're Invited — {name} ({date})",
        "body": "\n".join(lines),
    }


def wrap_plain_text_html(title: str, body: str) -> str:
    """Wrap an organizer-edited plain-text document in a simple, readable HTML email."""
    import html as _html

    safe_title = _html.escape(title or "")
    safe_body = _html.escape(body or "")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:680px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">
    <div style="background:#166534;padding:24px 32px;color:#fff">
      <h1 style="margin:0;font-size:20px;font-weight:700">{safe_title}</h1>
    </div>
    <div style="padding:24px 32px;white-space:pre-wrap;line-height:1.6;font-size:14px;color:#374151">{safe_body}</div>
  </div>
</body></html>"""


def generate_club_ops_text(
    doc: Dict[str, Any],
    registrations: List[Dict[str, Any]],
    players_registered: int,
    organizer_name: str = "",
    organizer_email: str = "",
    organizer_phone: str = "",
) -> Dict[str, str]:
    """
    Plain-text version of the club operations sheet, so the organizer can review
    and edit the content before it's emailed. Mirrors the sections in
    generate_club_ops_html.
    """
    import math

    name = doc.get("name", "Golf Tournament")
    date = doc.get("date", "TBD")
    venue = doc.get("venue", "TBD")
    fmt = doc.get("format", "TBD")
    n_days = int(doc.get("number_of_days") or 1)
    player_count = int(doc.get("player_count", 0))
    event_type = doc.get("event_type", "individual")
    team_size = int(doc.get("team_size") or 1)
    tee_start = doc.get("tee_time_start", "08:00")
    interval = int(doc.get("tee_time_interval", 12))
    catering = doc.get("catering", "")
    reg_deadline = doc.get("registration_deadline", "")
    schedule = doc.get("schedule", [])

    rental_total = sum(1 for r in registrations if r.get("rental_clubs"))
    rental_right = sum(1 for r in registrations if r.get("rental_clubs") and r.get("club_hand") == "right")
    rental_left = sum(1 for r in registrations if r.get("rental_clubs") and r.get("club_hand") == "left")
    cart_count = math.ceil(players_registered / 2) if players_registered > 0 else math.ceil(player_count / 2)
    n_groups = len(schedule)

    lines: List[str] = [
        f"GOLF CLUB OPERATIONS SHEET — {name} ({date})",
        "Confidential — for club staff use only.",
        "",
        "EVENT OVERVIEW",
        f"  Tournament: {name}",
        f"  Date: {date}" + (f" ({n_days} days)" if n_days > 1 else ""),
        f"  Venue: {venue}",
        f"  Format: {fmt}",
        "  Event Type: " + (f"Team — {team_size} players per team" if event_type == "team" else "Individual"),
    ]
    if reg_deadline:
        lines.append(f"  Registration Deadline: {reg_deadline}")
    lines += [
        "",
        "HEADCOUNT",
        f"  Total Slots: {player_count}",
        f"  Registered: {players_registered}",
        f"  Remaining: {max(0, player_count - players_registered)}",
        "",
        "TEE CONFIGURATION",
        f"  First Tee Time: {tee_start}",
        f"  Interval: {interval} minutes",
        f"  Total Groups: {n_groups}",
        "",
        "EQUIPMENT REQUIREMENTS",
        f"  Estimated Carts: {cart_count}",
        f"  Rental Clubs Needed: {rental_total}",
    ]
    if rental_total > 0:
        lines.append(f"    Right-Handed: {rental_right}")
        lines.append(f"    Left-Handed: {rental_left}")
    if catering:
        lines += ["", "CATERING", f"  {catering}"]
    if schedule:
        lines += ["", "CONFIRMED PAIRINGS"]
        for g in schedule:
            players = ", ".join(g.get("players", []))
            lines.append(f"  Group {g.get('group')} — {g.get('teeTime')}: {players}")
    if organizer_name or organizer_email or organizer_phone:
        lines += ["", "ORGANIZER CONTACT"]
        if organizer_name:
            lines.append(f"  Name: {organizer_name}")
        if organizer_email:
            lines.append(f"  Email: {organizer_email}")
        if organizer_phone:
            lines.append(f"  Phone: {organizer_phone}")

    return {
        "subject": f"Operations Sheet — {name} ({date})",
        "body": "\n".join(lines),
    }


def generate_club_ops_html(
    doc: Dict[str, Any],
    registrations: List[Dict[str, Any]],
    players_registered: int,
    organizer_name: str = "",
    organizer_email: str = "",
    organizer_phone: str = "",
) -> str:
    """
    Build a styled HTML operations sheet for the golf club.
    Covers: event overview, headcount, tee configuration, cart estimate,
    rental club breakdown, team structure (if applicable), catering,
    registration deadline, confirmed pairings, and organizer contact.
    """
    import math

    name          = doc.get("name", "Golf Tournament")
    date          = doc.get("date", "TBD")
    venue         = doc.get("venue", "TBD")
    fmt           = doc.get("format", "TBD")
    n_days        = int(doc.get("number_of_days") or 1)
    player_count  = int(doc.get("player_count", 0))
    event_type    = doc.get("event_type", "individual")
    team_size     = int(doc.get("team_size") or 1)
    tee_start     = doc.get("tee_time_start", "08:00")
    interval      = int(doc.get("tee_time_interval", 12))
    catering      = doc.get("catering", "")
    reg_deadline  = doc.get("registration_deadline", "")
    schedule      = doc.get("schedule", [])

    # Rental clubs breakdown
    rental_total  = sum(1 for r in registrations if r.get("rental_clubs"))
    rental_right  = sum(1 for r in registrations if r.get("rental_clubs") and r.get("club_hand") == "right")
    rental_left   = sum(1 for r in registrations if r.get("rental_clubs") and r.get("club_hand") == "left")
    cart_count    = math.ceil(players_registered / 2) if players_registered > 0 else math.ceil(player_count / 2)

    n_groups      = len(schedule)

    # ── Helper: info row ──────────────────────────────────────────────────
    def info_row(label: str, value: str, highlight: bool = False) -> str:
        val_style = "padding:10px 16px;color:#111827;font-weight:700;" if highlight else "padding:10px 16px;color:#374151;"
        return (
            f"<tr style='border-bottom:1px solid #e5e7eb'>"
            f"<td style='padding:10px 16px;font-weight:600;color:#6b7280;white-space:nowrap;width:200px'>{label}</td>"
            f"<td style='{val_style}'>{value}</td>"
            f"</tr>"
        )

    def section_header(title: str) -> str:
        return (
            f"<tr><td colspan='2' style='padding:14px 16px 6px;background:#f9fafb;"
            f"font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;"
            f"color:#6b7280;border-top:2px solid #e5e7eb'>{title}</td></tr>"
        )

    # ── Event overview rows ───────────────────────────────────────────────
    rows = ""
    rows += section_header("Event Overview")
    rows += info_row("Tournament", name)
    rows += info_row("Date", date + (f" ({n_days} days)" if n_days > 1 else ""))
    rows += info_row("Venue", venue)
    rows += info_row("Format", fmt)
    if event_type == "team":
        rows += info_row("Event Type", f"Team — {team_size} players per team")
    else:
        rows += info_row("Event Type", "Individual")
    if reg_deadline:
        rows += info_row("Registration Deadline", reg_deadline)

    # ── Headcount ────────────────────────────────────────────────────────
    rows += section_header("Headcount")
    rows += info_row("Total Slots", str(player_count))
    rows += info_row("Registered", str(players_registered), highlight=True)
    rows += info_row("Remaining", str(max(0, player_count - players_registered)))

    # ── Tee configuration ─────────────────────────────────────────────────
    rows += section_header("Tee Configuration")
    rows += info_row("Start Type", "Shotgun start" if n_groups >= player_count // 4 else "Sequential tee times")
    rows += info_row("First Tee Time", tee_start)
    rows += info_row("Interval", f"{interval} minutes")
    rows += info_row("Total Groups", str(n_groups))

    # ── Equipment ──────────────────────────────────────────────────────────
    rows += section_header("Equipment Requirements")
    rows += info_row("Estimated Carts", str(cart_count), highlight=True)
    rows += info_row("Rental Clubs Needed", str(rental_total), highlight=rental_total > 0)
    if rental_total > 0:
        rows += info_row("&nbsp;&nbsp;&nbsp;Right-Handed", str(rental_right))
        rows += info_row("&nbsp;&nbsp;&nbsp;Left-Handed", str(rental_left))

    # ── Catering ───────────────────────────────────────────────────────────
    if catering:
        rows += section_header("Catering")
        rows += info_row("Catering Notes", catering)

    # ── Schedule rows ─────────────────────────────────────────────────────
    schedule_rows = ""
    for i, g in enumerate(schedule):
        bg = "#f0fdf4" if i % 2 == 0 else "#fff"
        players_html = "<br>".join(g.get("players", []))
        schedule_rows += (
            f"<tr style='background:{bg}'>"
            f"<td style='padding:9px 14px;font-weight:600;color:#166534'>Group {g['group']}</td>"
            f"<td style='padding:9px 14px;font-weight:700;color:#166534'>{g['teeTime']}</td>"
            f"<td style='padding:9px 14px;color:#374151;font-size:13px'>{players_html}</td>"
            f"</tr>"
        )

    # ── Organizer contact ──────────────────────────────────────────────────
    contact_rows = ""
    if organizer_name:
        contact_rows += info_row("Name", organizer_name)
    if organizer_email:
        contact_rows += info_row("Email", f"<a href='mailto:{organizer_email}' style='color:#166534'>{organizer_email}</a>")
    if organizer_phone:
        contact_rows += info_row("Phone", organizer_phone)
    organizer_section = ""
    if contact_rows:
        organizer_section = f"""
    <div style="margin-top:32px">
      <h2 style="margin:0 0 12px;font-size:15px;color:#166534;font-weight:700">Organizer Contact</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
        <tbody>{contact_rows}</tbody>
      </table>
    </div>"""

    schedule_section = ""
    if schedule_rows:
        schedule_section = f"""
    <div style="margin-top:32px">
      <h2 style="margin:0 0 12px;font-size:15px;color:#166534;font-weight:700">Confirmed Pairings</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#166534">
            <th style="padding:9px 14px;text-align:left;color:#fff;font-weight:600">Group</th>
            <th style="padding:9px 14px;text-align:left;color:#fff;font-weight:600">Tee Time</th>
            <th style="padding:9px 14px;text-align:left;color:#fff;font-weight:600">Players</th>
          </tr>
        </thead>
        <tbody>{schedule_rows}</tbody>
      </table>
    </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Operations Sheet \u2014 {name}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:680px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

    <!-- Header -->
    <div style="background:#166534;padding:28px 32px;color:#fff">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;opacity:.75;margin-bottom:6px">Golf Club Operations Sheet</div>
      <h1 style="margin:0;font-size:22px;font-weight:700">{name}</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:.85">{date} &nbsp;&middot;&nbsp; {venue}</p>
    </div>

    <!-- Notice bar -->
    <div style="background:#fefce8;border-bottom:1px solid #fde047;padding:10px 24px;font-size:12px;color:#854d0e">
      <strong>Confidential operations document</strong> &mdash; for club staff use only. Please retain for event day preparation.
    </div>

    <!-- Main info table -->
    <div style="padding:28px 32px 0">
      <table style="width:100%;border-collapse:collapse;font-size:14px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
        <tbody>{rows}</tbody>
      </table>
    </div>

    {schedule_section}
    {organizer_section}

    <!-- Footer -->
    <div style="margin:32px 32px 0;padding:16px 0 28px;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af">
      This document was generated automatically by the Golf Event Planner system.
      Please contact the organizer above with any questions regarding event logistics.
    </div>

  </div>
</body></html>"""


# ─────────────────────────── cart placards PDF ───────────────────────────

import re as _re


def generate_cart_placards_pdf(
    doc: Dict[str, Any],
    registrations: List[Dict[str, Any]],
) -> bytes:
    """
    Build a print-ready PDF of cart placards — one A5-landscape page per cart.

    Pairing strategy:
    - team_size == 2: use ``team_name`` from registrations so partners always
      share a cart.
    - All other cases (individual, team_size 4, etc.): pair players
      sequentially within each schedule group ([0,1] and [2,3]).

    Unregistered placeholder slots appear as "TBD".
    """
    from fpdf import FPDF

    tournament_name = doc.get("name", "Golf Tournament")
    date            = doc.get("date", "TBD")
    venue           = doc.get("venue", "") or ""
    team_size       = int(doc.get("team_size") or 1)
    schedule        = doc.get("schedule", [])

    # ── name → team_name lookup from registrations ────────────────────────
    name_to_team: Dict[str, str] = {}
    for reg in registrations:
        full_name = f"{reg.get('first_name', '')} {reg.get('last_name', '')}".strip()
        if full_name and reg.get("team_name"):
            name_to_team[full_name] = reg["team_name"]

    _ph_re = _re.compile(r"^Player \d+$")

    def display(p: str) -> str:
        return "TBD" if _ph_re.match(p) else p

    # ── build list of (name1, name2, tee_time, group_num) ─────────────────
    pairs: List[tuple] = []
    for group in schedule:
        players   = group.get("players", [])
        tee_time  = group.get("teeTime", "")
        group_num = group.get("group", "")

        if team_size == 2 and name_to_team:
            # Sort players by team so partners are adjacent
            registered   = [p for p in players if not _ph_re.match(p)]
            placeholders = [p for p in players if _ph_re.match(p)]

            team_buckets: Dict[str, List[str]] = {}
            solo: List[str] = []
            for p in registered:
                team = name_to_team.get(p)
                if team:
                    team_buckets.setdefault(team, []).append(p)
                else:
                    solo.append(p)

            ordered: List[str] = []
            for members in team_buckets.values():
                ordered.extend(members)
            ordered.extend(solo)
            ordered.extend(placeholders)
        else:
            ordered = list(players)

        for i in range(0, max(len(ordered), 1), 2):
            p1 = display(ordered[i]) if i < len(ordered) else "TBD"
            p2 = display(ordered[i + 1]) if i + 1 < len(ordered) else "TBD"
            pairs.append((p1, p2, tee_time, group_num))

    if not pairs:
        pairs = [("TBD", "TBD", "—", 1)]

    # ── colours ───────────────────────────────────────────────────────────
    GREEN         = (22, 101, 52)      # #166534
    LIGHT_GREEN   = (240, 253, 244)    # #f0fdf4
    WHITE         = (255, 255, 255)
    DARK          = (17, 24, 39)       # #111827
    MEDIUM_GREEN  = (187, 247, 208)    # #bbf7d0 — subtle divider

    # ── page geometry (mm) ────────────────────────────────────────────────
    W, H       = 210, 148              # A5 landscape
    HEADER_H   = 40
    FOOTER_H   = 36
    BODY_Y     = HEADER_H
    BODY_H     = H - HEADER_H - FOOTER_H   # 72 mm

    # ── render ────────────────────────────────────────────────────────────
    pdf = FPDF(orientation="L", unit="mm", format="A5")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(0, 0, 0)

    for (p1, p2, tee_time, group_num) in pairs:
        pdf.add_page()

        # ── Header band ──────────────────────────────────────────────────
        pdf.set_fill_color(*GREEN)
        pdf.rect(0, 0, W, HEADER_H, style="F")

        # "CART ASSIGNMENT" label
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", size=7)
        pdf.set_xy(0, 5)
        label = "CART  ASSIGNMENT"
        # Letter-spaced effect: manual spacing not available, use normal
        pdf.cell(W, 4, label, align="C")

        # Thin divider under label
        pdf.set_draw_color(*MEDIUM_GREEN)
        pdf.set_line_width(0.2)
        pdf.line(60, 11, W - 60, 11)

        # Tournament name
        tn = tournament_name.upper()
        # Fit long names: try large font, fall back if > 40 chars
        font_sz = 15 if len(tn) <= 38 else 11
        pdf.set_font("Helvetica", style="B", size=font_sz)
        pdf.set_xy(8, 14)
        pdf.cell(W - 16, 9, tn, align="C")

        # Date · Venue subtitle
        subtitle_parts = [date]
        if venue:
            subtitle_parts.append(venue)
        subtitle = "   ·   ".join(subtitle_parts)
        pdf.set_font("Helvetica", size=9)
        pdf.set_xy(8, 26)
        pdf.cell(W - 16, 6, subtitle, align="C")

        # ── Body ─────────────────────────────────────────────────────────
        pdf.set_fill_color(*LIGHT_GREEN)
        pdf.rect(0, BODY_Y, W, BODY_H, style="F")

        # Body is 72 mm tall; centre content around the midpoint
        mid = BODY_Y + BODY_H / 2   # 76 mm from top

        # Player 1 — sits above mid
        pdf.set_text_color(*DARK)
        font_p = 24 if max(len(p1), len(p2)) <= 22 else (18 if max(len(p1), len(p2)) <= 30 else 14)
        pdf.set_font("Helvetica", style="B", size=font_p)
        p1_h = font_p * 0.35 + 1   # approximate line height in mm
        pdf.set_xy(12, mid - p1_h * 2.4)
        pdf.cell(W - 24, p1_h + 2, p1, align="C")

        # "&" separator
        pdf.set_text_color(*GREEN)
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_xy(12, mid - 3)
        pdf.cell(W - 24, 6, "&", align="C")

        # Player 2 — sits below mid
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", style="B", size=font_p)
        pdf.set_xy(12, mid + 4)
        pdf.cell(W - 24, p1_h + 2, p2, align="C")

        # ── Footer band ──────────────────────────────────────────────────
        FOOTER_Y = H - FOOTER_H
        pdf.set_fill_color(*GREEN)
        pdf.rect(0, FOOTER_Y, W, FOOTER_H, style="F")

        # Vertical divider between the two footer columns
        pdf.set_draw_color(*MEDIUM_GREEN)
        pdf.set_line_width(0.3)
        pdf.line(W / 2, FOOTER_Y + 6, W / 2, FOOTER_Y + FOOTER_H - 6)

        # Column labels
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", size=7)
        pdf.set_xy(0, FOOTER_Y + 5)
        pdf.cell(W / 2, 4, "TEE  TIME", align="C")
        pdf.set_xy(W / 2, FOOTER_Y + 5)
        pdf.cell(W / 2, 4, "GROUP", align="C")

        # Column values
        pdf.set_font("Helvetica", style="B", size=17)
        pdf.set_xy(0, FOOTER_Y + 12)
        pdf.cell(W / 2, 10, str(tee_time), align="C")
        pdf.set_xy(W / 2, FOOTER_Y + 12)
        pdf.cell(W / 2, 10, str(group_num), align="C")

    return bytes(pdf.output())


# ─────────────────────────── rule sheet ──────────────────────────────────


def generate_rule_sheet(tournament: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Player Information Guide / Rule Sheet.
    Pure template — no LLM call.
    Returns {subject, body, html}.
    """
    from typing import Optional as _Opt

    name          = tournament.get("name") or "Golf Tournament"
    date          = tournament.get("date") or "TBD"
    venue         = tournament.get("venue") or "TBD"
    fmt           = tournament.get("format") or "TBD"
    n_days        = int(tournament.get("numberOfDays") or 1)
    player_count  = tournament.get("playerCount", 0)
    event_type    = tournament.get("eventType") or ""
    team_size     = int(tournament.get("teamSize") or 1)
    tee_start     = tournament.get("teeTimeStart", "08:00") or "08:00"
    reg_deadline  = tournament.get("registrationDeadline") or ""
    entry_fee     = tournament.get("entryFee") or 0
    description   = tournament.get("description") or ""
    catering      = tournament.get("catering") or ""
    catering_enabled  = tournament.get("cateringEnabled", False)
    catering_items     = tournament.get("cateringItems") or ""
    catering_time     = tournament.get("cateringServingTime") or ""
    notes         = tournament.get("notes") or ""
    sponsors      = tournament.get("sponsors") or []

    # Arrival time = tee_start minus 45 min
    try:
        from datetime import datetime as _dt, timedelta as _td
        ts = _dt.strptime(tee_start, "%H:%M")
        arrival = (_dt.combine(_dt.today(), ts.time()) - _td(minutes=45)).strftime("%I:%M %p").lstrip("0")
    except Exception:
        arrival = "45 minutes before your tee time"

    event_str = event_type.capitalize() if event_type else "TBD"
    if event_type == "team":
        event_str += f" — {team_size} per team"

    body_lines = [
        f"Dear Participant — {name}",
        "",
        "WELCOME",
        "─" * 41,
        f"  Welcome to {name}! Please read this guide carefully.",
        "",
        "EVENT DETAILS",
        "─" * 41,
        f"  Tournament:   {name}",
        f"  Date:         {date}" + (f" ({n_days} days)" if n_days > 1 else ""),
        f"  Venue:        {venue}",
        f"  Format:       {fmt}",
        f"  Event Type:   {event_str}",
        f"  Players:      {player_count}",
    ]
    if entry_fee:
        body_lines.append(f"  Entry Fee:    ${entry_fee}")
    if reg_deadline:
        body_lines.append(f"  Reg. Deadline:{reg_deadline}")
    if sponsors:
        sp = ", ".join(sponsors) if isinstance(sponsors, list) else str(sponsors)
        body_lines.append(f"  Sponsors:     {sp}")

    # ── Format-specific rules grounded in knowledge documents ────────────
    fmt_lower = fmt.lower() if fmt and fmt != "TBD" else ""
    if "scramble" in fmt_lower:
        format_rules = [
            f"  Format: {fmt}",
            "  All players tee off; the team selects the best tee shot each time.",
            "  All team members then play from that spot and repeat until holed out.",
            "  Minimum drives: each player's drive must be used a minimum number of times",
            "    (announced at the opening ceremony) — this rule is mandatory for fairness.",
            "  Team scores are recorded as a gross team score unless otherwise announced.",
            "  Mulligans (if offered) will be announced at check-in — use is limited.",
        ]
        format_rules_html = [
            f"Format: <strong>{fmt}</strong>. All players tee off; the team selects the best tee shot.",
            "All team members then play from that spot and repeat until holed out.",
            "Minimum drives: each player's drive must be used a minimum number of times — confirmed at opening announcements.",
            "Team scores recorded as a <strong>gross team score</strong> unless otherwise announced.",
            "Mulligans (if offered) will be announced at check-in; use is limited.",
        ]
    elif "best ball" in fmt_lower or "four ball" in fmt_lower:
        format_rules = [
            f"  Format: {fmt}",
            "  Each player plays their own ball throughout the round.",
            "  The lowest score among team members on each hole counts as the team score.",
            "  USGA Rules of Golf apply. Handicaps will be applied per official rules.",
        ]
        format_rules_html = [
            f"Format: <strong>{fmt}</strong>. Each player plays their own ball throughout.",
            "The lowest score among team members on each hole counts as the team score.",
            "USGA Rules of Golf apply. Handicaps applied per official rules.",
        ]
    else:
        format_rules = [
            f"  Format: {fmt}",
            "  USGA Rules of Golf apply unless a local rule is announced.",
        ]
        format_rules_html = [
            f"Format: <strong>{fmt}</strong>. USGA Rules of Golf apply unless a local rule is announced.",
        ]
    _scoring = [
        "  Scorecards will be distributed at check-in — verify your group details.",
        "  Submit completed, signed scorecards to the scoring table immediately after play.",
        "  Tie-break sequence: scorecard playoff on the hardest holes, then back nine,",
        "    last six, last three, and finally the final hole.",
    ]
    _scoring_html = [
        "Scorecards distributed at check-in — verify your group details.",
        "Submit completed, <strong>signed</strong> scorecards to the scoring table immediately after play.",
        "Tie-break sequence: hardest holes \u2192 back nine \u2192 last six \u2192 last three \u2192 final hole.",
    ]
    format_rules += _scoring
    format_rules_html += _scoring_html

    body_lines += [
        "",
        "ARRIVAL & CHECK-IN",
        "─" * 41,
        f"  Please arrive by {arrival} for check-in and warm-up.",
        "  Check in at the pro shop upon arrival to receive your scorecard and cart key.",
        "  Confirm your tee time, cart assignment, and team pairing at check-in.",
        "  Opening announcements (local rules, format clarifications) will be made",
        "    before the first tee shot — attendance is required.",
        "",
        "FORMAT & SCORING",
        "─" * 41,
    ] + format_rules + [
        "",
        "PACE OF PLAY",
        "─" * 41,
        "  Please practise ready golf — play when it is safe and it is your turn.",
        "  Your group must maintain pace with the group ahead at all times.",
        "  A course marshal may issue a pace-of-play warning — respond promptly.",
        "  If your group falls significantly behind, you may be asked to skip a hole.",
        "  On-course contests should not delay the group behind you.",
        "",
        "PLAYER CONDUCT",
        "─" * 41,
        "  All participants must adhere to USGA Rules of Golf and posted local rules.",
        "  Dress code: collared shirts, golf slacks or shorts, and golf shoes required.",
        "  Cell phones must be set to silent during play.",
        "  Cheating or unsportsmanlike conduct will result in disqualification.",
        "",
        "CART & COURSE RULES",
        "─" * 41,
        "  Golf carts are provided. Cart assignment will be posted at the first tee.",
        "  Carts must remain on the cart path within 50 feet of the green.",
        "  Abide by all cart signs and course ropes without exception.",
        "  Damage to the course must be reported to golf club staff immediately.",
        "",
        "WEATHER & SAFETY",
        "─" * 41,
        "  In the event of lightning or dangerous weather, an air-horn signal will sound.",
        "  All players must immediately cease play and seek shelter in the clubhouse",
        "    or a designated on-course shelter area. Do not shelter under trees.",
        "  The round may be paused, shortened, or cancelled at the organizer's discretion.",
        "  Hydration stations are available on course — please stay hydrated.",
        "  First-aid support is available. Report any medical concerns to a marshal.",
    ]

    if catering_enabled or catering:
        body_lines += [
            "",
            "FOOD & BEVERAGE",
            "─" * 41,
        ]
        if catering_items:
            body_lines.append(f"  Menu Items:   {catering_items}")
        if catering_time:
            body_lines.append(f"  Service:      {catering_time}")
        if catering:
            body_lines.append(f"  Notes:        {catering}")
        if not catering_items and not catering_time and not catering:
            body_lines.append("  Catering will be provided — details to follow.")

    body_lines += [
        "",
        "PRIZES & AWARDS",
        "─" * 41,
        "  Awards ceremony will take place at the conclusion of play.",
        "  Prizes will be distributed for gross and net categories (1st, 2nd, 3rd).",
        "  Closest-to-the-pin and longest drive prizes will be announced at the ceremony.",
        "  Ties are broken via scorecard playoff: hardest holes, back nine, last six,",
        "    last three, and finally the final hole.",
        "",
        "CONTACT",
        "─" * 41,
        "  Questions? Contact the organizing committee before the event.",
        "  For day-of issues, see any tournament marshal or staff member on course.",
    ]

    if notes:
        body_lines += ["", "ADDITIONAL NOTES", "─" * 41, f"  {notes}"]

    body_lines += ["", "We look forward to a great day on the course!", "", "Warm regards,", f"The {name} Organizing Committee"]

    body = "\n".join(body_lines)
    subject = f"Player Information Guide — {name} ({date})"

    # ── HTML version ──────────────────────────────────────────────────────
    def _section(title: str, rows_html: str) -> str:
        return (
            f"<div style='margin-bottom:24px'>"
            f"<h2 style='margin:0 0 10px;font-size:14px;font-weight:700;color:#166534;"
            f"text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #bbf7d0;padding-bottom:4px'>"
            f"{title}</h2>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px'>{rows_html}</table></div>"
        )

    def _row(label: str, value: str) -> str:
        return (
            f"<tr style='border-bottom:1px solid #f0fdf4'>"
            f"<td style='padding:7px 12px;font-weight:600;color:#6b7280;width:160px;white-space:nowrap'>{label}</td>"
            f"<td style='padding:7px 12px;color:#111827'>{value}</td>"
            f"</tr>"
        )

    def _text_section(title: str, items: List[str]) -> str:
        li_html = "".join(f"<li style='margin-bottom:4px'>{i}</li>" for i in items)
        return (
            f"<div style='margin-bottom:24px'>"
            f"<h2 style='margin:0 0 10px;font-size:14px;font-weight:700;color:#166534;"
            f"text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #bbf7d0;padding-bottom:4px'>"
            f"{title}</h2>"
            f"<ul style='margin:0;padding-left:20px;font-size:13px;color:#374151;line-height:1.8'>{li_html}</ul></div>"
        )

    detail_rows = _row("Tournament", name)
    detail_rows += _row("Date", date + (f" ({n_days} days)" if n_days > 1 else ""))
    detail_rows += _row("Venue", venue)
    detail_rows += _row("Format", fmt)
    detail_rows += _row("Event Type", event_str)
    detail_rows += _row("Players", str(player_count))
    if entry_fee:
        detail_rows += _row("Entry Fee", f"${entry_fee}")
    if reg_deadline:
        detail_rows += _row("Reg. Deadline", reg_deadline)
    if sponsors:
        sp = ", ".join(sponsors) if isinstance(sponsors, list) else str(sponsors)
        detail_rows += _row("Sponsors", sp)

    catering_section = ""
    if catering_enabled or catering:
        c_rows = ""
        if catering_items:
            c_rows += _row("Menu Items", catering_items)
        if catering_time:
            c_rows += _row("Service Time", catering_time)
        if catering:
            c_rows += _row("Notes", catering)
        if not c_rows:
            c_rows = _row("Status", "Catering will be provided — details to follow.")
        catering_section = _section("Food &amp; Beverage", c_rows)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Player Information Guide &mdash; {name}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:660px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">
    <div style="background:#166534;padding:28px 32px;color:#fff">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;opacity:.7;margin-bottom:6px">Player Information Guide</div>
      <h1 style="margin:0;font-size:22px;font-weight:700">{name}</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:.85">{date} &nbsp;&middot;&nbsp; {venue}</p>
    </div>
    <div style="padding:28px 32px">

      {_section("Event Details", detail_rows)}

      {_text_section("Arrival &amp; Check-In", [
          f"Please arrive by <strong>{arrival}</strong> for check-in and warm-up.",
          "Check in at the pro shop upon arrival to receive your scorecard and cart key.",
          "Confirm your tee time, cart assignment, and team pairing at check-in.",
          "Opening announcements (local rules, format clarifications) will be made before the first tee shot — attendance is required.",
      ])}

      {_text_section("Format &amp; Scoring", format_rules_html)}

      {_text_section("Pace of Play", [
          "Please practise <strong>ready golf</strong> — play when it is safe and it is your turn.",
          "Your group must maintain pace with the group ahead at all times.",
          "A course marshal may issue a pace-of-play warning — please respond promptly.",
          "If your group falls significantly behind, you may be asked to skip a hole.",
          "On-course contests and sponsor activations should not delay the group behind you.",
      ])}

      {_text_section("Player Conduct", [
          "All participants must adhere to USGA Rules of Golf and posted local rules.",
          "Dress code: collared shirts, golf slacks or shorts, and golf shoes required.",
          "Cell phones must be set to silent during play.",
          "Cheating or unsportsmanlike conduct will result in disqualification.",
      ])}

      {_text_section("Cart &amp; Course Rules", [
          "Golf carts are provided. Cart assignment will be posted at the first tee.",
          "Carts must remain on the cart path within 50 feet of the green.",
          "Abide by all cart signs and course ropes without exception.",
          "Damage to the course must be reported to golf club staff immediately.",
      ])}

      {_text_section("Weather &amp; Safety", [
          "In the event of <strong>lightning or dangerous weather</strong>, an air-horn signal will sound.",
          "Players must immediately cease play and seek shelter in the clubhouse or a designated shelter area. <strong>Do not shelter under trees.</strong>",
          "The round may be paused, shortened, or cancelled at the organiser's discretion.",
          "Hydration stations are available on course — please stay hydrated throughout the round.",
          "First-aid support is available on site. Report any medical concerns to a marshal immediately.",
      ])}

      {catering_section}

      {_text_section("Prizes &amp; Awards", [
          "Awards ceremony will take place at the conclusion of play.",
          "Prizes will be distributed for gross and net categories (1st, 2nd, 3rd).",
          "Closest-to-the-pin and longest drive prizes will be announced at the ceremony.",
          "Tie-break sequence: scorecard playoff on hardest holes \u2192 back nine \u2192 last six \u2192 last three \u2192 final hole.",
      ])}

      {_text_section("Contact", [
          "Questions? Contact the organizing committee before the event.",
          "For day-of issues, see any tournament marshal or staff member on course.",
      ])}

      {('<div style="margin-bottom:24px;padding:14px 16px;background:#fefce8;border:1px solid #fde047;border-radius:8px;font-size:13px;color:#854d0e"><strong>Additional Notes:</strong> ' + notes + '</div>') if notes else ''}

    </div>
    <div style="padding:20px 32px 28px;background:#f9fafb;font-size:13px;color:#6b7280;border-top:1px solid #e5e7eb">
      We look forward to a great day on the course!<br>
      <strong style="color:#166534">The {name} Organizing Committee</strong>
    </div>
  </div>
</body></html>"""

    return {"subject": subject, "body": body, "html": html}


# ─────────────────────────── F&B summary ─────────────────────────────────


def generate_fnb_summary(tournament: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build a Food & Beverage Summary / Banquet Order Sheet.
    Returns None when catering is not enabled.
    Returns {subject, body, html} otherwise.
    """
    from typing import Optional as _Opt

    if not tournament.get("cateringEnabled"):
        return None

    name              = tournament.get("name") or "Golf Tournament"
    date              = tournament.get("date") or "TBD"
    venue             = tournament.get("venue") or "TBD"
    player_count      = tournament.get("playerCount", 0)
    catering_budget   = int(tournament.get("cateringBudget") or 0)
    catering_items    = tournament.get("cateringItems") or "TBD"
    catering_time     = tournament.get("cateringServingTime") or "TBD"
    dietary_notes     = tournament.get("cateringDietaryNotes") or ""
    catering          = tournament.get("catering") or ""

    per_head = round(catering_budget / int(player_count), 2) if int(player_count or 0) > 0 and catering_budget else 0

    body_lines = [
        f"Food & Beverage Summary — {name}",
        "",
        "EVENT OVERVIEW",
        "─" * 41,
        f"  Tournament:    {name}",
        f"  Date:          {date}",
        f"  Venue:         {venue}",
        f"  Total Players: {player_count}",
        "",
        "CATERING DETAILS",
        "─" * 41,
        f"  Menu Items:    {catering_items}",
        f"  Serving Time:  {catering_time}",
        f"  Budget:        ${catering_budget:,}",
    ]
    if per_head:
        body_lines.append(f"  Per Head:      ${per_head:.2f}")
    if dietary_notes:
        body_lines.append(f"  Dietary Notes: {dietary_notes}")
    if catering:
        body_lines.append(f"  Other Notes:   {catering}")

    body_lines += [
        "",
        "SERVING SCHEDULE",
        "─" * 41,
        f"  Service Time:  {catering_time}",
        "  Setup should begin at least 60 minutes before the serving window.",
        "  All food stations should be accessible within 10 minutes of conclusion.",
        "",
        "ACTION ITEMS FOR VENUE",
        "─" * 41,
        f"  1. Prepare the following menu items for {player_count} guests: {catering_items}.",
        f"  2. Prepare for service at: {catering_time}.",
        f"  3. Adhere to total catering budget of ${catering_budget:,}.",
    ]
    if dietary_notes:
        body_lines.append(f"  4. Accommodate dietary requirements: {dietary_notes}.")
    body_lines += [
        "",
        "Questions regarding catering should be directed to the tournament organizer.",
    ]

    body = "\n".join(body_lines)
    subject = f"Food & Beverage Summary — {name} ({date})"

    # ── HTML version ──────────────────────────────────────────────────────
    def _row(label: str, value: str) -> str:
        return (
            f"<tr style='border-bottom:1px solid #fef9c3'>"
            f"<td style='padding:8px 14px;font-weight:600;color:#6b7280;width:170px;white-space:nowrap'>{label}</td>"
            f"<td style='padding:8px 14px;color:#111827'>{value}</td>"
            f"</tr>"
        )

    def _section(title: str, rows_html: str) -> str:
        return (
            f"<div style='margin-bottom:24px'>"
            f"<h2 style='margin:0 0 10px;font-size:14px;font-weight:700;color:#92400e;"
            f"text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #fde68a;padding-bottom:4px'>"
            f"{title}</h2>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px;border:1px solid #fde68a;border-radius:6px;overflow:hidden'>{rows_html}</table></div>"
        )

    overview_rows = (
        _row("Tournament", name)
        + _row("Date", date)
        + _row("Venue", venue)
        + _row("Total Guests", str(player_count))
    )

    catering_rows = (
        _row("Menu Items", catering_items)
        + _row("Serving Time", catering_time)
        + _row("Budget", f"${catering_budget:,}")
        + (_row("Per Head", f"${per_head:.2f}") if per_head else "")
        + (_row("Dietary Notes", dietary_notes) if dietary_notes else "")
        + (_row("Other Notes", catering) if catering else "")
    )

    action_items = [
        f"Prepare the following menu items for <strong>{player_count} guests</strong>: <strong>{catering_items}</strong>.",
        f"Prepare for service at: <strong>{catering_time}</strong>.",
        f"Adhere to total catering budget of <strong>${catering_budget:,}</strong>.",
    ]
    if dietary_notes:
        action_items.append(f"Accommodate dietary requirements: <strong>{dietary_notes}</strong>.")
    action_li = "".join(f"<li style='margin-bottom:6px'>{a}</li>" for a in action_items)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food &amp; Beverage Summary &mdash; {name}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:660px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">
    <div style="background:#92400e;padding:28px 32px;color:#fff">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;opacity:.7;margin-bottom:6px">Food &amp; Beverage Summary</div>
      <h1 style="margin:0;font-size:22px;font-weight:700">{name}</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:.85">{date} &nbsp;&middot;&nbsp; {venue}</p>
    </div>
    <div style="padding:28px 32px">
      {_section("Event Overview", overview_rows)}
      {_section("Catering Details", catering_rows)}
      <div style="margin-bottom:24px">
        <h2 style="margin:0 0 10px;font-size:14px;font-weight:700;color:#92400e;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid #fde68a;padding-bottom:4px">Action Items for Venue</h2>
        <ol style="margin:0;padding-left:22px;font-size:13px;color:#374151;line-height:1.8">{action_li}</ol>
      </div>
    </div>
    <div style="padding:20px 32px 28px;background:#fffbeb;font-size:13px;color:#92400e;border-top:1px solid #fde68a">
      Questions regarding catering should be directed to the tournament organizer.
    </div>
  </div>
</body></html>"""

    return {"subject": subject, "body": body, "html": html}
