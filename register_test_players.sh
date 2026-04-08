#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# register_test_players.sh
#
# Reusable script to register realistic-looking test players for a Golf Event
# Planner tournament. Automatically detects event type (individual / team) and
# assigns team names.  Supports clearing existing registrations before re-running.
#
# Usage:
#   ./register_test_players.sh
#   BACKEND_URL=http://localhost:8000 ./register_test_players.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BASE_URL="${BACKEND_URL:-http://localhost:8000}"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
# Lowercase a string without relying on bash 4+ ${var,,} syntax
lowercase() { echo "$1" | tr '[:upper:]' '[:lower:]'; }

# ── Name pools (30 first names × 30 last names = 900 unique combinations) ────
FIRST_NAMES=(
  "Jack" "Emma" "Liam" "Olivia" "Noah" "Ava" "William" "Sophia" "James" "Isabella"
  "Oliver" "Mia" "Benjamin" "Charlotte" "Elijah" "Amelia" "Lucas" "Harper" "Mason" "Evelyn"
  "Logan" "Abigail" "Ethan" "Emily" "Aiden" "Elizabeth" "Ryan" "Sofia" "Michael" "Victoria"
)

LAST_NAMES=(
  "Smith" "Johnson" "Williams" "Brown" "Jones" "Garcia" "Miller" "Davis" "Wilson" "Taylor"
  "Anderson" "Thomas" "Jackson" "White" "Harris" "Martin" "Thompson" "Robinson" "Clark" "Rodriguez"
  "Lewis" "Lee" "Walker" "Hall" "Allen" "Young" "Hernandez" "King" "Wright" "Scott"
)

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║   Golf Event Planner — Test Player Registrar ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Backend: ${CYAN}${BASE_URL}${RESET}"
echo ""

# ── Step 1: Registration token ───────────────────────────────────────────────
echo -e "  ${BOLD}Tip:${RESET} Find your token in DevTools:"
echo -e "  Application → Local Storage → savedReservations → registration_token"
echo ""
read -rp "$(echo -e "  ${BOLD}Enter registration token:${RESET} ")" TOKEN
TOKEN="${TOKEN//[[:space:]]/}"

if [[ -z "$TOKEN" ]]; then
  echo -e "${RED}  Error: token cannot be empty.${RESET}"
  exit 1
fi

# ── Step 2: Fetch tournament info ─────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}Fetching tournament info...${RESET}"

RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/register/${TOKEN}")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" != "200" ]]; then
  echo -e "${RED}  Error: Could not find tournament (HTTP ${HTTP_CODE}).${RESET}"
  echo -e "${RED}  → Check the token and confirm the backend is running.${RESET}"
  exit 1
fi

