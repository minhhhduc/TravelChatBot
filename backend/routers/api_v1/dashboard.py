"""API v1 dashboard endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ai_module.models import config
from ai_module.models.chromadb import db_manager
from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from .common import jsonl_count, load_image_manifest, load_metadata

router = APIRouter(prefix="/dashboard", tags=["API v1 - Dashboard"])


@router.get("/overview")
def dashboard_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    metadata = load_metadata()
    collection = db_manager.get_or_create_collection(config.CHROMA_COLLECTION_NAME)
    return {
        "documents": metadata.get("articles", jsonl_count(config.PROCESSED_DATA_PATH)),
        "chunks": collection.count(),
        "entities": len(metadata.get("top_destinations", [])),
        "latency_ms_p50": None,
        "feedback": {"positive": 0, "negative": 0},
        "users": db.query(User).count(),
        "sessions": db.query(ChatSession).count(),
        "messages": db.query(ChatMessage).count(),
    }


@router.get("/dataops")
def dashboard_dataops(current_user: User = Depends(get_current_user)):
    metadata = load_metadata()
    collection = db_manager.get_or_create_collection(config.CHROMA_COLLECTION_NAME)
    return {
        "pipeline": [
            {"stage": "raw", "path": str(config.RAW_JSONL_PATH), "records": jsonl_count(config.RAW_JSONL_PATH)},
            {"stage": "processed", "path": str(config.PROCESSED_DATA_PATH), "records": jsonl_count(config.PROCESSED_DATA_PATH)},
            {"stage": "chunks", "records": metadata.get("keypoints", 0)},
            {"stage": "embeddings", "path": str(config.CHROMA_DB_PATH), "records": collection.count()},
            {"stage": "graph", "records": len(metadata.get("top_destinations", []))},
        ],
        "metadata": metadata,
    }


@router.get("/rag-graphrag")
def dashboard_rag_graphrag(current_user: User = Depends(get_current_user)):
    collection = db_manager.get_or_create_collection(config.CHROMA_COLLECTION_NAME)
    metadata = load_metadata()
    return {
        "rag": {
            "collection": config.CHROMA_COLLECTION_NAME,
            "chunks": collection.count(),
            "similarity_threshold": config.MIN_RELEVANCE_SCORE,
            "max_results": config.MAX_RESULTS,
        },
        "intents": [{"intent": "travel_recommendation", "count": collection.count()}],
        "graph_nodes": metadata.get("top_destinations", [])[:30],
    }


@router.get("/mlops")
def dashboard_mlops(current_user: User = Depends(get_current_user)):
    return {
        "precision": None,
        "groundedness": None,
        "hallucination_rate": None,
        "latency_ms": None,
        "status": "evaluation hooks ready; no offline benchmark run has been recorded",
    }


@router.get("/advanced-ai")
def dashboard_advanced_ai(current_user: User = Depends(get_current_user)):
    return {
        "modules": [
            {"name": "Prompt Engineering", "status": "active"},
            {"name": "RAG", "status": "active"},
            {"name": "GraphRAG", "status": "planned"},
            {"name": "Edge AI", "status": "planned"},
            {"name": "GAN", "status": "not_applicable"},
            {"name": "VAE", "status": "not_applicable"},
        ]
    }


@router.get("/cms-bi")
def dashboard_cms_bi(current_user: User = Depends(get_current_user)):
    return {
        "cms": {"provider": "custom", "status": "local_manifest", "images": len(load_image_manifest())},
        "bi": {"provider": "superset-compatible", "status": "api_ready"},
    }
