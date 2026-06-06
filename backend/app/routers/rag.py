# backend/app/routers/rag.py
"""
RAG (Retrieval-Augmented Generation) API — natural language Q&A
over uploaded procurement documents.

Endpoints:
    POST /rag/index-documents            — build / rebuild the vector index
    POST /rag/ask                        — ask a question across all documents
    POST /rag/ask-document/{document_id} — ask about a specific document
    GET  /rag/status                     — check index health
    GET  /rag/documents-indexed          — list indexed documents
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from backend.app.dependencies import DbSession
from backend.app.models import Document
from backend.app.schemas import (
    RagAskRequest,
    RagAskResponse,
    RagDocumentAskRequest,
    RagIndexedDocumentsResponse,
    RagIndexResponse,
    RagStatusResponse,
)
from backend.app.services.rag_service import RagService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

# ── Service singleton ──────────────────────────────────────────
_rag_service: Optional[RagService] = None


def _get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service


# =====================================================================
#  POST /rag/index-documents
# =====================================================================

@router.post(
    "/index-documents",
    response_model=RagIndexResponse,
    summary="Build or rebuild the document vector index",
    description=(
        "Loads all documents with completed OCR text from the database, "
        "chunks the text, embeds the chunks using a local sentence-transformer, "
        "and builds a FAISS vector index. The index is persisted to disk. "
        "Calling this endpoint again will fully rebuild the index."
    ),
)
def index_documents(db: DbSession) -> dict:
    """Build the RAG vector index from all processed documents."""
    svc = _get_rag_service()

    try:
        result = svc.index_documents(db)
    except Exception as exc:
        logger.exception("Failed to build RAG index.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index build failed: {exc}",
        )

    return result


# =====================================================================
#  POST /rag/ask
# =====================================================================

@router.post(
    "/ask",
    response_model=RagAskResponse,
    summary="Ask a question across all indexed documents",
    description=(
        "Submit a natural language question and receive a grounded answer "
        "synthesised from the most relevant document chunks.  The answer "
        "includes source citations and relevance scores."
    ),
)
def ask_question(body: RagAskRequest, db: DbSession) -> dict:
    """Ask a procurement question over all indexed documents."""
    svc = _get_rag_service()

    try:
        result = svc.ask(
            question=body.question,
            db=db,
            top_k=body.top_k,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("RAG ask failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {exc}",
        )

    return result


# =====================================================================
#  POST /rag/ask-document/{document_id}
# =====================================================================

@router.post(
    "/ask-document/{document_id}",
    response_model=RagAskResponse,
    summary="Ask a question about a specific document",
    description=(
        "Submit a question scoped to a single document.  Only chunks "
        "from the specified document are used for retrieval and answer "
        "generation."
    ),
)
def ask_document(
    document_id: int,
    body: RagDocumentAskRequest,
    db: DbSession,
) -> dict:
    """Ask a procurement question about a specific document."""
    # Verify the document exists
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    svc = _get_rag_service()

    try:
        result = svc.ask(
            question=body.question,
            db=db,
            top_k=body.top_k,
            document_id=document_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("RAG ask-document failed for document %d.", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {exc}",
        )

    return result


# =====================================================================
#  GET /rag/status
# =====================================================================

@router.get(
    "/status",
    response_model=RagStatusResponse,
    summary="Check RAG index status",
    description=(
        "Returns the current state of the vector index — whether it "
        "exists, how many documents and chunks are indexed, which "
        "models are configured, and when the index was last built."
    ),
)
def get_status() -> dict:
    """Return the current RAG pipeline status."""
    svc = _get_rag_service()
    return svc.get_status()


# =====================================================================
#  GET /rag/documents-indexed
# =====================================================================

@router.get(
    "/documents-indexed",
    response_model=RagIndexedDocumentsResponse,
    summary="List all documents in the vector index",
    description=(
        "Returns per-document statistics from the current index, "
        "including chunk counts and total indexed text length."
    ),
)
def get_documents_indexed() -> dict:
    """List documents currently in the RAG index."""
    svc = _get_rag_service()
    return svc.get_indexed_documents()
