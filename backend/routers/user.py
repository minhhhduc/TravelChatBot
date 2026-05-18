"""User and preferences router for TravelChatBot REST API.

This module provides endpoints to retrieve and update the user's travel profiles
and dietary goals.

Author: TravelChatBot Team
Version: 1.0.0
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPreference
from backend.auth_utils import get_current_user

router = APIRouter(prefix="/user", tags=["User Preferences"])

# --- Pydantic Schemas ---

class UserPreferenceUpdate(BaseModel):
    dietary_goals: Optional[List[str]] = None
    preferred_ingredients: Optional[List[str]] = None
    avoided_ingredients: Optional[List[str]] = None
    cuisine_types: Optional[List[str]] = None
    destinations: Optional[List[str]] = None


class UserPreferenceResponse(BaseModel):
    user_id: int
    dietary_goals: List[str]
    preferred_ingredients: List[str]
    avoided_ingredients: List[str]
    cuisine_types: List[str]
    destinations: List[str]
    updated_at: str

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/preferences", response_model=UserPreferenceResponse)
def get_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieves the active user's personalized travel profile preferences."""
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not prefs:
        # Create default preferences in case they are missing
        prefs = UserPreference(
            user_id=current_user.id,
            dietary_goals=[],
            preferred_ingredients=[],
            avoided_ingredients=[],
            cuisine_types=[],
            destinations=[]
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        
    return prefs


@router.put("/preferences", response_model=UserPreferenceResponse)
def update_preferences(
    prefs_in: UserPreferenceUpdate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Updates the active user's personalized travel profile preferences."""
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)

    # Perform updates if provided
    if prefs_in.dietary_goals is not None:
        prefs.dietary_goals = prefs_in.dietary_goals
    if prefs_in.preferred_ingredients is not None:
        prefs.preferred_ingredients = prefs_in.preferred_ingredients
    if prefs_in.avoided_ingredients is not None:
        prefs.avoided_ingredients = prefs_in.avoided_ingredients
    if prefs_in.cuisine_types is not None:
        prefs.cuisine_types = prefs_in.cuisine_types
    if prefs_in.destinations is not None:
        prefs.destinations = prefs_in.destinations

    prefs.updated_at = datetime.utcnow().isoformat()
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    
    return prefs
