"""Declarative base and core helpers for SQLAlchemy models in TravelChatBot.

This module provides the Base class used by all database entities
and helpful serialization mixins.

Author: TravelChatBot Team
Version: 1.0.0
"""
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base, declared_attr

class CustomBase:
    """Custom base helper with automatic table naming and common serializations."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        # Generate table name based on class name in snake_case lowercase
        import re
        name = cls.__name__
        # Convert CamelCase to snake_case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower() + 's'

    def to_dict(self) -> dict:
        """Serializes model attributes into a standard Python dictionary."""
        serialized = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            serialized[col.name] = val
        return serialized

# Declarative Base instance using CustomBase as metadata template
Base = declarative_base(cls=CustomBase)

class TimestampMixin:
    """Mixin to automatically append created_at and updated_at attributes."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
