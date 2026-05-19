"""Chat and RAG coordination router for TravelChatBot REST API.

This module provides endpoints to manage chat sessions, retrieve historical messages,
and post new messages with optional image or voice file uploads integrated with RAG.

Author: TravelChatBot Team
Version: 1.0.0
"""
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, ChatSession, ChatMessage
from backend.auth_utils import get_current_user
from ai_module.models.chatbot import Chatbot

router = APIRouter(prefix="/chat", tags=["Conversations & Assistant"])

# Directory where uploaded media files will be saved temporarily
UPLOADS_DIR = os.path.join("data", "uploads")
IMAGES_DIR = os.path.join(UPLOADS_DIR, "images")
AUDIO_DIR = os.path.join(UPLOADS_DIR, "audio")

# Create directories if they do not exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Lazily instantiated Chatbot singleton to avoid duplicate ChromaDB initialization
_chatbot_instance = None

def get_chatbot() -> Chatbot:
    """Helper to lazily instantiate or fetch the singleton Chatbot orchestrator."""
    global _chatbot_instance
    if _chatbot_instance is None:
        print("🤖 [ChatRouter] Instantiating TravelChatBot Coordinator...")
        _chatbot_instance = Chatbot()
    return _chatbot_instance


# --- Pydantic Schemas ---

class SessionCreate(BaseModel):
    title: Optional[str] = "Chuyến đi mới"


class SessionResponse(BaseModel):
    id: str
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    image_path: Optional[str]
    audio_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_in: SessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Creates a new unique chat session for the authenticated user."""
    session = ChatSession(
        user_id=current_user.id,
        title=session_in.title
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists all chat sessions belonging to the authenticated user."""
    return db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(
    session_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Retrieves conversation history log inside a specific chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    return session.messages


@router.post("/sessions/{session_id}/message", response_model=MessageResponse)
def post_message(
    session_id: str,
    content: Optional[str] = Form(None),
    sort_by: Optional[str] = Form(None),
    sort_order: str = Form("desc"),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bot: Chatbot = Depends(get_chatbot)
):
    """Sends a new text or multimodal query to the assistant and gets a RAG recommendation."""
    # Enforce granular, media-type specific rate limits
    from backend.rate_limiter import chat_rate_limiter
    chat_rate_limiter.check_rate_limit(
        user_id=current_user.id,
        has_audio=(audio is not None),
        has_image=(image is not None)
    )
    # 1. Retrieve session and verify ownership
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )

    # Validate that there's at least one form of query input
    if not content and not image and not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must contain at least a text message, image, or audio input."
        )

    saved_image_path = None
    saved_audio_path = None

    try:
        # 2. Process image upload if provided
        if image:
            ext = os.path.splitext(image.filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            saved_image_path = os.path.abspath(os.path.join(IMAGES_DIR, unique_filename))
            
            with open(saved_image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            print(f"📸 Saved vision file to: {saved_image_path}")

        # 3. Process audio upload if provided
        if audio:
            ext = os.path.splitext(audio.filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            saved_audio_path = os.path.abspath(os.path.join(AUDIO_DIR, unique_filename))
            
            with open(saved_audio_path, "wb") as buffer:
                shutil.copyfileobj(audio.file, buffer)
            print(f"🎙️ Saved voice file to: {saved_audio_path}")

        # 4. Coordinate session context (load before adding current query to DB)
        # Sync the conversational memory with existing SQLite chat logs for precision follow-ups
        bot.conversation_buffer = []
        for msg in session.messages[-10:]:  # Load last 10 messages as history context
            bot.conversation_buffer.append({
                "role": "user" if msg.role == "user" else "assistant",
                "text": msg.content
            })

        # 5. Generate user message entry in database
        user_message_text = content or ""
        if not user_message_text:
            if image and audio:
                user_message_text = "[Multimodal Image + Voice Request]"
            elif image:
                user_message_text = "[Image Request]"
            elif audio:
                user_message_text = "[Voice Request]"

        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=user_message_text,
            image_path=saved_image_path,
            audio_path=saved_audio_path
        )
        db.add(user_msg)

        # 6. Execute 6-agent RAG pipeline using Chatbot orchestrator
        print(f"🤖 Processing query: '{user_message_text}' | Sort: {sort_by} ({sort_order})")
        response_text = bot.get_response(
            user_query=content or "",
            image_path=saved_image_path,
            audio_path=saved_audio_path,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 7. Generate assistant message entry in database
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response_text
        )
        db.add(assistant_msg)
        
        # Update session timestamp to float latest activity
        session.updated_at = datetime.utcnow()
        db.add(session)
        
        db.commit()
        db.refresh(assistant_msg)

        return assistant_msg
        
    except Exception as e:
        # Cleanup uploaded files in case of processing failures
        if saved_image_path and os.path.exists(saved_image_path):
            os.remove(saved_image_path)
        if saved_audio_path and os.path.exists(saved_audio_path):
            os.remove(saved_audio_path)
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate travel guide recommendation: {e}"
        )
