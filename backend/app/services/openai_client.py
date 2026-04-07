import os
from functools import lru_cache

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


@lru_cache(maxsize=4)
def get_langchain_chat_model(temperature: float = 0.2):
    try:
        from langchain_openai import AzureChatOpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "LangChain dependencies are not installed. Run `pip install -r backend/requirements.txt`."
        ) from exc

    return AzureChatOpenAI(
        azure_deployment=CHAT_DEPLOYMENT,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature=temperature,
        timeout=float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "20")),
        max_retries=1,
    )
