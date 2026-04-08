#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# register_test_players.sh
#
# Reusable script to register test players for a Golf Event Planner tournament.
# Automatically detects event type (individual / team) and assigns team names.
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

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║   Golf Event Planner — Test Player Registrar ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Backend: ${CYAN}${BASE_URL}${RESET}"
echo ""

# ── Step 1: Registration token ───────────────────────────────────────────────
echo -e "  ${BOLD}Tip:${RESET} Find your token in the browser DevTools:"
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

if [[ "$IS_FULL" == "True" ]]; then
  echo -e "  ${RED}This tournament is already full — no slots remaining.${RESET}"
  exit 1
fi

# ── Step 3: Team size ────────────────────────────────────────────────────────
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
  [[ "${WARN_CONFIRM,,}" != "y" ]] && echo -e "  Cancelled." && exit 0
fi
echo ""

# ── Step 4: How many players? ─────────────────────────────────────────────────
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
    [[ "${CONFIRM,,}" != "y" ]] && echo -e "  Cancelled." && exit 0
  fi
fi

# ── Step 5: Register players ──────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}Registering ${COUNT} player(s)...${RESET}"
echo ""

SUCCESS=0
FAIL=0

for i in $(seq 1 "$COUNT"); do
  GLOBAL_NUM=$(( PLAYERS_REGISTERED + i ))
  FIRST="Player"
  LAST="$GLOBAL_NUM"
  PHONE="555-$(printf '%04d' "$GLOBAL_NUM")"

  if [[ "$EVENT_TYPE" == "team" ]]; then
    # Group players globally based on TEAM_SIZE_CHOICE:
    #   size=1 → every player is their own team (Team N = their global number)
    #   size=2 → pairs: players 1+2 → Team 1, 3+4 → Team 2, …
    #   size=4 → foursomes: players 1-4 → Team 1, 5-8 → Team 2, …
    GLOBAL_SLOT=$(( PLAYERS_REGISTERED + i - 1 ))
    TEAM_NUM=$(( GLOBAL_SLOT / TEAM_SIZE_CHOICE + 1 ))
    TEAM_NAME="Team $TEAM_NUM"
    PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":false,\"team_name\":\"${TEAM_NAME}\"}"
  else
    TEAM_NAME=""
    PAYLOAD="{\"first_name\":\"${FIRST}\",\"last_name\":\"${LAST}\",\"phone_number\":\"${PHONE}\",\"rental_clubs\":false}"
  fi

  RESP=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/register/${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

  HTTP=$(echo "$RESP" | tail -n1)
  RBODY=$(echo "$RESP" | sed '$d')
  RMSG=$(echo "$RBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || echo "")
  RSUCCESS=$(echo "$RBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success',False))" 2>/dev/null || echo "False")

  LABEL="${FIRST} ${LAST}"
  [[ -n "$TEAM_NAME" ]] && LABEL="${LABEL} (${TEAM_NAME})"

  if [[ "$HTTP" == "200" && "$RSUCCESS" == "True" ]]; then
    echo -e "  ${GREEN}✓${RESET} ${LABEL}"
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
