"""
MongoDB collection schema definitions.

MongoDB is schemaless; these TypedDicts document the expected shape of each
document so the rest of the codebase has a single source of truth.

Collections
───────────
  tournaments   – one document per saved tournament draft / finalised event
  registrations – one document per player who clicked the registration link
"""

from datetime import datetime
from typing import Any, Dict, List
from typing_extensions import TypedDict


# ─────────────────────────── sub-documents ───────────────────────────────


class PlayerGroup(TypedDict):
    """
    One row in the tee-time schedule.

    players is a mix of registered full names ("Alice Smith") and
    placeholder strings ("Player 1") that haven't been claimed yet.
    """

    group: int
    teeTime: str          # e.g. "8:00 AM"
    players: List[str]    # length 1–4


# ─────────────────────────── tournaments ─────────────────────────────────


class TournamentDocument(TypedDict):
    """
    Represents a document in the **tournaments** collection.

    Indexes
    -------
      tournament_id       – unique
      registration_token  – unique
    """

    tournament_id: str          # UUID4 string, primary key used in API paths
    name: str
    date: str
    venue: str
    format: str
    number_of_days: int         # how many days the tournament runs
    player_count: int
    event_type: str             # "individual" | "team"
    team_size: int              # players per team (1 if individual)
    registration_deadline: str  # last date players may register
    entry_fee: int              # optional; 0 means free
    description: str            # optional free-text description
    tee_time_start: str         # "HH:MM"
    tee_time_interval: int      # minutes between groups
    schedule: List[PlayerGroup]

    brochure_subject: str
    brochure_body: str

    registration_token: str     # UUID4 – embedded in the public registration URL
    brochure_recipients: List[str]  # organiser-supplied email list
    status: str                 # "pending" | "finalized"

    created_at: datetime

    # Complete tournament state dict from the frontend (preserved for
    # re-generation / editing via chat)
    original_tournament: Dict[str, Any]


# ─────────────────────────── registrations ───────────────────────────────


class RegistrationDocument(TypedDict):
    """
    Represents a document in the **registrations** collection.

    This is an audit log.  The authoritative player names live in
    TournamentDocument.schedule so they can be shuffled independently.

    Index
    -----
      tournament_id  – non-unique (one tournament → many registrations)
    """

    registration_id: str    # UUID4 string
    tournament_id: str      # FK → tournaments.tournament_id
    first_name: str
    last_name: str
    registered_at: datetime
