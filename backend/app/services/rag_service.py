# backend/app/services/rag_service.py
"""
Retrieval-Augmented Generation Service for SupplyMind.

Implements the full RAG pipeline:

    Document text  →  Chunking  →  Embeddings  →  FAISS index
                                                       ↓
    User question  →  Embed query  →  Retrieve chunks  →  LLM  →  Answer

Components:
  - Chunking:    Recursive character splitting with overlap
  - Embeddings:  sentence-transformers (all-MiniLM-L6-v2, runs locally)
  - Vector store: FAISS with persistent local storage
  - LLM:         Groq (LLaMA 3.3 70B) for answer generation
  - Metadata:    JSON sidecar for chunk → document mapping

Usage::

    from backend.app.services.rag_service import RagService

    svc = RagService()
    svc.index_documents(db)
    answer = svc.ask("What are the payment terms?", db)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.config import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")

# ── Constants ───────────────────────────────────────────────────
_EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
_EMBEDDING_DIMENSION: int = 384
_GROQ_MODEL: str = "llama-3.3-70b-versatile"

_CHUNK_SIZE: int = 800
_CHUNK_OVERLAP: int = 150
_MIN_CHUNK_LENGTH: int = 50

_TOP_K_DEFAULT: int = 5
_MAX_CONTEXT_CHARS: int = 12_000
_MAX_RETRIES: int = 3
_BASE_DELAY: float = 1.0

_INDEX_FILENAME: str = "supplymind_rag.index"
_METADATA_FILENAME: str = "supplymind_rag_meta.json"


# =====================================================================
#  Text Chunking
# =====================================================================

def _chunk_text(
    text: str,
    chunk_size: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
    min_length: int = _MIN_CHUNK_LENGTH,
) -> List[str]:
    """Split text into overlapping chunks using recursive separators.

    Tries to split on paragraph breaks first, then sentences, then
    words, preserving semantic coherence in each chunk.

    Parameters
    ----------
    text : str
        The source text to chunk.
    chunk_size : int
        Target chunk size in characters.
    overlap : int
        Number of characters to overlap between consecutive chunks.
    min_length : int
        Discard chunks shorter than this.

    Returns
    -------
    list[str]
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # If the entire text fits in one chunk, return it directly
    if len(text) <= chunk_size:
        return [text] if len(text) >= min_length else []

    # Try splitting on progressively finer separators
    separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
    chunks = _recursive_split(text, separators, chunk_size, overlap)

    # Filter out very short chunks
    return [c.strip() for c in chunks if len(c.strip()) >= min_length]


def _recursive_split(
    text: str,
    separators: List[str],
    chunk_size: int,
    overlap: int,
) -> List[str]:
    """Recursively split text on the first effective separator."""
    if len(text) <= chunk_size:
        return [text]

    # Find the best separator that actually exists in the text
    separator = ""
    for sep in separators:
        if sep in text:
            separator = sep
            break

    if not separator:
        # No separator found — hard split by character
        return _hard_split(text, chunk_size, overlap)

    # Split on the chosen separator
    parts = text.split(separator)
    chunks: List[str] = []
    current = ""

    for part in parts:
        candidate = (current + separator + part) if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single part exceeds chunk_size, split it further
            if len(part) > chunk_size:
                remaining_seps = separators[separators.index(separator) + 1:]
                sub_chunks = _recursive_split(part, remaining_seps, chunk_size, overlap)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    # Apply overlap between consecutive chunks
    if overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, overlap)

    return chunks


def _hard_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Fall-back hard split when no separators work."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap if overlap < (end - start) else end
    return chunks


def _apply_overlap(chunks: List[str], overlap: int) -> List[str]:
    """Add overlap context from the end of the previous chunk."""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
        result.append(prev_tail + " " + chunks[i])
    return result


# =====================================================================
#  Prompts
# =====================================================================

_RAG_SYSTEM_PROMPT = """\
You are SupplyMind, an AI assistant specialising in procurement document analysis.

RULES:
1. Answer ONLY using the context passages provided below.
2. If the answer is not in the provided context, say: "I could not find this information in the indexed documents."
3. NEVER invent facts, numbers, vendor names, dates, or amounts.
4. Cite the source document for each piece of information using [Document: filename].
5. Be concise and direct — use bullet points for lists.
6. For monetary amounts, always include the currency if available.
7. If multiple documents contain relevant information, synthesise across them.\
"""

