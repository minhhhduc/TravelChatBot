"""Pydantic schemas for Lumi Travel AI API v1."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApiUser(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: ApiUser


class VoiceQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    sort_by: Optional[str] = Field(None, pattern="^(time|evaluate_mean|evaluate_count)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class VoiceQueryResponse(BaseModel):
    answer: str
    conversation_id: Optional[str]
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    meta: Dict[str, Any]


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = "vi-default"


class PlannerRequest(BaseModel):
    destination: str
    days: int = Field(ge=1, le=30)
    budget: Optional[str] = None
    interests: List[str] = []
    travelers: int = Field(1, ge=1)


class EvidenceRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)
