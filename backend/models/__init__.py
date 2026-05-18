"""SQLAlchemy models for TravelChatBot.

This module consolidates and exposes all database entities for importing.

Author: TravelChatBot Team
Version: 1.0.0
"""
from .base import Base
from .user import User, UserPreference
from .chat import ChatSession, ChatMessage

__all__ = [
    "Base",
    "User",
    "UserPreference",
    "ChatSession",
    "ChatMessage",
]
