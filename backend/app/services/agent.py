import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


SYSTEM_PROMPT = """
You are an AI golf tournament planning assistant.

You will be given:
1. The user's latest message
2. The current tournament object

Your job:
- Update the tournament object using any new information from the user
- Preserve existing information unless the user changes it
- Ask for missing important details when needed 
- Return ONLY valid JSON
- The JSON must contain exactly these two top-level fields:
  "message": a helpful natural-language response to the user
  "tournament": the full updated tournament object

Rules:
- Do not wrap the JSON in markdown
- Do not return extra text
- Keep the same general object structure
- If a field is unknown, leave it as its current value
- When asking for missing details, only ask about one missing field at a time
"""

EXAMPLE_EMPTY_TOURNAMENT = {
    "id": "",
    "name": "",
    "date": "",
    "venue": "",
    "format": "",
    "playerCount": 0,
    "sponsors": [],
    "catering": "",
    "budget": 0,
    "staffing": {
        "volunteers": 0,
        "staff": 0
    },
    "accessibility": "",
    "notes": "",
    "constraints": []
}


def _normalize_tournament(tournament: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures the basic expected structure exists before sending to the model.
    """
    merged = dict(EXAMPLE_EMPTY_TOURNAMENT)
    merged.update(tournament or {})

    if not isinstance(merged.get("sponsors"), list):
        merged["sponsors"] = []

    if not isinstance(merged.get("constraints"), list):
        merged["constraints"] = []

    if not isinstance(merged.get("staffing"), dict):
        merged["staffing"] = {"volunteers": 0, "staff": 0}

    merged["staffing"].setdefault("volunteers", 0)
    merged["staffing"].setdefault("staff", 0)

    return merged


async def handle_chat(user_message: str, tournament: Dict[str, Any]) -> Dict[str, Any]:
    tournament = _normalize_tournament(tournament)

    user_prompt = f"""
User message:
{user_message}

Current tournament object:
{json.dumps(tournament, indent=2)}
"""

    try:
        response = await client.chat.completions.create(
            model=DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = (response.choices[0].message.content or "").strip()
        parsed = json.loads(content)

        message = parsed.get("message", "I updated the tournament.")
        updated_tournament = _normalize_tournament(parsed.get("tournament", tournament))

        return {
            "message": message,
            "tournament": updated_tournament,
        }

    except Exception as exc:
        return {
            "message": f"I ran into an error while updating the tournament: {str(exc)}",
            "tournament": tournament,
        }