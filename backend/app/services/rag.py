import asyncio
import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Sequence

from app.data.knowledge_documents import KNOWLEDGE_DOCUMENTS

if TYPE_CHECKING:
    from fastembed import TextEmbedding

DEFAULT_CHUNK_WORD_SIZE = int(os.getenv("RAG_CHUNK_WORD_SIZE", "120"))
DEFAULT_CHUNK_WORD_OVERLAP = int(os.getenv("RAG_CHUNK_WORD_OVERLAP", "30"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
LOCAL_EMBEDDING_MODEL = os.getenv(
    "RAG_LOCAL_EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5",
)
# Set DISABLE_RAG=true to skip model loading entirely (useful on memory-limited hosts).
DISABLE_RAG: bool = os.getenv("DISABLE_RAG", "").lower() in ("1", "true", "yes")
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


@dataclass
class SourceDocumentSet:
    documents: List[Dict[str, str]]
    source_kind: str
    skipped_files: List[str]


_INDEX_LOCK = asyncio.Lock()
_MODEL_LOCK = asyncio.Lock()
_CHUNK_INDEX: List[IndexedChunk] = []
_INDEX_READY = False
_EMBEDDING_MODEL: Any = None
_RAG_STATUS: Dict[str, Any] = {
    "state": "idle",
    "ready": False,
    "embedding_model": LOCAL_EMBEDDING_MODEL,
    "corpus_dir": str(CORPUS_DIR),
    "source_kind": "unknown",
    "document_count": 0,
    "chunk_count": 0,
    "started_at": None,
    "finished_at": None,
    "last_error": "",
    "skipped_files": [],
}


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


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_rag_status(**updates: Any) -> None:
    _RAG_STATUS.update(updates)


def get_rag_status() -> Dict[str, Any]:
    return {
        **_RAG_STATUS,
        "supported_suffixes": sorted(SUPPORTED_CORPUS_SUFFIXES),
    }


def _load_corpus_documents() -> SourceDocumentSet:
    if not CORPUS_DIR.exists():
        logger.warning(
            "RAG corpus directory does not exist at %s. Falling back to bundled knowledge documents.",
            CORPUS_DIR,
        )
        return SourceDocumentSet(documents=[], source_kind="corpus", skipped_files=[])

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

    return SourceDocumentSet(
        documents=documents,
        source_kind="corpus",
        skipped_files=skipped_files,
    )


def _load_source_documents() -> SourceDocumentSet:
    corpus_documents = _load_corpus_documents()
    if corpus_documents.documents:
        return corpus_documents
    return SourceDocumentSet(
        documents=KNOWLEDGE_DOCUMENTS,
        source_kind="bundled",
        skipped_files=corpus_documents.skipped_files,
    )


def _base_chunks() -> tuple[List[IndexedChunk], SourceDocumentSet]:
    chunks: List[IndexedChunk] = []
    source_documents = _load_source_documents()

    for document in source_documents.documents:
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

    return chunks, source_documents


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


def _load_model() -> "TextEmbedding":
    global _EMBEDDING_MODEL

    if _EMBEDDING_MODEL is None:
        from fastembed import TextEmbedding

        _EMBEDDING_MODEL = TextEmbedding(LOCAL_EMBEDDING_MODEL)

    return _EMBEDDING_MODEL


async def _get_model() -> "TextEmbedding":
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    async with _MODEL_LOCK:
        if _EMBEDDING_MODEL is not None:
            return _EMBEDDING_MODEL
        return await asyncio.to_thread(_load_model)


def _encode_texts_sync(texts: Sequence[str]) -> List[List[float]]:
    model = _load_model()
    # fastembed.embed() returns a generator of numpy arrays (already L2-normalised)
    return [emb.tolist() for emb in model.embed(list(texts))]


async def _embed_texts(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []

    await _get_model()
    return await asyncio.to_thread(_encode_texts_sync, texts)


async def _build_index() -> None:
    global _CHUNK_INDEX, _INDEX_READY

    chunks, source_documents = _base_chunks()
    _update_rag_status(
        state="building",
        ready=False,
        source_kind=source_documents.source_kind,
        document_count=len(source_documents.documents),
        chunk_count=0,
        started_at=_timestamp_utc(),
        finished_at=None,
        last_error="",
        skipped_files=source_documents.skipped_files,
    )
    if not chunks:
        _CHUNK_INDEX = []
        _INDEX_READY = True
        logger.warning("RAG index build completed with 0 chunks.")
        _update_rag_status(
            state="ready",
            ready=True,
            finished_at=_timestamp_utc(),
            chunk_count=0,
        )
        return

    try:
        embeddings = await _embed_texts([chunk.text for chunk in chunks])
    except Exception as exc:
        _CHUNK_INDEX = []
        _INDEX_READY = False
        _update_rag_status(
            state="error",
            ready=False,
            finished_at=_timestamp_utc(),
            last_error=str(exc),
        )
        raise

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
    _update_rag_status(
        state="ready",
        ready=True,
        chunk_count=len(_CHUNK_INDEX),
        finished_at=_timestamp_utc(),
        last_error="",
    )
    logger.info(
        "RAG index ready with %s chunk(s) using embedding model %s.",
        len(_CHUNK_INDEX),
        LOCAL_EMBEDDING_MODEL,
    )


def _build_index_sync() -> None:
    """Build the RAG index synchronously, intended to run via asyncio.to_thread().

    Runs entirely outside the event loop so the app can serve requests
    (including health checks) while the model loads.
    """
    global _CHUNK_INDEX, _INDEX_READY

    chunks, source_documents = _base_chunks()
    _update_rag_status(
        state="building",
        ready=False,
        source_kind=source_documents.source_kind,
        document_count=len(source_documents.documents),
        chunk_count=0,
        started_at=_timestamp_utc(),
        finished_at=None,
        last_error="",
        skipped_files=source_documents.skipped_files,
    )

    if not chunks:
        _CHUNK_INDEX = []
        _INDEX_READY = True
        logger.warning("RAG index build completed with 0 chunks.")
        _update_rag_status(
            state="ready",
            ready=True,
            finished_at=_timestamp_utc(),
            chunk_count=0,
        )
        return

    try:
        model = _load_model()
        # fastembed.embed() returns a generator of numpy arrays (already L2-normalised)
        embeddings: List[List[float]] = [
            emb.tolist() for emb in model.embed([chunk.text for chunk in chunks])
        ]
    except Exception as exc:
        _CHUNK_INDEX = []
        _INDEX_READY = False
        _update_rag_status(
            state="error",
            ready=False,
            finished_at=_timestamp_utc(),
            last_error=str(exc),
        )
        raise

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
    _update_rag_status(
        state="ready",
        ready=True,
        chunk_count=len(_CHUNK_INDEX),
        finished_at=_timestamp_utc(),
        last_error="",
    )
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


async def warm_rag_index() -> None:
    if DISABLE_RAG:
        logger.info("RAG warmup skipped: DISABLE_RAG is set.")
        _update_rag_status(state="disabled", ready=False)
        return

    if _INDEX_READY:
        _update_rag_status(state="ready", ready=True)
        return

    logger.info("Starting background RAG warmup.")
    try:
        # Run entirely in a thread so the event loop (and HTTP health checks)
        # are never blocked while the model loads or embeddings are computed.
        await asyncio.to_thread(_build_index_sync)
    except asyncio.CancelledError:
        _update_rag_status(
            state="idle",
            ready=False,
            finished_at=_timestamp_utc(),
            last_error="Warmup cancelled during shutdown.",
        )
        raise
    except Exception:
        logger.exception("Background RAG warmup failed.")


async def retrieve_relevant_chunks(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> List[RetrievedChunk]:
    if not query.strip():
        return []

    if DISABLE_RAG or not _INDEX_READY:
        if DISABLE_RAG:
            logger.debug("RAG retrieval skipped: DISABLE_RAG is set.")
        else:
            logger.warning("RAG index is not ready yet; skipping retrieval for this query.")
        return []

    query_embedding = (await asyncio.to_thread(_encode_texts_sync, [query.strip()]))[0]

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


async def get_rag_chunk_by_id(chunk_id: str) -> Dict[str, Any] | None:
    target = str(chunk_id).strip()
    if not target:
        return None

    if not _INDEX_READY:
        return None
    for chunk in _CHUNK_INDEX:
        if chunk.chunk_id == target:
            return {
                "document_id": chunk.document_id,
                "title": chunk.title,
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
            }

    return None


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
