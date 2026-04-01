from typing import Dict, List


KNOWLEDGE_DOCUMENTS: List[Dict[str, str]] = [
    {
        "id": "planning-timeline",
        "title": "Tournament Planning Timeline",
        "content": """
Start planning at least six to eight weeks before the event. Confirm the course,
shotgun versus tee time format, player count target, budget guardrails, and the
primary objective of the tournament such as fundraising, networking, or team
building. Once those foundations are decided, lock in registration deadlines,
sponsorship outreach, catering windows, and staffing requirements.

Four weeks before the event, publish a detailed schedule covering arrival,
check-in, warm-up, opening remarks, first tee or shotgun start, meal service,
awards, and cleanup. Confirm signage, scorecards, pairings, sponsor placements,
and any special contests like longest drive or closest to the pin. This is also
the point where contingency plans for rain, late players, and cart shortages
should be documented.

In the final week, shift from planning to execution. Reconfirm vendors, print
player materials, brief volunteers, and walk the venue with the course staff.
Assign one person to own registration, one to own scoring, and one to own vendor
coordination so that problems are routed quickly on tournament day.
""".strip(),
    },
    {
        "id": "scramble-format",
        "title": "Scramble Format Operations",
        "content": """
In a scramble, every player on a team tees off, the team selects the best shot,
and all players hit the next stroke from that location. The format is popular for
charity and corporate events because it keeps pace moving and allows mixed skill
levels to contribute without slowing the field.

Before play begins, communicate whether the event is a four-person scramble,
whether mulligans are allowed, and whether a minimum number of drives from each
player must be used. Those rules matter because they affect fairness and team
strategy. If minimum-drive rules are used, print them on the scorecard and repeat
them during the opening announcements.

Scramble events work best when scoring instructions are simple. Use gross team
score unless there is a handicap adjustment method the field already understands.
If you expect a large field, prepare a visible process for turning in scorecards
promptly so the awards ceremony is not delayed.
""".strip(),
    },
    {
        "id": "registration-checkin",
        "title": "Registration and Check-In Procedures",
        "content": """
Registration should open early enough to avoid a line fifteen minutes before the
start. A common approach is to open check-in sixty to ninety minutes before play
with separate stations for pre-paid players, walk-up issues, and sponsor or VIP
guests. Each station should have the player list, cart assignment, scorecard
packet, contest entry instructions, and contact information for the event lead.

Use volunteers to greet players, confirm names, hand out materials, and direct
them to warm-up areas, breakfast, or the practice range. If the event includes a
raffle, silent auction, or donation table, keep that traffic away from the main
check-in line so registration keeps moving.

The most common failure point at check-in is missing assignments. Avoid that by
preparing pairings, cart numbers, and hole assignments the day before. Keep a
small buffer for late substitutions so the registration team can solve problems
without rewriting the entire field.
""".strip(),
    },
    {
        "id": "tee-times-pace",
        "title": "Tee Times and Pace of Play",
        "content": """
Tee time spacing should reflect the course layout and player skill level. For
mixed-skill charity fields, a little more spacing reduces backups and frustration.
If the event uses a shotgun start, hole assignments should balance high-traffic
holes with beginner-friendly pacing so one slow group does not stall the entire
field.

Publish expectations for ready golf, scorekeeping, and pickup rules before the
round starts. Pace improves when players know who records scores, where to stage
carts, and what to do if a team falls behind. On-course marshals should be briefed
to solve pace issues politely and consistently rather than only reacting when
groups are already far out of position.

If the tournament includes contests or sponsor activations on holes, make sure
they do not block the teeing ground or interfere with the group behind them. Any
extra activity at a hole needs a volunteer plan so play continues smoothly.
""".strip(),
    },
    {
        "id": "staffing-volunteers",
        "title": "Staffing and Volunteer Coverage",
        "content": """
A small tournament still needs clearly assigned ownership. Core roles typically
include an event lead, registration lead, scoring coordinator, course operations
contact, sponsor liaison, and a floating troubleshooter. In a lean setup, one
person can cover more than one role, but responsibilities should still be named
in advance.

Volunteer coverage is usually needed at registration, hole contests, photo or
social moments, raffle support, meal service, and teardown. Build schedules with
breaks because volunteers become less reliable when they are left on one station
for the entire day without rotation.

Before the event begins, give every staff member and volunteer a one-page run of
show with phone numbers, start times, escalation paths, and site map notes. That
single document reduces repetitive questions and helps the team respond faster
when weather, timing, or player issues change the plan.
""".strip(),
    },
    {
        "id": "sponsorship-catering",
        "title": "Sponsorship and Catering Coordination",
        "content": """
Sponsor benefits should be matched to specific moments in the player journey. Good
placements include registration signage, branded tee gifts, hole signage, sponsor
remarks during opening announcements, and award presentation mentions. If a sponsor
expects a table or on-course activation, confirm the physical footprint with the
course so it does not conflict with golf operations.

Catering decisions should align with the schedule and event type. Morning rounds
often need coffee, light breakfast, beverage carts, and a post-round lunch. An
afternoon start might shift the budget toward reception food and award service.
Keep dietary restrictions simple to manage by collecting them during registration
and giving the caterer a final count ahead of the event.

When budgets are tight, protect the items players notice most: check-in flow,
course readiness, meal timing, and awards experience. Decorative extras matter
less than avoiding long waits or running out of food and drinks.
""".strip(),
    },
    {
        "id": "weather-safety-accessibility",
        "title": "Weather, Safety, and Accessibility",
        "content": """
Every tournament should document what happens during lightning, heavy rain, extreme
heat, or unsafe course conditions. Players need to know whether the round will be
paused, shortened, rescheduled, or cancelled, and staff need one person authorized
to make that call in coordination with the course.

Safety planning also includes hydration, first-aid access, cart rules, and clear
communication channels. If the event uses volunteers on holes, provide a quick
briefing on who to contact for medical, weather, or facility issues instead of
expecting volunteers to improvise.

Accessibility needs should be handled early rather than on tournament morning.
Ask about mobility support, cart access, parking proximity, dietary needs, and
communication accommodations during registration so the event can prepare rather
than react.
""".strip(),
    },
    {
        "id": "scoring-awards",
        "title": "Scoring, Tie-Breaks, and Awards",
        "content": """
Scoring should be designed for fast collection and easy verification. Teams should
know exactly where scorecards are returned, who signs them, and when unofficial
results will be posted. If the field is large, assign one person to data entry and
another to card verification to reduce mistakes during the awards rush.

Tie-break rules must be announced before play starts. Common options include a
scorecard playoff, matching scorecards on the hardest holes, or a pre-declared
sequence such as back nine, last six, last three, and final hole. Whatever rule is
used, it should be printed and applied consistently.

Awards ceremonies work best when they begin soon after the round and follow a short
agenda. Thank sponsors, recognize contest winners, announce team results, and keep
transitions tight. Long scoring delays drain energy and weaken the close of the
event.
""".strip(),
    },
]
