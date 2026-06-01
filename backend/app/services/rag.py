"""RAG stub — embedding model removed on the No-RAG branch.

All public symbols that the rest of the codebase imports are preserved so
no other file needs to change.  Retrieval always returns an empty result.
"""
from typing import Any, List, Sequence

# Kept so agent.py can reference it for logging without errors.
LOCAL_EMBEDDING_MODEL = "none"


async def retrieve_relevant_chunks(
    query: str,
    top_k: int = 3,
) -> List[Any]:
    """No-op: always returns an empty list."""
    return []


def format_retrieved_context(chunks: Sequence[Any]) -> str:
    return "No retrieved knowledge snippets."