_RAG_USER_TEMPLATE = """\
Answer the following question using ONLY the document context below.

QUESTION: {question}

DOCUMENT CONTEXT:
{context}

Provide a clear, grounded answer with source citations.\
"""


# =====================================================================
#  RAG Service
# =====================================================================

class RagService:
    """End-to-end RAG pipeline for procurement document Q&A.

    Manages local sentence-transformer embeddings, a FAISS vector
    index, and Groq-based answer generation.  The index is persisted
    to disk and reloaded on subsequent startups.
    """

    def __init__(
        self,
        index_dir: Optional[str] = None,
        embedding_model: str = _EMBEDDING_MODEL_NAME,
        groq_model: str = _GROQ_MODEL,
    ) -> None:
        self._index_dir = Path(index_dir or settings.FAISS_INDEX_DIR)
        self._embedding_model_name = embedding_model
        self._groq_model = groq_model

        # Lazy-loaded components
        self._embedder: Optional[Any] = None
        self._faiss_index: Optional[Any] = None
        self._chunk_metadata: List[Dict[str, Any]] = []
        self._groq_client: Optional[Any] = None

        # State
        self._index_loaded = False
        self._indexed_doc_ids: List[int] = []

    # ─────────────────────────────────────────────────────────────
    #  Lazy loading — embeddings
    # ─────────────────────────────────────────────────────────────

    def _get_embedder(self) -> Any:
        """Load the sentence-transformer model on first use."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s …", self._embedding_model_name)
            self._embedder = SentenceTransformer(self._embedding_model_name)
            logger.info("Embedding model loaded.")
        return self._embedder

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts into dense vectors."""
        embedder = self._get_embedder()
        embeddings = embedder.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    # ─────────────────────────────────────────────────────────────
    #  Lazy loading — Groq LLM
    # ─────────────────────────────────────────────────────────────

    def _get_groq_client(self) -> Any:
        """Return a Groq client, creating on first use."""
        if self._groq_client is None:
            api_key = settings.GROQ_API_KEY
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY is not set. Provide it via environment "
                    "variable or .env file."
                )
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
            logger.info("Groq client initialised for RAG (model=%s).", self._groq_model)
        return self._groq_client

    # ─────────────────────────────────────────────────────────────
    #  FAISS index management
    # ─────────────────────────────────────────────────────────────

    @property
    def _index_path(self) -> Path:
        return self._index_dir / _INDEX_FILENAME

    @property
    def _metadata_path(self) -> Path:
        return self._index_dir / _METADATA_FILENAME

    def _save_index(self) -> None:
        """Persist the FAISS index and metadata to disk."""
        import faiss

        self._index_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._faiss_index, str(self._index_path))

        meta = {
            "chunks": self._chunk_metadata,
            "indexed_doc_ids": self._indexed_doc_ids,
            "embedding_model": self._embedding_model_name,
            "chunk_count": len(self._chunk_metadata),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        logger.info(
            "FAISS index saved: %d chunks, %d documents → %s",
            len(self._chunk_metadata),
            len(self._indexed_doc_ids),
            self._index_path,
        )

    def _load_index(self) -> bool:
        """Load a previously persisted index from disk. Returns True on success."""
        if not self._index_path.exists() or not self._metadata_path.exists():
            return False

        try:
            import faiss
            self._faiss_index = faiss.read_index(str(self._index_path))

            with open(self._metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            self._chunk_metadata = meta.get("chunks", [])
            self._indexed_doc_ids = meta.get("indexed_doc_ids", [])
            self._index_loaded = True

            logger.info(
                "FAISS index loaded from disk: %d chunks, %d documents.",
                len(self._chunk_metadata),
                len(self._indexed_doc_ids),
            )
            return True
        except Exception as exc:
            logger.warning("Failed to load FAISS index: %s", exc)
            return False

    def _ensure_index(self) -> None:
        """Make sure the in-memory index is available (load from disk if needed)."""
        if self._index_loaded and self._faiss_index is not None:
            return
        if not self._load_index():
            raise FileNotFoundError(
                "No RAG index found. Call POST /rag/index-documents first "
                "to build the vector index."
            )

    # ─────────────────────────────────────────────────────────────
    #  Document loading from DB
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _load_indexable_documents(db: Any) -> List[Dict[str, Any]]:
        """Load documents from the DB that have usable text content."""
        from backend.app.models import Document, OCRStatus

        docs = (
            db.query(Document)
            .filter(
                Document.ocr_status == OCRStatus.COMPLETED,
                Document.extracted_text.isnot(None),
            )
            .all()
        )

        result = []
        for doc in docs:
            text = (doc.extracted_text or "").strip()
            if len(text) < _MIN_CHUNK_LENGTH:
                continue

            # Also include structured extraction data if available
            entity_text = ""
            if doc.extracted_entities:
                for entity in doc.extracted_entities:
                    if entity.entity_data:
                        entity_text += _format_entity_data(entity.entity_data)

            result.append({
                "document_id": doc.id,
                "filename": doc.original_filename,
                "text": text,
                "entity_text": entity_text,
                "page_count": doc.page_count,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            })

        return result

    # ─────────────────────────────────────────────────────────────
    #  Retrieval
    # ─────────────────────────────────────────────────────────────

    def _retrieve(
        self,
        query: str,
        top_k: int = _TOP_K_DEFAULT,
        document_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant chunks for a query.

        Parameters
        ----------
        query : str
            The user's question.
        top_k : int
            Number of chunks to retrieve.
        document_id : int | None
            If set, filter to chunks from this document only.

        Returns
        -------
        list[dict]
            Retrieved chunks with scores and metadata.
        """
        self._ensure_index()

        query_embedding = self._embed_texts([query])

        # Retrieve more candidates when filtering by document_id
        search_k = top_k * 5 if document_id is not None else top_k

        scores, indices = self._faiss_index.search(query_embedding, min(search_k, len(self._chunk_metadata)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_metadata):
                continue

            meta = self._chunk_metadata[idx]

            # Filter by document_id if specified
            if document_id is not None and meta["document_id"] != document_id:
                continue

            results.append({
                "chunk_index": int(idx),
                "score": round(float(score), 4),
                "document_id": meta["document_id"],
                "filename": meta["filename"],
                "chunk_type": meta.get("chunk_type", "ocr_text"),
                "text": self._get_chunk_text(int(idx)),
            })

            if len(results) >= top_k:
                break

        return results

    def _get_chunk_text(self, chunk_idx: int) -> str:
        """Retrieve the original chunk text by re-reading from metadata.

        Since FAISS stores only vectors, we re-derive chunk text from
        the persisted metadata + original document.  For efficiency,
        we cache texts alongside metadata at index time.
        """
        # Check if text is stored in metadata (populated during current session)
        meta = self._chunk_metadata[chunk_idx]
        if "text" in meta:
            return meta["text"]

        # If not in metadata, return a placeholder (the chunk was created
        # in a previous session and text wasn't persisted to save space)
        return f"[Chunk {chunk_idx} from {meta.get('filename', 'unknown')}]"

    # ─────────────────────────────────────────────────────────────
    #  Answer generation
    # ─────────────────────────────────────────────────────────────

    def ask(
        self,
        question: str,
        db: Any,
        top_k: int = _TOP_K_DEFAULT,
        document_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ask a question and get a grounded answer from the indexed documents.

        Parameters
        ----------
        question : str
            Natural language question.
        db : Session
            SQLAlchemy session (for document lookups if needed).
        top_k : int
            Number of chunks to retrieve.
        document_id : int | None
            Restrict the search to a single document.

        Returns
        -------
        dict
            Answer with sources and metadata.
        """
        start = time.perf_counter()

        if not question or not question.strip():
            return {
                "answer": "Please provide a question.",
                "sources": [],
                "grounded": False,
                "question": question,
            }

        # Retrieve relevant chunks
        retrieved = self._retrieve(question, top_k=top_k, document_id=document_id)

        if not retrieved:
            scope = f"document {document_id}" if document_id else "the indexed documents"
            return {
                "answer": f"I could not find any relevant information in {scope} to answer your question.",
                "sources": [],
                "grounded": False,
                "question": question,
                "chunks_searched": 0,
            }

        # Build context from retrieved chunks
        context = self._build_context(retrieved)

        # Generate answer via Groq
        answer = self._generate_answer(question, context)

        elapsed = time.perf_counter() - start

        # Build source references
        sources = []
        seen_docs = set()
        for chunk in retrieved:
            doc_key = chunk["document_id"]
            sources.append({
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "chunk_type": chunk["chunk_type"],
                "relevance_score": chunk["score"],
                "snippet": chunk["text"][:300] + ("…" if len(chunk["text"]) > 300 else ""),
            })
            seen_docs.add(doc_key)

        return {
            "answer": answer,
            "question": question,
            "grounded": True,
            "sources": sources,
            "documents_referenced": len(seen_docs),
            "chunks_retrieved": len(retrieved),
            "model": self._groq_model,
            "elapsed_seconds": round(elapsed, 2),
        }

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Assemble retrieved chunks into a context string for the LLM."""
        parts = []
        total_len = 0

        for chunk in chunks:
            header = f"[Document: {chunk['filename']} | Score: {chunk['score']}]"
            text = chunk["text"]

            # Truncate if we're exceeding context budget
            remaining = _MAX_CONTEXT_CHARS - total_len - len(header) - 10
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining] + "…"

            entry = f"{header}\n{text}"
            parts.append(entry)
            total_len += len(entry)

        return "\n\n---\n\n".join(parts)

    def _generate_answer(self, question: str, context: str) -> str:
        """Call Groq to generate a grounded answer from context."""
        client = self._get_groq_client()

        prompt = _RAG_USER_TEMPLATE.format(question=question, context=context)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=self._groq_model,
                    messages=[
                        {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.15,
                    max_completion_tokens=2048,
                )

                content = response.choices[0].message.content
                if content:
                    return content.strip()

                logger.warning("Groq returned empty answer (attempt %d/%d).", attempt, _MAX_RETRIES)

            except Exception as exc:
                delay = min(_BASE_DELAY * (2 ** (attempt - 1)), 10.0)
                logger.warning(
                    "Groq RAG answer error (attempt %d/%d): %s. Retrying in %.1fs …",
                    attempt, _MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)

        return (
            "I was unable to generate an answer due to a temporary service issue. "
            "Please try again."
        )

    # ─────────────────────────────────────────────────────────────
    #  Index building with chunk text persistence
    # ─────────────────────────────────────────────────────────────

    def index_documents(self, db: Any) -> Dict[str, Any]:
        """Build the FAISS index from all indexable documents in the DB.

        Loads documents, chunks their text, embeds the chunks, builds
        a FAISS index, and persists everything to disk including the
        original chunk text for retrieval.
        """
        start = time.perf_counter()

        docs = self._load_indexable_documents(db)
        if not docs:
            return {
                "status": "no_documents",
                "message": "No documents with extracted text found to index.",
                "documents_indexed": 0,
                "chunks_created": 0,
            }

        # Chunk all documents
        all_chunks: List[str] = []
        all_metadata: List[Dict[str, Any]] = []
        indexed_ids: List[int] = []

        for doc in docs:
            text_chunks = _chunk_text(doc["text"])

            entity_chunks: List[str] = []
            if doc["entity_text"]:
                entity_chunks = _chunk_text(
                    doc["entity_text"],
                    chunk_size=_CHUNK_SIZE // 2,
                    overlap=_CHUNK_OVERLAP // 2,
                )

            doc_chunks = text_chunks + entity_chunks

            for i, chunk in enumerate(doc_chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "document_id": doc["document_id"],
                    "filename": doc["filename"],
                    "chunk_index": i,
                    "chunk_type": "ocr_text" if i < len(text_chunks) else "entity_data",
                    "chunk_length": len(chunk),
                    "page_count": doc["page_count"],
                    "text": chunk,
                })

            indexed_ids.append(doc["document_id"])

        if not all_chunks:
            return {
                "status": "no_chunks",
                "message": "Documents found but produced no indexable chunks.",
                "documents_indexed": 0,
                "chunks_created": 0,
            }

        logger.info("Embedding %d chunks from %d documents …", len(all_chunks), len(docs))
        embeddings = self._embed_texts(all_chunks)

        import faiss

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        self._faiss_index = index
        self._chunk_metadata = all_metadata
        self._indexed_doc_ids = indexed_ids
        self._index_loaded = True

        self._save_index()

        elapsed = time.perf_counter() - start

        return {
            "status": "indexed",
            "message": f"Successfully indexed {len(docs)} documents into {len(all_chunks)} chunks.",
            "documents_indexed": len(docs),
            "chunks_created": len(all_chunks),
            "embedding_model": self._embedding_model_name,
            "embedding_dimension": dimension,
            "index_path": str(self._index_path),
            "elapsed_seconds": round(elapsed, 2),
        }

    # ─────────────────────────────────────────────────────────────
    #  Status and inspection
    # ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return the current state of the RAG index."""
        index_exists = self._index_path.exists() and self._metadata_path.exists()

        if not index_exists:
            return {
                "index_exists": False,
                "index_loaded": False,
                "documents_indexed": 0,
                "chunks_indexed": 0,
                "embedding_model": self._embedding_model_name,
                "llm_model": self._groq_model,
                "index_path": str(self._index_path),
            }

        # Load metadata without loading the full index
        try:
            with open(self._metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

        return {
            "index_exists": True,
            "index_loaded": self._index_loaded,
            "documents_indexed": len(meta.get("indexed_doc_ids", [])),
            "chunks_indexed": meta.get("chunk_count", 0),
            "embedding_model": meta.get("embedding_model", self._embedding_model_name),
            "llm_model": self._groq_model,
            "index_path": str(self._index_path),
            "created_at": meta.get("created_at"),
        }

    def get_indexed_documents(self) -> Dict[str, Any]:
        """Return a list of documents currently in the index."""
        if not self._metadata_path.exists():
            return {"documents": [], "total": 0}

        try:
            with open(self._metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            return {"documents": [], "total": 0}

        chunks = meta.get("chunks", [])
        doc_ids = meta.get("indexed_doc_ids", [])

        # Aggregate per document
        doc_stats: Dict[int, Dict[str, Any]] = {}
        for chunk in chunks:
            did = chunk["document_id"]
            if did not in doc_stats:
                doc_stats[did] = {
                    "document_id": did,
                    "filename": chunk["filename"],
                    "chunk_count": 0,
                    "total_chunk_length": 0,
                }
            doc_stats[did]["chunk_count"] += 1
            doc_stats[did]["total_chunk_length"] += chunk.get("chunk_length", 0)

        documents = sorted(doc_stats.values(), key=lambda x: x["document_id"])

        return {
            "documents": documents,
            "total": len(documents),
            "index_created_at": meta.get("created_at"),
        }


# =====================================================================
#  Helpers
# =====================================================================

def _format_entity_data(data: Dict[str, Any]) -> str:
    """Convert structured entity data into readable text for embedding."""
    lines = []
    key_labels = {
        "vendor_name": "Vendor",
        "vendor_gstin": "GSTIN",
        "document_type": "Document Type",
        "document_number": "Document Number",
        "document_date": "Date",
        "due_date": "Due Date",
        "currency": "Currency",
        "subtotal": "Subtotal",
        "tax_amount": "Tax Amount",
        "total_amount": "Total Amount",
        "payment_terms": "Payment Terms",
        "delivery_terms": "Delivery Terms",
        "warranty_terms": "Warranty Terms",
        "penalty_clause": "Penalty Clause",
        "product_or_service_name": "Product/Service",
    }

    for key, label in key_labels.items():
        val = data.get(key)
        if val is not None and str(val).strip():
            lines.append(f"{label}: {val}")

    # Line items
    items = data.get("line_items", [])
    if items:
        lines.append(f"Line Items ({len(items)}):")
        for i, item in enumerate(items, 1):
            desc = item.get("description", "N/A")
            qty = item.get("quantity", "")
            price = item.get("total_price", "")
            lines.append(f"  {i}. {desc} — Qty: {qty}, Total: {price}")

    return "\n".join(lines)
