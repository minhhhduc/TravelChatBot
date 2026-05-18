"""User and UserPreference database models for TravelChatBot.

This module declares the database schema for users and their personalized travel/dietary
preferences, complete with secure password management using bcrypt.

Author: TravelChatBot Team
Version: 1.0.0
"""
from datetime import datetime
import json
import bcrypt
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    """User database model representingTravelChatBot accounts."""
    
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(50), default="user", nullable=False) # 'user', 'admin'

    # Relationships
    preferences = relationship(
        "UserPreference", 
        back_populates="user", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    sessions = relationship(
        "ChatSession", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hashes the plain-text password using bcrypt and stores it."""
        salt = bcrypt.gensalt()
        pw_bytes = password.encode('utf-8')
        self.password_hash = bcrypt.hashpw(pw_bytes, salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verifies the plain-text password against the stored bcrypt hash."""
        if not self.password_hash:
            return False
        try:
            pw_bytes = password.encode('utf-8')
            hash_bytes = self.password_hash.encode('utf-8')
            return bcrypt.checkpw(pw_bytes, hash_bytes)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<User username='{self.username}' role='{self.role}'>"


class UserPreference(Base):
    """User preference database model storing personalized travel profiles."""
    
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True, 
        nullable=False
    )
    
    # Store dynamic lists of favorite items in standard JSON column format
    dietary_goals = Column(JSON, default=list, nullable=False)
    preferred_ingredients = Column(JSON, default=list, nullable=False)
    avoided_ingredients = Column(JSON, default=list, nullable=False)
    cuisine_types = Column(JSON, default=list, nullable=False)
    destinations = Column(JSON, default=list, nullable=False)
    
    updated_at = Column(
        Text, 
        default=lambda: datetime.utcnow().isoformat(),
        onupdate=lambda: datetime.utcnow().isoformat(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id}>"
