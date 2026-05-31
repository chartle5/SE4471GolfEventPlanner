# Golf Tournament Planner — Feature Documentation

## Overview

The **Golf Event Planner** is a web application that helps a tournament organizer
plan a golf event from start to finish — without spreadsheets or guesswork. An
AI assistant interviews the organizer about their event (name, date, venue,
format, players, tee times, catering, and more), then automatically generates a
tee-time schedule and a set of ready-to-send documents (player brochure, rule
sheet, food & beverage summary, and a golf-club operations sheet).

Players sign themselves up through a public registration link — no account
needed — and the organizer can email invites, view who has registered, rearrange
pairings by drag-and-drop, print cart placards, and finalize the event.

It is designed for a **non-technical organizer**: most of the work happens
through a friendly chat and a few clearly labeled buttons.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + Vite, React Router, drag-and-drop via `@dnd-kit` |
| **Backend** | Python **FastAPI** (async) |
| **Database** | **MongoDB** (via Motor async driver) — MongoDB Atlas in the cloud |
| **AI** | **Claude API** (`claude-sonnet-4-6`) via `langchain-anthropic`, with a multi-step planning agent |
| **Knowledge retrieval (RAG)** | Local `sentence-transformers` embeddings over a built-in library of golf-planning documents |
| **Live data** | Weather / sunrise-sunset lookups via a local MCP (Model Context Protocol) server |
| **Email** | SendGrid |
| **Auth** | JWT (organizer accounts); public registration uses an opaque token link |
| **PDF** | `fpdf2` (cart placards) |

> **Note:** The AI integration was migrated from Azure OpenAI to the Claude API.
> The Claude key is read from `CLAUDE_API_KEY` in `backend/.env`. Document
> embeddings run locally and do not call any external AI provider.

---

## Current Features

### 1. Organizer Accounts (Sign Up / Sign In)
- **What it does:** Lets an organizer create an account and securely sign in.
  Sessions persist across page reloads.
- **Where it lives:** The Login and Create Account screens (shown when you are
  signed out).
- **Technical notes:** JWT tokens issued by `/auth/login` and `/auth/register`;
  passwords hashed with bcrypt; user records stored in MongoDB.

### 2. Dashboard
- **What it does:** A quick snapshot of the current planning session — tournament
  name, player count, event type, and status — plus a "Plan Tournament" shortcut.
- **Where it lives:** The home screen after signing in.

### 3. AI Tournament Planner (Chat)
- **What it does:** A conversational assistant that collects all the details of
  your event one question at a time, validates them (e.g. the venue must be a
  real course; the registration deadline must be before the event), and tells you
  when it has everything it needs. It can also answer planning questions and look
  up live weather or sunrise/sunset times for tee scheduling. A live side panel
  shows which required fields are filled.
- **Where it lives:** **Plan Tournament** page.
- **Technical notes:** A multi-step agent (analyze → validate → respond) built on
  Claude (`claude-sonnet-4-6`) with structured outputs, retrieval-augmented with
  a local planning-document library, and live tools via an MCP weather server.

### 4. Document Generation
- **What it does:** From the collected details, generates a tee-time schedule and
  a player brochure (and, where relevant, a rule sheet and a food & beverage
  summary). Saving the tournament writes it to the database and produces a public
  registration link.
- **Where it lives:** Triggered by **Save Tournament** on the Plan Tournament
  page; results appear under **Reservations**.

### 5. Knowledge Base
- **What it does:** A searchable library of golf-tournament planning resources
  (rules summaries, format guides, pace-of-play, weather policy, etc.) the
  organizer can read in-app.
- **Where it lives:** **Knowledge Base** page.

### 6. Reservations
- **What it does:** Lists every saved tournament with its key details, and lets
  you open one or delete it (with a confirmation prompt).
- **Where it lives:** **Reservations** page.

### 7. Tournament Detail — the operations hub
- **What it does:** Everything you do with a saved event:
  - **Live tee schedule** that updates as players register.
  - **Registration progress** and a shareable sign-up link.
  - **Drag-and-drop pairing editor** — rearrange who plays in which tee group
    (teammates locked together; see Feature 11).
  - **Shuffle** — randomly redistribute players across the existing tee times.
  - **Generate Test Players** — seed synthetic registrants for testing (see
    Feature 10).
  - **Email actions:** send invites, send the schedule, send the player rule
    sheet, send the food & beverage summary, and send the club operations sheet.
  - **View Registrants** — a table of everyone signed up (name, phone, rental
    clubs, team, tee slot).
  - **Cart Placards** — download a print-ready PDF, one placard per cart.
  - **Delete** the tournament (with confirmation).
