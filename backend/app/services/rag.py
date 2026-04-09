import asyncio
import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Sequence

from app.data.knowledge_documents import KNOWLEDGE_DOCUMENTS

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

DEFAULT_CHUNK_WORD_SIZE = int(os.getenv("RAG_CHUNK_WORD_SIZE", "120"))
DEFAULT_CHUNK_WORD_OVERLAP = int(os.getenv("RAG_CHUNK_WORD_OVERLAP", "30"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
LOCAL_EMBEDDING_MODEL = os.getenv(
    "RAG_LOCAL_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
CORPUS_DIR = Path(
    os.getenv(
        "RAG_CORPUS_DIR",
        str(Path(__file__).resolve().parents[1] / "data" / "corpus"),
    )
)
SUPPORTED_CORPUS_SUFFIXES = {".md", ".markdown", ".txt"}

logger = logging.getLogger("uvicorn.error")


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "document"


def _load_corpus_documents() -> List[dict[str, str]]:
    if not CORPUS_DIR.exists():
        logger.warning(
            "RAG corpus directory does not exist at %s. Falling back to bundled knowledge documents.",
            CORPUS_DIR,
        )
        return []

    documents: List[dict[str, str]] = []
    skipped_files: List[str] = []

    for path in sorted(CORPUS_DIR.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(CORPUS_DIR)
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_CORPUS_SUFFIXES:
            skipped_files.append(f"{relative_path} (unsupported {suffix or 'extension'})")
            continue

        try:
            content = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            skipped_files.append(f"{relative_path} (read error: {exc})")
            continue

        if not content:
            skipped_files.append(f"{relative_path} (empty)")
            continue

        document_id = _slugify(relative_path.with_suffix("").as_posix())
        documents.append(
            {
                "id": document_id,
                "title": path.stem,
                "content": content,
            }
        )

    if skipped_files:
        logger.info("RAG corpus skipped files: %s", "; ".join(skipped_files))

    if documents:
        logger.info(
            "RAG corpus loaded %s document(s) from %s.",
            len(documents),
            CORPUS_DIR,
        )
    else:
        logger.warning(
            "RAG corpus contained no usable .md/.markdown/.txt files in %s. Falling back to bundled knowledge documents.",
            CORPUS_DIR,
        )

    return documents


def _load_source_documents() -> List[dict[str, str]]:
    corpus_documents = _load_corpus_documents()
    if corpus_documents:
        return corpus_documents
    return KNOWLEDGE_DOCUMENTS


def _base_chunks() -> List[IndexedChunk]:
    chunks: List[IndexedChunk] = []

    for document in _load_source_documents():
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


def _load_model() -> "SentenceTransformer":
    global _EMBEDDING_MODEL

    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer

        _EMBEDDING_MODEL = SentenceTransformer(LOCAL_EMBEDDING_MODEL)

    return _EMBEDDING_MODEL


async def _get_model() -> "SentenceTransformer":
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
        logger.warning("RAG index build completed with 0 chunks.")
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
    logger.info(
        "RAG index ready with %s chunk(s) using embedding model %s.",
        len(_CHUNK_INDEX),
        LOCAL_EMBEDDING_MODEL,
    )


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
