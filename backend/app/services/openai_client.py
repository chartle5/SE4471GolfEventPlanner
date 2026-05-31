"""Chat-model factory.

Migrated from Azure OpenAI to the Claude API. The module name is kept as
``openai_client`` so existing imports (``app.services.agent`` etc.) continue to
work unchanged; only the underlying provider changed.

The Claude key is read from ``CLAUDE_API_KEY`` in the environment / .env — it is
never hardcoded. The model is ``claude-sonnet-4-6``.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Claude API key — pulled from the environment, never hardcoded.
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Model used for every chat completion. Kept as CHAT_DEPLOYMENT so the rest of
# the codebase (logging/trace fields) keeps working without renames.
CHAT_DEPLOYMENT = "claude-sonnet-4-6"
LOG_LLM_PROMPTS = _env_flag("LOG_LLM_PROMPTS")


@lru_cache(maxsize=4)
def get_langchain_chat_model(temperature: float = 0.2):
    """Return a cached LangChain ChatAnthropic model.

    Preserves the previous interface (a LangChain chat model that supports
    ``.with_structured_output(...)``) so callers in ``agent.py`` are unchanged.
    """
    try:
        from langchain_anthropic import ChatAnthropic
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "langchain-anthropic is not installed. Run `pip install -r backend/requirements.txt`."
        ) from exc

    if not CLAUDE_API_KEY:
        raise RuntimeError(
            "CLAUDE_API_KEY is not set. Add it to backend/.env before starting the server."
        )

    return ChatAnthropic(
        model=CHAT_DEPLOYMENT,
        api_key=CLAUDE_API_KEY,
        temperature=temperature,
        timeout=float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "20")),
        max_retries=1,
    )
