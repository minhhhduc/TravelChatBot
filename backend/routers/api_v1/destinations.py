"""API v1 destination explorer endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ai_module.models import config
from ai_module.models.chromadb import db_manager
from .common import load_metadata, sources_from_rag

router = APIRouter(prefix="/destinations", tags=["API v1 - Destinations"])


@router.get("")
def list_destinations(
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    metadata = load_metadata()
    items = metadata.get("top_destinations", [])
    normalized_search = (search or "").casefold()
    destinations = []
    for item in items:
        name = item.get("destination", "")
        if normalized_search and normalized_search not in name.casefold():
            continue
        destinations.append(
            {
                "id": name,
                "name": name,
                "type": type or "destination",
                "document_count": item.get("count", 0),
            }
        )
    return {"items": destinations[:limit], "total": len(destinations)}


@router.get("/{destination_id}")
def get_destination(destination_id: str):
    rag_context = db_manager.prepare_rag_context(
        collection_name=config.CHROMA_COLLECTION_NAME,
        query_text=destination_id,
        limit=8,
    )
    sources = sources_from_rag(rag_context)
    return {
        "id": destination_id,
        "name": destination_id,
        "summary": f"Thông tin du lịch liên quan đến {destination_id}.",
        "sources": sources,
        "relation_graph": {
            "nodes": [{"id": destination_id, "label": destination_id, "type": "destination"}]
            + [{"id": s["id"], "label": s["title"], "type": "chunk"} for s in sources],
            "edges": [{"source": destination_id, "target": s["id"], "type": "has_evidence"} for s in sources],
        },
    }
