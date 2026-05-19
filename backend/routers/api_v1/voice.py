"""API v1 voice and conversational endpoints."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response, StreamingResponse

from ai_module.models import config
from ai_module.models.chromadb import db_manager
from backend.routers.chat import get_chatbot
from .common import AUDIO_UPLOAD_DIR, save_upload, silent_wav_response, sources_from_rag
from .schemas import TtsRequest, VoiceQueryRequest, VoiceQueryResponse

router = APIRouter(prefix="/voice", tags=["API v1 - Voice"])


@router.post("/query", response_model=VoiceQueryResponse)
def voice_query(payload: VoiceQueryRequest):
    bot = get_chatbot()
    answer = bot.get_response(
        user_query=payload.query,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
    )
    rag_context = db_manager.prepare_rag_context(
        collection_name=config.CHROMA_COLLECTION_NAME,
        query_text=payload.query,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        limit=5,
    )
    sources = sources_from_rag(rag_context)
    return {
        "answer": answer,
        "conversation_id": payload.conversation_id,
        "sources": sources,
        "citations": [{"index": i, "source_id": item["id"], "url": item["url"]} for i, item in enumerate(sources, 1)],
        "meta": {
            "documents_found": rag_context.get("documents_found", 0),
            "candidates_found": rag_context.get("candidates_found", 0),
            "similarity_threshold": config.MIN_RELEVANCE_SCORE,
        },
    }


@router.post("/stt")
def voice_stt(audio: UploadFile = File(...)):
    path = save_upload(audio, AUDIO_UPLOAD_DIR)
    transcript = get_chatbot().speech_agent.transcribe_audio(str(path))
    return {"text": transcript, "audio_path": str(path)}


@router.post("/tts")
def voice_tts(payload: TtsRequest):
    # Placeholder audio contract. Replace with a real TTS provider when selected.
    audio = silent_wav_response()
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "inline; filename=lumi-tts.wav",
            "X-TTS-Provider": "placeholder",
            "X-TTS-Text-Length": str(len(payload.text)),
        },
    )


@router.get("/suggestions")
def voice_suggestions(context: Optional[str] = None):
    topic = context or "chuyến đi"
    return {
        "suggestions": [
            f"{topic} nên đi mấy ngày là hợp lý?",
            f"{topic} có món gì nên thử?",
            f"Chi phí dự kiến cho {topic} là bao nhiêu?",
            f"Nên đi {topic} vào mùa nào?",
        ]
    }


@router.get("/status")
def voice_status():
    def events():
        for step in ("listening", "transcribing", "retrieving", "generating", "done"):
            yield f"event: status\ndata: {json.dumps({'step': step, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
