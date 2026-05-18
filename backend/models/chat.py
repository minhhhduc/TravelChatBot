"""Chat session and message history database models for TravelChatBot.

This module declares the database models to persist chat sessions and individual
messages with support for text, images, and audio query inputs.

Author: TravelChatBot Team
Version: 1.0.0
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin

def generate_uuid() -> str:
    """Generates a standard string UUID for chat session ids."""
    return str(uuid.uuid4())

class ChatSession(Base, TimestampMixin):
    """Chat session model to group sequential conversation messages."""
    
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    title = Column(String(255), default="Chuyến đi mới", nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "ChatMessage", 
        back_populates="session", 
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<ChatSession id='{self.id}' title='{self.title}'>"


class ChatMessage(Base):
    """Chat message model to record individual role inputs and responses."""
    
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), 
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), 
        nullable=False
    )
    role = Column(String(50), nullable=False) # 'user', 'assistant'
    content = Column(Text, nullable=False)
    
    # Media paths for multimodal context
    image_path = Column(String(500), nullable=True)
    audio_path = Column(String(500), nullable=True)
    
    created_at = Column(
        Text, 
        default=lambda: datetime.utcnow().isoformat(), 
        nullable=False
    )

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role='{self.role}'>"
