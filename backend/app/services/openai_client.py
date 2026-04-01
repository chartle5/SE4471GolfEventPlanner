import os

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()


def _env_flag(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}

client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
LOG_LLM_PROMPTS = _env_flag("LOG_LLM_PROMPTS")
