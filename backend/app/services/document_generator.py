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