- **Where it lives:** Open any card on the **Reservations** page.

### 8. Public Player Registration
- **What it does:** A no-login page where invited players enter their name, phone,
  rental-club preference (and team name for team events) to claim an open tee
  slot. Shows remaining spots and a success confirmation.
- **Where it lives:** The link emailed to players (`/player-register/<token>`).

### 9. Email Delivery
- **What it does:** Sends branded HTML emails — invitations with a "Register Now"
  button, the full schedule, the rule sheet, the F&B/banquet order sheet, and the
  club operations sheet.
- **Technical notes:** SendGrid; recipients can be entered as a comma/space list.

### 10. Generate Test Players (dev/testing tool)
- **What it does:** One click registers a chosen number of realistic synthetic
  players (names, phone numbers, ~15% with rental clubs, and team assignment for
  team events). Optionally clears existing registrations first. Useful for demos
  and testing without manually filling the form many times.
- **Where it lives:** **Generate Test Players** button (outlined/secondary style)
  on the Tournament Detail page. Also available from the terminal via
  `register_test_players.sh`.
- **Technical notes:** Backend endpoint `POST /tournaments/{id}/seed-players`
  (organizer-authenticated) reusing the same registration logic as real players.

### 11. Drag-and-Drop Pairing Editor (teams locked)
- **What it does:** Lets the organizer rearrange players across tee groups by
  dragging. **Registered teammates are bundled into a single block** and always
  move together — partners can never be split up. A **Save Order** button commits
  the arrangement, with a success/error toast; **Reset** discards unsaved changes.
- **Where it lives:** Inside the **Tee Schedule** card on Tournament Detail
  (shown while the event is not finalized).
- **Technical notes:** Built with `@dnd-kit`. Saving calls
  `POST /tournaments/{id}/reorder`, which re-validates server-side that no player
  was added or removed and that teammates remain in one group before persisting
  to MongoDB.

### 12. Finalize Tournament
- **What it does:** Locks the schedule and emails the final tee sheet to all saved
  recipients. After finalizing, the schedule becomes read-only.
- **Technical notes:** `POST /tournaments/{id}/finalize`.

---

## Future Features (Planned)

### 1. Payment Processing
**What it would do:** Collect the entry fee online as part of registration. After
a player fills in their details, they would be taken to a secure checkout; their
**payment status** (paid / pending / refunded) would be tracked per player and
shown in the Registrants table and on the club operations sheet. The organizer
could see total collected at a glance and gate a slot until payment clears.

**How it could work:**
- Integrate **Stripe Checkout** (hosted payment page — least PCI burden).
- On the public registration page, if `entryFee > 0`, create a Stripe Checkout
  session and redirect the player; confirm the slot only after a successful
  Stripe **webhook** (`checkout.session.completed`).
- Add a `payment_status` and `payment_ref` field to each registration document.
- New env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.

**Impact on the registration flow:** Registration becomes two steps (details →
pay). Slot reservation should be held briefly during checkout and released if
payment is abandoned, so seats aren't lost to incomplete payments.

### 2. Live Leaderboard with Marshal Scoring
**What it would do:** During the event, marshals enter scores **hole by hole** in
real time from their phones. A live leaderboard ranks players/teams and updates
for organizers and spectators as scores come in, using the tournament's existing
tie-breaking rules.

**How it could work:**
- A lightweight, mobile-friendly **marshal scoring view** keyed off the
  registration token or a per-marshal code; enter strokes per hole per group.
- A new `scores` collection (player/team → hole → strokes) and a computed
  leaderboard endpoint that applies the format's scoring + tie-breakers.
- **Real-time updates** via either short-interval polling (simplest, reuses the
  existing 15-second poll pattern on Tournament Detail) or **WebSockets** for
  instant push to a public spectator leaderboard.
- A public, read-only leaderboard page (no login), similar to the existing public
  registration page.

**Data model changes:** Add a `scores` collection and a derived leaderboard;
extend the tournament document with a `scoring_status` (in-progress / final).
