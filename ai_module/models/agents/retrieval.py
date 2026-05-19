"""Retrieval agent for TravelChatBot."""

from __future__ import annotations

from typing import Optional, Dict, Any

from ..chromadb import ChromaDBManager
from .. import config


class RetrievalAgent:
    """Agent for querying the ChromaDB vector database with custom sorting support."""

    def __init__(self, db_manager: ChromaDBManager):
        self.db_manager = db_manager

    def retrieve_context(
        self,
        prompt: str,
        limit: int = 5,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Queries the vector database and performs programmatic post-retrieval metadata sorting."""
        try:
            print(f"🔍 RetrievalAgent: Querying ChromaDB for '{prompt}'...")

            sort_field = None
            if sort_by == "time":
                sort_field = "time"
            elif sort_by == "evaluate_mean":
                sort_field = "evaluate_mean"
            elif sort_by == "evaluate_count":
                sort_field = "evaluate_count"

            rag_context = self.db_manager.prepare_rag_context(
                collection_name=config.CHROMA_COLLECTION_NAME,
                query_text=prompt,
                sort_by=sort_field,
                sort_order=sort_order,
                limit=limit,
            )
            print(f"✨ RetrievalAgent: Found {rag_context.get('documents_found', 0)} matching documents.")
            return rag_context
        except Exception as e:
            print(f"⚠️  RetrievalAgent query failed: {e}")
            return {"context": "Error retrieving travel guides.", "sources": [], "documents_found": 0}