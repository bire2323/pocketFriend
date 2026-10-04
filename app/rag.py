"""Retrieval-Augmented Generation over the student's own PDFs.

Pipeline:
    question -> embed -> search ChromaDB -> build context -> Gemma -> answer

Two rules drive the design:

1. Never send a whole PDF to the model. Only the top few retrieved chunks.
2. Never invent a citation. Sources come from the metadata of chunks that were
   genuinely returned by the vector search.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Iterable, Optional, Sequence

from . import config
from .documents import Chunk, DocumentError, load_pdf
from .gemma import ModelNotFoundError, OllamaUnavailableError, generate

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EmbeddingError(RuntimeError):
    """The local embedding model could not be loaded or used."""


class RetrievalError(RuntimeError):
    """The vector store could not be read or written."""


NO_ANSWER_MESSAGE = (
    "I couldn't find enough relevant information in your uploaded documents."
)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

_EMBEDDER_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _sentence_transformer(name: str = config.EMBEDDING_MODEL):
    """Load (and cache) the local sentence-embedding model.

    Cached at module level so a Streamlit session and the pytest suite do not
    each hold their own copy of the weights in RAM.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingError(
            "sentence-transformers is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    with _EMBEDDER_LOCK:
        try:
            return SentenceTransformer(name)
        except Exception as exc:
            raise EmbeddingError(
                f"PocketFriend could not load the local embedding model '{name}'.\n\n"
                "The model downloads once (~90 MB) and is then cached for offline "
                "use. Fix it by running:\n\n"
                f"    python -c \"from huggingface_hub import snapshot_download; "
                f"snapshot_download('{name}')\"\n\n"
                f"Details: {type(exc).__name__}: {exc}"
            ) from exc


def embed_texts(texts: Sequence[str], embedder: Optional[Callable] = None) -> list[list[float]]:
    """Embed a list of strings with the local model."""
    if not texts:
        return []
    if embedder is not None:
        return [list(embedder(text)) for text in texts]
    model = _sentence_transformer()
    try:
        vectors = model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
    except Exception as exc:
        raise EmbeddingError(
            f"PocketFriend could not create embeddings.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc
    return [vector.tolist() for vector in vectors]


def embed_query(query: str, embedder: Optional[Callable] = None) -> list[float]:
    vectors = embed_texts([query], embedder=embedder)
    return vectors[0]


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

_CLIENT_LOCK = threading.Lock()
_CLIENT = None


def get_client():
    """Chroma persistent client, created once per process."""
    global _CLIENT
    if _CLIENT is None:
        with _CLIENT_LOCK:
            if _CLIENT is None:
                config.ensure_directories()
                try:
                    import chromadb
                    from chromadb.config import Settings
                except ImportError as exc:
                    raise RetrievalError(
                        "chromadb is not installed. Run: pip install -r requirements.txt"
                    ) from exc
                try:
                    _CLIENT = chromadb.PersistentClient(
                        path=str(config.CHROMA_DIR),
                        settings=Settings(anonymized_telemetry=False, allow_reset=True),
                    )
                except Exception as exc:
                    raise RetrievalError(
                        f"PocketFriend could not open the local vector database.\n\n"
                        f"Details: {type(exc).__name__}: {exc}"
                    ) from exc
    return _CLIENT


def get_collection():
    """The single document collection, created on first use.

    Cosine distance keeps the relevance threshold in `config` meaningful.
    Embeddings are always supplied by this module, so the collection needs no
    built-in embedding function.
    """
    client = get_client()
    try:
        return client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as exc:
        raise RetrievalError(
            f"PocketFriend could not open the document index.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _first_meta(metadata: dict, key: str):
    """Chroma returns metadata values as lists even for single strings."""
    value = metadata.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def index_document(
    pdf_source: str | bytes,
    filename: str,
    embedder: Optional[Callable] = None,
) -> dict:
    """Extract, chunk, embed and store one PDF.

    Re-indexing a file first removes its old chunks, so a document is never
    duplicated. Returns a summary dict for the UI.
    """
    chunks, report = load_pdf(pdf_source, filename=filename)
    return index_chunks(chunks, filename=filename, report=report, embedder=embedder)


def index_chunks(
    chunks: Sequence[Chunk],
    filename: str,
    report=None,
    embedder: Optional[Callable] = None,
) -> dict:
    """Embed and store already-built chunks."""
    if not chunks:
        raise DocumentError(f"No text found in {filename}.")

    collection = get_collection()

    # Replace any previous version of this document.
    try:
        collection.delete(where={"filename": filename})
    except Exception:
        # An empty or brand-new collection can complain about the where filter.
        pass

    documents = [chunk.text for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]
    embeddings = embed_texts(documents, embedder=embedder)

    try:
        collection.add(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )
    except Exception as exc:
        raise RetrievalError(
            "PocketFriend could not save this document to the local index.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc

    return {
        "filename": filename,
        "pages": report.pages if report else 0,
        "chunks": len(chunks),
        "characters": report.characters if report else sum(len(c) for c in chunks),
        "warnings": list(report.warnings) if report else [],
    }


def remove_document(filename: str) -> int:
    """Delete every chunk belonging to a filename. Returns chunks removed."""
    collection = get_collection()
    try:
        existing = collection.get(where={"filename": filename}, include=[])
        count = len(_as_list(existing.get("ids") if isinstance(existing, dict) else existing.ids))
    except Exception:
        count = 0
    try:
        collection.delete(where={"filename": filename})
    except Exception as exc:
        raise RetrievalError(
            f"PocketFriend could not remove '{filename}' from the index.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc
    return count


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@dataclass
class Source:
    """One retrieved chunk, with the real provenance of the answer."""

    filename: str
    page: int
    chunk_id: str
    text: str
    score: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.filename} — Page {self.page}"

    @property
    def short_label(self) -> str:
        return f"{self.filename}, page {self.page}"

    def excerpt(self, limit: int = 320) -> str:
        text = " ".join(self.text.split())
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@dataclass
class Answer:
    """The result of answering a question."""

    question: str
    text: str
    sources: list[Source] = field(default_factory=list)
    grounded: bool = False
    note: str = ""

    @property
    def best_score(self) -> float:
        return self.sources[0].score if self.sources else 1.0


def document_count() -> int:
    """How many distinct files are indexed."""
    collection = get_collection()
    try:
        existing = collection.get(include=["metadatas"])
    except Exception as exc:
        raise RetrievalError(
            "PocketFriend could not read the document index.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc
    names = set()
    raw = existing.get("metadatas") if isinstance(existing, dict) else existing.metadatas
    for meta in _as_list(raw):
        if meta:
            names.add(_first_meta(meta, "filename"))
    return len([name for name in names if name])


def chunk_count() -> int:
    collection = get_collection()
    try:
        return collection.count()
    except Exception:
        return 0


def indexed_documents() -> list[str]:
    """Filenames present in the index, sorted."""
    collection = get_collection()
    try:
        existing = collection.get(include=["metadatas"])
    except Exception:
        return []
    names = set()
    raw = existing.get("metadatas") if isinstance(existing, dict) else existing.metadatas
    for meta in _as_list(raw):
        if meta:
            names.add(_first_meta(meta, "filename"))
    return sorted(str(name) for name in names if name)


def library_snapshot() -> dict:
    """Everything the document library screen needs, from a single index read.

    Read-only helper for the interface. Returns::

        {"documents": [filename, ...], "pages": {filename: pages},
         "chunks": {filename: chunks}}

    Page counts are the highest page number actually indexed for a file, which is
    the honest number to show a student.
    """
    snapshot: dict = {"documents": [], "pages": {}, "chunks": {}}
    try:
        collection = get_collection()
        existing = collection.get(include=["metadatas"])
    except Exception as exc:
        raise RetrievalError(
            "PocketFriend could not read the document index.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc

    raw = existing.get("metadatas") if isinstance(existing, dict) else existing.metadatas
    for meta in _as_list(raw):
        if not meta:
            continue
        filename = _first_meta(meta, "filename")
        if not filename:
            continue
        filename = str(filename)
        snapshot["chunks"][filename] = snapshot["chunks"].get(filename, 0) + 1
        try:
            page = int(_first_meta(meta, "page") or 0)
        except (TypeError, ValueError):
            page = 0
        snapshot["pages"][filename] = max(snapshot["pages"].get(filename, 0), page)

    snapshot["documents"] = sorted(snapshot["chunks"])
    return snapshot


def search_documents(
    query: str,
    n_results: int = config.TOP_K,
    filename: Optional[str] = None,
    embedder: Optional[Callable] = None,
) -> list[Source]:
    """Retrieve the chunks most similar to a query.

    Similarity is reported as a 0-1 score (1 = identical) so the UI can talk
    about confidence without exposing raw cosine distances.
    """
    query = (query or "").strip()
    if not query:
        return []
    if chunk_count() == 0:
        return []

    collection = get_collection()
    query_vector = embed_query(query, embedder=embedder)

    where = {"filename": filename} if filename else None
    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": max(1, int(n_results)),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    try:
        result = collection.query(**kwargs)
    except Exception as exc:
        raise RetrievalError(
            "PocketFriend could not search your documents.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc

    def read(key: str) -> list:
        value = result.get(key) if isinstance(result, dict) else getattr(result, key, None)
        rows = _as_list(value)
        return rows[0] if rows else []

    documents = read("documents")
    metadatas = read("metadatas")
    distances = read("distances")

    sources: list[Source] = []
    for position, text in enumerate(documents):
        meta = metadatas[position] if position < len(metadatas) else {}
        meta = meta or {}
        distance = 0.0
        if position < len(distances):
            raw_distance = distances[position]
            if isinstance(raw_distance, list):
                raw_distance = raw_distance[0] if raw_distance else 0.0
            try:
                distance = float(raw_distance)
            except (TypeError, ValueError):
                distance = 0.0
        if not math.isfinite(distance):
            distance = 1.0

        try:
            page = int(_first_meta(meta, "page") or 0)
        except (TypeError, ValueError):
            page = 0

        sources.append(
            Source(
                filename=str(_first_meta(meta, "filename") or "unknown"),
                page=page,
                chunk_id=str(_first_meta(meta, "chunk_id") or f"chunk_{position}"),
                text=str(text),
                # Cosine distance -> similarity in [0, 1].
                score=round(max(0.0, min(1.0, 1.0 - distance)), 3),
            )
        )

    # Deduplicate sources that come from the same page, keeping the best hit.
    best_per_page: dict[tuple, Source] = {}
    ordered: list[Source] = []
    for source in sources:
        key = (source.filename, source.page)
        if key not in best_per_page:
            best_per_page[key] = source
            ordered.append(source)
    return ordered


def build_context(sources: Sequence[Source]) -> str:
    """Format retrieved chunks for the model, with visible provenance labels.

    The labels let Gemma quote or refer to a section, and the user sees the same
    labels in the sources panel.
    """
    blocks = []
    for source in sources:
        blocks.append(f"[{source.short_label}]\n{source.text}")
    return "\n\n---\n\n".join(blocks)


def relevant_sources(
    sources: Sequence[Source], threshold: float = config.RELEVANCE_THRESHOLD
) -> list[Source]:
    """Keep only chunks similar enough to answer from."""
    return [source for source in sources if source.score >= threshold]


def answer_question(
    question: str,
    n_results: int = config.TOP_K,
    history: str = "",
    threshold: float = config.RELEVANCE_THRESHOLD,
    filename: Optional[str] = None,
) -> Answer:
    """Answer a question from the student's documents, with real citations.

    Retrieval runs first. If nothing clears the relevance threshold, the answer
    is an explicit refusal rather than a guess. `filename` limits retrieval to a
    single document, which is what the Sources list selects; leaving it None
    searches everything, as before.
    """
    question = (question or "").strip()
    if not question:
        return Answer(question=question, text="Ask a question and I'll search your documents.")

    hits = search_documents(question, n_results=n_results, filename=filename)
    good = relevant_sources(hits, threshold=threshold)

    if not good:
        best = hits[0].score if hits else 0.0
        return Answer(
            question=question,
            text=NO_ANSWER_MESSAGE,
            sources=hits,
            grounded=False,
            note=(
                "No chunk in your documents was close enough to this question "
                f"(best similarity {best:.2f}). Try different wording, or upload "
                "the material that covers this topic."
            ),
        )

    context = build_context(good)
    try:
        from .prompts import answer_question_prompt

        text = generate(answer_question_prompt(question, context, history=history))
    except (OllamaUnavailableError, ModelNotFoundError) as exc:
        return Answer(
            question=question,
            text="",
            sources=good,
            grounded=False,
            note=str(exc),
        )

    return Answer(question=question, text=text, sources=good, grounded=True)


def gather_context_for(
    topic: str,
    n_results: int = 4,
    filename: Optional[str] = None,
) -> list[Source]:
    """Retrieve context for a topic without generating an answer.

    Used by the quiz, the planner and the daily plan, which need material
    rather than a prose answer.
    """
    return search_documents(topic, n_results=n_results, filename=filename)


def index_directory_pdfs(paths: Optional[Iterable] = None) -> list[dict]:
    """Index PDFs from disk. Used by the demo loader and the startup sync."""
    from .documents import index_uploaded_files

    summaries = []
    for path in paths if paths is not None else index_uploaded_files():
        try:
            summaries.append(index_document(str(path), filename=path.name))
        except (DocumentError, EmbeddingError, RetrievalError):
            continue
    return summaries