import asyncio
import math
import os
from dataclasses import dataclass
from typing import Any, List, Sequence

from app.data.knowledge_documents import KNOWLEDGE_DOCUMENTS
from sentence_transformers import SentenceTransformer

DEFAULT_CHUNK_WORD_SIZE = int(os.getenv("RAG_CHUNK_WORD_SIZE", "120"))
DEFAULT_CHUNK_WORD_OVERLAP = int(os.getenv("RAG_CHUNK_WORD_OVERLAP", "30"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
LOCAL_EMBEDDING_MODEL = os.getenv(
    "RAG_LOCAL_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


@dataclass
class IndexedChunk:
    document_id: str
    title: str
    chunk_id: str
    text: str
    embedding: List[float]


@dataclass
class RetrievedChunk:
    document_id: str
    title: str
    chunk_id: str
    text: str
    score: float


_INDEX_LOCK = asyncio.Lock()
_MODEL_LOCK = asyncio.Lock()
_CHUNK_INDEX: List[IndexedChunk] = []
_INDEX_READY = False
_EMBEDDING_MODEL: Any = None


def _chunk_text(
    text: str,
    chunk_word_size: int = DEFAULT_CHUNK_WORD_SIZE,
    overlap_words: int = DEFAULT_CHUNK_WORD_OVERLAP,
) -> List[str]:
    words = text.split()
    if not words:
        return []

    if overlap_words >= chunk_word_size:
        overlap_words = max(0, chunk_word_size // 4)

    chunks: List[str] = []
    start = 0

    while start < len(words):
        end = min(len(words), start + chunk_word_size)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap_words)

    return chunks


def _base_chunks() -> List[IndexedChunk]:
    chunks: List[IndexedChunk] = []

    for document in KNOWLEDGE_DOCUMENTS:
        for index, text in enumerate(_chunk_text(document["content"]), start=1):
            chunks.append(
                IndexedChunk(
                    document_id=document["id"],
                    title=document["title"],
                    chunk_id=f'{document["id"]}-chunk-{index}',
                    text=text,
                    embedding=[],
                )
            )

    return chunks


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = 0.0
    left_norm = 0.0
    right_norm = 0.0

    for left_value, right_value in zip(left, right):
        numerator += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return numerator / (math.sqrt(left_norm) * math.sqrt(right_norm))


def _load_model() -> SentenceTransformer:
    global _EMBEDDING_MODEL

    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer(LOCAL_EMBEDDING_MODEL)

    return _EMBEDDING_MODEL


async def _get_model() -> SentenceTransformer:
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    async with _MODEL_LOCK:
        if _EMBEDDING_MODEL is not None:
            return _EMBEDDING_MODEL
        return await asyncio.to_thread(_load_model)


def _encode_texts_sync(texts: Sequence[str]) -> List[List[float]]:
    model = _load_model()
    embeddings = model.encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


async def _embed_texts(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []

    await _get_model()
    return await asyncio.to_thread(_encode_texts_sync, texts)


async def _build_index() -> None:
    global _CHUNK_INDEX, _INDEX_READY

    chunks = _base_chunks()
    if not chunks:
        _CHUNK_INDEX = []
        _INDEX_READY = True
        return

    embeddings = await _embed_texts([chunk.text for chunk in chunks])

    _CHUNK_INDEX = [
        IndexedChunk(
            document_id=chunk.document_id,
            title=chunk.title,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            embedding=embeddings[index],
        )
        for index, chunk in enumerate(chunks)
    ]
    _INDEX_READY = True


async def ensure_rag_index() -> None:
    if _INDEX_READY:
        return

    async with _INDEX_LOCK:
        if _INDEX_READY:
            return
        await _build_index()


async def retrieve_relevant_chunks(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> List[RetrievedChunk]:
    if not query.strip():
        return []

    await ensure_rag_index()

    query_embedding = (await _embed_texts([query.strip()]))[0]

    ranked_chunks = [
        RetrievedChunk(
            document_id=chunk.document_id,
            title=chunk.title,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            score=_cosine_similarity(query_embedding, chunk.embedding),
        )
        for chunk in _CHUNK_INDEX
    ]

    ranked_chunks.sort(key=lambda chunk: chunk.score, reverse=True)
    return ranked_chunks[:top_k]


def format_retrieved_context(chunks: Sequence[RetrievedChunk]) -> str:
    if not chunks:
        return "No retrieved knowledge snippets."

    sections = []
    for chunk in chunks:
        sections.append(
            "\n".join(
                [
                    f"Source: {chunk.title}",
                    f"Chunk: {chunk.chunk_id}",
                    f"Similarity: {chunk.score:.3f}",
                    f"Snippet: {chunk.text}",
                ]
            )
        )

    return "\n\n".join(sections)
