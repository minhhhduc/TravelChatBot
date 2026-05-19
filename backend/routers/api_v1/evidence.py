"""API v1 evidence and retrieval analysis endpoints."""
from fastapi import APIRouter

from ai_module.models import config
from ai_module.models.chromadb import db_manager
from .common import sources_from_rag
from .schemas import EvidenceRequest

router = APIRouter(prefix="/evidence", tags=["API v1 - Evidence"])


@router.post("/analyze")
def evidence_analyze(payload: EvidenceRequest):
    rag_context = db_manager.prepare_rag_context(
        collection_name=config.CHROMA_COLLECTION_NAME,
        query_text=payload.query,
        limit=payload.limit,
    )
    sources = sources_from_rag(rag_context)
    return {
        "query": payload.query,
        "intent": "travel_recommendation",
        "entities": [{"text": token, "type": "keyword"} for token in payload.query.split()[:8]],
        "chunks": sources,
        "relations": [{"source": "query", "target": source["id"], "type": "retrieved"} for source in sources],
        "scores": {
            "documents_found": rag_context.get("documents_found", 0),
            "candidates_found": rag_context.get("candidates_found", 0),
            "similarity_threshold": config.MIN_RELEVANCE_SCORE,
        },
    }
