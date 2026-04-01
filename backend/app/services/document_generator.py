from datetime import datetime, timedelta
from typing import Any, Dict, List


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
    Players are placeholder names (Player 1 … N), grouped in fours.
    Returns a list of group dicts: {group, teeTime, players}.
    """
    player_count = max(int(tournament.get("playerCount", 0)), 1)
    interval = int(tournament.get("teeTimeInterval", 12))
    tee_start_str = tournament.get("teeTimeStart", "08:00") or "08:00"

    tee_start = _parse_tee_time(tee_start_str)

    players = [f"Player {i + 1}" for i in range(player_count)]

    groups = []
    group_num = 1
    idx = 0
    while idx < len(players):
        group_players = players[idx: idx + 4]
        tee_time = tee_start + timedelta(minutes=interval * (group_num - 1))
        groups.append(
            {
                "group": group_num,
                "teeTime": tee_time.strftime("%I:%M %p").lstrip("0"),
                "players": group_players,
            }
        )
        idx += 4
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
