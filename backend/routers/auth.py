"""Authentication router for TravelChatBot REST API.

This module handles user registration, JWT login authentication,
and self-profile retrieval.

Author: TravelChatBot Team
Version: 1.0.0
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPreference
from backend.auth_utils import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Pydantic Schemas ---

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Minimum 6 characters password")
    email: Optional[EmailStr] = Field(None, description="Optional valid email address")


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user and configures default blank preferences."""
    # Check if username exists
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered."
            )

    try:
        new_user = User(
            username=user_in.username,
            email=user_in.email,
            role="user",
            is_active=True
        )
        new_user.set_password(user_in.password)
        db.add(new_user)
        db.flush() # Populate generated user ID

        # Generate standard default preferences
        prefs = UserPreference(
            user_id=new_user.id,
            dietary_goals=[],
            preferred_ingredients=[],
            avoided_ingredients=[],
            cuisine_types=[],
            destinations=[]
        )
        db.add(prefs)
        
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e}"
        )


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates username/password and issues a secure JWT token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user profile."
        )
        
    # Generate access token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieves profile of the currently logged-in user."""
    return current_user