# Parse response fields
parse() { echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1', '$2'))"; }

NAME=$(parse name "Unknown")
DATE=$(parse date "Unknown")
VENUE=$(parse venue "Unknown")
EVENT_TYPE=$(parse event_type "individual")
TEAM_SIZE=$(parse team_size "1")
SLOTS_REMAINING=$(parse slots_remaining "0")
TOTAL_SLOTS=$(parse total_slots "0")
PLAYERS_REGISTERED=$(parse players_registered "0")
IS_FULL=$(parse is_full "False")

echo ""
echo -e "  ┌─────────────────────────────────────────────┐"
printf  "  │  %-43s│\n" "Tournament: $NAME"
printf  "  │  %-43s│\n" "Date:       $DATE"
printf  "  │  %-43s│\n" "Venue:      $VENUE"
printf  "  │  %-43s│\n" "Type:       $EVENT_TYPE (team size: $TEAM_SIZE)"
printf  "  │  %-43s│\n" "Registered: $PLAYERS_REGISTERED / $TOTAL_SLOTS  ($SLOTS_REMAINING slot(s) open)"
echo -e "  └─────────────────────────────────────────────┘"
echo ""

# ── Step 3: Offer to clear existing registrations ────────────────────────────
if [[ "$PLAYERS_REGISTERED" -gt 0 ]]; then
  if [[ "$IS_FULL" == "True" ]]; then
    echo -e "  ${YELLOW}⚠  Tournament is full (${PLAYERS_REGISTERED} / ${TOTAL_SLOTS} registered).${RESET}"
  else
    echo -e "  ${YELLOW}⚠  ${PLAYERS_REGISTERED} player(s) are already registered.${RESET}"
  fi
  echo -e "  Clearing will remove all existing players and reset the schedule"
  echo -e "  so you can start fresh (useful when re-running for testing)."
  echo ""
  read -rp "$(echo -e "  ${BOLD}Clear existing registrations before adding new ones? (y/n):${RESET} ")" CLEAR_CONFIRM
  if [[ "$(lowercase "$CLEAR_CONFIRM")" != "y" ]]; then
    if [[ "$IS_FULL" == "True" ]]; then
      echo -e "  ${RED}Tournament is full and no slots were cleared — nothing to register.${RESET}"
      exit 1
    fi
    echo ""
  else
    echo ""
    echo -e "  ${CYAN}Clearing existing registrations...${RESET}"
    CLEAR_RESP=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/register/${TOKEN}")
    CLEAR_CODE=$(echo "$CLEAR_RESP" | tail -n1)
    if [[ "$CLEAR_CODE" == "200" ]]; then
      echo -e "  ${GREEN}✓ All registrations cleared.${RESET}"
      PLAYERS_REGISTERED=0
      SLOTS_REMAINING="$TOTAL_SLOTS"
      IS_FULL="False"
    else
      echo -e "  ${RED}Failed to clear registrations (HTTP ${CLEAR_CODE}).${RESET}"
      exit 1
    fi
    echo ""
  fi
fi

# ── Step 4: Team size ────────────────────────────────────────────────────────
echo -e "  ${BOLD}Team size controls how players are grouped into teams.${RESET}"
echo -e "  ${CYAN}1${RESET} = individual (no teams)   ${CYAN}2${RESET} = pairs   ${CYAN}4${RESET} = foursomes"
echo -e "  Tournament is saved with team size: ${BOLD}${TEAM_SIZE}${RESET}"
echo ""

while true; do
  read -rp "$(echo -e "  ${BOLD}Enter team size to use (1, 2, or 4):${RESET} ")" TEAM_SIZE_CHOICE
  TEAM_SIZE_CHOICE="${TEAM_SIZE_CHOICE//[[:space:]]/}"
  if [[ "$TEAM_SIZE_CHOICE" == "1" || "$TEAM_SIZE_CHOICE" == "2" || "$TEAM_SIZE_CHOICE" == "4" ]]; then
    break
  fi
  echo -e "  ${RED}  Invalid — please enter 1, 2, or 4.${RESET}"
done

# Warn if the chosen size differs from the tournament's saved setting
if [[ "$TEAM_SIZE_CHOICE" != "$TEAM_SIZE" ]]; then
  echo ""
  echo -e "  ${YELLOW}Warning: You chose team size ${TEAM_SIZE_CHOICE}, but this tournament"
  echo -e "  was saved with team size ${TEAM_SIZE}."
  if [[ "$EVENT_TYPE" == "team" ]]; then
    echo -e "  The backend enforces the tournament's team size (${TEAM_SIZE}) per team."
    echo -e "  Registrations to a team beyond that cap will be rejected.${RESET}"
  else
    echo -e "  Event type is '${EVENT_TYPE}' — team names will not be sent.${RESET}"
  fi
  read -rp "$(echo -e "  ${BOLD}Continue anyway? (y/n):${RESET} ")" WARN_CONFIRM
  [[ "$(lowercase "$WARN_CONFIRM")" != "y" ]] && echo -e "  Cancelled." && exit 0
fi
echo ""

# ── Step 5: How many players? ─────────────────────────────────────────────────
read -rp "$(echo -e "  ${BOLD}How many players to register?${RESET} (max ${SLOTS_REMAINING}): ")" COUNT
COUNT="${COUNT//[[:space:]]/}"

if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [[ "$COUNT" -lt 1 ]]; then
  echo -e "${RED}  Error: Enter a positive whole number.${RESET}"
  exit 1
fi

if [[ "$COUNT" -gt "$SLOTS_REMAINING" ]]; then
  echo -e "${RED}  Error: Only ${SLOTS_REMAINING} slot(s) remaining — you requested ${COUNT}.${RESET}"
  exit 1
fi

# Warn if team count doesn't divide evenly (only relevant when grouping into teams)
if [[ "$EVENT_TYPE" == "team" && "$TEAM_SIZE_CHOICE" -gt 1 ]]; then
  REMAINDER=$(( COUNT % TEAM_SIZE_CHOICE ))
  if [[ "$REMAINDER" -ne 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}Warning: ${COUNT} player(s) doesn't divide evenly into groups of ${TEAM_SIZE_CHOICE}."
    echo -e "  Result: $(( COUNT / TEAM_SIZE_CHOICE )) complete team(s) + ${REMAINDER} leftover player(s).${RESET}"
    read -rp "$(echo -e "  ${BOLD}Continue anyway? (y/n):${RESET} ")" CONFIRM
    [[ "$(lowercase "$CONFIRM")" != "y" ]] && echo -e "  Cancelled." && exit 0
  fi
fi

# ── Step 6: Register players ──────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}Registering ${COUNT} player(s) with realistic names...${RESET}"
echo ""

N_FIRST=${#FIRST_NAMES[@]}
N_LAST=${#LAST_NAMES[@]}

SUCCESS=0
FAIL=0

for i in $(seq 1 "$COUNT"); do
  GLOBAL_NUM=$(( PLAYERS_REGISTERED + i ))

  # Pick names: rotate through the pool using a prime-step offset for last names
  # so the same surname doesn't repeat in a predictable short cycle.
  F_IDX=$(( (GLOBAL_NUM - 1) % N_FIRST ))
  L_IDX=$(( ((GLOBAL_NUM - 1) * 7 + 3) % N_LAST ))
  FIRST="${FIRST_NAMES[$F_IDX]}"
  LAST="${LAST_NAMES[$L_IDX]}"

  # Phone: fake 555 number, zero-padded to 4 digits
  PHONE="555-$(printf '%04d' "$GLOBAL_NUM")"

  # Rental clubs: ~15% chance per player; if renting, randomly assign club hand
  if [[ $(( RANDOM % 100 )) -lt 15 ]]; then
    RENTAL="true"
    if [[ $(( RANDOM % 2 )) -eq 0 ]]; then
      CLUB_HAND="right"
    else
      CLUB_HAND="left"
    fi
  else
    RENTAL="false"
    CLUB_HAND="null"
  fi

  if [[ "$EVENT_TYPE" == "team" ]]; then
    GLOBAL_SLOT=$(( PLAYERS_REGISTERED + i - 1 ))
    TEAM_NUM=$(( GLOBAL_SLOT / TEAM_SIZE_CHOICE + 1 ))
    TEAM_NAME="Team $TEAM_NUM"
    if [[ "$RENTAL" == "true" ]]; then
      PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":true,\"club_hand\":\"${CLUB_HAND}\",\"team_name\":\"${TEAM_NAME}\"}"
    else
      PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":false,\"club_hand\":null,\"team_name\":\"${TEAM_NAME}\"}"
    fi
  else
    TEAM_NAME=""
    if [[ "$RENTAL" == "true" ]]; then
      PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":true,\"club_hand\":\"${CLUB_HAND}\"}"
    else
      PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":false,\"club_hand\":null}"
    fi
  fi

  RESP=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/register/${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

  HTTP=$(echo "$RESP" | tail -n1)
  RBODY=$(echo "$RESP" | sed '$d')
  RMSG=$(echo "$RBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || echo "")
  RSUCCESS=$(echo "$RBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success',False))" 2>/dev/null || echo "False")

  LABEL="${FIRST} ${LAST}"
  RENTAL_LABEL=""
  [[ "$RENTAL" == "true" ]] && RENTAL_LABEL=" ${YELLOW}[rental clubs — ${CLUB_HAND}-handed]${RESET}"
  [[ -n "$TEAM_NAME" ]] && LABEL="${LABEL} (${TEAM_NAME})"

  if [[ "$HTTP" == "200" && "$RSUCCESS" == "True" ]]; then
    echo -e "  ${GREEN}✓${RESET} ${LABEL}${RENTAL_LABEL}"
    echo -e "    ${RMSG}"
    SUCCESS=$(( SUCCESS + 1 ))
  else
    echo -e "  ${RED}✗${RESET} ${LABEL} — HTTP ${HTTP}: ${RMSG}"
    FAIL=$(( FAIL + 1 ))
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}${CYAN}──────────────────────────────────────────────${RESET}"
echo -e "  ${BOLD}Done!${RESET}  ${GREEN}${SUCCESS} registered${RESET}  •  ${RED}${FAIL} failed${RESET}"
TOTAL_NOW=$(( PLAYERS_REGISTERED + SUCCESS ))
echo -e "  Tournament total: ${TOTAL_NOW} / ${TOTAL_SLOTS} player(s)"
echo -e "  ${BOLD}${CYAN}──────────────────────────────────────────────${RESET}"
echo ""
echo -e "  Verify on the ${BOLD}Reservations${RESET} page → ${BOLD}View Registrants${RESET}"
echo ""
